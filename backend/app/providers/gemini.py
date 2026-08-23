from __future__ import annotations

import asyncio
import re
import time
from collections import deque

from google import genai
from google.genai import types

from typing import Any

from app.config import get_settings
from app.providers.base import Completion, ProviderError, ToolCallRequest


class GeminiProvider:
    name = "gemini"

    _call_times: deque[float] = deque(maxlen=5)
    _lock = asyncio.Lock()

    def __init__(self, model: str | None = None) -> None:
        s = get_settings()
        if not s.gemini_api_key:
            raise ProviderError("GEMINI_API_KEY is not set")
        self.model = model or s.gemini_model
        self._client = genai.Client(api_key=s.gemini_api_key)

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        tools: list[dict[str, Any]] | None = None,
    ) -> Completion:
        await self._wait_for_quota()
        started = time.perf_counter()

        gemini_tools = None
        if tools:
            gemini_tools = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=t["function"]["name"],
                            description=t["function"].get("description", ""),
                            parameters=t["function"].get("parameters"),
                        )
                        for t in tools
                    ]
                )
            ]

        for attempt in range(3):
            try:
                r = await asyncio.to_thread(
                    self._client.models.generate_content,
                    model=self.model,
                    contents=user,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        max_output_tokens=max_tokens,
                        temperature=temperature,
                        tools=gemini_tools,
                        automatic_function_calling=types.AutomaticFunctionCallingConfig(
                            disable=True
                        )
                        if gemini_tools
                        else None,
                    ),
                )
                break
            except Exception as e:
                is_rate_limit = "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e)
                if is_rate_limit and attempt < 2:
                    wait = 20.0
                    m = re.search(r"retry in ([\d.]+)s", str(e)) or re.search(
                        r"retryDelay['\"]?\s*:\s*['\"]?(\d+)", str(e)
                    )
                    if m:
                        wait = float(m.group(1)) + 1
                    await asyncio.sleep(wait)
                    continue
                raise ProviderError(f"gemini request failed: {type(e).__name__}: {e}") from e
        else:
            raise ProviderError("gemini rate-limited repeatedly")

        elapsed = int((time.perf_counter() - started) * 1000)

        tool_calls: list[ToolCallRequest] = []
        parts = []
        if r.candidates:
            parts = r.candidates[0].content.parts or []
        for i, part in enumerate(parts):
            fc = getattr(part, "function_call", None)
            if fc is not None:
                tool_calls.append(
                    ToolCallRequest(id=f"call_{i}", name=fc.name, arguments=dict(fc.args or {}))
                )

        text = (r.text or "").strip() if not tool_calls else ""
        if not text and not tool_calls:
            raise ProviderError("gemini returned an empty completion")

        usage = getattr(r, "usage_metadata", None)
        return Completion(
            text=text,
            model=self.model,
            latency_ms=elapsed,
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
            tool_calls=tool_calls,
        )

    async def _wait_for_quota(self) -> None:
        async with self._lock:
            now = time.monotonic()
            while self._call_times and now - self._call_times[0] > 60:
                self._call_times.popleft()
            if len(self._call_times) >= 5:
                sleep_for = 60 - (now - self._call_times[0]) + 0.5
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
            self._call_times.append(time.monotonic())

    async def healthy(self) -> bool:
        try:
            await asyncio.to_thread(lambda: list(self._client.models.list())[:1])
            return True
        except Exception:
            return False
