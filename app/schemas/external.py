from pydantic import BaseModel

class KMAMonthlyIrradianceResponse(BaseModel):
    year: int
    month: int
    avg_irradiance: float  # W/m² or MJ/m² depending on unit
    unit: str = "MJ/m²"
    stn_id: str | None = None
    stn_name: str | None = None

class KPXMonthlyPriceResponse(BaseModel):
    year: int
    month: int
    avg_smp: float  # 원/kWh
    avg_rec: float  # 원/REC
    smp_unit: str = "원/kWh"
    rec_unit: str = "원/REC"
