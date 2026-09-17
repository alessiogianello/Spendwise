"""Claude via the Anthropic Messages API - the native provider.

Also reaches Claude through OpenRouter's Anthropic-compatible endpoint when
ANTHROPIC_BASE_URL=https://openrouter.ai/api is set (Anthropic models only).
"""

from collections.abc import AsyncIterator

import anthropic

from app.agent.providers.base import ProviderError, StreamDelta, TurnResult, TurnUsage

MAX_TOKENS = 4096


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, model: str, api_key: str | None, base_url: str | None = None):
        self.model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key, base_url=base_url)

    async def stream(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> AsyncIterator[StreamDelta | TurnResult]:
        # The static prompt is marked cacheable; volatile context (date,
        # preferences) is injected into the user turn by the orchestrator so it
        # never invalidates the cached prefix.
        system_blocks = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        try:
            async with self._client.messages.stream(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=system_blocks,
                thinking={"type": "adaptive", "display": "summarized"},
                tools=tools,
                messages=messages,
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_start" and event.content_block.type == "tool_use":
                        yield StreamDelta("tool_start", event.content_block.name)
                    elif event.type == "content_block_delta":
                        if event.delta.type == "thinking_delta":
                            yield StreamDelta("thinking", event.delta.thinking)
                        elif event.delta.type == "text_delta":
                            yield StreamDelta("text", event.delta.text)

                response = await stream.get_final_message()
        except anthropic.APIError as exc:
            raise ProviderError(f"Errore Claude API: {exc}") from exc

        usage = response.usage
        yield TurnResult(
            content=[block.model_dump() for block in response.content],
            stop_reason=response.stop_reason or "end_turn",
            usage=TurnUsage(
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
                cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            ),
        )

    async def aclose(self) -> None:
        await self._client.close()
