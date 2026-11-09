from app.services import reference_video_analysis as analysis


def _valid_result():
    return {"summary": "A short explainer.", "creative_elements": []}


def test_provider_chain_uses_gemini_primary_then_gemini_fallback(monkeypatch):
    monkeypatch.setattr(analysis.settings, "gemini_analysis_model", "gemini-3.5-flash-lite")
    monkeypatch.setattr(analysis.settings, "gemini_fallback_model", "gemini-2.5-flash")
    calls = []

    def gemini(path, prompt, model):
        calls.append(("gemini", model))
        if model == "gemini-3.5-flash-lite":
            raise RuntimeError("503 UNAVAILABLE")
        return _valid_result(), 100, 20

    monkeypatch.setattr(analysis, "_gemini_analyze", gemini)
    result = analysis.analyze_video_with_fallback("video.mp4", {})
    assert calls == [("gemini", "gemini-3.5-flash-lite"), ("gemini", "gemini-2.5-flash")]
    assert result.provider == "gemini"
    assert result.model_id == "gemini-2.5-flash"
    assert [item.status for item in result.attempts] == ["failed", "completed"]
    assert result.attempts[0].error_code == "RuntimeError"
    assert result.attempts[1].input_tokens == 100


def test_manual_gemini_primary_runs_first(monkeypatch):
    monkeypatch.setattr(analysis.settings, "gemini_analysis_model", "gemini-3.5-flash-lite")
    monkeypatch.setattr(analysis.settings, "gemini_fallback_model", "gemini-2.5-flash")
    calls = []
    def succeed(path, prompt, model):
        calls.append(("gemini", model))
        return _valid_result(), None, None
    monkeypatch.setattr(analysis, "_gemini_analyze", succeed)
    result = analysis.analyze_video_with_fallback("video.mp4", {}, primary_provider="gemini", primary_model="gemini-2.5-flash")
    assert calls == [("gemini", "gemini-2.5-flash")]
    assert result.model_id == "gemini-2.5-flash"


def test_both_gemini_models_fail_and_are_returned_for_logging(monkeypatch):
    monkeypatch.setattr(analysis.settings, "gemini_analysis_model", "gemini-3.5-flash-lite")
    monkeypatch.setattr(analysis.settings, "gemini_fallback_model", "gemini-2.5-flash")
    monkeypatch.setattr(analysis, "_gemini_analyze", lambda *args: (_ for _ in ()).throw(RuntimeError("offline")))
    try:
        analysis.analyze_video_with_fallback("video.mp4", {})
    except analysis.AllAnalysisProvidersFailed as exc:
        assert len(exc.attempts) == 2
        assert all(item.provider == "gemini" for item in exc.attempts)
        assert all(item.status == "failed" for item in exc.attempts)
    else:
        raise AssertionError("Expected both Gemini models to fail")


def test_provider_chain_contains_only_two_gemini_models(monkeypatch):
    monkeypatch.setattr(analysis.settings, "gemini_analysis_model", "gemini-3.5-flash-lite")
    monkeypatch.setattr(analysis.settings, "gemini_fallback_model", "gemini-2.5-flash")
    assert analysis.configured_provider_chain() == [("gemini", "gemini-3.5-flash-lite"), ("gemini", "gemini-2.5-flash")]
