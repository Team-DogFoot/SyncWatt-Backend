import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ai.agents.data_agent import DataFetcherAgent
from app.schemas.ai.settlement import SettlementOcrData
from app.schemas.external import IrradianceData


@pytest.fixture
def agent():
    return DataFetcherAgent()


@pytest.fixture
def mock_ctx():
    ctx = MagicMock()
    ctx.session.state = {}
    return ctx


def _make_irradiance(year, month, value, lat=37.57, lon=126.98):
    return IrradianceData(
        year=year, month=month, avg_irradiance=value,
        latitude=lat, longitude=lon, source="nasa_power",
    )


@pytest.mark.asyncio
async def test_data_fetcher_uses_coordinates(agent, mock_ctx):
    """주소가 있으면 위경도 변환 후 weather_service에 전달한다."""
    mock_ctx.session.state["settlement_data"] = SettlementOcrData(
        year_month="2024-01",
        address="전라남도 해남군",
        generation_kwh=1000.0,
        total_revenue_krw=200000,
    )

    with patch("app.services.ai.agents.data_agent.smp_service.get_avg_smp", return_value=150.0), \
         patch("app.services.ai.agents.data_agent.weather_service.get_monthly_irradiance", new_callable=AsyncMock) as mock_weather:
        mock_weather.return_value = _make_irradiance(2024, 1, 2.5, 34.57, 126.60)

        events = []
        async for event in agent._run_async_impl(mock_ctx):
            events.append(event)

        # weather_service가 호출되었는지 확인
        assert mock_weather.call_count == 2  # curr + prev_year


@pytest.mark.asyncio
async def test_data_fetcher_no_address_uses_default(agent, mock_ctx):
    """주소 없으면 기본 좌표 사용."""
    mock_ctx.session.state["settlement_data"] = SettlementOcrData(
        year_month="2024-01",
        generation_kwh=1000.0,
        total_revenue_krw=200000,
    )

    with patch("app.services.ai.agents.data_agent.smp_service.get_avg_smp", return_value=150.0), \
         patch("app.services.ai.agents.data_agent.weather_service.get_monthly_irradiance", new_callable=AsyncMock) as mock_weather:
        mock_weather.return_value = _make_irradiance(2024, 1, 2.5)

        events = []
        async for event in agent._run_async_impl(mock_ctx):
            events.append(event)

        assert mock_weather.call_count == 2  # curr + prev_year


@pytest.mark.asyncio
async def test_data_fetcher_smp_none_sets_error_flag(agent, mock_ctx):
    """SMP가 None이면 error_smp 플래그가 설정된다."""
    mock_ctx.session.state["settlement_data"] = SettlementOcrData(
        year_month="2024-01",
        generation_kwh=1000.0,
        total_revenue_krw=200000,
    )

    with patch("app.services.ai.agents.data_agent.smp_service.get_avg_smp", return_value=None), \
         patch("app.services.ai.agents.data_agent.weather_service.get_monthly_irradiance", new_callable=AsyncMock) as mock_weather:
        mock_weather.return_value = _make_irradiance(2024, 1, 2.5)

        events = []
        async for event in agent._run_async_impl(mock_ctx):
            events.append(event)

        market_data = None
        for event in events:
            if hasattr(event, "actions") and event.actions and "market_data" in event.actions.state_delta:
                market_data = event.actions.state_delta["market_data"]

        assert market_data is not None
        assert market_data["error_smp"] is True


@pytest.mark.asyncio
async def test_data_fetcher_weather_failure_uses_fallback(agent, mock_ctx):
    """날씨 API 실패 시 기본값으로 폴백한다."""
    mock_ctx.session.state["settlement_data"] = SettlementOcrData(
        year_month="2024-01",
        generation_kwh=1000.0,
        total_revenue_krw=200000,
    )

    with patch("app.services.ai.agents.data_agent.smp_service.get_avg_smp", return_value=150.0), \
         patch("app.services.ai.agents.data_agent.weather_service.get_monthly_irradiance", new_callable=AsyncMock) as mock_weather:
        mock_weather.side_effect = Exception("API timeout")

        events = []
        async for event in agent._run_async_impl(mock_ctx):
            events.append(event)

        # 에러가 발생해도 market_data는 전달되어야 함 (irr 기본값으로)
        market_data = None
        for event in events:
            if hasattr(event, "actions") and event.actions and "market_data" in event.actions.state_delta:
                market_data = event.actions.state_delta["market_data"]

        assert market_data is not None
        assert market_data["curr_irr"] == 3.5  # DEFAULT_IRRADIANCE
        assert market_data["prev_year_irr"] == 3.5
