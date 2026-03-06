import logging
import time
from google.adk.agents import LlmAgent
from app.schemas.ai.settlement import SettlementOcrData
from app.core.config import settings
from app.services.ai.state_keys import RAW_TEXT, SETTLEMENT_DATA

logger = logging.getLogger(__name__)


class OcrRefinerAgent(LlmAgent):
    """
    OCR로 추출된 가공되지 않은 텍스트에서 정형화된 정산 데이터를 추출하는 에이전트입니다.
    """
    def __init__(self):
        super().__init__(
            name="ocr_refiner",
            model=settings.GEMINI_MODEL,
            instruction="""
            다음의 OCR 텍스트를 분석하여 정산 정보를 추출하고 정형화된 데이터로 변환하세요.
            ---
            OCR 텍스트:
            {raw_text}
            ---
            반드시 다음 필드를 포함해야 합니다:
            - 정산 연월 (YYYY-MM 형식. 만약 텍스트에 '2019'가 있다면 반드시 2019로 추출하세요. 절대 현재 연도로 추측하지 마세요.)
            - 실제 발전량 (kWh 단위 숫자만)
            - 정산 기준 단가 (원/kWh 단위 숫자만, '기준단가' 또는 '단가' 항목 확인)
            - 실제 총 수령액 (공급가액 기준으로 추출하세요. 부가세나 합계 금액과 혼동하지 마세요. 숫자만 추출)
            - 발전소 설비용량 (kW 단위, '용량' 항목 확인. 없으면 null)
            - 발전소 주소 (문서에 있는 경우만, 없으면 null)
            - 정산서 발행처 (문서에서 발행 기관명을 추출하세요. 예: '한국전력공사', '한국수력원자력', 'KPX', '해줌' 등. 보낸사람이나 문서 제목에서 확인. 없으면 null)

            추출 팁:
            - '공급가액' 항목의 숫자가 실제 총 수령액입니다.
            - '발전량' 또는 '당월발전량' 항목의 숫자가 실제 발전량입니다.
            - '기준단가' 또는 '단가' 항목의 숫자가 정산 기준 단가입니다.
            - '용량' 항목의 숫자가 설비용량입니다. (예: "용 량 : 99 kWh" -> 99)

            중요: 텍스트에 보이는 숫자를 있는 그대로 추출하세요. 직접 계산하거나 보정하지 마세요.
            """,
            output_schema=SettlementOcrData,
            output_key="settlement_data"
        )
        logger.info(f"[{self.name}] Agent initialized")

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        raw_text = ctx.session.state.get(RAW_TEXT, "")
        logger.info(f"[{self.name}] Starting OCR data refinement (input text length: {len(raw_text)})")

        if not raw_text:
            logger.error(f"[{self.name}] raw_text is empty. LLM refinement not possible.")
            return

        # ADK LlmAgent는 instruction의 {{raw_text}} 를 session.state["raw_text"]로 자동 치환
        logger.info(f"[{self.name}] raw_text first 200 chars for LLM: {raw_text[:200]}")

        async for event in super()._run_async_impl(ctx):
            if not event.partial:
                duration = time.perf_counter() - start_t
                logger.info(f"[{self.name}] Data refinement process complete ({duration:.2f}s)")

                refined_data = event.actions.state_delta.get(SETTLEMENT_DATA)
                if refined_data:
                    logger.info(f"[{self.name}] [Result]: {refined_data}")
                else:
                    logger.warning(f"[{self.name}] settlement_data not in state_delta (check after runner applies)")
            yield event
