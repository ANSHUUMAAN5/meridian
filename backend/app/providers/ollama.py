"""Local Ollama. Development and offline smoke tests only — never deployed.

Exists so the whole pipeline can be built and tested without an API key and
without spending free-tier rate limits on every iteration.
"""

from __future__ import annotations

import time

import httpx

from app.config import get_settings
from app.providers.base import Completion, ProviderError


class OllamaProvider:
    name = "ollama"

    def __init__(self) -> None:
        s = get_settings()
        self.base_url = s.ollama_base_url.rstrip("/")
        self.model = s.ollama_model

    async def complete(
        self, *, system: str, user: str, max_tokens: int = 1024, temperature: float = 0.0
    ) -> Completion:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                r = await client.post(f"{self.base_url}/api/chat", json=payload)
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPError as e:
            raise ProviderError(f"ollama request failed: {e}") from e

        elapsed = int((time.perf_counter() - started) * 1000)
        text = (data.get("message") or {}).get("content", "").strip()
        if not text:
            raise ProviderError("ollama returned an empty completion")

        return Completion(
            text=text,
            model=self.model,
            latency_ms=elapsed,
            input_tokens=data.get("prompt_eval_count"),
            output_tokens=data.get("eval_count"),
        )

    async def healthy(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except httpx.HTTPError:
            return False
