from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "InstallOps API"
    ENVIRONMENT: str = "development"
    TIMEZONE: str = "Europe/Kyiv"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/installops"
    
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
