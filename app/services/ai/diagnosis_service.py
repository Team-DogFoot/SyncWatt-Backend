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
    curr_smp = market_data.get("curr_smp") or 0
    prev_smp = market_data.get("prev_smp") or 0
    curr_irr = market_data.get("curr_irr") or 0
    prev_irr = market_data.get("prev_year_irr") or 0

    # 계산
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

    result = {
        "optimal_revenue": optimal,
        "actual_revenue": actual,
        "loss": loss,
        "improvement_potential": improvement_potential,
        "cause": cause,
        "irr_diff_pct": round(irr_diff_pct, 1),
        "smp_diff_pct": round(smp_diff_pct, 1),
        "address_used": market_data.get("address_used", False),
    }

    logger.info(
        f"[DiagnosisService] [Core Calculation]: "
        f"{gen}kWh * {curr_smp:.2f}원 = {optimal}원 (Optimal) vs {actual}원 (Actual). "
        f"Loss={loss}원, Cause={cause}, "
        f"Irr diff={irr_diff_pct:.1f}%, SMP diff={smp_diff_pct:.1f}%"
    )

    return result
