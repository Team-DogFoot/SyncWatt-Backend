import logging
import time
from google.adk.agents import LlmAgent
from app.schemas.ai.settlement import SettlementOcrData
from app.core.config import settings

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
            입력받은 OCR 텍스트에서 정산 정보를 추출하여 정형화된 데이터로 변환하세요.
            반드시 다음 필드를 포함해야 합니다:
            - 정산 연월 (YYYY-MM 형식)
            - 실제 발전량 (kWh)
            - 실제 총 수령액 (원)
            - 발전소 주소 (문서에 있는 경우만, 없으면 null)
            
            필요시 세션의 {raw_text}를 참조할 수 있습니다.
            """,
            output_schema=SettlementOcrData,
            output_key="settlement_data"
        )
        logger.info(f"[{self.name}] 에이전트가 초기화되었습니다.")

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] OCR 데이터 정제 시작")
        
        async for event in super()._run_async_impl(ctx):
            if not event.partial:
                duration = time.perf_counter() - start_t
                logger.info(f"[{self.name}] 데이터 정제 완료 (소요시간: {duration:.2f}초)")
                logger.info(f"[{self.name}] 정제된 데이터: {ctx.session.state.get('settlement_data')}")
            yield event
