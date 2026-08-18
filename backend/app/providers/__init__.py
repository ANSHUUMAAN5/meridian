"""LLM providers behind one interface.

Agents import `get_provider()` and never a vendor SDK. Two reasons: the free
tiers this project runs on can change their terms at any time, and Sextant
needs to run the same eval against several models to justify which one each
agent uses. Both require swapping the backend without touching agent code.
"""

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
    else:  # pragma: no cover - guarded by the Literal type
        raise ProviderError(f"unknown provider {name!r}")

    _cache[name] = provider
    return provider


__all__ = ["Completion", "LLMProvider", "ProviderError", "get_provider"]
