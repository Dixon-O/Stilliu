"""
tests/conftest.py — shared pytest fixtures and env setup.
Forces demo_mode=true for all tests so no real API calls are made.
"""
import os
import pytest

# Override env before any module imports settings
os.environ.setdefault("WATSONX_API_KEY", "test-key")
os.environ.setdefault("WATSONX_PROJECT_ID", "test-project-id")
os.environ.setdefault("WATSONX_URL", "https://eu-gb.ml.cloud.ibm.com")
os.environ.setdefault("DEMO_MODE", "true")


@pytest.fixture(autouse=True)
def force_demo_mode(monkeypatch):
    """Ensure every test runs with demo_mode=true regardless of local .env."""
    monkeypatch.setenv("DEMO_MODE", "true")
    # Clear lru_cache so settings reload with the patched env
    from app.config import get_settings
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
