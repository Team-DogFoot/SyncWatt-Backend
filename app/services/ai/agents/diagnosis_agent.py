import logging
import time
from google.adk.agents import LlmAgent
from app.schemas.ai.diagnosis import DiagnosisResult
from app.core.config import settings
from app.services.ai.utils import create_text_event

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

            지침:
            - 수익 분석 관점: 이 진단은 "만약 KPX(전력거래소) 시장가로 정산받았다면?"을 가정하여 소장님의 기회 수익을 분석하는 것입니다.
            - 실제 수령액(공급가액)은 {settlement_data}의 total_revenue_krw를 사용하세요.
            - 최적 수익 = {settlement_data}.generation_kwh * {market_data}.curr_smp
            - 손실액 = 최적 수익 - {settlement_data}.total_revenue_krw
            - 손실액이 양수(+)면 "KPX로 전환 시 얻을 수 있었던 기회 수익"으로, 음수(-)면 "현재 한전 계약이 시장가보다 유리함"으로 해석합니다.

            분류 기준 (우선순위):
            1. 일조량 원인: {market_data}.curr_irr이 {market_data}.prev_year_irr 대비 10% 이상 낮으면 -> WEATHER
               메시지: "주요 원인은 [월]월 일조량이 평균보다 [N]%% 낮았기 때문이에요."
            2. SMP 원인: {market_data}.curr_smp가 {market_data}.prev_smp 대비 10% 이상 낮으면 -> SMP
               메시지: "주요 원인은 SMP 시장가가 전달 대비 [N]%% 하락했기 때문이에요."
            3. 복합 원인: 일조량과 SMP 둘 다 5% 이상 낮으면 -> COMPLEX
               메시지: "일조량 감소([N]%%)와 SMP 하락([N]%%)이 복합적으로 영향을 줬어요."
            4. 원인 불명 -> UNKNOWN
               메시지: "현재 소장님의 정산 방식은 시장가 변동과 무관한 고정 단가 방식일 수 있습니다."

            모든 출력은 DiagnosisResult 스키마 형식을 엄격히 준수해야 하며, JSON 형식으로만 응답하세요. 다른 부가 설명은 생략하세요.
            """,
            output_schema=DiagnosisResult,
            output_key="analysis_result"
        )
        logger.info(f"[{self.name}] 에이전트가 초기화되었습니다.")

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        settlement_data = ctx.session.state.get("settlement_data")
        market_data = ctx.session.state.get("market_data")
        
        logger.info(f"[{self.name}] 수익 손실 최종 진단 시작")
        
        # market_data가 없거나 비어있는 경우(KeyError 방지용 빈 객체 포함)
        if not market_data or market_data.get("curr_smp") == 0:
            logger.warning(f"[{self.name}] 필수 시장 데이터 누락으로 분석을 진행할 수 없습니다.")
            # 진단 불가 결과 수동 생성
            from app.schemas.ai.diagnosis import DiagnosisResult, LossCause
            
            error_result = DiagnosisResult(
                year_month=settlement_data.year_month if settlement_data else "UNKNOWN",
                actual_revenue_krw=settlement_data.total_revenue_krw if settlement_data else 0,
                optimal_revenue_krw=0,
                opportunity_loss_krw=0,
                loss_cause=LossCause.UNKNOWN,
                one_line_message="시장 가격(SMP) 데이터가 부족하여 진단을 수행할 수 없습니다.",
                address_used=True if settlement_data and settlement_data.address else False
            )
            
            yield create_text_event(
                self.name,
                "데이터 부족으로 인한 진단 실패",
                state_delta={"analysis_result": error_result}
            )
            return

        async for event in super()._run_async_impl(ctx):
            if not event.partial:
                duration = time.perf_counter() - start_t
                logger.info(f"[{self.name}] 최종 진단 프로세스 완료 (소요시간: {duration:.2f}초)")
            yield event
