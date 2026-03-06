from __future__ import annotations

import logging
from typing import Protocol

from app.schemas.external import IrradianceData

logger = logging.getLogger(__name__)


class WeatherProvider(Protocol):
    """일사량 데이터 제공자 인터페이스. Solcast 등으로 교체 시 이 프로토콜만 구현하면 됨."""

    async def get_monthly_irradiance(
        self, year: int, month: int, latitude: float, longitude: float
    ) -> IrradianceData:
        """특정 연월, 위경도의 월평균 일사량을 반환한다."""
        ...
