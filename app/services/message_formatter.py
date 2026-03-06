"""DiagnosisResult to user-facing message formatter."""
from app.schemas.ai.diagnosis import DiagnosisResult


def build_response_message(analysis: DiagnosisResult) -> str:
    """Convert DiagnosisResult into a Telegram-formatted message."""
    f = format  # shorthand
    loss_val = int(analysis.opportunity_loss_krw)
    loss_abs = f(abs(loss_val), ",")
    optimal = f(int(analysis.optimal_revenue_krw), ",")
    actual = f(int(analysis.actual_revenue_krw), ",")
    gen = f(int(analysis.generation_kwh), ",")
    recovery = int(analysis.potential_recovery_krw) if analysis.potential_recovery_krw else 0

    # Header
    ym = analysis.year_month
    parts = ym.split("-")
    header = f"📝 *{parts[0]}년 {int(parts[1])}월 정산 분석*" if len(parts) == 2 else f"📝 *{ym} 정산 분석*"

    # Monthly summary
    summary_lines = [f"• 발전량: {gen} kWh"]

    if analysis.capacity_kw and analysis.utilization_pct is not None:
        cap = f(int(analysis.capacity_kw), ",")
        summary_lines.append(f"• 설비용량 {cap}kW 기준 이용률 {analysis.utilization_pct}%")

    unit_str = f"{analysis.unit_price:.1f}" if analysis.unit_price else "?"
    summary_lines.append(f"• 실제 수령: {actual}원 (단가 {unit_str}원/kWh)")

    smp_str = f"{analysis.curr_smp:.1f}" if analysis.curr_smp else "?"
    summary_lines.append(f"• 전력시장 직접 판매 시(KPX): {optimal}원 (시장가(SMP) 평균 {smp_str}원/kWh)")

    summary = "\n".join(summary_lines)

    # Verdict
    if loss_val > 0:
        verdict = f"→ 이번 달은 약 *{loss_abs}원*의 기회손실이 있었어요."
    elif loss_val == 0:
        verdict = "→ 이번 달은 전력시장 직접 판매 시와 동일해요."
    else:
        verdict = f"→ 한전 고정단가 계약이 이번달 기준 *{loss_abs}원* 유리했어요."

    # Cause + utilization context
    utilization_note = ""
    if analysis.utilization_pct is not None:
        u = analysis.utilization_pct
        if u < 10:
            utilization_note = f" 이용률 {u}%는 평균(12~16%) 대비 낮은 편이에요."
        elif u > 16:
            utilization_note = f" 이용률 {u}%로 평균(12~16%) 이상의 좋은 성과예요."

    if loss_val > 0:
        cause_section = f"💡 *주요 원인*\n{analysis.one_line_message}{utilization_note}"
    else:
        cause_section = f"💡 *참고*\n이번달 {_simplify_cause(analysis.one_line_message)} 한전 고정단가가 시장가(SMP)보다 높아 오히려 유리했어요.{utilization_note}"

    # SMP context
    smp_section = ""
    if analysis.smp_context_message:
        smp_section = f"\n\n📈 *알아두시면 좋아요*\n{analysis.smp_context_message}"

    # Recovery (only when loss > 0)
    recovery_section = ""
    if loss_val > 0 and recovery > 0:
        recovery_fmt = f(recovery, ",")
        recovery_section = f"\n\n🔧 이 중 약 *{recovery_fmt}원*은 입찰 예측값 최적화로 회수 가능해요."

    # CTA
    cta = (
        "\n\n✅ *가입하면 받을 수 있어요*\n"
        "• 매일 아침 최적 입찰가 추천\n"
        "• 월간 발전소 성적표\n"
        "• 연간 누적 기회비용 분석"
    )

    # Location notice
    location = ""
    if not analysis.address_used:
        location = "\n\n📍 현재 전국 평균 일조량으로 분석했어요. 위치를 등록하면 우리 발전소 지역 기반 정밀 분석이 가능해요."

    # Assemble
    msg = (
        f"{header}\n\n"
        f"📊 *이번 달 요약*\n"
        f"{summary}\n"
        f"{verdict}\n\n"
        f"{cause_section}"
        f"{smp_section}"
        f"{recovery_section}"
        f"{cta}"
        f"{location}"
    )
    return msg


def _simplify_cause(one_line: str) -> str:
    """Transform '주요 원인은 ... 때문이에요' into '일조량이 ... 낮았지만,' form."""
    s = one_line.replace("주요 원인은 ", "").replace("이번달 ", "")
    s = s.replace("기 때문이에요.", "").replace("기 때문이에요", "")
    s = s.replace("때문이에요.", "").replace("때문이에요", "")
    s = s.strip()
    if s:
        return f"{s}지만,"
    return ""
