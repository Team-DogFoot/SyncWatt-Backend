from pydantic import BaseModel, Field

class SettlementOcrData(BaseModel):
    year_month: str = Field(description="정산 연월 (예: 2024-02)")
    generation_kwh: float = Field(description="실제 발전량 (kWh)")
    unit_price: float = Field(default=0.0, description="정산 기준 단가 (원/kWh)")
    total_revenue_krw: int = Field(description="실제 총 수령액 (원)")
    address: str | None = Field(default=None, description="발전소 주소")
    selection_reason: str | None = Field(default=None, description="데이터 선택 사유 (로그용)")
