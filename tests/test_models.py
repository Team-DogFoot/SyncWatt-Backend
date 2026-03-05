import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from app.models.base import Base
from app.models.user import User
from app.models.plant import PowerPlant
from app.models.settlement import MonthlySettlement, LossCause
import uuid

@pytest.mark.asyncio
async def test_model_instantiation():
    user = User(telegram_chat_id="12345678", plan="free")
    assert user.telegram_chat_id == "12345678"
    assert user.plan == "free"
    
    plant = PowerPlant(
        user_id=user.id,
        name="Test Plant",
        capacity_kw=100.5,
        address="123 Solar St"
    )
    assert plant.name == "Test Plant"
    assert plant.capacity_kw == 100.5

    settlement = MonthlySettlement(
        plant_id=plant.id,
        year_month="2024-03",
        actual_generation_kwh=1000.0,
        actual_revenue_krw=200000.0,
        optimal_revenue_krw=220000.0,
        opportunity_loss_krw=20000.0,
        loss_cause=LossCause.SHADING
    )
    assert settlement.year_month == "2024-03"
    assert settlement.loss_cause == LossCause.SHADING

@pytest.mark.asyncio
async def test_metadata_creation():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
