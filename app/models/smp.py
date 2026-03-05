from typing import Optional
from sqlmodel import SQLModel, Field

class SMP(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    year_month: str = Field(unique=True, index=True) # 예: "2024-02"
    avg_smp: float
