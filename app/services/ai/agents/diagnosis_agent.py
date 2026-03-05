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

            계산 공식:
            1. 최적 수익 = {settlement_data}.generation_kwh * {market_data}.curr_smp
            2. 손실액 = 최적 수익 - {settlement_data}.total_revenue_krw
            3. 예측 오차 개선 가능 금액 = 손실액 * 0.4 (손실액의 40%는 예측 오차 개선으로 회수 가능하다는 추산값)

            분류 기준 (우선순위):
            1. 일조량 원인: {market_data}.curr_irr이 {market_data}.prev_year_irr 대비 10% 이상 낮으면 -> WEATHER
               메시지: "주요 원인은 [월]월 일조량이 평균보다 [N]%% 낮았기 때문이에요."
            2. SMP 원인: {market_data}.curr_smp가 {market_data}.prev_smp 대비 10% 이상 낮으면 -> SMP
               메시지: "주요 원인은 SMP가 전달 대비 [N]%% 하락했기 때문이에요."
            3. 복합 원인: 일조량과 SMP 둘 다 5% 이상 낮으면 -> COMPLEX
               메시지: "일조량 감소([N]%%)와 SMP 하락([N]%%)이 복합적으로 영향을 줬어요."
            4. 원인 불명 -> UNKNOWN
               메시지: "이번달은 특이한 손실 원인이 없어요. 예측 오차를 점검해보세요."

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
                logger.info(f"[{self.name}] 진단 결과: {ctx.session.state.get('analysis_result')}")
            yield event
