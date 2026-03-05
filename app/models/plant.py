from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel, Field

class PowerPlant(SQLModel, table=True):
    plant_id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.user_id")
    name: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    capacity_kw: Optional[float] = None
    contract_type: Optional[str] = None # kepco / kpx
    inverter_brand: Optional[str] = None
    commission_date: Optional[date] = None
    eds_linked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
