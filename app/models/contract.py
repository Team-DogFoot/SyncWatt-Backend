from datetime import datetime, date
from typing import Optional
from sqlmodel import SQLModel, Field

class ContractHistory(SQLModel, table=True):
    history_id: Optional[int] = Field(default=None, primary_key=True)
    plant_id: int = Field(foreign_key="powerplant.plant_id")
    contract_type: str # kepco / kpx
    start_date: date
    end_date: Optional[date] = None # null이면 현재 계약
    triggered_by: str # initial / syncwatt_recommendation / self
    created_at: datetime = Field(default_factory=datetime.utcnow)
