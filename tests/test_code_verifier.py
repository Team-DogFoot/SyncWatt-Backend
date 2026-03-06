import pytest
from unittest.mock import MagicMock
from app.services.ai.agents.code_verifier import CodeVerifierAgent
from app.schemas.ai.settlement import SettlementOcrData

def get_final_settlement_data(events):
    for event in reversed(events):
        if hasattr(event, 'actions') and 'settlement_data' in event.actions.state_delta:
            return event.actions.state_delta['settlement_data']
    return None

@pytest.mark.asyncio
async def test_code_verifier_dynamic_tolerance():
    agent = CodeVerifierAgent()
    ctx = MagicMock()
    
    # total_revenue_krw = 1,000,000. 2% is 20,000.
    # unit_price = 200, generation_kwh = 5000. Expected = 1,000,000.
    # If actual is 1,015,000, diff is 15,000.
    # 15,000 > 1,000 (old tolerance) but 15,000 < 20,000 (new tolerance).
    
    ocr_data = SettlementOcrData(
        year_month="2024-02",
        generation_kwh=5000.0,
        unit_price=200.0,
        total_revenue_krw=1015000, # 1.5% error
        address="OCR Address"
    )
    
    # Visual has larger error
    visual_data = SettlementOcrData(
        year_month="2024-02",
        generation_kwh=5000.0,
        unit_price=200.0,
        total_revenue_krw=1100000, # 10% error
        address="Visual Address"
    )
    
    ctx.session.state = {
        "settlement_data": ocr_data,
        "visual_data": visual_data
    }
    
    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)
    
    final_data = get_final_settlement_data(events)
    assert final_data is not None
    assert final_data.total_revenue_krw == 1015000
    assert "수치 정합성이 맞는 OCR" in final_data.selection_reason

@pytest.mark.asyncio
async def test_code_verifier_fallback_smaller_error():
    agent = CodeVerifierAgent()
    ctx = MagicMock()
    
    # OCR: Expected 1,000,000, Actual 1,100,000 (10% error)
    ocr_data = SettlementOcrData(
        year_month="2024-02",
        generation_kwh=5000.0,
        unit_price=200.0,
        total_revenue_krw=1100000,
        address="OCR Address"
    )
    
    # Visual: Expected 1,000,000, Actual 1,050,000 (5% error)
    visual_data = SettlementOcrData(
        year_month="2024-02",
        generation_kwh=5000.0,
        unit_price=200.0,
        total_revenue_krw=1050000,
        address="Visual Address"
    )
    
    ctx.session.state = {
        "settlement_data": ocr_data,
        "visual_data": visual_data
    }
    
    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)
    
    final_data = get_final_settlement_data(events)
    assert final_data is not None
    assert final_data.total_revenue_krw == 1050000
    assert "오차가 더 적은" in final_data.selection_reason

@pytest.mark.asyncio
async def test_code_verifier_is_same_logic():
    agent = CodeVerifierAgent()
    ctx = MagicMock()
    
    # Different address but same key fields
    ocr_data = SettlementOcrData(
        year_month="2024-02",
        generation_kwh=5000.0,
        unit_price=200.0,
        total_revenue_krw=1000000,
        address="OCR Address"
    )
    visual_data = SettlementOcrData(
        year_month="2024-02",
        generation_kwh=5000.0,
        unit_price=200.0,
        total_revenue_krw=1000000,
        address="Visual Address"
    )
    
    ctx.session.state = {
        "settlement_data": ocr_data,
        "visual_data": visual_data
    }
    
    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)
    
    final_data = get_final_settlement_data(events)
    assert final_data is not None
    assert "주요 필드에서 일치" in final_data.selection_reason


@pytest.mark.asyncio
async def test_code_verifier_both_none_sets_error():
    """When both OCR and Visual are None, should set analysis_result with error."""
    agent = CodeVerifierAgent()
    ctx = MagicMock()
    ctx.session.state = {
        "settlement_data": None,
        "visual_data": None,
    }

    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)

    assert len(events) == 1
    delta = events[0].actions.state_delta
    assert "analysis_result" in delta
    result = delta["analysis_result"]
    assert result.opportunity_loss_krw == 0


@pytest.mark.asyncio
async def test_code_verifier_both_invalid_sets_error():
    """When both results fail Pydantic parsing, should set analysis_result with error."""
    agent = CodeVerifierAgent()
    ctx = MagicMock()
    ctx.session.state = {
        "settlement_data": {"invalid": "data"},
        "visual_data": {"also": "invalid"},
    }

    events = []
    async for event in agent._run_async_impl(ctx):
        events.append(event)

    assert len(events) == 1
    delta = events[0].actions.state_delta
    assert "analysis_result" in delta
