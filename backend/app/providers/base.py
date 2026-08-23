from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolCallRequest:

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
        ...

    async def healthy(self) -> bool:
        ...
