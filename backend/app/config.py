"""
config.py — loads all environment variables from .env
Never import secrets directly; always go through this module.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # watsonx.ai credentials
    watsonx_api_key: str
    watsonx_project_id: str
    watsonx_url: str = "https://eu-gb.ml.cloud.ibm.com"

    # Models
    generation_model_id: str = "ibm/granite-3-8b-instruct"
    embedding_model_id: str = "ibm/granite-embedding-125m-english"

    # Demo / fallback mode — set DEMO_MODE=true to serve fixture responses
    demo_mode: bool = False

    # API timeouts (seconds)
    watsonx_timeout: int = 8

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
