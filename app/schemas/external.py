from pydantic import BaseModel
from typing import Optional

class KMAMonthlyIrradianceResponse(BaseModel):
    year: int
    month: int
    avg_irradiance: float  # W/m² or MJ/m² depending on unit
    unit: str = "MJ/m²"
    stn_id: Optional[str] = None
    stn_name: Optional[str] = None

class KPXMonthlyPriceResponse(BaseModel):
    year: int
    month: int
    avg_smp: float  # 원/kWh
    avg_rec: float  # 원/REC
    smp_unit: str = "원/kWh"
    rec_unit: str = "원/REC"
