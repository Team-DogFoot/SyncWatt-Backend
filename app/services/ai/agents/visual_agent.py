import logging
import time
from google.adk.agents import LlmAgent
from app.schemas.ai.settlement import SettlementOcrData
from app.core.config import settings

logger = logging.getLogger(__name__)

class DirectVisionAgent(LlmAgent):
    """
    이미지를 직접 분석하여 정산 데이터를 추출하는 에이전트입니다.
    """
    def __init__(self):
        super().__init__(
            name="direct_vision",
            model=settings.GEMINI_MODEL,
            instruction="""
            이 이미지는 태양광 발전소 정산서입니다. 
            이미지를 직접 보고 정산 연월, 실제 발전량, 실제 총 수령액을 추출하세요. 
            출력은 SettlementOcrData 스키마를 따르세요.
            """,
            output_schema=SettlementOcrData,
            output_key="visual_data"
        )
        logger.info(f"[{self.name}] 에이전트가 초기화되었습니다.")

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] 이미지 직접 시각 분석 시작")
        
        # ADK LlmAgent의 기본 구현을 호출합니다.
        # LlmAgent는 세션 상태의 image_bytes 등을 활용하여 멀티모달 추론을 수행할 수 있다고 가정합니다.
        async for event in super()._run_async_impl(ctx):
            if not event.partial:
                duration = time.perf_counter() - start_t
                logger.info(f"[{self.name}] 시각 분석 완료 (소요시간: {duration:.2f}초)")
            yield event
