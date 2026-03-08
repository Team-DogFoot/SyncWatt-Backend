from fastapi import APIRouter
from app.schemas.calculator import ROIRequest, ROIResponse

router = APIRouter(prefix="/api/v1/calculator", tags=["calculator"])


@router.post("/roi", response_model=ROIResponse)
async def calculate_roi(req: ROIRequest):
    AVG_SMP = 120.0
    AVG_SUNSHINE = 3.5
    SYSTEM_EFFICIENCY = 0.78
    FORECAST_IMPROVEMENT = 0.15

    daily_gen = req.capacity_kw * AVG_SUNSHINE * SYSTEM_EFFICIENCY
    annual_optimal = daily_gen * 365 * AVG_SMP
    annual_current = annual_optimal * 0.85
    annual_saving = annual_optimal * FORECAST_IMPROVEMENT

    return ROIResponse(
        capacity_kw=req.capacity_kw,
        avg_smp_krw=AVG_SMP,
        avg_sunshine_hours=AVG_SUNSHINE,
        annual_optimal_krw=int(annual_optimal),
        annual_current_est_krw=int(annual_current),
        annual_saving_krw=int(annual_saving),
        monthly_saving_krw=int(annual_saving / 12),
    )
