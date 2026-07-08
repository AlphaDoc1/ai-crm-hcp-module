"""
app/core/config.py
Application settings loaded from environment variables via pydantic-settings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:hcp123@localhost:5432/hcp_crm"

    # Groq LLM
    groq_api_key: str = ""

    # Primary and fallback models
    # gemma2-9b-it was deprecated/shut down by Groq in October 2025.
    # Replaced with openai/gpt-oss-20b (primary) and openai/gpt-oss-120b (fallback),
    # both purpose-built for agentic tool-use workflows on Groq.
    primary_model: str = "openai/gpt-oss-20b"
    fallback_model: str = "openai/gpt-oss-120b"

    # App
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origin: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
