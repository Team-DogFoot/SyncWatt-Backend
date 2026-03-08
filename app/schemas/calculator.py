from pydantic import BaseModel, Field


class ROIRequest(BaseModel):
    capacity_kw: float = Field(gt=0, le=1000, description="설비 용량 (kW)")


class ROIResponse(BaseModel):
    capacity_kw: float
    avg_smp_krw: float
    avg_sunshine_hours: float
    annual_optimal_krw: int
    annual_current_est_krw: int
    annual_saving_krw: int
    monthly_saving_krw: int
