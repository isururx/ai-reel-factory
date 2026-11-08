from typing import Protocol

class LLMProvider(Protocol):
    def generate_json(self, prompt: str) -> str: ...
