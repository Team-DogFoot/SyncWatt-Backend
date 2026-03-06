"""
통합 테스트: 실제 정산서 이미지로 AI 파이프라인 전체를 실행합니다.

실행 방법:
    pytest tests/test_pipeline_integration.py -v -s

필수 환경변수:
    - GOOGLE_API_KEY: Gemini API 키
    - GCP_SA_KEY 또는 GOOGLE_APPLICATION_CREDENTIALS: Cloud Vision OCR용 (없으면 OCR 경로 스킵)

주의:
    - 실제 Gemini API를 호출하므로 비용이 발생할 수 있습니다.
    - SMP DB가 없으면 SMP 조회가 실패하여 진단이 제한됩니다.
      이 테스트에서는 SMP를 mock하여 파이프라인 전체 흐름을 검증합니다.
"""

import logging
import pathlib
import pytest
from unittest.mock import patch

from google.adk.runners import InMemoryRunner
from google.genai import types

from app.services.ai.pipeline import pipeline as global_pipeline
from app.schemas.ai.settlement import SettlementOcrData
from app.schemas.ai.diagnosis import DiagnosisResult, LossCause

logger = logging.getLogger(__name__)

FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures"
SAMPLE_IMAGE = FIXTURE_DIR / "sample_settlement.png"

# 이 정산서의 기대값 (이미지에서 읽을 수 있는 정보)
EXPECTED = {
    "year_month": "2019-12",
    "generation_kwh": 6600.0,
    "unit_price": 84.13,
    "total_revenue_krw": 555258,
}


@pytest.fixture
def image_bytes():
    assert SAMPLE_IMAGE.exists(), f"테스트 이미지가 없습니다: {SAMPLE_IMAGE}"
    return SAMPLE_IMAGE.read_bytes()


@pytest.fixture
def mock_smp():
    """SMP DB 의존성을 mock하여 테스트용 SMP 값을 반환합니다."""
    def fake_get_avg_smp(year_month: str):
        smp_map = {
            "2019-12": 110.38,
            "2019-11": 115.50,
        }
        return smp_map.get(year_month)

    with patch("app.services.external.smp_service.smp_service.get_avg_smp", side_effect=fake_get_avg_smp):
        yield


@pytest.fixture
def mock_kma():
    """KMA API 의존성을 mock하여 테스트용 일조량 값을 반환합니다."""
    from app.schemas.external import KMAMonthlyIrradianceResponse

    async def fake_irradiance(year, month, stn_id="108"):
        irr_map = {
            (2019, 12): 9.8,
            (2018, 12): 11.2,
        }
        avg = irr_map.get((year, month), 15.5)
        return KMAMonthlyIrradianceResponse(
            year=year, month=month, avg_irradiance=avg,
            unit="MJ/m²", stn_id=stn_id, stn_name="TEST"
        )

    with patch(
        "app.services.external.kma_service.kma_service.get_monthly_avg_irradiance",
        side_effect=fake_irradiance,
    ):
        yield


@pytest.mark.asyncio
async def test_full_pipeline_with_sample_image(image_bytes, mock_smp, mock_kma):
    """
    실제 정산서 이미지 → ParallelAgent(OCR+Vision) → CodeVerifier → DataFetcher → Diagnosis
    전체 파이프라인을 실행하고 최종 analysis_result를 검증합니다.
    """
    runner = InMemoryRunner(agent=global_pipeline)
    runner.auto_create_session = True

    user_id = "test_user"
    session_id = "test_integration_001"

    initial_state = {
        "image_bytes": image_bytes,
        "raw_text": None,
        "settlement_data": None,
        "visual_data": None,
        "market_data": None,
        "diagnosis_calc": None,
        "analysis_result": None,
    }

    logger.info("=" * 60)
    logger.info("통합 테스트: 파이프라인 실행 시작")
    logger.info("=" * 60)

    events = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        state_delta=initial_state,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text="정산서 분석 시작")],
        ),
    ):
        events.append(event)
        if event.content and event.content.parts:
            text_parts = [p.text for p in event.content.parts if hasattr(p, "text") and p.text]
            if text_parts:
                logger.info(f"[Event] {event.author}: {' '.join(text_parts)}")

    # 세션에서 최종 결과 추출
    session = await runner.session_service.get_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    state = session.state

    # ── 1. settlement_data 검증 (OCR 또는 Vision 중 하나가 추출해야 함) ──
    settlement_data = state.get("settlement_data")
    logger.info(f"[검증] settlement_data: {settlement_data}")
    assert settlement_data is not None, "settlement_data가 None입니다. OCR/Vision 모두 실패."

    if isinstance(settlement_data, SettlementOcrData):
        sd = settlement_data
    else:
        sd = SettlementOcrData.model_validate(settlement_data)

    assert sd.year_month == EXPECTED["year_month"], (
        f"연월 불일치: {sd.year_month} != {EXPECTED['year_month']}"
    )
    # 발전량: 6600 kWh (허용 오차 ±100)
    assert abs(sd.generation_kwh - EXPECTED["generation_kwh"]) < 100, (
        f"발전량 불일치: {sd.generation_kwh} (기대: {EXPECTED['generation_kwh']})"
    )
    # 총 수령액: 555,258원 (허용 오차 ±5000)
    assert abs(sd.total_revenue_krw - EXPECTED["total_revenue_krw"]) < 5000, (
        f"총 수령액 불일치: {sd.total_revenue_krw} (기대: {EXPECTED['total_revenue_krw']})"
    )
    logger.info(f"[검증] settlement_data 통과: {sd.year_month}, {sd.generation_kwh}kWh, {sd.total_revenue_krw}원")

    # ── 2. visual_data 검증 (DirectVisionAgent 결과) ──
    visual_data = state.get("visual_data")
    logger.info(f"[검증] visual_data: {visual_data}")
    assert visual_data is not None, "visual_data가 None입니다. DirectVisionAgent가 이미지를 받지 못했을 수 있습니다."

    # ── 3. market_data 검증 ──
    market_data = state.get("market_data")
    logger.info(f"[검증] market_data: {market_data}")
    assert market_data is not None, "market_data가 None입니다."
    assert market_data.get("curr_smp") == 110.38
    assert market_data.get("prev_smp") == 115.50
    # KMA mock 값 확인 (두 값이 서로 달라야 함)
    assert market_data.get("curr_irr") != market_data.get("prev_year_irr"), (
        "curr_irr과 prev_year_irr이 같습니다. KMA 데이터가 default fallback으로 빠진 것 같습니다."
    )
    logger.info(
        f"[검증] market_data 통과: SMP({market_data['curr_smp']} vs {market_data['prev_smp']}), "
        f"Irr({market_data['curr_irr']} vs {market_data['prev_year_irr']})"
    )

    # ── 4. diagnosis_calc 검증 (Python 계산 결과) ──
    calc = state.get("diagnosis_calc")
    logger.info(f"[검증] diagnosis_calc: {calc}")
    assert calc is not None, "diagnosis_calc이 None입니다."
    assert calc["cause"] in ("WEATHER", "SMP", "COMPLEX", "UNKNOWN")
    # 최적수익 = 6600 * 110.38 ≈ 728,508
    assert calc["optimal_revenue"] > 0
    assert isinstance(calc["loss"], (int, float))
    logger.info(
        f"[검증] diagnosis_calc 통과: optimal={calc['optimal_revenue']}, "
        f"loss={calc['loss']}, cause={calc['cause']}"
    )

    # ── 5. analysis_result 검증 (최종 DiagnosisResult) ──
    analysis_result = state.get("analysis_result")
    logger.info(f"[검증] analysis_result: {analysis_result}")
    assert analysis_result is not None, "analysis_result가 None입니다."

    if isinstance(analysis_result, DiagnosisResult):
        ar = analysis_result
    else:
        ar = DiagnosisResult.model_validate(analysis_result)

    assert ar.year_month == "2019-12"
    assert ar.actual_revenue_krw == sd.total_revenue_krw
    assert ar.optimal_revenue_krw > 0
    assert ar.one_line_message, "one_line_message가 비어있습니다."
    assert ar.loss_cause in LossCause
    logger.info(
        f"[검증] analysis_result 통과: "
        f"loss={ar.opportunity_loss_krw}, cause={ar.loss_cause.value}, "
        f"message='{ar.one_line_message}'"
    )

    # ── 6. DB 저장은 이 테스트에서는 검증하지 않음 (telegram_service 레벨) ──
    logger.info("=" * 60)
    logger.info("통합 테스트 전체 통과!")
    logger.info("=" * 60)


@pytest.mark.asyncio
async def test_pipeline_ocr_path_extracts_text(image_bytes):
    """
    OCR 경로만 별도 검증: VisionAgent가 raw_text를 추출하는지 확인합니다.
    GCP Vision API 키가 없으면 스킵합니다.
    """
    from app.core.config import settings
    if not settings.GCP_SA_KEY and not settings.GOOGLE_APPLICATION_CREDENTIALS:
        pytest.skip("GCP Vision 자격 증명이 없어 OCR 테스트를 건너뜁니다.")

    from google.adk.agents import SequentialAgent
    from app.services.ai.agents.vision_agent import VisionAgent
    from app.services.ai.agents.ocr_agent import OcrRefinerAgent

    # 새 인스턴스 생성 (ADK는 에이전트가 하나의 parent만 허용)
    ocr_path = SequentialAgent(
        name="test_ocr_path",
        sub_agents=[VisionAgent(), OcrRefinerAgent()],
    )

    runner = InMemoryRunner(agent=ocr_path)
    runner.auto_create_session = True

    async for event in runner.run_async(
        user_id="test",
        session_id="test_ocr_001",
        state_delta={"image_bytes": image_bytes},
        new_message=types.Content(role="user", parts=[types.Part(text="OCR 시작")]),
    ):
        pass

    session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id="test", session_id="test_ocr_001"
    )

    raw_text = session.state.get("raw_text", "")
    assert len(raw_text) > 50, f"OCR 추출 텍스트가 너무 짧습니다: {len(raw_text)}자"
    assert "555258" in raw_text or "공급가액" in raw_text, (
        f"OCR 텍스트에 핵심 정보가 없습니다: {raw_text[:200]}"
    )
    logger.info(f"[OCR 검증] raw_text 길이: {len(raw_text)}, 앞 200자: {raw_text[:200]}")

    settlement = session.state.get("settlement_data")
    assert settlement is not None, "OcrRefinerAgent가 settlement_data를 생성하지 못했습니다."
    logger.info(f"[OCR 검증] settlement_data: {settlement}")
