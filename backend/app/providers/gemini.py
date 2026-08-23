"""Google Gemini — used for answering (Almanac, Manifest).

Answering is lower-volume than routing and quality-sensitive: the output is
read by a customer and must stay inside the retrieved documents. Splitting it
onto a second provider also means neither free tier's rate limit can take the
whole system down on its own.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections import deque

from google import genai
from google.genai import types

from app.config import get_settings
from app.providers.base import Completion, ProviderError


class GeminiProvider:
    name = "gemini"

    # Free tier allows 5 requests per minute PER MODEL. This is shared across
    # every GeminiProvider instance in the process (a class variable, not an
    # instance one), because the limit is Google's, not ours — two instances
    # calling the same model still share one quota.
    _call_times: deque[float] = deque(maxlen=5)
    _lock = asyncio.Lock()

    def __init__(self, model: str | None = None) -> None:
        s = get_settings()
        if not s.gemini_api_key:
            raise ProviderError("GEMINI_API_KEY is not set")
        self.model = model or s.gemini_model
        self._client = genai.Client(api_key=s.gemini_api_key)

    async def complete(
        self, *, system: str, user: str, max_tokens: int = 1024, temperature: float = 0.0
    ) -> Completion:
        await self._wait_for_quota()
        started = time.perf_counter()
        # Belt and braces: pacing below should prevent 429s, but if one still
        # arrives (a burst from another process, a shortened window), retry
        # using the wait time Google reports, up to a few times.
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
        text = (r.text or "").strip()
        if not text:
            raise ProviderError("gemini returned an empty completion")

        usage = getattr(r, "usage_metadata", None)
        return Completion(
            text=text,
            model=self.model,
            latency_ms=elapsed,
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
        )

    async def _wait_for_quota(self) -> None:
        """Block until a call would not exceed 5 requests in the last 60s.

        Proactive pacing rather than reactive retrying: waiting a known short
        time before a call is more reliable than discovering after the fact
        that the call failed, especially since Google's failure message
        format is not perfectly stable to parse.
        """
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
