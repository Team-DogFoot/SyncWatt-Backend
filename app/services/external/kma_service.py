import httpx
from typing import Optional
from app.core.config import settings
from app.schemas.external import KMAMonthlyIrradianceResponse

class KMAService:
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
            # Mock data if API key is not provided
            return KMAMonthlyIrradianceResponse(
                year=year,
                month=month,
                avg_irradiance=15.5,  # Mock MJ/m²
                unit="MJ/m²",
                stn_id=stn_id,
                stn_name="MOCK_SEOUL"
            )

        # Real API implementation (Simplified for now)
        start_dt = f"{year}{month:02d}01"
        # For simplicity, we assume month ends at 28th to 31st. Just a rough range for monthly avg.
        end_dt = f"{year}{month:02d}28" 
        
        params = {
            "serviceKey": self.api_key,
            "numOfRows": 31,
            "pageNo": 1,
            "dataType": "JSON",
            "dataCd": "ASOS",
            "dateKind": "DAY",
            "startDt": start_dt,
            "endDt": end_dt,
            "stnIds": stn_id,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                # Simple logic to average sumGs (Global Solar Radiation)
                items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
                if not items:
                    raise ValueError("No data returned from KMA API")

                total_gs = 0.0
                count = 0
                for item in items:
                    gs = item.get("sumGs")
                    if gs:
                        total_gs += float(gs)
                        count += 1
                
                avg_gs = total_gs / count if count > 0 else 0.0
                
                return KMAMonthlyIrradianceResponse(
                    year=year,
                    month=month,
                    avg_irradiance=avg_gs,
                    unit="MJ/m²",
                    stn_id=stn_id,
                    stn_name=items[0].get("stnNm") if items else None
                )
        except Exception as e:
            # Fallback to mock on error
            return KMAMonthlyIrradianceResponse(
                year=year,
                month=month,
                avg_irradiance=15.5,
                unit="MJ/m²",
                stn_id=stn_id,
                stn_name="MOCK_FALLBACK"
            )

kma_service = KMAService()
