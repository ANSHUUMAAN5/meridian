"""Groq — fast inference on open models. Used for routing (Compass).

Routing is high-volume and simple: one short classification per customer
message. Latency matters more than depth, which is what Groq is good at.
"""

from __future__ import annotations

import asyncio
import json
import time

from typing import Any

from groq import APIError, AsyncGroq, RateLimitError

from app.config import get_settings
from app.providers.base import Completion, ProviderError, ToolCallRequest


class GroqProvider:
    name = "groq"

    def __init__(self, model: str | None = None) -> None:
        s = get_settings()
        if not s.groq_api_key:
            raise ProviderError("GROQ_API_KEY is not set")
        self.model = model or s.groq_model
        self._client = AsyncGroq(api_key=s.groq_api_key)

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        tools: list[dict[str, Any]] | None = None,
    ) -> Completion:
        started = time.perf_counter()
        kwargs: dict[str, Any] = {}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        # Free tier has a tokens-per-minute cap. Groq's error tells us exactly
        # how long to wait, which is normally well under a second.
        for attempt in range(3):
            try:
                r = await self._client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    max_completion_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs,
                )
                break
            except RateLimitError as e:
                if attempt == 2:
                    raise ProviderError(f"groq rate-limited 3 times in a row: {e}") from e
                await asyncio.sleep(1.5 * (attempt + 1))
            except APIError as e:
                raise ProviderError(f"groq request failed: {e}") from e

        elapsed = int((time.perf_counter() - started) * 1000)
        message = r.choices[0].message
        raw_calls = message.tool_calls or []

        tool_calls = [
            ToolCallRequest(
                id=tc.id,
                name=tc.function.name,
                arguments=json.loads(tc.function.arguments or "{}"),
            )
            for tc in raw_calls
        ]

        text = (message.content or "").strip()
        if not text and not tool_calls:
            raise ProviderError("groq returned an empty completion")

        usage = r.usage
        return Completion(
            text=text,
            model=self.model,
            latency_ms=elapsed,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
            tool_calls=tool_calls,
        )

    async def healthy(self) -> bool:
        try:
            await self._client.models.list()
            return True
        except Exception:
            return False
