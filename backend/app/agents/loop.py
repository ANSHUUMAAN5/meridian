from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.providers import Completion, LLMProvider

MAX_TOOL_ITERATIONS = 4


@dataclass(frozen=True)
class ToolCall:
    name: str
    args: dict
    result: dict


@dataclass(frozen=True)
class LoopResult:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    completions: list[Completion] = field(default_factory=list)
    iterations: int = 0
    stopped_reason: str = "final_answer"


async def run_tool_loop(
    provider: LLMProvider,
    *,
    system: str,
    user: str,
    tools: list[dict],
    tool_impls: dict[str, Callable[..., Awaitable[dict]]],
    max_iterations: int = MAX_TOOL_ITERATIONS,
    max_tokens: int = 800,
    temperature: float = 0.0,
) -> LoopResult:
    transcript = user
    all_calls: list[ToolCall] = []
    completions: list[Completion] = []

    for iteration in range(max_iterations):
        completion = await provider.complete(
            system=system, user=transcript, max_tokens=max_tokens, temperature=temperature, tools=tools
        )
        completions.append(completion)

        if not completion.tool_calls:
            return LoopResult(
                text=completion.text, tool_calls=all_calls, completions=completions,
                iterations=iteration + 1, stopped_reason="final_answer",
            )

        for call in completion.tool_calls:
            impl = tool_impls.get(call.name)
            if impl is None:
                result = {"error": f"unknown tool {call.name!r}"}
            else:
                result = await impl(**call.arguments)
            executed = ToolCall(name=call.name, args=call.arguments, result=result)
            all_calls.append(executed)
            transcript += f"\n\nTool call: {call.name}({json.dumps(call.arguments)}) -> {json.dumps(result)}"

    final = await provider.complete(
        system=system,
        user=transcript + "\n\nAnswer the customer now, using only the tool results above. No more tool calls are available.",
        max_tokens=max_tokens,
        temperature=temperature,
        tools=None,
    )
    completions.append(final)
    return LoopResult(
        text=final.text, tool_calls=all_calls, completions=completions,
        iterations=max_iterations + 1, stopped_reason="max_iterations",
    )
