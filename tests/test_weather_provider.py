import pytest
from app.schemas.external import IrradianceData


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
