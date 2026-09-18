"""The agent loop end to end with a scripted provider: proves the orchestrator is
provider-agnostic (tool execution, persistence in canonical blocks, SSE events,
cost handling) without any API call."""

import json

import pytest

import app.agent.orchestrator as orchestrator
from app.agent.providers.base import ProviderError, StreamDelta, TurnResult, TurnUsage
from app.models import ConversationMessage, Transaction


class ScriptedProvider:
    """Replays a list of turns; each turn is a list of StreamDelta/TurnResult items."""

    name = "scripted"
    model = "test/model"

    def __init__(self, turns):
        self.turns = list(turns)
        self.seen_messages = []
        self.closed = False

    async def stream(self, *, system, messages, tools):
        self.seen_messages.append([json.loads(json.dumps(m)) for m in messages])
        for item in self.turns.pop(0):
            yield item

    async def aclose(self):
        self.closed = True


async def collect(db, user_id, session_id, message):
    return [e async for e in orchestrator.stream_agent_turn(db, user_id, session_id, message)]


@pytest.mark.asyncio
async def test_tool_loop_executes_writes_and_reports_billed_cost(db_session, monkeypatch):
    provider = ScriptedProvider(
        [
            [
                StreamDelta("thinking", "registro la spesa"),
                StreamDelta("tool_start", "add_expense"),
                TurnResult(
                    content=[
                        {"type": "thinking", "thinking": "registro la spesa"},
                        {"type": "tool_use", "id": "call_1", "name": "add_expense",
                         "input": {"amount": 12.5, "category": "Ristoranti", "description": "pizza"}},
                    ],
                    stop_reason="tool_use",
                    usage=TurnUsage(input_tokens=100, output_tokens=10, cost_usd=0.001),
                ),
            ],
            [
                StreamDelta("text", "Fatto: 12,50 € in Ristoranti."),
                TurnResult(
                    content=[{"type": "text", "text": "Fatto: 12,50 € in Ristoranti."}],
                    stop_reason="end_turn",
                    usage=TurnUsage(input_tokens=150, output_tokens=20, cost_usd=0.002),
                ),
            ],
        ]
    )
    monkeypatch.setattr(orchestrator, "create_provider", lambda settings: provider)
    session = orchestrator.get_or_create_session(db_session, 1, None)
    before = db_session.query(Transaction).count()

    events = await collect(db_session, 1, session.id, "Ho speso 12.50 in pizza")

    kinds = [e["event"] for e in events]
    assert kinds == ["thinking", "status", "tool_call", "tool_result", "text", "done"]
    assert events[2]["data"]["name"] == "add_expense"
    assert events[3]["data"]["is_error"] is False

    # The write really happened.
    assert db_session.query(Transaction).count() == before + 1

    done = events[-1]["data"]
    assert done["final_text"] == "Fatto: 12,50 € in Ristoranti."
    assert done["usage"]["input_tokens"] == 250
    assert done["cost_usd"] == 0.003  # billed by the provider, not estimated
    assert done["provider"] == "scripted" and done["model"] == "test/model"

    # Second call saw the tool result in canonical block form.
    second = provider.seen_messages[1]
    assert second[-1]["role"] == "user"
    assert second[-1]["content"][0]["type"] == "tool_result"
    assert second[-1]["content"][0]["tool_use_id"] == "call_1"

    # History persisted: user, assistant(tool_use), user(tool_result), assistant(text).
    rows = db_session.query(ConversationMessage).filter_by(session_id=session.id).order_by(ConversationMessage.id).all()
    assert [r.role for r in rows] == ["user", "assistant", "user", "assistant"]
    assert provider.closed


@pytest.mark.asyncio
async def test_tool_error_is_reported_and_fed_back(db_session, monkeypatch):
    provider = ScriptedProvider(
        [
            [TurnResult(
                content=[{"type": "tool_use", "id": "c1", "name": "add_expense",
                          "input": {"amount": -5, "category": "Ristoranti"}}],
                stop_reason="tool_use",
            )],
            [TurnResult(content=[{"type": "text", "text": "Importo non valido."}])],
        ]
    )
    monkeypatch.setattr(orchestrator, "create_provider", lambda settings: provider)
    session = orchestrator.get_or_create_session(db_session, 1, None)

    events = await collect(db_session, 1, session.id, "spesa -5")

    tool_result = next(e for e in events if e["event"] == "tool_result")
    assert tool_result["data"]["is_error"] is True
    fed_back = provider.seen_messages[1][-1]["content"][0]
    assert fed_back["is_error"] is True
    assert events[-1]["event"] == "done"
    assert events[-1]["data"]["cost_usd"] == 0.0  # provider reported no charge


@pytest.mark.asyncio
async def test_provider_error_becomes_error_event(db_session, monkeypatch):
    class Failing:
        name = "failing"
        model = "x/y"

        async def stream(self, **_):
            raise ProviderError("chiave non valida")
            yield  # noqa: unreachable - makes this an async generator

        async def aclose(self):
            pass

    monkeypatch.setattr(orchestrator, "create_provider", lambda settings: Failing())
    session = orchestrator.get_or_create_session(db_session, 1, None)

    events = await collect(db_session, 1, session.id, "ciao")

    assert events == [{"event": "error", "data": {"message": "chiave non valida"}}]
