import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings configured via environment variables.
    """
    APP_NAME: str = "ai-code-review-bot"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # Database Settings
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "ai_code_review_db"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "your_postgres_password"
    DATABASE_URL: str = ""

    # Docker / Postgres Env Var Overrides
    POSTGRES_HOST: str = ""
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""

    # Redis & Celery Settings
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""
    USE_CELERY: bool = False

    # GitHub Settings
    GITHUB_TOKEN: str = ""
    GITHUB_API_URL: str = "https://api.github.com"
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_REVIEW_MODE: str = "COMMENT"

    # LLM Settings (Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"
    LLM_MAX_FILE_SIZE: int = 500 * 1024  # 500 KB
    LLM_MAX_DIFF_SIZE: int = 100 * 1024  # 100 KB
    LLM_MAX_FILES_PER_REVIEW: int = 15

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def redis_broker_url(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def redis_backend_url(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL


    @property
    def cors_origins_list(self) -> List[str]:
        """
        Parses comma-separated CORS_ORIGINS string into a list of strings.
        """
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return ["http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache()
def get_settings() -> Settings:
    """
    Cached getter for application settings.
    """
    return Settings()
