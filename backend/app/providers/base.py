"""The provider contract.

Deliberately small. Everything an agent needs is a system prompt, a
conversation, and a completion back — plus the token counts, because Trace
records cost per step and cost is only reconstructible if the provider reports
usage at the time of the call.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class ProviderError(RuntimeError):
    """Any failure reaching or parsing a provider response."""


@dataclass(frozen=True)
class ToolCallRequest:
    """A tool the model wants to run, in the caller's chosen format.

    id is opaque per-provider bookkeeping (Groq/OpenAI-style APIs need it to
    match a result back to a call in a follow-up turn); Ollama has no concept
    of it and leaves it empty.
    """

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Completion:
    text: str
    model: str
    latency_ms: int
    input_tokens: int | None = None
    output_tokens: int | None = None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)

    @property
    def cost_usd(self) -> float:
        """Zero on every provider this project uses. Kept so the field exists
        in Trace from day one — the moment anything moves to paid inference the
        number is already being recorded rather than needing backfill."""
        return 0.0


@runtime_checkable
class LLMProvider(Protocol):
    name: str
    model: str

    async def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        tools: list[dict[str, Any]] | None = None,
    ) -> Completion:
        """`tools` is OpenAI's function-calling schema — the format Groq and
        Ollama already speak natively; the Gemini provider translates it.
        One schema shape for every caller, even though the wire format
        differs per provider underneath."""
        ...

    async def healthy(self) -> bool:
        """Cheap reachability check, used by /health."""
        ...
