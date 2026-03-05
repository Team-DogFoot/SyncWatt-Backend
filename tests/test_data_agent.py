import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.schemas.ai.settlement import SettlementOcrData
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.genai import types

from app.services.ai.data_agent import DataFetcherAgent

@pytest.mark.asyncio
async def test_data_fetcher_agent():
    # 1. Setup Data
    settlement_data = {
        "year_month": "2024-02",
        "generation_kwh": 1234.5,
        "total_revenue_krw": 150000
    }
    
    # Mock context
    ctx = AsyncMock()
    ctx.session.state = {"analysis_result": settlement_data}
    
    # 2. Mock Services
    mock_irradiance = MagicMock()
    mock_irradiance.avg_irradiance = 15.5
    mock_irradiance.unit = "MJ/m²"
    mock_irradiance.model_dump = MagicMock(return_value={
        "year": 2024, "month": 2, "avg_irradiance": 15.5, "unit": "MJ/m²"
    })
    
    mock_market_data = MagicMock()
    mock_market_data.avg_smp = 180.0
    mock_market_data.avg_rec = 70.0
    mock_market_data.model_dump = MagicMock(return_value={
        "year": 2024, "month": 2, "avg_smp": 180.0, "avg_rec": 70.0
    })
    
    with patch("app.services.external.kma_service.kma_service.get_monthly_avg_irradiance", new_callable=AsyncMock) as mock_kma, \
         patch("app.services.external.kpx_service.kpx_service.get_monthly_avg_prices", new_callable=AsyncMock) as mock_kpx:
        
        mock_kma.return_value = mock_irradiance
        mock_kpx.return_value = mock_market_data
        
        agent = DataFetcherAgent()
        
        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)
        
        # 3. Assertions
        mock_kma.assert_called_once_with(2024, 2)
        mock_kpx.assert_called_once_with(2024, 2)
        
        assert len(events) == 1
        event = events[0]
        assert event.author == "data_fetcher"
        
        state_delta = event.actions.state_delta
        assert "market_data" in state_delta
        market_data = state_delta["market_data"]
        assert market_data["avg_irradiance"] == 15.5
        assert market_data["avg_smp"] == 180.0
        assert market_data["avg_rec"] == 70.0
