from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # .env 또는 환경변수에서 로드
    TELEGRAM_BOT_TOKEN: str
    WEBHOOK_SECRET_TOKEN: str | None = "syncwatt_secret_1234"
    
    # 텔레그램 API 베이스 URL
    TELEGRAM_API_URL: str = "https://api.telegram.org/bot"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
