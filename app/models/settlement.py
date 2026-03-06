from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
from app.schemas.ai.diagnosis import LossCause

class MonthlySettlement(SQLModel, table=True):
    settlement_id: Optional[int] = Field(default=None, primary_key=True)
    plant_id: Optional[int] = Field(default=None, foreign_key="powerplant.plant_id", nullable=True) # 가입 전 OCR은 plant_id 없음
    telegram_chat_id: Optional[str] = Field(index=True, nullable=True) # 가입 전 유저 식별용
    year_month: str # 예: "2019-12"
    actual_generation_kwh: float
    actual_revenue_krw: int
    smp_avg: Optional[float] = None
    irradiance_avg: Optional[float] = None
    optimal_revenue_krw: Optional[int] = None
    opportunity_cost_krw: Optional[int] = None
    loss_reason: Optional[LossCause] = None # weather / smp / complex / unknown
    source: str # ocr / eds_api / excel_upload
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
