"""Pure-function coverage for the OpenRouter provider: block translation in both
directions and folding of streamed chunks. No network."""

import json

import pytest

from app.agent.providers.base import ProviderError, StreamDelta, TurnResult
from app.agent.providers.openrouter_provider import (
    _Accumulator,
    parse_sse,
    to_openai_messages,
    to_openai_tools,
)
from app.agent.tools import TOOLS


def test_tools_translate_to_function_schema():
    out = to_openai_tools(TOOLS)
    assert len(out) == len(TOOLS)
    first = out[0]
    assert first["type"] == "function"
    assert first["function"]["name"] == TOOLS[0]["name"]
    assert first["function"]["parameters"] == TOOLS[0]["input_schema"]


def test_history_translates_tool_loop():
    messages = [
        {"role": "user", "content": [{"type": "text", "text": "Posso permettermi 80€?"}]},
        {
            "role": "assistant",
            "content": [
                {"type": "thinking", "thinking": "controllo il budget", "reasoning_details": [{"type": "reasoning.text", "text": "controllo il budget"}]},
                {"type": "tool_use", "id": "call_1", "name": "get_budget_status", "input": {"category": "Ristoranti"}},
            ],
        },
        {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": "call_1", "content": '{"remaining": 60.0}'}],
        },
        {"role": "assistant", "content": [{"type": "text", "text": "Ti restano 60 €."}]},
    ]

    out = to_openai_messages("SYSTEM", messages)

    assert out[0] == {"role": "system", "content": "SYSTEM"}
    assert out[1] == {"role": "user", "content": "Posso permettermi 80€?"}
    assistant = out[2]
    assert assistant["role"] == "assistant"
    assert assistant["content"] is None
    assert assistant["reasoning_details"][0]["text"] == "controllo il budget"
    assert assistant["tool_calls"] == [
        {
            "id": "call_1",
            "type": "function",
            "function": {"name": "get_budget_status", "arguments": json.dumps({"category": "Ristoranti"})},
        }
    ]
    assert out[3] == {"role": "tool", "tool_call_id": "call_1", "content": '{"remaining": 60.0}'}
    assert out[4] == {"role": "assistant", "content": "Ti restano 60 €."}


def test_signed_thinking_history_falls_back_to_plain_reasoning():
    # Sessions stored before the OpenRouter-only switch carry Anthropic-native
    # thinking blocks (a signature, no reasoning_details).
    messages = [
        {"role": "assistant", "content": [{"type": "thinking", "thinking": "ragiono", "signature": "abc"}, {"type": "text", "text": "ok"}]}
    ]
    out = to_openai_messages("S", messages)
    assert out[1]["reasoning"] == "ragiono"
    assert "reasoning_details" not in out[1]


def test_accumulator_folds_streamed_tool_call_and_usage():
    acc = _Accumulator()
    chunks = [
        {"choices": [{"delta": {"reasoning": "prima "}}]},
        {"choices": [{"delta": {"reasoning": "verifico"}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_9", "function": {"name": "get_budget_status", "arguments": ""}}]}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"categ'}}]}}]},
        {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": 'ory":"Ristoranti"}'}}]}, "finish_reason": "tool_calls"}]},
        {"choices": [], "usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": 0.00123, "prompt_tokens_details": {"cached_tokens": 40}}},
    ]
    deltas: list[StreamDelta] = []
    for c in chunks:
        deltas.extend(acc.feed(c))

    assert [d.kind for d in deltas] == ["thinking", "thinking", "tool_start"]
    assert deltas[2].text == "get_budget_status"

    result = acc.result("x/y")
    assert isinstance(result, TurnResult)
    assert result.stop_reason == "tool_use"
    assert result.content == [
        {"type": "thinking", "thinking": "prima verifico"},
        {"type": "tool_use", "id": "call_9", "name": "get_budget_status", "input": {"category": "Ristoranti"}},
    ]
    assert result.usage.input_tokens == 100
    assert result.usage.output_tokens == 20
    assert result.usage.cache_read_tokens == 40
    assert result.usage.cost_usd == 0.00123


def test_accumulator_text_only_turn_ends_normally():
    acc = _Accumulator()
    acc.feed({"choices": [{"delta": {"content": "Ciao"}}]})
    acc.feed({"choices": [{"delta": {"content": "!"}, "finish_reason": "stop"}]})
    result = acc.result("x/y")
    assert result.stop_reason == "end_turn"
    assert result.content == [{"type": "text", "text": "Ciao!"}]
    assert result.usage.cost_usd is None  # no usage chunk -> orchestrator reports 0.0


def test_accumulator_rejects_malformed_tool_arguments():
    acc = _Accumulator()
    acc.feed({"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "c", "function": {"name": "add_expense", "arguments": "{not json"}}]}}]})
    with pytest.raises(ProviderError):
        acc.result("x/y")


@pytest.mark.asyncio
async def test_parse_sse_skips_comments_and_done():
    async def lines():
        for line in [": OPENROUTER PROCESSING", "", 'data: {"a": 1}', "", "data: [DONE]", ""]:
            yield line

    assert [c async for c in parse_sse(lines())] == [{"a": 1}]
