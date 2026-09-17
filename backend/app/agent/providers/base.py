"""Provider-neutral contract for one model call inside the agent loop.

The orchestrator owns the loop (history, tool execution, persistence, SSE); a
provider owns exactly one thing: turning a request into a stream of deltas and
a final result. Content blocks use the Anthropic Messages shape everywhere
(`text`, `thinking`, `tool_use`, `tool_result`) - that is the format stored in
`conversation_messages.content_json`, so every provider converts to/from it and
the rest of the app never notices which vendor answered.
"""

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Literal, Protocol


@dataclass
class StreamDelta:
    """A fragment emitted while the model is still generating."""

    kind: Literal["thinking", "text", "tool_start"]
    text: str  # for tool_start: the tool name


@dataclass
class TurnUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    # Billed cost when the provider reports it (OpenRouter does); None means
    # "estimate it from the pricing table".
    cost_usd: float | None = None


@dataclass
class TurnResult:
    """The completed model call, in canonical (Anthropic-shaped) blocks."""

    content: list[dict] = field(default_factory=list)
    stop_reason: str = "end_turn"  # "tool_use" when the loop must run tools
    usage: TurnUsage = field(default_factory=TurnUsage)


class ProviderError(Exception):
    """Raised for any upstream API failure, already formatted for the user."""


class LLMProvider(Protocol):
    name: str
    model: str

    def stream(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> AsyncIterator[StreamDelta | TurnResult]:
        """Yields StreamDelta items while generating, then exactly one TurnResult."""
        ...

    async def aclose(self) -> None: ...
