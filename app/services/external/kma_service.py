import calendar
import httpx
import logging
from app.core.config import settings
from app.schemas.external import KMAMonthlyIrradianceResponse

logger = logging.getLogger(__name__)

class KMAService:
    DEFAULT_IRRADIANCE = 15.5 # Mock MJ/m² (Proxy avg)

    def __init__(self):
        self.api_key = settings.KMA_API_KEY
        self.base_url = "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"

    async def get_monthly_avg_irradiance(
        self, year: int, month: int, stn_id: str = "108"
    ) -> KMAMonthlyIrradianceResponse:
        """
        Fetches monthly average irradiance for a given year and month.
        If API key is missing or request fails, returns mock data.
        """
        if not self.api_key:
            logger.info(f"[KMA] No API key. Using default irradiance: {self.DEFAULT_IRRADIANCE}")
            # Mock data if API key is not provided
            return KMAMonthlyIrradianceResponse(
                year=year,
                month=month,
                avg_irradiance=self.DEFAULT_IRRADIANCE,
                unit="MJ/m²",
                stn_id=stn_id,
                stn_name="MOCK_SEOUL"
            )

        # Real API implementation (Simplified for now)
        start_dt = f"{year}{month:02d}01"
        last_day = calendar.monthrange(year, month)[1]
        end_dt = f"{year}{month:02d}{last_day}"
        
        params = {
            "serviceKey": self.api_key,
            "numOfRows": 31,
            "pageNo": 1,
            "dataType": "JSON",
            "dataCd": "ASOS",
            "dateCd": "DAY",
            "startDt": start_dt,
            "endDt": end_dt,
            "stnIds": stn_id,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params, timeout=15.0)
                response.raise_for_status()
                data = response.json()
                
                # Simple logic to average sumGs (Global Solar Radiation)
                items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
                if not items:
                    logger.warning(f"[KMA] No weather data found for {year}-{month} at stn {stn_id}. Using default: {self.DEFAULT_IRRADIANCE}")
                    return KMAMonthlyIrradianceResponse(
                        year=year, month=month, avg_irradiance=self.DEFAULT_IRRADIANCE, unit="MJ/m²", stn_id=stn_id, stn_name="API_NO_DATA_FALLBACK"
                    )

                total_gs = 0.0
                count = 0
                for item in items:
                    gs = item.get("sumGsr")
                    if gs and str(gs).strip():
                        total_gs += float(gs)
                        count += 1
                
                avg_gs = total_gs / count if count > 0 else self.DEFAULT_IRRADIANCE 
                if count == 0:
                    logger.warning(f"[KMA] Irradiance sum was 0 for {year}-{month}. Using default: {self.DEFAULT_IRRADIANCE}")
                
                return KMAMonthlyIrradianceResponse(
                    year=year,
                    month=month,
                    avg_irradiance=avg_gs,
                    unit="MJ/m²",
                    stn_id=stn_id,
                    stn_name=items[0].get("stnNm") if items else "UNKNOWN"
                )
        except Exception as e:
            logger.error(f"KMA API Error ({year}-{month}): {str(e)}. Using default: {self.DEFAULT_IRRADIANCE}")
            # Fallback to mock on error
            return KMAMonthlyIrradianceResponse(
                year=year,
                month=month,
                avg_irradiance=self.DEFAULT_IRRADIANCE,
                unit="MJ/m²",
                stn_id=stn_id,
                stn_name="MOCK_FALLBACK"
            )

kma_service = KMAService()
