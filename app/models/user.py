from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)
    telegram_chat_id: Optional[str] = Field(default=None, unique=True, index=True)
    kakao_id: Optional[str] = Field(default=None, unique=True, index=True)
    kakao_nickname: Optional[str] = None
    kakao_email: Optional[str] = None
    phone: Optional[str] = None
    plan: str = Field(default="free")
    plant_count: int = Field(default=0)
    link_code: Optional[str] = Field(default=None, unique=True)
    link_code_expires: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
