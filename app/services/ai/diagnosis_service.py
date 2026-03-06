import calendar
import logging
from app.schemas.ai.settlement import SettlementOcrData

logger = logging.getLogger(__name__)


def calculate_and_diagnose(settlement_data: SettlementOcrData, market_data: dict) -> dict:
    """
    정산 데이터와 시장 데이터를 기반으로 손실 진단을 수행합니다.
    순수 Python 로직으로 계산 및 원인 판단을 수행합니다.
    """
    gen = settlement_data.generation_kwh
    actual = settlement_data.total_revenue_krw
    unit_price = settlement_data.unit_price or 0
    capacity_kw = settlement_data.capacity_kw
    curr_smp = market_data.get("curr_smp") or 0
    prev_smp = market_data.get("prev_smp") or 0
    curr_irr = market_data.get("curr_irr") or 0
    prev_irr = market_data.get("prev_year_irr") or 0

    # 이용률 계산
    utilization_pct = None
    if capacity_kw and capacity_kw > 0:
        year_month = settlement_data.year_month
        try:
            parts = year_month.split("-")
            year, month = int(parts[0]), int(parts[1])
            hours_in_month = calendar.monthrange(year, month)[1] * 24
            utilization_pct = round(gen / (capacity_kw * hours_in_month) * 100, 1)
        except (ValueError, IndexError):
            pass

    # 수익 계산
    optimal = round(gen * curr_smp)
    loss = optimal - actual
    improvement_potential = max(0, round(loss * 0.4))

    # 원인 판단 (우선순위 순서 엄수)
    irr_diff_pct = (curr_irr - prev_irr) / prev_irr * 100 if prev_irr > 0 else 0
    smp_diff_pct = (curr_smp - prev_smp) / prev_smp * 100 if prev_smp > 0 else 0

    if prev_irr > 0 and irr_diff_pct <= -10:
        cause = "WEATHER"
    elif smp_diff_pct <= -10:
        cause = "SMP"
    elif irr_diff_pct <= -5 and smp_diff_pct <= -5:
        cause = "COMPLEX"
    else:
        cause = "UNKNOWN"

    # SMP 계절 변동 맥락 메시지
    smp_context = ""
    if curr_smp > 0 and unit_price > 0:
        if curr_smp > unit_price:
            diff_pct = round((curr_smp - unit_price) / unit_price * 100, 1)
            smp_context = (
                f"이번 달 SMP 평균({curr_smp:.1f}원)은 소장님 단가({unit_price:.1f}원)보다 "
                f"{diff_pct}% 높아요. SMP가 더 오르는 여름철에는 차이가 더 벌어질 수 있어요."
            )
        elif loss <= 0:
            smp_context = (
                f"이번 달 SMP({curr_smp:.1f}원)가 소장님 단가({unit_price:.1f}원)보다 낮았지만, "
                f"SMP는 계절에 따라 크게 변동해요. 여름철 SMP 급등기에는 차이가 벌어질 수 있어요."
            )

    result = {
        "optimal_revenue": optimal,
        "actual_revenue": actual,
        "loss": loss,
        "improvement_potential": improvement_potential,
        "cause": cause,
        "irr_diff_pct": round(irr_diff_pct, 1),
        "smp_diff_pct": round(smp_diff_pct, 1),
        "address_used": market_data.get("address_used", False),
        "generation_kwh": gen,
        "capacity_kw": capacity_kw,
        "utilization_pct": utilization_pct,
        "unit_price": unit_price,
        "curr_smp": curr_smp,
        "smp_context": smp_context,
    }

    logger.info(
        f"[DiagnosisService] [Core Calculation]: "
        f"{gen}kWh * {curr_smp:.2f}원 = {optimal}원 (Optimal) vs {actual}원 (Actual). "
        f"Loss={loss}원, Cause={cause}, "
        f"Irr diff={irr_diff_pct:.1f}%, SMP diff={smp_diff_pct:.1f}%, "
        f"Utilization={utilization_pct}%"
    )

    return result
