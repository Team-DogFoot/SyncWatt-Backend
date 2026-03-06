from datetime import datetime, timezone
from sqlmodel import SQLModel, Field


class MonthlySettlement(SQLModel, table=True):
    settlement_id: int | None = Field(default=None, primary_key=True)
    plant_id: int | None = Field(default=None, foreign_key="powerplant.plant_id", nullable=True) # 가입 전 OCR은 plant_id 없음
    telegram_chat_id: str | None = Field(index=True, nullable=True) # 가입 전 유저 식별용
    year_month: str # 예: "2019-12"
    actual_generation_kwh: float
    actual_revenue_krw: int
    smp_avg: float | None = None
    irradiance_avg: float | None = None
    optimal_revenue_krw: int | None = None
    opportunity_cost_krw: int | None = None
    loss_reason: str | None = None # weather / smp / complex / unknown
    source: str # ocr / eds_api / excel_upload
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
