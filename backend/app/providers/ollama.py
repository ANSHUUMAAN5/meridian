"""Local Ollama. Development and offline smoke tests only — never deployed.

Exists so the whole pipeline can be built and tested without an API key and
without spending free-tier rate limits on every iteration.
"""

from __future__ import annotations

import time

import httpx

from typing import Any

from app.config import get_settings
from app.providers.base import Completion, ProviderError, ToolCallRequest


class OllamaProvider:
    name = "ollama"

    def __init__(self) -> None:
        s = get_settings()
        self.base_url = s.ollama_base_url.rstrip("/")
        self.model = s.ollama_model

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        tools: list[dict[str, Any]] | None = None,
    ) -> Completion:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if tools:
            payload["tools"] = tools
        started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                r = await client.post(f"{self.base_url}/api/chat", json=payload)
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPError as e:
            raise ProviderError(f"ollama request failed: {e}") from e

        elapsed = int((time.perf_counter() - started) * 1000)
        message = data.get("message") or {}
        raw_calls = message.get("tool_calls") or []
        tool_calls = [
            ToolCallRequest(
                id=str(i),
                name=tc["function"]["name"],
                arguments=tc["function"].get("arguments", {}),
            )
            for i, tc in enumerate(raw_calls)
        ]

        text = (message.get("content") or "").strip()
        if not text and not tool_calls:
            raise ProviderError("ollama returned an empty completion")

        return Completion(
            text=text,
            model=self.model,
            latency_ms=elapsed,
            input_tokens=data.get("prompt_eval_count"),
            output_tokens=data.get("eval_count"),
            tool_calls=tool_calls,
        )

    async def healthy(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except httpx.HTTPError:
            return False
