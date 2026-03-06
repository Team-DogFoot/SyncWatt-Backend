import logging
import time
from google.adk.agents import LlmAgent, BaseAgent
from app.schemas.ai.diagnosis import DiagnosisResult, LossCause
from app.core.config import settings
from app.services.ai.utils import create_text_event
from app.services.ai.diagnosis_service import calculate_and_diagnose

logger = logging.getLogger(__name__)


class DiagnosisCalculatorAgent(BaseAgent):
    """
    순수 Python 로직으로 진단 계산을 수행하고 결과를 세션에 저장하는 에이전트입니다.
    """
    def __init__(self):
        super().__init__(
            name="diagnosis_calculator",
            description="Python 로직으로 손실 진단 계산을 수행합니다."
        )

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] 진단 계산 시작")

        settlement_data = ctx.session.state.get("settlement_data")
        market_data = ctx.session.state.get("market_data")

        if not settlement_data:
            logger.error(f"[{self.name}] settlement_data 누락")
            yield create_text_event(self.name, "정산 데이터가 없어 진단 불가.")
            return

        if not market_data or market_data.get("error_smp") or market_data.get("curr_smp") is None:
            logger.warning(f"[{self.name}] 필수 시장 데이터 누락 (error_smp={market_data.get('error_smp') if market_data else 'N/A'})")
            error_result = DiagnosisResult(
                year_month=settlement_data.year_month,
                actual_revenue_krw=settlement_data.total_revenue_krw,
                optimal_revenue_krw=0,
                opportunity_loss_krw=0,
                potential_recovery_krw=0,
                loss_cause=LossCause.UNKNOWN,
                one_line_message="시장 가격(SMP) 데이터가 부족하여 진단을 수행할 수 없습니다.",
                address_used=bool(settlement_data.address),
            )
            yield create_text_event(
                self.name,
                "데이터 부족으로 인한 진단 실패",
                state_delta={"analysis_result": error_result},
            )
            return

        calc = calculate_and_diagnose(settlement_data, market_data)

        # 세션에 계산 결과 저장 (DiagnosisAgent가 참조)
        ctx.session.state["diagnosis_calc"] = calc

        duration = time.perf_counter() - start_t
        logger.info(f"[{self.name}] 진단 계산 완료 (소요시간: {duration:.2f}초)")

        yield create_text_event(
            self.name,
            f"진단 계산 완료: cause={calc['cause']}, loss={calc['loss']}",
            state_delta={"diagnosis_calc": calc},
        )


class DiagnosisAgent(LlmAgent):
    """
    진단 계산 결과를 바탕으로 소장님용 한 줄 메시지만 생성하는 에이전트입니다.
    """
    def __init__(self):
        super().__init__(
            name="diagnoser",
            model=settings.GEMINI_MODEL,
            instruction="""
            아래 진단 결과를 바탕으로 소장님께 전달할 친근한 한 줄 메시지를 생성하세요.

            입력:
            - 원인 코드: {cause} (WEATHER / SMP / COMPLEX / UNKNOWN 중 하나)
            - 일조량 변화율: {irr_diff_pct}%
            - SMP 변화율: {smp_diff_pct}%

            원인별 메시지 형식:
            - WEATHER: "주요 원인은 이번달 일조량이 평균보다 {irr_diff_pct의 절댓값}% 낮았기 때문이에요."
            - SMP: "주요 원인은 SMP 시장가가 전달 대비 {smp_diff_pct의 절댓값}% 하락했기 때문이에요."
            - COMPLEX: "일조량 감소({irr_diff_pct의 절댓값}%)와 SMP 하락({smp_diff_pct의 절댓값}%)이 복합적으로 영향을 줬어요."
            - UNKNOWN: "이번달은 특이한 손실 원인이 없어요. 예측 오차를 점검해보세요."

            출력: one_line_message 필드만 포함한 JSON
            예: {"one_line_message": "주요 원인은 ..."}
            """,
            output_key="diagnosis_message",
        )
        logger.info(f"[{self.name}] 에이전트가 초기화되었습니다.")

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] 메시지 생성 시작")

        calc = ctx.session.state.get("diagnosis_calc")
        if not calc:
            logger.error(f"[{self.name}] diagnosis_calc이 세션에 없습니다.")
            return

        # analysis_result가 이미 있으면 (에러 케이스) 스킵
        if ctx.session.state.get("analysis_result"):
            logger.info(f"[{self.name}] analysis_result가 이미 존재. 메시지 생성 스킵.")
            return

        settlement_data = ctx.session.state.get("settlement_data")

        # LLM 프롬프트에 사용될 변수를 세션 state에 주입
        ctx.session.state["cause"] = calc["cause"]
        ctx.session.state["irr_diff_pct"] = calc["irr_diff_pct"]
        ctx.session.state["smp_diff_pct"] = calc["smp_diff_pct"]

        async for event in super()._run_async_impl(ctx):
            if not event.partial:
                duration = time.perf_counter() - start_t
                logger.info(f"[{self.name}] 메시지 생성 완료 (소요시간: {duration:.2f}초)")

                # LLM 생성 메시지 추출
                diagnosis_msg = ctx.session.state.get("diagnosis_message")
                one_line = ""
                if isinstance(diagnosis_msg, dict):
                    one_line = diagnosis_msg.get("one_line_message", "")
                elif isinstance(diagnosis_msg, str):
                    one_line = diagnosis_msg
                else:
                    one_line = str(diagnosis_msg) if diagnosis_msg else ""

                if not one_line:
                    # fallback: Python으로 직접 생성
                    one_line = self._fallback_message(calc)

                # DiagnosisResult 조립
                cause_map = {
                    "WEATHER": LossCause.WEATHER,
                    "SMP": LossCause.SMP,
                    "COMPLEX": LossCause.COMPLEX,
                    "UNKNOWN": LossCause.UNKNOWN,
                }
                result = DiagnosisResult(
                    year_month=settlement_data.year_month if settlement_data else "UNKNOWN",
                    generation_kwh=calc.get("generation_kwh", 0),
                    capacity_kw=calc.get("capacity_kw"),
                    utilization_pct=calc.get("utilization_pct"),
                    unit_price=calc.get("unit_price", 0),
                    curr_smp=calc.get("curr_smp", 0),
                    actual_revenue_krw=calc["actual_revenue"],
                    optimal_revenue_krw=calc["optimal_revenue"],
                    opportunity_loss_krw=calc["loss"],
                    potential_recovery_krw=calc["improvement_potential"],
                    loss_cause=cause_map.get(calc["cause"], LossCause.UNKNOWN),
                    one_line_message=one_line,
                    smp_context_message=calc.get("smp_context", ""),
                    address_used=calc["address_used"],
                )

                logger.info(f"[{self.name}] [Final DiagnosisResult]: {result.model_dump_json(indent=2)}")

                # analysis_result에 최종 결과 저장
                yield create_text_event(
                    self.name,
                    f"진단 완료: {one_line}",
                    state_delta={"analysis_result": result},
                )
                return
            yield event

    @staticmethod
    def _fallback_message(calc: dict) -> str:
        cause = calc["cause"]
        irr = abs(calc["irr_diff_pct"])
        smp = abs(calc["smp_diff_pct"])
        if cause == "WEATHER":
            return f"주요 원인은 이번달 일조량이 평균보다 {irr}% 낮았기 때문이에요."
        elif cause == "SMP":
            return f"주요 원인은 SMP 시장가가 전달 대비 {smp}% 하락했기 때문이에요."
        elif cause == "COMPLEX":
            return f"일조량 감소({irr}%)와 SMP 하락({smp}%)이 복합적으로 영향을 줬어요."
        else:
            return "이번달은 특이한 손실 원인이 없어요. 예측 오차를 점검해보세요."
