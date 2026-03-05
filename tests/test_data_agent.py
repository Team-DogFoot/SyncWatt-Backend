import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ai.agents.data_agent import DataFetcherAgent
from app.schemas.ai.settlement import SettlementOcrData
from app.schemas.external import KMAMonthlyIrradianceResponse

@pytest.fixture
def agent():
    return DataFetcherAgent()

@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.session.state = {}
    ctx.inputs = {}
    return ctx

@pytest.mark.asyncio
async def test_data_fetcher_station_mapping(agent, mock_ctx):
    # Test cases for address to stn_id mapping
    test_cases = [
        ("경기도 안성시", "119"), # 수원 (Proxy for Anseong)
        ("경기도 평택시", "119"), # 수원 (Proxy for Pyeongtaek)
        ("강원도 춘천시", "101"),
        ("강원도 원주시", "114"),
        ("경상북도 의성군", "278"),
        ("경상북도 영주시", "272"),
        ("전라남도 해남군", "261"),
        ("전라남도 영암군", "165"), # Mokpo as proxy
    ]

    for address, expected_stn_id in test_cases:
        mock_ctx.session.state["settlement_data"] = SettlementOcrData(
            year_month="2024-01",
            address=address,
            generation_kwh=1000.0,
            total_revenue_krw=200000,
            customer_name="Test User",
            plant_name="Test Plant"
        )
        
        with patch("app.services.ai.agents.data_agent.smp_service.get_avg_smp", return_value=150.0), \
             patch("app.services.ai.agents.data_agent.kma_service.get_monthly_avg_irradiance", new_callable=AsyncMock) as mock_kma:
            
            mock_kma.return_value = KMAMonthlyIrradianceResponse(
                year=2024, month=1, avg_irradiance=15.0, unit="MJ/m2", stn_id=expected_stn_id, stn_name="Test"
            )
            
            events = []
            async for event in agent._run_async_impl(mock_ctx):
                events.append(event)
            
            # Verify stn_id used in KMA call
            # Check if any call used the expected_stn_id
            call_stn_ids = [call.kwargs.get("stn_id") for call in mock_kma.call_args_list]
            assert expected_stn_id in call_stn_ids, f"Failed for address: {address}. Expected {expected_stn_id} in {call_stn_ids}"

@pytest.mark.asyncio
async def test_data_fetcher_smp_none_handling(agent, mock_ctx):
    mock_ctx.session.state["settlement_data"] = SettlementOcrData(
        year_month="2024-01",
        address="서울시",
        generation_kwh=1000.0,
        total_revenue_krw=200000,
        customer_name="Test User",
        plant_name="Test Plant"
    )

    with patch("app.services.ai.agents.data_agent.smp_service.get_avg_smp", return_value=None), \
         patch("app.services.ai.agents.data_agent.kma_service.get_monthly_avg_irradiance", new_callable=AsyncMock) as mock_kma:
        
        mock_kma.return_value = KMAMonthlyIrradianceResponse(
            year=2024, month=1, avg_irradiance=15.0, unit="MJ/m2", stn_id="108", stn_name="Seoul"
        )
        
        events = []
        async for event in agent._run_async_impl(mock_ctx):
            events.append(event)
        
        # In ADK, the runner updates the session state based on state_delta.
        # Here we check the yielded event's state_delta.
        market_data = None
        for event in events:
            if hasattr(event, "actions") and event.actions and "market_data" in event.actions.state_delta:
                market_data = event.actions.state_delta["market_data"]
        
        # According to requirements, if SMP is missing, it should handle it gracefully, 
        # not necessarily setting it to 0. 
        # Here we expect it to be None or have an error flag.
        assert market_data is not None
        assert market_data["curr_smp"] is None
        assert market_data.get("error_smp") is True

@pytest.mark.asyncio
async def test_data_fetcher_prev_year_dt(agent, mock_ctx):
    mock_ctx.session.state["settlement_data"] = SettlementOcrData(
        year_month="2024-01",
        address="서울시",
        generation_kwh=1000.0,
        total_revenue_krw=200000,
        customer_name="Test User",
        plant_name="Test Plant"
    )

    with patch("app.services.ai.agents.data_agent.smp_service.get_avg_smp", return_value=150.0), \
         patch("app.services.ai.agents.data_agent.kma_service.get_monthly_avg_irradiance", new_callable=AsyncMock) as mock_kma:
        
        mock_kma.return_value = KMAMonthlyIrradianceResponse(
            year=2024, month=1, avg_irradiance=15.0, unit="MJ/m2", stn_id="108", stn_name="Seoul"
        )
        
        events = []
        async for event in agent._run_async_impl(mock_ctx):
            events.append(event)
        
        # Verify KMA was called for 2023-01
        # 1st call: 2024-01, 2nd call: 2023-01
        found_prev_year = False
        for call in mock_kma.call_args_list:
            if call.args[0] == 2023 and call.args[1] == 1:
                found_prev_year = True
        
        assert found_prev_year, "KMA service should be called for previous year same month"
