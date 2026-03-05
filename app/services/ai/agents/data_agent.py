import logging
import datetime
from google.adk.agents import BaseAgent
from app.services.external.kma_service import kma_service
from app.services.external.smp_service import smp_service
from app.services.ai.utils import create_text_event

logger = logging.getLogger(__name__)

class DataFetcherAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="data_fetcher",
            description="Fetches weather and market data based on the settlement period"
        )

    async def _run_async_impl(self, ctx):
        settlement_data = ctx.session.state.get("settlement_data")
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
            # 4. Fetch SMP (Current vs Prev Month)
            curr_smp = smp_service.get_avg_smp(year_month)
            prev_smp = smp_service.get_avg_smp(prev_year_month)
            
            logger.info(f"[{self.name}] DB SMP lookup: {year_month} -> {curr_smp}, {prev_year_month} -> {prev_smp}")
            
            if curr_smp is None or prev_smp is None:
                missing_msg = f"[{self.name}] SMP data missing for {year_month} or {prev_year_month}. Diagnosis cannot proceed."
                logger.error(missing_msg)
                # market_data 키는 생성하되 빈 값을 넣어 뒤 단계의 KeyError 방지
                yield create_text_event(
                    self.name, 
                    f"시장 가격(SMP) 데이터가 부족하여 분석을 진행할 수 없습니다. (대상 월: {year_month})",
                    state_delta={"market_data": {"year_month": year_month, "curr_smp": 0, "prev_smp": 0, "curr_irr": 0, "prev_year_irr": 0}}
                )
                return
            
            # 5. Fetch Irradiance (Current vs Last Year Same Month)
            # 주소에 따른 관측소(stn_id) 처리 (태양광 밀집 지역 위주 확대)
            stn_id = "108" # Default (Seoul)
            if address:
                # 주요 도별 대표 관측소 매핑
                if any(x in address for x in ["전남", "전라남도", "목포", "무안"]):
                    stn_id = "165" # 목포
                elif any(x in address for x in ["전북", "전라북도", "전주"]):
                    stn_id = "146" # 전주
                elif any(x in address for x in ["충남", "충청남도", "홍성", "천안"]):
                    stn_id = "129" # 서산(충남 인근)
                elif any(x in address for x in ["충북", "충청북도", "청주"]):
                    stn_id = "131" # 청주
                elif any(x in address for x in ["경남", "경상남도", "창원", "진주"]):
                    stn_id = "155" # 창원
                elif any(x in address for x in ["경북", "경상북도", "안동", "포항"]):
                    stn_id = "138" # 포항
                elif any(x in address for x in ["부산"]):
                    stn_id = "159"
                elif any(x in address for x in ["대구"]):
                    stn_id = "143"
                elif any(x in address for x in ["광주"]):
                    stn_id = "156"
                elif any(x in address for x in ["대전"]):
                    stn_id = "133"
                elif any(x in address for x in ["울산"]):
                    stn_id = "152"
                elif any(x in address for x in ["제주"]):
                    stn_id = "184"
                
                logger.info(f"[{self.name}] Address found: {address}. Using stn_id: {stn_id}")
            else:
                logger.info(f"[{self.name}] No address found. Using national average (Seoul 108 as proxy).")

            curr_irr_data = await kma_service.get_monthly_avg_irradiance(year, month, stn_id=stn_id)
            prev_year_irr_data = await kma_service.get_monthly_avg_irradiance(year - 1, month, stn_id=stn_id)
            
            market_data = {
                "year_month": year_month,
                "curr_smp": curr_smp,
                "prev_smp": prev_smp,
                "curr_irr": curr_irr_data.avg_irradiance,
                "prev_year_irr": prev_year_irr_data.avg_irradiance,
                "stn_id": stn_id,
                "address_used": True if address else False
            }
            
            logger.info(f"[{self.name}] Data fetched for {year_month}: "
                        f"SMP({curr_smp} vs {prev_smp}), "
                        f"Irr({curr_irr_data.avg_irradiance} vs {prev_year_irr_data.avg_irradiance})")
            
            yield create_text_event(
                self.name,
                f"Fetched data for {year_month}.",
                state_delta={"market_data": market_data}
            )
        except Exception as e:
            logger.error(f"[{self.name}] Error fetching data: {str(e)}", exc_info=True)
            yield create_text_event(self.name, f"Error fetching market/weather data: {str(e)}")
