from pydantic import BaseModel, Field

class SettlementOcrData(BaseModel):
    year_month: str = Field(description="정산 연월 (예: 2024-02)")
    generation_kwh: float = Field(description="실제 발전량 (kWh)")
    total_revenue_krw: int = Field(description="실제 총 수령액 (원)")
