from google import genai
from google.genai import types

from app.core.settings import settings


class GeminiProvider:
    def __init__(self, model: str | None = None) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")

        self.model = model or settings.llm_model
        self.client = genai.Client(
            api_key=settings.gemini_api_key,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )

    def generate_json(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
                max_output_tokens=8192,
            ),
        )

        if not response.text:
            raise RuntimeError(f"Gemini model {self.model} returned an empty response.")

        for candidate in response.candidates or []:
            print("Gemini finish reason:", candidate.finish_reason)

        print(f"Gemini model: {self.model}; response length: {len(response.text)}")
        return response.text
