"""Any OpenRouter model via its OpenAI-compatible chat-completions API.

Two jobs: translate the canonical Anthropic-shaped blocks to/from the OpenAI
message format, and parse the streamed SSE chunks. Reasoning is requested with
OpenRouter's unified `reasoning` parameter and surfaced as `thinking` blocks so
the UI trace looks the same whichever vendor is behind the model.

Cost is taken from `usage.cost` (OpenRouter bills in USD credits and reports
the charge on the final chunk), so no local pricing table is needed.
"""

import json
from collections.abc import AsyncIterator

import httpx

from app.agent.providers.base import ProviderError, StreamDelta, TurnResult, TurnUsage

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
MAX_TOKENS = 4096


# --- canonical blocks -> OpenAI messages -------------------------------------


def to_openai_tools(tools: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t["input_schema"],
            },
        }
        for t in tools
    ]


def to_openai_messages(system: str, messages: list[dict]) -> list[dict]:
    out: list[dict] = [{"role": "system", "content": system}]
    for msg in messages:
        blocks = msg["content"]
        if isinstance(blocks, str):
            blocks = [{"type": "text", "text": blocks}]
        if msg["role"] == "assistant":
            out.append(_assistant_message(blocks))
        else:
            out.extend(_user_messages(blocks))
    return out


def _assistant_message(blocks: list[dict]) -> dict:
    msg: dict = {"role": "assistant", "content": None}
    text_parts: list[str] = []
    tool_calls: list[dict] = []
    for b in blocks:
        match b.get("type"):
            case "text":
                text_parts.append(b["text"])
            case "thinking":
                # Echo reasoning back so the model keeps its train of thought
                # across the tool-result round trip. Prefer the structured form
                # OpenRouter gave us; fall back to plain text (also covers
                # history produced by the Anthropic provider).
                if b.get("reasoning_details"):
                    msg["reasoning_details"] = b["reasoning_details"]
                elif b.get("thinking"):
                    msg["reasoning"] = b["thinking"]
            case "tool_use":
                tool_calls.append(
                    {
                        "id": b["id"],
                        "type": "function",
                        "function": {"name": b["name"], "arguments": json.dumps(b.get("input") or {})},
                    }
                )
    if text_parts:
        msg["content"] = "".join(text_parts)
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg


def _user_messages(blocks: list[dict]) -> list[dict]:
    """A user turn is either plain text or a batch of tool results; OpenAI
    wants each tool result as its own `tool` message."""
    out: list[dict] = []
    text_parts: list[str] = []
    for b in blocks:
        match b.get("type"):
            case "text":
                text_parts.append(b["text"])
            case "tool_result":
                content = b.get("content", "")
                if not isinstance(content, str):
                    content = json.dumps(content, ensure_ascii=False, default=str)
                out.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": content})
    if text_parts:
        out.insert(0, {"role": "user", "content": "".join(text_parts)})
    return out


# --- streamed chunks -> canonical blocks -------------------------------------


class _Accumulator:
    """Folds streamed deltas into one assistant message."""

    def __init__(self) -> None:
        self.text: list[str] = []
        self.reasoning: list[str] = []
        self.reasoning_details: list[dict] = []
        self.tool_calls: dict[int, dict] = {}  # by stream index
        self.finish_reason: str | None = None
        self.usage: dict | None = None

    def feed(self, chunk: dict) -> list[StreamDelta]:
        deltas: list[StreamDelta] = []
        if chunk.get("usage"):
            self.usage = chunk["usage"]
        for choice in chunk.get("choices") or []:
            if choice.get("finish_reason"):
                self.finish_reason = choice["finish_reason"]
            delta = choice.get("delta") or {}

            if delta.get("reasoning"):
                self.reasoning.append(delta["reasoning"])
                deltas.append(StreamDelta("thinking", delta["reasoning"]))
            for detail in delta.get("reasoning_details") or []:
                self.reasoning_details.append(detail)
                # Only surface text-type details; encrypted/summary-less ones
                # carry nothing readable.
                if not delta.get("reasoning") and detail.get("text"):
                    self.reasoning.append(detail["text"])
                    deltas.append(StreamDelta("thinking", detail["text"]))

            if delta.get("content"):
                self.text.append(delta["content"])
                deltas.append(StreamDelta("text", delta["content"]))

            for tc in delta.get("tool_calls") or []:
                idx = tc.get("index", 0)
                entry = self.tool_calls.setdefault(idx, {"id": None, "name": None, "arguments": ""})
                if tc.get("id"):
                    entry["id"] = tc["id"]
                fn = tc.get("function") or {}
                if fn.get("name"):
                    entry["name"] = fn["name"]
                    deltas.append(StreamDelta("tool_start", fn["name"]))
                if fn.get("arguments"):
                    entry["arguments"] += fn["arguments"]
        return deltas

    def result(self, model: str) -> TurnResult:
        content: list[dict] = []
        if self.reasoning or self.reasoning_details:
            block: dict = {"type": "thinking", "thinking": "".join(self.reasoning)}
            if self.reasoning_details:
                block["reasoning_details"] = self.reasoning_details
            content.append(block)
        if self.text:
            content.append({"type": "text", "text": "".join(self.text)})
        for idx in sorted(self.tool_calls):
            tc = self.tool_calls[idx]
            try:
                arguments = json.loads(tc["arguments"] or "{}")
            except json.JSONDecodeError as exc:
                raise ProviderError(
                    f"{model} ha prodotto argomenti non validi per {tc['name']}: {tc['arguments']!r}"
                ) from exc
            content.append(
                {"type": "tool_use", "id": tc["id"] or f"call_{idx}", "name": tc["name"], "input": arguments}
            )

        stop_reason = "tool_use" if self.tool_calls else _map_finish_reason(self.finish_reason)
        return TurnResult(content=content, stop_reason=stop_reason, usage=_usage_from(self.usage))


def _map_finish_reason(reason: str | None) -> str:
    return {"tool_calls": "tool_use", "length": "max_tokens", "stop": "end_turn"}.get(reason or "", "end_turn")


def _usage_from(raw: dict | None) -> TurnUsage:
    if not raw:
        return TurnUsage()
    prompt_details = raw.get("prompt_tokens_details") or {}
    cost = raw.get("cost")
    return TurnUsage(
        input_tokens=raw.get("prompt_tokens", 0) or 0,
        output_tokens=raw.get("completion_tokens", 0) or 0,
        cache_creation_tokens=prompt_details.get("cache_write_tokens", 0) or 0,
        cache_read_tokens=prompt_details.get("cached_tokens", 0) or 0,
        cost_usd=round(float(cost), 6) if cost is not None else None,
    )


async def parse_sse(lines: AsyncIterator[str]) -> AsyncIterator[dict]:
    """Yields the JSON payload of each `data:` event; skips comments and [DONE]."""
    async for line in lines:
        if not line.startswith("data:"):
            continue  # blank separators and ':' keep-alive comments
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        yield json.loads(payload)


# --- provider ----------------------------------------------------------------


class OpenRouterProvider:
    name = "openrouter"

    def __init__(
        self,
        model: str,
        api_key: str | None,
        base_url: str = DEFAULT_BASE_URL,
        reasoning_effort: str | None = None,
    ):
        self.model = model
        self._reasoning_effort = reasoning_effort
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key or ''}",
                "Content-Type": "application/json",
                # Optional attribution headers OpenRouter uses for its rankings.
                "HTTP-Referer": "https://github.com/spendwise",
                "X-Title": "Spendwise",
            },
            timeout=httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0),
        )

    def _body(self, system: str, messages: list[dict], tools: list[dict]) -> dict:
        body: dict = {
            "model": self.model,
            "messages": to_openai_messages(system, messages),
            "tools": to_openai_tools(tools),
            "stream": True,
            "max_tokens": MAX_TOKENS,
        }
        if self._reasoning_effort:
            body["reasoning"] = {"effort": self._reasoning_effort}
        return body

    async def stream(
        self, *, system: str, messages: list[dict], tools: list[dict]
    ) -> AsyncIterator[StreamDelta | TurnResult]:
        acc = _Accumulator()
        try:
            async with self._client.stream("POST", "/chat/completions", json=self._body(system, messages, tools)) as resp:
                if resp.status_code != 200:
                    detail = (await resp.aread()).decode("utf-8", "replace")
                    raise ProviderError(f"Errore OpenRouter (HTTP {resp.status_code}): {_error_message(detail)}")
                async for chunk in parse_sse(resp.aiter_lines()):
                    if chunk.get("error"):
                        # Mid-stream errors arrive as a normal data event.
                        raise ProviderError(f"Errore OpenRouter: {_error_message(json.dumps(chunk['error']))}")
                    for delta in acc.feed(chunk):
                        yield delta
        except httpx.HTTPError as exc:
            raise ProviderError(f"Errore di rete verso OpenRouter: {exc}") from exc

        yield acc.result(self.model)

    async def aclose(self) -> None:
        await self._client.aclose()


def _error_message(body: str) -> str:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return body[:300]
    err = data.get("error", data)
    return err.get("message", json.dumps(err)) if isinstance(err, dict) else str(err)
