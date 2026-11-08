import json
from typing import Any
from app.core.settings import settings
from app.services.llm.gemini import GeminiProvider
from app.services.llm.openai_compatible import OpenAICompatibleProvider

def _provider():
    name = settings.llm_provider.lower()
    if name == "gemini": return GeminiProvider()
    if name in {"openai-compatible", "openrouter", "groq", "nvidia-nim"}: return OpenAICompatibleProvider()
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")

def _prompt(context: dict[str, Any]) -> str:
    return f"""You are an original short-form video scriptwriter. Create exactly 3 DISTINCT English-language 60–90 second Reel script variations for the Page described below.
Treat the supplied trend/source as inspiration and factual context, not text to copy. Never invent facts, quotes, statistics, dates, or sources. If evidence is insufficient, qualify the claim and flag it for human fact-checking. Do not provide medical advice. Respect restricted topics. Avoid copyrighted lyrics and imitation of living creators.
Return ONLY valid JSON with this shape:
{{"variations":[{{"title":"...","hook":"...","narration":"...","caption":"...","hashtags":["#..."],"estimated_duration_seconds":75,"evaluation":{{"hook_score":1,"storytelling_score":1,"originality_score":1,"visual_suitability_score":1,"fact_check_notes":"...","strengths":"..."}}}}]}}
Scores are integers from 1 to 10. Narration should fit 60–90 seconds. Make hooks and story structures meaningfully different. Evaluation is preliminary, not proof of accuracy.
PAGE PROFILE: {json.dumps(context["profile"], ensure_ascii=False)}
ACTIVE CONTENT STRATEGY: {json.dumps(context["strategy"], ensure_ascii=False)}
SELECTED TREND: {json.dumps(context["trend"], ensure_ascii=False)}
SOURCE URL (for human verification): {context["source_url"]}
"""

def generate_variations(context: dict[str, Any]) -> list[dict[str, Any]]:
    raw = _provider().generate_json(_prompt(context))
    try: payload = json.loads(raw)
    except json.JSONDecodeError as exc: raise RuntimeError("The LLM returned invalid JSON. Please retry generation.") from exc
    variations = payload.get("variations") if isinstance(payload, dict) else None
    if not isinstance(variations, list) or len(variations) != 3:
        raise RuntimeError("The LLM must return exactly three script variations. Please retry.")
    clean = []
    for item in variations:
        if not isinstance(item, dict) or not all(isinstance(item.get(k), str) for k in ("title", "hook", "narration")):
            raise RuntimeError("A generated variation is missing required text fields. Please retry.")
        clean.append({"title": item["title"][:200], "hook": item["hook"][:500], "narration": item["narration"],
            "caption": str(item.get("caption", "")),
            "hashtags": [str(tag)[:80] for tag in item.get("hashtags", []) if isinstance(tag, str)][:20],
            "script_data": {"estimated_duration_seconds": item.get("estimated_duration_seconds"),
                "evaluation": item.get("evaluation", {}), "source_url": context["source_url"]}})
    return clean
