from __future__ import annotations

import logging
from typing import Protocol

import httpx

from app.schemas.external import IrradianceData

logger = logging.getLogger(__name__)


class WeatherProvider(Protocol):
    """일사량 데이터 제공자 인터페이스. Solcast 등으로 교체 시 이 프로토콜만 구현하면 됨."""

    async def get_monthly_irradiance(
        self, year: int, month: int, latitude: float, longitude: float
    ) -> IrradianceData:
        """특정 연월, 위경도의 월평균 일사량을 반환한다."""
        ...


NASA_POWER_BASE = "https://power.larc.nasa.gov/api/temporal/monthly/point"


class NasaPowerProvider:
    """NASA POWER API를 사용한 일사량 데이터 제공자. API 키 불필요."""

    async def get_monthly_irradiance(
        self, year: int, month: int, latitude: float, longitude: float
    ) -> IrradianceData:
        params = {
            "parameters": "ALLSKY_SFC_SW_DWN",
            "community": "RE",
            "longitude": longitude,
            "latitude": latitude,
            "start": year,
            "end": year,
            "format": "JSON",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(NASA_POWER_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()

        monthly = data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
        key = f"{year}{month:02d}"
        value = monthly.get(key)

        if value is None or value == -999.0:
            raise ValueError(f"NASA POWER 결측 데이터: {key} (lat={latitude}, lon={longitude})")

        logger.info(f"[NasaPower] {year}-{month:02d} ({latitude},{longitude}): {value} kWh/m²/day")

        return IrradianceData(
            year=year,
            month=month,
            avg_irradiance=value,
            latitude=latitude,
            longitude=longitude,
            source="nasa_power",
        )
