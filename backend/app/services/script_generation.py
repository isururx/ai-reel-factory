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
    return f"""You are an expert original short-form video scriptwriter.

    TASK:
    Create exactly 3 DISTINCT English-language Facebook/Instagram Reel script variations for the Page described below.

    VIDEO REQUIREMENTS:
    - Target duration: 60–90 seconds per variation.
    - Narration: 120–170 words per variation.
    - Each variation must have a different hook, storytelling approach, and narrative structure.
    - Write natural, engaging narration suitable for voice-over.
    - Make the content understandable to a general audience.
    - Include a compelling opening, a well-developed middle, and a satisfying ending.
    - End with a natural audience engagement question or call to action where appropriate.

    FACTUAL AND SAFETY REQUIREMENTS:
    - Treat the supplied trend/source as inspiration and factual context, not text to copy.
    - Never invent facts, statistics, quotes, dates, research findings, or sources.
    - Do not present assumptions as established facts.
    - If evidence is insufficient, qualify the claim and clearly flag it for human fact-checking.
    - Do not provide medical advice or imply that a study proves medical causation.
    - Respect the Page's restricted topics.
    - Avoid copyrighted lyrics and imitation of living creators.
    - Preserve important limitations and context from the source.

    OUTPUT FORMAT — STRICT:
    Return ONLY one valid JSON object.
    Do not use Markdown code fences.
    Do not include explanations before or after the JSON.
    Do not add comments or trailing commas.
    Use exactly this structure:

    {{
    "variations": [
        {{
        "title": "Short descriptive title",
        "hook": "Opening hook",
        "narration": "Complete 120–170 word voice-over script",
        "caption": "Engaging social media caption",
        "hashtags": ["#Example", "#Example2"],
        "estimated_duration_seconds": 75,
        "evaluation": {{
            "hook_score": 8,
            "storytelling_score": 8,
            "originality_score": 8,
            "visual_suitability_score": 8,
            "fact_check_notes": "Claims requiring human verification",
            "strengths": "Brief explanation of the variation's strengths"
        }}
        }}
    ]
    }}

    FINAL VALIDATION BEFORE RESPONDING:
    1. Include exactly 3 variations.
    2. Every variation must contain all required fields.
    3. Every narration must contain 120–170 words.
    4. All four evaluation scores must be integers from 1 to 10.
    5. Hashtags must be returned as a JSON array of strings.
    6. Ensure the entire JSON object is complete and syntactically valid.
    7. Never stop midway through a variation or JSON object.

    PAGE PROFILE:
    {json.dumps(context["profile"], ensure_ascii=False)}

    ACTIVE CONTENT STRATEGY:
    {json.dumps(context["strategy"], ensure_ascii=False)}

    SELECTED TREND:
    {json.dumps(context["trend"], ensure_ascii=False)}

    SOURCE URL FOR HUMAN FACT-CHECKING:
    {context["source_url"]}
    """


def generate_variations(context: dict[str, Any]) -> list[dict[str, Any]]:
    raw = _provider().generate_json(_prompt(context))
    
    try:
        payload = json.loads(raw)

    except json.JSONDecodeError as exc:
        print("\n========== JSON PARSE ERROR ==========")
        print("Error:", exc)
        print("Line:", exc.lineno)
        print("Column:", exc.colno)
        print("Position:", exc.pos)
        print("Response length:", len(raw))
        print("\nResponse beginning:")
        print(repr(raw[:500]))
        print("\nResponse ending:")
        print(repr(raw[-500:]))
        print("========== END JSON ERROR ==========\n")

        raise RuntimeError(
            f"The LLM returned invalid JSON at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc

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
