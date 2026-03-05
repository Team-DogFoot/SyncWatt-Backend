from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class User(SQLModel, table=True):
    user_id: Optional[int] = Field(default=None, primary_key=True)
    telegram_chat_id: str = Field(unique=True, index=True)
    kakao_id: Optional[str] = None
    phone: Optional[str] = None
    plan: str = Field(default="free") # free / standard / pro
    plant_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
