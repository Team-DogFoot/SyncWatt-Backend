import uuid
from enum import Enum
from sqlalchemy import ForeignKey, String, Float, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class LossCause(str, Enum):
    PANEL_AGING = "PANEL_AGING"
    INVERTER_FAULT = "INVERTER_FAULT"
    SHADING = "SHADING"
    SNOW_COVER = "SNOW_COVER"
    DUST_POLLUTION = "DUST_POLLUTION"
    GRID_LIMIT = "GRID_LIMIT"
    UNKNOWN = "UNKNOWN"

class MonthlySettlement(Base):
    __tablename__ = "monthly_settlements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("power_plants.id"), index=True)
    year_month: Mapped[str] = mapped_column(String(7), index=True) # "YYYY-MM"
    
    actual_generation_kwh: Mapped[float] = mapped_column(Float)
    actual_revenue_krw: Mapped[float] = mapped_column(Float)
    optimal_revenue_krw: Mapped[float] = mapped_column(Float)
    opportunity_loss_krw: Mapped[float] = mapped_column(Float)
    
    loss_cause: Mapped[LossCause] = mapped_column(SQLEnum(LossCause), default=LossCause.UNKNOWN)

    plant: Mapped["PowerPlant"] = relationship("PowerPlant", backref="settlements")
