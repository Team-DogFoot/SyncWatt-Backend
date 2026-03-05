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
            - 정산 연월 (YYYY-MM 형식. 만약 텍스트에 '2019'가 있다면 반드시 2019로 추출하세요. 절대 현재 연도로 추측하지 마세요.)
            - 실제 발전량 (kWh 단위 숫자만)
            - 정산 기준 단가 (원/kWh 단위 숫자만, '기준단가' 또는 '단가' 항목 확인)
            - 실제 총 수령액 (공급가액 기준으로 추출하세요. 부가세나 합계 금액과 혼동하지 마세요. 숫자만 추출)
            - 발전소 주소 (문서에 있는 경우만, 없으면 null)
            
            추출 팁:
            - '공급가액' 항목의 숫자가 실제 총 수령액입니다.
            - '발전량' 또는 '당월발전량' 항목의 숫자가 실제 발전량입니다.
            - '기준단가' 또는 '단가' 항목의 숫자가 정산 기준 단가입니다.
            """,
            output_schema=SettlementOcrData,
            output_key="settlement_data"
        )
        logger.info(f"[{self.name}] 에이전트가 초기화되었습니다.")

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        raw_text = ctx.session.state.get("raw_text", "")
        logger.info(f"[{self.name}] OCR 데이터 정제 시작 (입력 텍스트 길이: {len(raw_text)})")
        
        # 입력 텍스트 로그 출력 (디버깅용)
        logger.debug(f"[{self.name}] Raw text for refining: {raw_text[:500]}...")
        
        async for event in super()._run_async_impl(ctx):
            if not event.partial:
                duration = time.perf_counter() - start_t
                logger.info(f"[{self.name}] 데이터 정제 완료 (소요시간: {duration:.2f}초)")
                
                refined_data = ctx.session.state.get("settlement_data")
                if refined_data:
                    logger.info(f"[{self.name}] 정제된 데이터: {refined_data.model_dump()}")
                else:
                    logger.error(f"[{self.name}] 데이터 정제 실패: 결과가 None입니다.")
            yield event
