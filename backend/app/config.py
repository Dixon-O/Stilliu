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
    # Generation: llama-3-3-70b is the best available in eu-gb region
    generation_model_id: str = "meta-llama/llama-3-3-70b-instruct"
    # Embedding: IBM Granite multilingual embedding (eu-gb available)
    embedding_model_id: str = "ibm/granite-embedding-278m-multilingual"

    # Demo / fallback mode — set DEMO_MODE=true to serve fixture responses
    demo_mode: bool = False

    # Timeouts (seconds) — based on measured eu-gb latency:
    #   embed call (warm):  ~1s  |  cold: ~8s
    #   generate (warm):    ~8s  |  cold: ~12s
    #   score_timeout covers: embed + generate + embed = ~12s warm / ~28s cold
    #   analyze_timeout covers: score + 3x parallel generate + 3x embed = ~25s warm
    score_timeout: int = 60
    analyze_timeout: int = 120

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
