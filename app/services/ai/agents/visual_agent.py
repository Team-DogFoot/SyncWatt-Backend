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
            이미지를 직접 보고 다음 정보를 정확하게 추출하세요:
            - 정산 연월 (YYYY-MM 형식. 이미지에 '2019'가 있다면 반드시 2019로 추출하세요. 절대 현재 연도로 추측하지 마세요.)
            - 실제 발전량 (kWh 단위, '발전량' 항목 확인)
            - 정산 기준 단가 (원/kWh 단위, '기준단가' 또는 '단가' 항목 확인)
            - 실제 총 수령액 (원 단위, 반드시 '공급가액' 항목을 추출하세요. 부가세 포함 금액과 혼동 주의)
            
            출력은 SettlementOcrData 스키마를 따르세요.
            """,
            output_schema=SettlementOcrData,
            output_key="visual_data"
        )
        logger.info(f"[{self.name}] 에이전트가 초기화되었습니다.")

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] 이미지 직접 시각 분석 시작")
        
        async for event in super()._run_async_impl(ctx):
            if not event.partial:
                duration = time.perf_counter() - start_t
                logger.info(f"[{self.name}] 시각 분석 완료 (소요시간: {duration:.2f}초)")
                
                visual_data = ctx.session.state.get("visual_data")
                if visual_data:
                    logger.info(f"[{self.name}] 추출된 시각 데이터: {visual_data.model_dump()}")
                else:
                    logger.error(f"[{self.name}] 시각 분석 실패: 결과가 None입니다.")
            yield event
