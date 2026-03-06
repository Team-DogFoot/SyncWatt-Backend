from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "SyncWatt-Backend"
    # .env 또는 환경변수에서 로드
    TELEGRAM_BOT_TOKEN: str
    WEBHOOK_SECRET_TOKEN: str | None = None
    
    # 텔레그램 API 베이스 URL
    TELEGRAM_API_URL: str = "https://api.telegram.org/bot"

    # Google Cloud & Gemini Settings
    GCP_SA_KEY: str | None = None
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    GOOGLE_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"
    # Database Settings
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/syncwatt"
    POSTGRES_USER: str | None = "postgres"
    POSTGRES_PASSWORD: str | None = "postgres"
    POSTGRES_DB: str | None = "syncwatt"

    # External Data API Keys
    KPX_API_KEY: str | None = None

    # AWS S3 (이미지 저장)
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_S3_BUCKET: str = "syncwatt-images"
    AWS_REGION: str = "ap-northeast-2"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
