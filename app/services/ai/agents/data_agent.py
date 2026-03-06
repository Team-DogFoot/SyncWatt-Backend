import logging
import datetime
from google.adk.agents import BaseAgent
from app.services.external.kma_service import kma_service
from app.services.external.smp_service import smp_service
from app.services.ai.utils import create_text_event
from app.services.ai.state_keys import SETTLEMENT_DATA, MARKET_DATA

logger = logging.getLogger(__name__)

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

        # settlement_data is SettlementOcrData schema (Pydantic model)
        year_month = settlement_data.year_month
        address = settlement_data.address

        try:
            # 1. Parse year and month
            parts = year_month.split("-")
            year = int(parts[0])
            month = int(parts[1])
            
            curr_dt = datetime.date(year, month, 1)
            
            # 2. Previous month for SMP comparison
            prev_month_dt = (curr_dt - datetime.timedelta(days=1)).replace(day=1)
            prev_year_month = prev_month_dt.strftime("%Y-%m")
            
            # 3. Last year same month for Irradiance comparison
            prev_year_dt = datetime.date(year - 1, month, 1)
            
            # 4. Fetch SMP (Current vs Prev Month)
            curr_smp = smp_service.get_avg_smp(year_month)
            prev_smp = smp_service.get_avg_smp(prev_year_month)
            
            logger.info(f"[{self.name}] DB SMP lookup: {year_month} -> {curr_smp}, {prev_year_month} -> {prev_smp}")
            
            error_smp = False
            if curr_smp is None or prev_smp is None:
                logger.warning(f"[{self.name}] SMP data missing for {year_month} or {prev_year_month}. Setting error flag.")
                error_smp = True
            
            # 5. Fetch Irradiance (Current vs Last Year Same Month)
            # 주소에 따른 관측소(stn_id) 처리 (태양광 밀집 지역 위주 확대)
            stn_id = "108" # Default (Seoul)
            match_reason = "default (Seoul)"
            
            if address:
                # 주요 도별 대표 관측소 매핑
                if any(x in address for x in ["전남", "전라남도"]):
                    if any(x in address for x in ["해남"]):
                        stn_id = "261" # 해남
                        match_reason = "Jeonnam Haenam"
                    elif any(x in address for x in ["영암", "목포", "무안"]):
                        stn_id = "165" # 목포 (영암 인근)
                        match_reason = "Jeonnam West (Mokpo/Yeongam)"
                    else:
                        stn_id = "165" # Default Jeonnam
                        match_reason = "Jeonnam general"
                elif any(x in address for x in ["전북", "전라북도", "전주"]):
                    stn_id = "146" # 전주
                    match_reason = "Jeonbuk"
                elif any(x in address for x in ["충남", "충청남도", "홍성", "천안"]):
                    stn_id = "129" # 서산(충남 인근)
                    match_reason = "Chungnam"
                elif any(x in address for x in ["충북", "충청북도", "청주"]):
                    stn_id = "131" # 청주
                    match_reason = "Chungbuk"
                elif any(x in address for x in ["경남", "경상남도", "창원", "진주"]):
                    stn_id = "155" # 창원
                    match_reason = "Gyeongnam"
                elif any(x in address for x in ["경북", "경상북도"]):
                    if any(x in address for x in ["의성"]):
                        stn_id = "278" # 의성
                        match_reason = "Gyeongbuk Uiseong"
                    elif any(x in address for x in ["영주"]):
                        stn_id = "272" # 영주
                        match_reason = "Gyeongbuk Yeongju"
                    elif any(x in address for x in ["안동"]):
                        stn_id = "136" # 안동
                        match_reason = "Gyeongbuk Andong"
                    elif any(x in address for x in ["포항"]):
                        stn_id = "138" # 포항
                        match_reason = "Gyeongbuk Pohang"
                    else:
                        stn_id = "143" # 대구 (Gyeongbuk proxy)
                        match_reason = "Gyeongbuk general"
                elif any(x in address for x in ["경기", "경기도"]):
                    if any(x in address for x in ["안성", "평택", "수원"]):
                        stn_id = "119" # 수원 (경기 남부)
                        match_reason = "Gyeonggi South"
                    else:
                        stn_id = "108" # 서울 (경기 북부/일반)
                        match_reason = "Gyeonggi general"
                elif any(x in address for x in ["강원", "강원도"]):
                    if any(x in address for x in ["춘천"]):
                        stn_id = "101" # 춘천
                        match_reason = "Gangwon Chuncheon"
                    elif any(x in address for x in ["원주"]):
                        stn_id = "114" # 원주
                        match_reason = "Gangwon Wonju"
                    else:
                        stn_id = "101" # Default Gangwon
                        match_reason = "Gangwon general"
                elif "부산" in address:
                    stn_id = "159"
                    match_reason = "Busan"
                elif "대구" in address:
                    stn_id = "143"
                    match_reason = "Daegu"
                elif "광주" in address:
                    stn_id = "156"
                    match_reason = "Gwangju"
                elif "대전" in address:
                    stn_id = "133"
                    match_reason = "Daejeon"
                elif "울산" in address:
                    stn_id = "152"
                    match_reason = "Ulsan"
                elif "제주" in address:
                    stn_id = "184"
                    match_reason = "Jeju"
                
                logger.info(f"[{self.name}] Address found: {address}. Using stn_id: {stn_id} ({match_reason})")
            else:
                logger.info(f"[{self.name}] No address found. Using national average (Seoul 108 as proxy).")

            curr_irr_data = await kma_service.get_monthly_avg_irradiance(curr_dt.year, curr_dt.month, stn_id=stn_id)
            prev_year_irr_data = await kma_service.get_monthly_avg_irradiance(prev_year_dt.year, prev_year_dt.month, stn_id=stn_id)
            
            market_data = {
                "year_month": year_month,
                "curr_smp": curr_smp,
                "prev_smp": prev_smp,
                "curr_irr": curr_irr_data.avg_irradiance,
                "prev_year_irr": prev_year_irr_data.avg_irradiance,
                "stn_id": stn_id,
                "address_used": True if address else False,
                "error_smp": error_smp
            }
            
            logger.info(f"[{self.name}] Data fetched for {year_month}: "
                        f"SMP({curr_smp} vs {prev_smp}, error={error_smp}), "
                        f"Irr({curr_irr_data.avg_irradiance} vs {prev_year_irr_data.avg_irradiance})")
            
            yield create_text_event(
                self.name,
                f"Fetched data for {year_month}.",
                state_delta={MARKET_DATA: market_data}
            )
        except Exception as e:
            logger.error(f"[{self.name}] Error fetching data: {str(e)}", exc_info=True)
            yield create_text_event(self.name, f"Error fetching market/weather data: {str(e)}")
