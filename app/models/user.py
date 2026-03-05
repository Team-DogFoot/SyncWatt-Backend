import uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    telegram_chat_id: Mapped[str] = mapped_column(unique=True, index=True)
    plan: Mapped[str] = mapped_column(default="free") # free, pro
