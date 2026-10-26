import os

import pytest

from core import report_ai


@pytest.fixture(autouse=True)
def isolate_ai_settings(monkeypatch):
    """Tests must never read the real keys in .env or call a real AI service: start from no keys and no network."""
    monkeypatch.setattr(report_ai, "_env", lambda name: os.environ.get(name, "").strip())
    monkeypatch.setattr(report_ai, "_models_list", lambda s: [])
    for name in ("GROQ_API_KEY", "CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN", "LLM_PROVIDER", "LLM_MODEL", "LLM_BASE_URL", "LLM_API_KEY"):
        monkeypatch.delenv(name, raising=False)
