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


class CachedWeatherService:
    """DB 캐시 + Provider 조합. DataFetcherAgent는 이 클래스만 사용."""

    def __init__(self, provider: WeatherProvider | None = None):
        self._provider = provider or NasaPowerProvider()

    async def get_monthly_irradiance(
        self, year: int, month: int, latitude: float, longitude: float
    ) -> IrradianceData:
        from sqlmodel import Session, select

        from app.db.session import engine
        from app.models.irradiance import Irradiance

        lat_r = round(latitude, 2)
        lon_r = round(longitude, 2)
        ym = f"{year}-{month:02d}"

        # 1) DB 캐시 조회
        with Session(engine) as session:
            stmt = select(Irradiance).where(
                Irradiance.year_month == ym,
                Irradiance.latitude == lat_r,
                Irradiance.longitude == lon_r,
            )
            cached = session.exec(stmt).first()
            if cached:
                logger.info(f"[Weather] Cache hit: {ym} ({lat_r},{lon_r}) = {cached.avg_irradiance}")
                return IrradianceData(
                    year=year, month=month,
                    avg_irradiance=cached.avg_irradiance,
                    latitude=lat_r, longitude=lon_r,
                    source=cached.source,
                )

        # 2) Provider에서 가져오기
        result = await self._provider.get_monthly_irradiance(year, month, lat_r, lon_r)

        # 3) DB에 캐시 저장
        with Session(engine) as session:
            record = Irradiance(
                year_month=ym,
                latitude=lat_r,
                longitude=lon_r,
                avg_irradiance=result.avg_irradiance,
                source=result.source,
            )
            session.add(record)
            session.commit()
            logger.info(f"[Weather] Cached: {ym} ({lat_r},{lon_r}) = {result.avg_irradiance}")

        return result


# 모듈 레벨 인스턴스 (DataFetcherAgent에서 import)
weather_service = CachedWeatherService()
