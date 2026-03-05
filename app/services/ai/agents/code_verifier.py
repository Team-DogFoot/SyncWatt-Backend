import logging
import time
from google.adk.agents import BaseAgent
from app.schemas.ai.settlement import SettlementOcrData
from app.services.ai.utils import create_text_event

logger = logging.getLogger(__name__)

class CodeVerifierAgent(BaseAgent):
    """
    Python 코드를 사용하여 OCR 추출 결과와 시각 분석 결과를 수치적으로 검증하고 
    최적의 데이터를 선택하는 에이전트입니다.
    """
    def __init__(self):
        super().__init__(
            name="code_verifier",
            description="Verifies and selects the best settlement data using Python logic."
        )

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] 코드 기반 데이터 검증 시작")

        ocr_data_dict = ctx.session.state.get("settlement_data")
        visual_data_dict = ctx.session.state.get("visual_data")

        # 딕셔너리 또는 Pydantic 객체 대응
        ocr = self._to_model(ocr_data_dict)
        visual = self._to_model(visual_data_dict)

        logger.info(f"[{self.name}] OCR Data: {ocr}")
        logger.info(f"[{self.name}] Visual Data: {visual}")

        # 필드별 차이점 비교 로그 추가
        if ocr and visual:
            diffs = []
            if ocr.year_month != visual.year_month: diffs.append(f"year_month ({ocr.year_month} vs {visual.year_month})")
            if ocr.generation_kwh != visual.generation_kwh: diffs.append(f"generation_kwh ({ocr.generation_kwh} vs {visual.generation_kwh})")
            if ocr.total_revenue_krw != visual.total_revenue_krw: diffs.append(f"total_revenue_krw ({ocr.total_revenue_krw} vs {visual.total_revenue_krw})")
            if diffs:
                logger.info(f"[{self.name}] [Data Discrepancy Found]: {', '.join(diffs)}")
            else:
                logger.info(f"[{self.name}] [Data Match]: OCR and Visual results are identical.")

        final_choice = None
        reason = ""

        if not ocr and not visual:
            reason = "둘 다 데이터를 추출하지 못했습니다."
        elif ocr and not visual:
            final_choice = ocr
            reason = "시각 분석 결과가 없어 OCR 결과를 채택했습니다."
        elif visual and not ocr:
            final_choice = visual
            reason = "OCR 결과가 없어 시각 분석 결과를 채택했습니다."
        else:
            # 둘 다 있는 경우 수치 정합성 체크
            ocr_valid = self._check_integrity(ocr)
            visual_valid = self._check_integrity(visual)

            if ocr_valid and not visual_valid:
                final_choice = ocr
                reason = "수치 정합성이 맞는 OCR 결과를 채택했습니다."
            elif visual_valid and not ocr_valid:
                final_choice = visual
                reason = "수치 정합성이 맞는 시각 분석 결과를 채택했습니다."
            elif ocr == visual:
                final_choice = ocr
                reason = "두 결과가 일치하여 채택했습니다."
            else:
                # 둘 다 정합성이 맞거나 둘 다 틀린 경우 -> 공급가액이 더 큰(또는 존재하는) OCR 우선 (기본 전략)
                final_choice = ocr
                reason = "두 결과가 다르지만 OCR 결과를 기본으로 채택했습니다 (정밀 검정 필요)."

        if final_choice:
            final_choice.selection_reason = reason
            logger.info(f"[{self.name}] 최종 선택: {final_choice.model_dump()}, 사유: {reason}")
            
            yield create_text_event(
                self.name,
                f"데이터 검증 완료: {reason}",
                state_delta={"settlement_data": final_choice}
            )
        else:
            logger.error(f"[{self.name}] 검증 실패: 유효한 데이터를 찾을 수 없습니다.")
            yield create_text_event(self.name, "데이터 검증 중 오류가 발생했습니다. 유효한 정보를 찾을 수 없습니다.")

        duration = time.perf_counter() - start_t
        logger.info(f"[{self.name}] 검증 완료 (소요시간: {duration:.2f}초)")

    def _to_model(self, data):
        if not data:
            return None
        try:
            if isinstance(data, SettlementOcrData):
                return data
            return SettlementOcrData.model_validate(data)
        except Exception:
            return None

    def _check_integrity(self, data: SettlementOcrData) -> bool:
        """
        단가 * 발전량 ≈ 총 수령액(공급가액) 인지 확인합니다.
        오차 범위 1000원 이내면 정상으로 판단합니다.
        """
        if not data.unit_price or not data.generation_kwh or not data.total_revenue_krw:
            logger.info(f"[{self.name}] [Integrity Check Skip]: Missing required fields for calculation.")
            return False
        
        expected_revenue = data.unit_price * data.generation_kwh
        diff = abs(expected_revenue - data.total_revenue_krw)
        
        is_valid = diff < 1000
        logger.info(f"[{self.name}] [Integrity Check]: {data.unit_price} (Price) * {data.generation_kwh} (Gen) = {expected_revenue:.0f} (Expected) vs {data.total_revenue_krw} (Actual). Diff: {diff:.0f} -> Valid: {is_valid}")
        return is_valid
