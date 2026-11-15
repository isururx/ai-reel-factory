from unittest.mock import patch

import pytest

from app.core.settings import settings
from app.services import script_generation


def test_primary_failure_switches_immediately_to_gemini_fallback():
    calls = []

    class FakeGeminiProvider:
        def __init__(self, model=None):
            self.model = model

        def generate_json(self, prompt):
            calls.append(self.model)
            if self.model == "gemini-3.5-flash-lite":
                raise RuntimeError("503 Service Unavailable")
            return '{"ok": true}'

    with (
        patch.object(settings, "llm_model", "gemini-3.5-flash-lite"),
        patch.object(settings, "gemini_fallback_model", "gemini-2.5-flash"),
        patch.object(script_generation, "GeminiProvider", FakeGeminiProvider),
    ):
        raw, metadata = script_generation._generate_with_fallback("test prompt")

    assert raw == '{"ok": true}'
    assert calls == ["gemini-3.5-flash-lite", "gemini-2.5-flash"]
    assert metadata["provider"] == "gemini"
    assert metadata["model"] == "gemini-2.5-flash"
    assert [attempt["status"] for attempt in metadata["attempts"]] == ["failed", "succeeded"]


def test_same_primary_and_fallback_model_is_not_called_twice():
    calls = []

    class FakeGeminiProvider:
        def __init__(self, model=None):
            self.model = model

        def generate_json(self, prompt):
            calls.append(self.model)
            raise RuntimeError("temporary failure")

    with (
        patch.object(settings, "llm_model", "gemini-2.5-flash"),
        patch.object(settings, "gemini_fallback_model", "gemini-2.5-flash"),
        patch.object(script_generation, "GeminiProvider", FakeGeminiProvider),
    ):
        with pytest.raises(RuntimeError, match="all configured Gemini models"):
            script_generation._generate_with_fallback("test prompt")

    assert calls == ["gemini-2.5-flash"]
