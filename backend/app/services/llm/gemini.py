from google import genai
from google.genai import types
from app.core.settings import settings

class GeminiProvider:
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def generate_json(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=settings.llm_model, contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.8),
        )
        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")
        return response.text
