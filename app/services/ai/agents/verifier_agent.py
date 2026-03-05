import logging
import time
from google.adk.agents import LlmAgent
from app.schemas.ai.settlement import SettlementOcrData
from app.core.config import settings

logger = logging.getLogger(__name__)

class VerifierAgent(LlmAgent):
    """
    OCR 추출 결과와 시각 분석 결과를 비교 검증하여 최적의 데이터를 선택하는 에이전트입니다.
    """
    def __init__(self):
        super().__init__(
            name="verifier",
            model=settings.GEMINI_MODEL,
            instruction="""
            {settlement_data} (OCR 추출)와 {visual_data} (시각 분석) 결과를 비교하여 가장 정확하다고 판단되는 최종 정산 데이터를 선택하세요. 
            불일치하는 항목이 있다면 논리적으로 더 타당한 쪽을 선택하고, 선택 이유를 로그로 남길 수 있게 하세요.
            최종 결과는 반드시 SettlementOcrData 스키마를 따라야 합니다.
            """,
            output_schema=SettlementOcrData,
            output_key="settlement_data"
        )
        logger.info(f"[{self.name}] 에이전트가 초기화되었습니다.")

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] 데이터 검증 및 최종 선택 시작")
        
        async for event in super()._run_async_impl(ctx):
            if not event.partial:
                duration = time.perf_counter() - start_t
                logger.info(f"[{self.name}] 데이터 검증 완료 (소요시간: {duration:.2f}초)")
            yield event
