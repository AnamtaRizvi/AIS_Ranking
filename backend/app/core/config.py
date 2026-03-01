"""Environment and app settings."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./app.db"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENALEX_MAILTO: str = ""
    OPENALEX_BASE_URL: str = "https://api.openalex.org"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
