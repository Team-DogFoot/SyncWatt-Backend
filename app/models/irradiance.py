from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Irradiance(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    year_month: str = Field(index=True)  # "2024-01"
    latitude: float  # 소수 2자리로 라운딩
    longitude: float  # 소수 2자리로 라운딩
    avg_irradiance: float  # kWh/m²/day
    source: str = "nasa_power"  # 데이터 출처
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
