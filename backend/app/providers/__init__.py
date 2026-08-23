from __future__ import annotations

from typing import Any

from app.config import Provider as ProviderName
from app.config import get_settings
from app.providers.base import Completion, LLMProvider, ProviderError

_cache: dict[str, LLMProvider] = {}

_FALLBACK_PARTNER: dict[str, str] = {"gemini": "groq", "groq": "gemini"}


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


class _FallbackProvider:
    """Tries `primary`; on a `ProviderError` (the primary already exhausted
    its own intra-provider retries), tries `secondary` once before raising.
    Not cached in `_cache` — cheap to construct, wraps two already-cached
    real providers."""

    def __init__(self, primary: LLMProvider, secondary: LLMProvider) -> None:
        self._primary = primary
        self._secondary = secondary
        self.name = primary.name
        self.model = primary.model

    async def complete(self, **kwargs: Any) -> Completion:
        try:
            return await self._primary.complete(**kwargs)
        except ProviderError:
            return await self._secondary.complete(**kwargs)

    async def healthy(self) -> bool:
        return await self._primary.healthy() or await self._secondary.healthy()


def get_provider_with_fallback(name: ProviderName | None = None) -> LLMProvider:
    settings = get_settings()
    name = name or settings.answer_provider
    partner = _FALLBACK_PARTNER.get(name)
    if partner is None:
        return get_provider(name)
    return _FallbackProvider(get_provider(name), get_provider(partner))


__all__ = [
    "Completion", "LLMProvider", "ProviderError", "get_provider", "get_provider_with_fallback",
]
