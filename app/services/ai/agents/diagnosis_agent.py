import logging
import time
from google.adk.agents import BaseAgent
from app.schemas.ai.diagnosis import DiagnosisResult, LossCause
from app.services.ai.utils import create_text_event
from app.services.ai.diagnosis_service import calculate_and_diagnose
from app.services.ai.state_keys import (
    SETTLEMENT_DATA, MARKET_DATA, DIAGNOSIS_CALC,
    CAUSE, IRR_DIFF_PCT, SMP_DIFF_PCT, ANALYSIS_RESULT,
)

logger = logging.getLogger(__name__)


class DiagnosisCalculatorAgent(BaseAgent):
    """순수 Python 로직으로 진단 계산을 수행하고 결과를 세션에 저장하는 에이전트입니다."""
    def __init__(self):
        super().__init__(
            name="diagnosis_calculator",
            description="Python 로직으로 손실 진단 계산을 수행합니다."
        )

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] Starting diagnosis calculation")

        settlement_data = ctx.session.state.get(SETTLEMENT_DATA)
        market_data = ctx.session.state.get(MARKET_DATA)

        if not settlement_data:
            logger.error(f"[{self.name}] settlement_data missing")
            yield create_text_event(self.name, "정산 데이터가 없어 진단 불가.")
            return

        if not market_data or market_data.get("error_smp") or market_data.get("curr_smp") is None:
            logger.warning(f"[{self.name}] Required market data missing")
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
                state_delta={ANALYSIS_RESULT: error_result},
            )
            return

        calc = calculate_and_diagnose(settlement_data, market_data)

        duration = time.perf_counter() - start_t
        logger.info(f"[{self.name}] Diagnosis calculation done ({duration:.2f}s)")

        yield create_text_event(
            self.name,
            f"Diagnosis done: cause={calc['cause']}, loss={calc['loss']}",
            state_delta={
                DIAGNOSIS_CALC: calc,
                CAUSE: calc["cause"],
                IRR_DIFF_PCT: calc["irr_diff_pct"],
                SMP_DIFF_PCT: calc["smp_diff_pct"],
            },
        )


class DiagnosisAgent(BaseAgent):
    """진단 계산 결과를 바탕으로 DiagnosisResult를 조립하는 에이전트입니다. LLM 호출 없음."""
    def __init__(self):
        super().__init__(
            name="diagnoser",
            description="진단 계산 결과를 최종 DiagnosisResult로 조립합니다."
        )
        logger.info(f"[{self.name}] Agent initialized")

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] Starting result assembly")

        calc = ctx.session.state.get(DIAGNOSIS_CALC)
        if not calc:
            logger.error(f"[{self.name}] diagnosis_calc not found in session")
            return

        if ctx.session.state.get(ANALYSIS_RESULT):
            logger.info(f"[{self.name}] analysis_result already exists. Skipping.")
            return

        settlement_data = ctx.session.state.get(SETTLEMENT_DATA)
        one_line = self._build_message(calc)

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

        duration = time.perf_counter() - start_t
        logger.info(f"[{self.name}] Result assembly complete ({duration:.2f}s)")
        logger.info(f"[{self.name}] [Final DiagnosisResult]: {result.model_dump_json(indent=2)}")

        yield create_text_event(
            self.name,
            f"진단 완료: {one_line}",
            state_delta={ANALYSIS_RESULT: result},
        )

    @staticmethod
    def _build_message(calc: dict) -> str:
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
