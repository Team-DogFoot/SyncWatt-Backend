from pydantic import BaseModel, Field

class SettlementOcrData(BaseModel):
    year_month: str = Field(description="정산 연월 (예: 2024-02)")
    generation_kwh: float = Field(description="실제 발전량 (kWh)")
    unit_price: float = Field(default=0.0, description="정산 기준 단가 (원/kWh)")
    total_revenue_krw: int = Field(description="실제 총 수령액 (원)")
    capacity_kw: float | None = Field(default=None, description="발전소 설비용량 (kW)")
    address: str | None = Field(default=None, description="발전소 주소")
    issuer: str | None = Field(default=None, description="정산서 발행처 (예: 한국전력공사, 한수원, KPX 등)")
    selection_reason: str | None = Field(default=None, description="데이터 선택 사유 (로그용)")
