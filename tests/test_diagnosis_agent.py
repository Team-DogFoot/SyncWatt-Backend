import pytest
from unittest.mock import MagicMock
from app.services.ai.agents.diagnosis_agent import DiagnosisCalculatorAgent, DiagnosisAgent
from app.schemas.ai.settlement import SettlementOcrData
from app.schemas.ai.diagnosis import LossCause


def make_ctx(state: dict):
    ctx = MagicMock()
    ctx.session.state = state
    return ctx


@pytest.mark.asyncio
async def test_calculator_produces_diagnosis_calc():
    agent = DiagnosisCalculatorAgent()
    settlement = SettlementOcrData(
        year_month="2024-02",
        generation_kwh=5000.0,
        unit_price=100.0,
        total_revenue_krw=500000,
        address="Test Address"
    )
    market = {
        "curr_smp": 150.0,
        "prev_smp": 140.0,
        "curr_irr": 4.0,
        "prev_year_irr": 4.5,
    }
    ctx = make_ctx({"settlement_data": settlement, "market_data": market})

    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)

    assert len(events) == 1
    delta = events[0].actions.state_delta
    assert "diagnosis_calc" in delta
    assert "cause" in delta
    assert delta["diagnosis_calc"]["optimal_revenue"] == 750000
    assert delta["diagnosis_calc"]["actual_revenue"] == 500000


@pytest.mark.asyncio
async def test_calculator_missing_settlement_data():
    agent = DiagnosisCalculatorAgent()
    ctx = make_ctx({"settlement_data": None, "market_data": {}})

    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)

    assert len(events) == 1
    assert "정산 데이터" in events[0].content.parts[0].text


@pytest.mark.asyncio
async def test_calculator_missing_smp_produces_error_result():
    agent = DiagnosisCalculatorAgent()
    settlement = SettlementOcrData(
        year_month="2024-02",
        generation_kwh=1000.0,
        total_revenue_krw=150000,
    )
    ctx = make_ctx({
        "settlement_data": settlement,
        "market_data": {"error_smp": True, "curr_smp": None},
    })

    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)

    delta = events[0].actions.state_delta
    assert "analysis_result" in delta
    result = delta["analysis_result"]
    assert result.opportunity_loss_krw == 0
    assert "데이터가 부족하여" in result.one_line_message


@pytest.mark.asyncio
async def test_diagnosis_agent_assembles_result():
    agent = DiagnosisAgent()
    settlement = SettlementOcrData(
        year_month="2024-02",
        generation_kwh=5000.0,
        unit_price=100.0,
        total_revenue_krw=500000,
        address="Test Address"
    )
    calc = {
        "optimal_revenue": 750000,
        "actual_revenue": 500000,
        "loss": 250000,
        "improvement_potential": 100000,
        "cause": "WEATHER",
        "irr_diff_pct": -15.0,
        "smp_diff_pct": -2.0,
        "address_used": True,
        "generation_kwh": 5000.0,
        "capacity_kw": 99.0,
        "utilization_pct": 7.2,
        "unit_price": 100.0,
        "curr_smp": 150.0,
        "smp_context": "",
    }
    ctx = make_ctx({
        "settlement_data": settlement,
        "diagnosis_calc": calc,
        "analysis_result": None,
    })

    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)

    assert len(events) == 1
    delta = events[0].actions.state_delta
    result = delta["analysis_result"]
    assert result.loss_cause == LossCause.WEATHER
    assert result.actual_revenue_krw == 500000
    assert result.optimal_revenue_krw == 750000
    assert "일조량" in result.one_line_message


@pytest.mark.asyncio
async def test_diagnosis_agent_skips_when_result_exists():
    agent = DiagnosisAgent()
    existing_result = MagicMock()
    ctx = make_ctx({
        "diagnosis_calc": {"some": "data"},
        "analysis_result": existing_result,
    })

    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)

    assert len(events) == 0


@pytest.mark.asyncio
async def test_diagnosis_agent_no_calc_skips():
    agent = DiagnosisAgent()
    ctx = make_ctx({"diagnosis_calc": None, "analysis_result": None})

    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)

    assert len(events) == 0
