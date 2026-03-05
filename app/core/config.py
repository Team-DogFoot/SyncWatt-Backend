from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "SyncWatt-Backend"
    # .env 또는 환경변수에서 로드
    TELEGRAM_BOT_TOKEN: str
    WEBHOOK_SECRET_TOKEN: str | None = "syncwatt_secret_1234"
    
    # 텔레그램 API 베이스 URL
    TELEGRAM_API_URL: str = "https://api.telegram.org/bot"

    # Google Cloud & Gemini Settings
    GCP_SA_KEY: str | None = None
    GOOGLE_APPLICATION_CREDENTIALS: str | None = None
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
