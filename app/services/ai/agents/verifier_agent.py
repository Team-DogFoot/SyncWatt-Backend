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

            검증 기준:
            1. 수치 정합성: (추출된 총 수령액)이 (추출된 발전량 * 예상 단가)와 논리적으로 일치하는지 확인하세요. 
            2. 두 경로의 값이 다를 경우, 정산서의 '공급가액' 항목을 더 정확하게 반영한 쪽을 선택하세요.
            3. 연도 검증: 2019년 또는 2023년 등 문서에 명시된 연도가 현재 연도로 오파싱되지 않았는지 최우선으로 확인하세요.

            최종 결과는 반드시 SettlementOcrData 스키마를 따라야 하며, 선택 이유를 'selection_reason' 필드(로그용)에 간략히 기술하세요.
            """,
            output_schema=SettlementOcrData,
            output_key="settlement_data"
        )
        logger.info(f"[{self.name}] 에이전트가 초기화되었습니다.")

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] 데이터 검증 및 최종 선택 시작")
        
        ocr_data = ctx.session.state.get("settlement_data")
        visual_data = ctx.session.state.get("visual_data")
        logger.info(f"[{self.name}] OCR Data: {ocr_data}")
        logger.info(f"[{self.name}] Visual Data: {visual_data}")
        
        async for event in super()._run_async_impl(ctx):
            if not event.partial:
                duration = time.perf_counter() - start_t
                logger.info(f"[{self.name}] 데이터 검증 완료 (소요시간: {duration:.2f}초)")
                
                final_data = ctx.session.state.get("settlement_data")
                if final_data:
                    logger.info(f"[{self.name}] 최종 선택된 데이터: {final_data.model_dump()}")
                else:
                    logger.error(f"[{self.name}] 데이터 검증 실패: 결과가 None입니다.")
            yield event
