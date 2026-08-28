from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "InstallOps API"
    ENVIRONMENT: str = "development"
    TIMEZONE: str = "Europe/Kyiv"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/installops"
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_postgres_url(cls, v: str) -> str:
        if v and v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql://", 1)
        if v and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    
    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ADMIN_CHAT_ID: str = ""
    
    # Google Sheets
    GOOGLE_SPREADSHEET_ID: str = ""
    GOOGLE_SERVICE_ACCOUNT_FILE: str = ""
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""
    
    # External API
    EXTERNAL_API_URL: str = ""
    EXTERNAL_API_TOKEN: str = ""
    WEBHOOK_SECRET: str = ""
    
    # Thresholds
    SYNC_INTERVAL_MINUTES: int = 15
    MIN_INSTALLATIONS_FOR_RANKING: int = 10
    EMPLOYEE_POSTPONEMENT_ALERT_THRESHOLD: int = 3

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

settings = Settings()
