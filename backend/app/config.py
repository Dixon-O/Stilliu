"""
config.py — loads all environment variables from .env
Never import secrets directly; always go through this module.
"""
from functools import lru_cache
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # watsonx.ai credentials.
    #
    # Deliberately defaulted to empty rather than required. A required field here
    # means a fresh clone — which has no .env, since .env is gitignored — dies at
    # startup with a pydantic ValidationError before demo mode can be considered.
    # Anyone evaluating the project would see a stack trace instead of the app.
    # Absent credentials now mean "demo mode" (see `demo_mode` below), which is
    # the only sensible reading: there is nothing to authenticate with.
    watsonx_api_key: str = ""
    watsonx_project_id: str = ""
    watsonx_url: str = "https://eu-gb.ml.cloud.ibm.com"

    # Models — HYBRID strategy:
    #   Llama-3-3-70b  → creative persona rewrites (best instruction-following in eu-gb)
    #   Granite        → the "generic baseline" anchor + optional Guardian safety pass
    #   Granite-embed  → all distance measurement (voice, distinctiveness, on-message)
    generation_model_id: str = "meta-llama/llama-3-3-70b-instruct"
    # Baseline generation uses a Granite instruct model so the "bland default" is a
    # genuine watsonx Granite artifact. This is only a *request*: model_registry
    # resolves it against what the region actually hosts and walks down
    # BASELINE_PREFERENCES (granite-4-h-small, then the 3.x line) if it is absent,
    # so no single id can strand the measurement.
    baseline_model_id: str = "ibm/granite-4-h-small"
    # Granite Guardian — hallucination / safety review pass. Optional; skipped
    # gracefully if not available in-region.
    guardian_model_id: str = "ibm/granite-guardian-3-2-5b"
    enable_guardian: bool = False
    # Embedding: IBM Granite multilingual embedding (eu-gb available)
    embedding_model_id: str = "ibm/granite-embedding-278m-multilingual"

    # Demo / fallback mode — serves fixture responses instead of calling watsonx.
    # Set DEMO_MODE=true to force it on even with valid credentials. It also turns
    # itself on when credentials are missing (see the validator below), so a fresh
    # clone runs rather than failing on the first request.
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

    @model_validator(mode="after")
    def _demo_mode_without_credentials(self) -> "Settings":
        """
        No credentials means demo mode, whatever DEMO_MODE says.

        Without this, a checkout with no .env would start happily and then fail on
        the first request with an SDK authentication error — the worst possible
        place to discover the problem. Deciding it here means one code path owns
        the question "can we call watsonx at all?".
        """
        if not (self.watsonx_api_key and self.watsonx_project_id):
            object.__setattr__(self, "demo_mode", True)
        return self

    @property
    def has_credentials(self) -> bool:
        """True when watsonx can actually be called."""
        return bool(self.watsonx_api_key and self.watsonx_project_id)


@lru_cache
def get_settings() -> Settings:
    return Settings()
