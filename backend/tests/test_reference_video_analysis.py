from app.services import reference_video_analysis as analysis


MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"


def _valid_result():
    return {"summary": "A short explainer.", "creative_elements": []}


def test_provider_chain_uses_gemini_nemotron_then_gemini(monkeypatch):
    monkeypatch.setattr(analysis.settings, "gemini_analysis_model", "gemini-3.5-flash-lite")
    monkeypatch.setattr(analysis.settings, "nemotron_analysis_model", MODEL)
    monkeypatch.setattr(analysis.settings, "gemini_fallback_model", "gemini-2.5-flash")
    monkeypatch.setattr(analysis, "create_download_url", lambda *args, **kwargs: "https://signed.example/video.mp4")
    calls = []

    def gemini(path, prompt, model):
        calls.append(("gemini", model))
        if model == "gemini-3.5-flash-lite":
            raise RuntimeError("503 UNAVAILABLE")
        return _valid_result(), 100, 20

    def nemotron(url, prompt, model):
        calls.append(("nemotron", model))
        return _valid_result(), 120, 30

    monkeypatch.setattr(analysis, "_gemini_analyze", gemini)
    monkeypatch.setattr(analysis, "_nemotron_analyze", nemotron)
    result = analysis.analyze_video_with_fallback("video.mp4", {}, object_key="private/video.mp4")

    assert calls == [("gemini", "gemini-3.5-flash-lite"), ("nemotron", MODEL)]
    assert result.provider == "nemotron"
    assert result.model_id == MODEL
    assert [item.status for item in result.attempts] == ["failed", "completed"]
    assert result.attempts[0].error_code == "RuntimeError"
    assert result.attempts[1].input_tokens == 120


def test_manual_primary_model_runs_first_then_uses_other_fallbacks(monkeypatch):
    monkeypatch.setattr(analysis.settings, "gemini_analysis_model", "gemini-3.5-flash-lite")
    monkeypatch.setattr(analysis.settings, "nemotron_analysis_model", MODEL)
    monkeypatch.setattr(analysis.settings, "gemini_fallback_model", "gemini-2.5-flash")
    monkeypatch.setattr(analysis, "create_download_url", lambda *args, **kwargs: "https://signed.example/video.mp4")
    calls = []

    def fail_gemini(path, prompt, model):
        calls.append(("gemini", model))
        raise RuntimeError("unavailable")

    def succeed_nemotron(url, prompt, model):
        calls.append(("nemotron", model))
        return _valid_result(), None, None

    monkeypatch.setattr(analysis, "_gemini_analyze", fail_gemini)
    monkeypatch.setattr(analysis, "_nemotron_analyze", succeed_nemotron)
    result = analysis.analyze_video_with_fallback(
        "video.mp4", {}, object_key="private/video.mp4",
        primary_provider="nemotron", primary_model=MODEL,
    )

    assert calls == [("nemotron", MODEL)]
    assert result.provider == "nemotron"


def test_all_provider_failures_are_returned_for_logging(monkeypatch):
    monkeypatch.setattr(analysis.settings, "gemini_analysis_model", "gemini-3.5-flash-lite")
    monkeypatch.setattr(analysis.settings, "nemotron_analysis_model", MODEL)
    monkeypatch.setattr(analysis.settings, "gemini_fallback_model", "gemini-2.5-flash")
    monkeypatch.setattr(analysis, "create_download_url", lambda *args, **kwargs: "https://signed.example/video.mp4")
    monkeypatch.setattr(analysis, "_gemini_analyze", lambda *args: (_ for _ in ()).throw(RuntimeError("offline")))
    monkeypatch.setattr(analysis, "_nemotron_analyze", lambda *args: (_ for _ in ()).throw(RuntimeError("offline")))

    try:
        analysis.analyze_video_with_fallback("video.mp4", {}, object_key="private/video.mp4")
    except analysis.AllAnalysisProvidersFailed as exc:
        assert len(exc.attempts) == 3
        assert all(item.status == "failed" for item in exc.attempts)
    else:
        raise AssertionError("Expected all providers to fail")


def test_fallback_reaches_gemini_25_after_nemotron_failure(monkeypatch):
    monkeypatch.setattr(analysis.settings, "gemini_analysis_model", "gemini-3.5-flash-lite")
    monkeypatch.setattr(analysis.settings, "nemotron_analysis_model", MODEL)
    monkeypatch.setattr(analysis.settings, "gemini_fallback_model", "gemini-2.5-flash")
    monkeypatch.setattr(analysis, "create_download_url", lambda *args, **kwargs: "https://signed.example/video.mp4")
    calls = []

    def gemini(path, prompt, model):
        calls.append(("gemini", model))
        if model == "gemini-3.5-flash-lite":
            raise RuntimeError("primary unavailable")
        return _valid_result(), 80, 15

    def nemotron(url, prompt, model):
        calls.append(("nemotron", model))
        raise RuntimeError("NVIDIA quota exceeded")

    monkeypatch.setattr(analysis, "_gemini_analyze", gemini)
    monkeypatch.setattr(analysis, "_nemotron_analyze", nemotron)
    result = analysis.analyze_video_with_fallback("video.mp4", {}, object_key="private/video.mp4")

    assert calls == [
        ("gemini", "gemini-3.5-flash-lite"),
        ("nemotron", MODEL),
        ("gemini", "gemini-2.5-flash"),
    ]
    assert result.provider == "gemini"
    assert result.model_id == "gemini-2.5-flash"
    assert [item.status for item in result.attempts] == ["failed", "failed", "completed"]
}
