import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.external import IrradianceData
from app.services.external.weather import NasaPowerProvider


def test_irradiance_data_schema():
    data = IrradianceData(
        year=2024, month=1,
        avg_irradiance=2.25,
        latitude=37.57, longitude=126.98,
        source="nasa_power",
    )
    assert data.avg_irradiance == 2.25
    assert data.source == "nasa_power"


def test_irradiance_data_rejects_missing_fields():
    with pytest.raises(Exception):
        IrradianceData(year=2024, month=1)  # missing required fields


@pytest.fixture
def provider():
    return NasaPowerProvider()


@pytest.fixture
def mock_nasa_response():
    """NASA POWER API 월별 응답 mock"""
    return {
        "properties": {
            "parameter": {
                "ALLSKY_SFC_SW_DWN": {
                    "202401": 2.2574,
                    "202402": 2.5834,
                    "202403": 4.0188,
                    "202404": 4.8898,
                    "202405": 6.5522,
                    "202406": 5.6501,
                    "202407": 4.469,
                    "202408": 5.3813,
                    "202409": 3.701,
                    "202410": 3.641,
                    "202411": 2.6306,
                    "202412": 2.291,
                    "202413": 3.9581,
                }
            }
        }
    }


@pytest.mark.asyncio
async def test_nasa_provider_monthly(provider, mock_nasa_response):
    with patch("app.services.external.weather.httpx.AsyncClient") as MockClient:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_nasa_response
        mock_resp.raise_for_status = MagicMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=MockClient.return_value)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value.get = AsyncMock(return_value=mock_resp)

        result = await provider.get_monthly_irradiance(2024, 1, 37.57, 126.98)

        assert result.avg_irradiance == 2.2574
        assert result.source == "nasa_power"
        assert result.latitude == 37.57
        assert result.longitude == 126.98


@pytest.mark.asyncio
async def test_nasa_provider_api_error_raises(provider):
    with patch("app.services.external.weather.httpx.AsyncClient") as MockClient:
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = Exception("API Error")
        MockClient.return_value.__aenter__ = AsyncMock(return_value=MockClient.return_value)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value.get = AsyncMock(return_value=mock_resp)

        with pytest.raises(Exception):
            await provider.get_monthly_irradiance(2024, 1, 37.57, 126.98)


@pytest.mark.asyncio
async def test_nasa_provider_missing_month_returns_fallback(provider):
    """요청한 월 데이터가 -999(결측값)이면 ValueError"""
    bad_response = {
        "properties": {
            "parameter": {
                "ALLSKY_SFC_SW_DWN": {
                    "202401": -999.0,
                }
            }
        }
    }
    with patch("app.services.external.weather.httpx.AsyncClient") as MockClient:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = bad_response
        mock_resp.raise_for_status = MagicMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=MockClient.return_value)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        MockClient.return_value.get = AsyncMock(return_value=mock_resp)

        with pytest.raises(ValueError, match="결측"):
            await provider.get_monthly_irradiance(2024, 1, 37.57, 126.98)
