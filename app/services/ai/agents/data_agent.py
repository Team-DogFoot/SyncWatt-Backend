import logging
import time
import asyncio
from google.adk.agents import BaseAgent
from app.services.external.kma_service import kma_service
from app.services.external.kpx_service import kpx_service
from app.services.ai.utils import create_text_event
from app.schemas.ai.settlement import SettlementOcrData

logger = logging.getLogger(__name__)

class DataFetcherAgent(BaseAgent):
    """
    정산 연월을 기준으로 기상청 일조량 데이터와 KPX 시장 단가 데이터를 조회하는 에이전트입니다.
    """
    def __init__(self):
        super().__init__(
            name="data_fetcher",
            description="정산 기간에 따른 날씨 및 시장 데이터를 조회합니다."
        )
        logger.info(f"[{self.name}] 에이전트가 초기화되었습니다.")

    async def _run_async_impl(self, ctx):
        start_t = time.perf_counter()
        logger.info(f"[{self.name}] 외부 데이터 조회 시작")
        
        settlement_data = ctx.session.state.get("settlement_data")
        if not settlement_data:
            logger.error(f"[{self.name}] 세션에서 settlement_data를 찾을 수 없습니다.")
            yield create_text_event(self.name, "정산 데이터가 누락되어 외부 데이터를 조회할 수 없습니다.")
            return

        if isinstance(settlement_data, dict):
            settlement_data = SettlementOcrData.model_validate(settlement_data)

        year_month = settlement_data.year_month

        try:
            year, month = map(int, year_month.split("-"))
            
            irradiance_task = kma_service.get_monthly_avg_irradiance(year, month)
            market_task = kpx_service.get_monthly_avg_prices(year, month)
            
            irradiance_data, market_data = await asyncio.gather(irradiance_task, market_task)
            
            combined_market_data = {}
            for data in [irradiance_data, market_data]:
                if hasattr(data, "model_dump"):
                    combined_market_data.update(data.model_dump())
                else:
                    combined_market_data.update(data)
            
            duration = time.perf_counter() - start_t
            logger.info(f"[{self.name}] 데이터 조회 성공: {year_month} (소요시간: {duration:.2f}초)")
            
            yield create_text_event(
                self.name,
                f"{year_month} 기준 기상 및 시장 데이터 조회를 완료했습니다.",
                state_delta={"market_data": combined_market_data}
            )
            
        except Exception as e:
            logger.error(f"[{self.name}] 데이터 조회 중 오류 발생: {str(e)}", exc_info=True)
            yield create_text_event(self.name, f"외부 데이터 조회 중 문제가 발생했습니다: {str(e)}")
