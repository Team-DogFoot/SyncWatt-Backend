import pytest
from app.services.external.kma_service import kma_service
from app.services.external.kpx_service import kpx_service
from app.schemas.external import KMAMonthlyIrradianceResponse, KPXMonthlyPriceResponse

@pytest.mark.asyncio
async def test_kma_service_mock():
    # Test KMA service returns mock data (when no API key is provided)
    result = await kma_service.get_monthly_avg_irradiance(year=2024, month=1)
    
    assert isinstance(result, KMAMonthlyIrradianceResponse)
    assert result.year == 2024
    assert result.month == 1
    assert result.avg_irradiance > 0
    assert result.unit == "MJ/m²"

@pytest.mark.asyncio
async def test_kpx_service_mock():
    # Test KPX service returns mock data (when no API key is provided)
    result = await kpx_service.get_monthly_avg_prices(year=2024, month=1)
    
    assert isinstance(result, KPXMonthlyPriceResponse)
    assert result.year == 2024
    assert result.month == 1
    assert result.avg_smp > 0
    assert result.avg_rec > 0
    assert result.smp_unit == "원/kWh"
    assert result.rec_unit == "원/REC"
