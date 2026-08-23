from __future__ import annotations

from app.config import Provider as ProviderName
from app.config import get_settings
from app.providers.base import Completion, LLMProvider, ProviderError

_cache: dict[str, LLMProvider] = {}


def get_provider(name: ProviderName | None = None) -> LLMProvider:
    settings = get_settings()
    name = name or settings.answer_provider
    if name in _cache:
        return _cache[name]

    if name == "ollama":
        from app.providers.ollama import OllamaProvider

        provider: LLMProvider = OllamaProvider()
    elif name == "groq":
        from app.providers.groq import GroqProvider

        provider = GroqProvider()
    elif name == "gemini":
        from app.providers.gemini import GeminiProvider

        provider = GeminiProvider()
    else:
        raise ProviderError(f"unknown provider {name!r}")

    _cache[name] = provider
    return provider


__all__ = ["Completion", "LLMProvider", "ProviderError", "get_provider"]
