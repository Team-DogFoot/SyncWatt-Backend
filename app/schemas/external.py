from pydantic import BaseModel


class IrradianceData(BaseModel):
    """일사량 데이터 (Provider 공통)"""
    year: int
    month: int
    avg_irradiance: float  # kWh/m²/day (일평균)
    latitude: float
    longitude: float
    source: str  # "nasa_power", "solcast", "kma" 등


class KPXMonthlyPriceResponse(BaseModel):
    year: int
    month: int
    avg_smp: float  # 원/kWh
    avg_rec: float  # 원/REC
    smp_unit: str = "원/kWh"
    rec_unit: str = "원/REC"
