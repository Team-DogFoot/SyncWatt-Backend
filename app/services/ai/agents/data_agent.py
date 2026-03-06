import logging
import datetime
from google.adk.agents import BaseAgent
from app.services.external.weather import weather_service
from app.services.external.smp_service import smp_service
from app.services.external.geocoding import get_coordinates
from app.services.ai.utils import create_text_event
from app.services.ai.state_keys import SETTLEMENT_DATA, MARKET_DATA

logger = logging.getLogger(__name__)

DEFAULT_IRRADIANCE = 3.5  # kWh/m²/day 한국 연평균 근사치 (폴백용)


class DataFetcherAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="data_fetcher",
            description="Fetches weather and market data based on the settlement period"
        )

    async def _run_async_impl(self, ctx):
        settlement_data = ctx.session.state.get(SETTLEMENT_DATA)
        if not settlement_data:
            logger.error(f"[{self.name}] Missing settlement_data in session state")
            yield create_text_event(self.name, "Settlement data missing in session state.")
            return

        year_month = settlement_data.year_month
        address = settlement_data.address

        try:
            parts = year_month.split("-")
            year, month = int(parts[0]), int(parts[1])
            curr_dt = datetime.date(year, month, 1)

            # 전월 (SMP 비교용)
            prev_month_dt = (curr_dt - datetime.timedelta(days=1)).replace(day=1)
            prev_year_month = prev_month_dt.strftime("%Y-%m")

            # 전년 동월 (일사량 비교용)
            prev_year_dt = datetime.date(year - 1, month, 1)

            # 1. SMP 조회
            curr_smp = smp_service.get_avg_smp(year_month)
            prev_smp = smp_service.get_avg_smp(prev_year_month)
            error_smp = curr_smp is None or prev_smp is None
            if error_smp:
                logger.warning(f"[{self.name}] SMP data missing for {year_month} or {prev_year_month}")

            # 2. 주소 → 위경도
            lat, lon = get_coordinates(address)

            # 3. 일사량 조회 (현재 vs 전년 동월)
            curr_irr = DEFAULT_IRRADIANCE
            prev_year_irr = DEFAULT_IRRADIANCE
            try:
                curr_data = await weather_service.get_monthly_irradiance(curr_dt.year, curr_dt.month, lat, lon)
                curr_irr = curr_data.avg_irradiance
            except Exception as e:
                logger.warning(f"[{self.name}] Weather API failed for {curr_dt}: {e}. Using default.")

            try:
                prev_data = await weather_service.get_monthly_irradiance(prev_year_dt.year, prev_year_dt.month, lat, lon)
                prev_year_irr = prev_data.avg_irradiance
            except Exception as e:
                logger.warning(f"[{self.name}] Weather API failed for {prev_year_dt}: {e}. Using default.")

            market_data = {
                "year_month": year_month,
                "curr_smp": curr_smp,
                "prev_smp": prev_smp,
                "curr_irr": curr_irr,
                "prev_year_irr": prev_year_irr,
                "latitude": lat,
                "longitude": lon,
                "address_used": address is not None,
                "error_smp": error_smp,
            }

            logger.info(
                f"[{self.name}] Data fetched for {year_month}: "
                f"SMP({curr_smp} vs {prev_smp}), "
                f"Irr({curr_irr} vs {prev_year_irr}), "
                f"Coords({lat},{lon})"
            )

            yield create_text_event(
                self.name,
                f"Fetched data for {year_month}.",
                state_delta={MARKET_DATA: market_data}
            )
        except Exception as e:
            logger.error(f"[{self.name}] Error fetching data: {str(e)}", exc_info=True)
            yield create_text_event(self.name, f"Error fetching market/weather data: {str(e)}")
