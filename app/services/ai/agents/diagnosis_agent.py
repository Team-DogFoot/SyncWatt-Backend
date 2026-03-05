import logging
import time
from google.adk.agents import LlmAgent
from app.schemas.ai.diagnosis import DiagnosisResult
from app.core.config import settings

logger = logging.getLogger(__name__)

class DiagnosisAgent(LlmAgent):
    """
    정산 데이터와 외부 시장 데이터를 분석하여 최종적인 기회 손실액과 원인을 진단하는 에이전트입니다.
    """
    def __init__(self):
        super().__init__(
            name="diagnoser",
            model=settings.GEMINI_MODEL,
            instruction="""
            입력받은 정산 데이터 {settlement_data}와 외부 시장 데이터 {market_data}를 분석하여 수익 손실 진단을 수행하세요.

            분석 지침:
            1. 최적 수익 계산: 해당 월의 기상 기반 최적 발전량, 최적 SMP 단가, 예측 인센티브를 고려하여 소장님이 얻을 수 있었던 최대 수익을 계산합니다.
            2. 기회 비용(손실액) 계산: (최적 수익) - {settlement_data}의 실제 수령액
            3. 원인 분류: 날씨(weather), 예측 오류(prediction_error), 시장 가격(market_price), 복합(mixed) 중 가장 적절한 것을 선택하세요.
            4. 메시지 생성: 소장님께 드릴 따뜻하지만 정확한 한 줄 메시지를 생성하세요.
               예시: "날씨: 이번달 손실 38만원. 일조량이 평균보다 18% 낮았어요."

            모든 출력은 DiagnosisResult 스키마 형식을 엄격히 준수해야 합니다.
            """,
            output_schema=DiagnosisResult,
            output_key="analysis_result"
        )
        logger.info(f"[{self.name}] 에이전트가 초기화되었습니다.")

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] 수익 손실 최종 진단 시작")
        
        async for event in super()._run_async_impl(ctx):
            if not event.partial:
                duration = time.perf_counter() - start_t
                logger.info(f"[{self.name}] 최종 진단 완료 (소요시간: {duration:.2f}초)")
            yield event
