import logging
from google.adk.agents import BaseAgent
from app.services.external.kma_service import kma_service
from app.services.external.kpx_service import kpx_service
from app.services.ai.utils import create_text_event

logger = logging.getLogger(__name__)

class DataFetcherAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="data_fetcher",
            description="Fetches weather and market data based on the settlement period"
        )

    async def _run_async_impl(self, ctx):
        # 1. Extract analysis_result from session state
        # The instruction specifically mentioned analysis_result
        analysis_result = ctx.session.state.get("analysis_result")
        if not analysis_result:
            # Fallback to settlement_data as seen in some pipeline implementations
            analysis_result = ctx.session.state.get("settlement_data")
            
        if not analysis_result:
            logger.error(f"[{self.name}] Missing analysis_result in session state")
            yield create_text_event(self.name, "Analysis result missing in session state.")
            return

        # Handle both dict and object (Pydantic model)
        if isinstance(analysis_result, dict):
            year_month = analysis_result.get("year_month")
        else:
            year_month = getattr(analysis_result, "year_month", None)

        if not year_month:
            logger.error(f"[{self.name}] Missing year_month in analysis_result")
            yield create_text_event(self.name, "Year-month missing in analysis result.")
            return

        try:
            # 2. Parse year and month
            # Format: YYYY-MM
            parts = year_month.split("-")
            if len(parts) != 2:
                raise ValueError(f"Invalid year_month format: {year_month}")
            
            year = int(parts[0])
            month = int(parts[1])
            
            # 3. Fetch data from services
            # Note: Coordination lat/lng might be needed for KMA in the future,
            # but currently kma_service uses stn_id defaulting to "108" (Seoul).
            irradiance_data = await kma_service.get_monthly_avg_irradiance(year, month)
            market_data = await kpx_service.get_monthly_avg_prices(year, month)
            
            # 4. Combine results and yield event
            combined_data = {}
            if hasattr(irradiance_data, "model_dump"):
                combined_data.update(irradiance_data.model_dump())
            else:
                combined_data.update(irradiance_data)

            if hasattr(market_data, "model_dump"):
                combined_data.update(market_data.model_dump())
            else:
                combined_data.update(market_data)
            
            logger.info(f"[{self.name}] Successfully fetched data for {year_month}")
            
            yield create_text_event(
                self.name,
                f"Fetched market and weather data for {year_month}.",
                state_delta={"market_data": combined_data}
            )
        except Exception as e:
            logger.error(f"[{self.name}] Error fetching data: {str(e)}", exc_info=True)
            yield create_text_event(self.name, f"Error fetching market/weather data: {str(e)}")
