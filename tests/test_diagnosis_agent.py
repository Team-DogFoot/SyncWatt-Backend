import pytest
from unittest.mock import MagicMock, patch
from app.services.ai.agents.diagnosis_agent import DiagnosisAgent
from app.schemas.ai.settlement import SettlementOcrData

@pytest.mark.asyncio
async def test_diagnosis_agent_precalculates_values():
    agent = DiagnosisAgent()
    ctx = MagicMock()
    
    settlement_data = SettlementOcrData(
        year_month="2024-02",
        generation_kwh=1000.0,
        total_revenue_krw=150000,
        address="Test Address"
    )
    market_data = {
        "curr_smp": 200.0,
        "prev_smp": 180.0,
        "curr_irr": 4.5,
        "prev_year_irr": 4.0
    }
    
    ctx.session.state = {
        "settlement_data": settlement_data,
        "market_data": market_data
    }
    ctx.inputs = {}
    
    with patch("google.adk.agents.LlmAgent._run_async_impl") as mock_super:
        async def mock_gen(*args, **kwargs):
            mock_event = MagicMock()
            mock_event.partial = False
            yield mock_event
            
        mock_super.side_effect = mock_gen
        
        async for _ in agent._run_async_impl(ctx):
            pass
        
        # Check if pre-calculated values are in session state
        assert "optimal_revenue_krw" in ctx.session.state
        assert "opportunity_loss_krw" in ctx.session.state
        
        # 1000 kWh * 200 SMP = 200,000
        assert ctx.session.state["optimal_revenue_krw"] == 200000
        # 200,000 - 150,000 = 50,000
        assert ctx.session.state["opportunity_loss_krw"] == 50000
        
        # Check if settlement_data is formatted as JSON string for the LLM
        # LlmAgent will use session.state.get("settlement_data_json") for the template
        assert isinstance(ctx.session.state.get("settlement_data_json"), str)
        assert isinstance(ctx.session.state.get("market_data_json"), str)
        assert mock_super.called

@pytest.mark.asyncio
async def test_diagnosis_agent_handles_missing_data():
    agent = DiagnosisAgent()
    ctx = MagicMock()
    
    settlement_data = SettlementOcrData(
        year_month="2024-02",
        generation_kwh=1000.0,
        total_revenue_krw=150000,
        address="Test Address"
    )
    
    ctx.session.state = {
        "settlement_data": settlement_data,
        "market_data": None # Missing market data
    }
    ctx.inputs = {}
    
    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)
    
    assert len(events) > 0
    # The agent should produce a text event with the error result in state_delta
    last_event = events[-1]
    assert "analysis_result" in last_event.actions.state_delta
    result = last_event.actions.state_delta["analysis_result"]
    assert result.year_month == "2024-02"
    assert result.opportunity_loss_krw == 0
    assert "데이터가 부족하여" in result.one_line_message

@pytest.mark.asyncio
async def test_diagnosis_agent_handles_error_smp_flag():
    agent = DiagnosisAgent()
    ctx = MagicMock()
    
    settlement_data = SettlementOcrData(
        year_month="2024-02",
        generation_kwh=1000.0,
        total_revenue_krw=150000,
        address="Test Address"
    )
    
    ctx.session.state = {
        "settlement_data": settlement_data,
        "market_data": {
            "error_smp": True,
            "curr_smp": None
        }
    }
    ctx.inputs = {}
    
    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)
    
    last_event = events[-1]
    assert "analysis_result" in last_event.actions.state_delta
    result = last_event.actions.state_delta["analysis_result"]
    assert "데이터가 부족하여" in result.one_line_message
