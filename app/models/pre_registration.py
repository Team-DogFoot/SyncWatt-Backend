from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field


class PreRegistration(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_chat_id: str = Field(index=True)
    registered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
