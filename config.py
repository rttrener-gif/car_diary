"""Application configuration via pydantic BaseSettings."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    TELEGRAM_BOT_TOKEN: str
    GEMINI_API_KEY: str
    DATABASE_URL: str

    REMINDER_CHECK_TIME: str = "09:00"
    MAX_CONVERSATION_HISTORY: int = 20


settings = Settings()  # type: ignore[call-arg]
