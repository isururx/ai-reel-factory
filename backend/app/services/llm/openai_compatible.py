import httpx
from app.core.settings import settings

class OpenAICompatibleProvider:
    """Adapter for OpenAI-compatible endpoints such as Groq, OpenRouter and NIM."""
    def generate_json(self, prompt: str) -> str:
        if not settings.llm_api_key or not settings.llm_base_url:
            raise RuntimeError("LLM_API_KEY and LLM_BASE_URL are required for this provider.")
        response = httpx.post(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={"model": settings.llm_model, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.8, "response_format": {"type": "json_object"}}, timeout=90.0,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
