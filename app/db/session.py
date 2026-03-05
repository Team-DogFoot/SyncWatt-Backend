from sqlmodel import create_engine, SQLModel, Session
from app.core.config import settings

# engine = create_engine(settings.DATABASE_URL, echo=True) # echo=True for development logs
engine = create_engine(settings.DATABASE_URL)

def init_db():
    # This will create tables if they don't exist
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
