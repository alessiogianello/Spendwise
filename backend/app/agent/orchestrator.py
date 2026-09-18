import json
import time
from collections.abc import AsyncGenerator

from sqlalchemy.orm import Session

from app.agent.memory import get_preferences
from app.agent.prompts import STATIC_SYSTEM_PROMPT, build_context_prefix
from app.agent.providers import ProviderError, StreamDelta, TurnResult, create_provider
from app.agent.tool_impls import execute_tool
from app.agent.tools import STATUS_MESSAGES, TOOLS
from app.config import get_settings
from app.models import ConversationMessage, ConversationSession

settings = get_settings()
MAX_TOOL_ITERATIONS = 6


def _load_history(db: Session, session_id: int) -> list[dict]:
    rows = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.session_id == session_id)
        .order_by(ConversationMessage.id)
        .all()
    )
    return [{"role": row.role, "content": json.loads(row.content_json)} for row in rows]


def _save_message(
    db: Session,
    session_id: int,
    role: str,
    content: list[dict],
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> None:
    db.add(
        ConversationMessage(
            session_id=session_id,
            role=role,
            content_json=json.dumps(content),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
    )
    db.commit()


def get_or_create_session(db: Session, user_id: int, session_id: int | None) -> ConversationSession:
    if session_id is not None:
        session = db.get(ConversationSession, session_id)
        if session is not None and session.user_id == user_id:
            return session
    session = ConversationSession(user_id=user_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


async def stream_agent_turn(
    db: Session, user_id: int, session_id: int, user_message: str
) -> AsyncGenerator[dict, None]:
    """Runs one agentic turn against the configured provider, yielding SSE-ready
    event dicts: status, thinking, tool_call, tool_result, text, error, done."""
    start = time.monotonic()
    provider = None

    messages = _load_history(db, session_id)
    preferences = get_preferences(db, user_id)
    first_turn_content = build_context_prefix(preferences) + user_message
    user_content = [{"type": "text", "text": first_turn_content}]
    messages.append({"role": "user", "content": user_content})
    _save_message(db, session_id, "user", user_content)

    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_creation = 0
    total_cache_read = 0
    billed_cost_usd: float | None = None  # None until the provider reports a charge
    final_text_parts: list[str] = []

    try:
        provider = create_provider(settings)
        for _ in range(MAX_TOOL_ITERATIONS):
            result: TurnResult | None = None
            async for item in provider.stream(system=STATIC_SYSTEM_PROMPT, messages=messages, tools=TOOLS):
                if isinstance(item, TurnResult):
                    result = item  # last item; let the generator finish so it cleans up
                    continue
                yield _delta_event(item, final_text_parts)
            if result is None:
                raise ProviderError("Il provider ha chiuso lo stream senza un risultato finale.")

            usage = result.usage
            total_input_tokens += usage.input_tokens
            total_output_tokens += usage.output_tokens
            total_cache_creation += usage.cache_creation_tokens
            total_cache_read += usage.cache_read_tokens
            if usage.cost_usd is not None:
                billed_cost_usd = (billed_cost_usd or 0.0) + usage.cost_usd

            messages.append({"role": "assistant", "content": result.content})
            _save_message(
                db, session_id, "assistant", result.content, usage.input_tokens, usage.output_tokens
            )

            if result.stop_reason != "tool_use":
                break

            tool_use_blocks = [b for b in result.content if b["type"] == "tool_use"]
            tool_results = []
            for block in tool_use_blocks:
                yield {"event": "tool_call", "data": {"name": block["name"], "input": block["input"]}}
                try:
                    tool_output = execute_tool(db, user_id, block["name"], block["input"])
                    is_error = False
                except ValueError as exc:
                    tool_output = {"error": str(exc)}
                    is_error = True
                yield {
                    "event": "tool_result",
                    "data": {"name": block["name"], "output": tool_output, "is_error": is_error},
                }
                tool_result_block = {
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": json.dumps(tool_output, default=str, ensure_ascii=False),
                }
                if is_error:
                    tool_result_block["is_error"] = True
                tool_results.append(tool_result_block)

            messages.append({"role": "user", "content": tool_results})
            _save_message(db, session_id, "user", tool_results)
        else:
            yield {
                "event": "error",
                "data": {"message": "Raggiunto il numero massimo di passaggi con i tool."},
            }

        latency_ms = round((time.monotonic() - start) * 1000)
        # OpenRouter reports the billed amount on the final chunk; 0.0 means
        # no usage chunk arrived, not a free call.
        cost_usd = round(billed_cost_usd, 6) if billed_cost_usd is not None else 0.0
        yield {
            "event": "done",
            "data": {
                "session_id": session_id,
                "final_text": "".join(final_text_parts),
                "provider": provider.name,
                "model": provider.model,
                "usage": {
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens,
                    "cache_creation_input_tokens": total_cache_creation,
                    "cache_read_input_tokens": total_cache_read,
                },
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
            },
        }
    except ProviderError as exc:
        yield {"event": "error", "data": {"message": str(exc)}}
    except Exception as exc:  # noqa: BLE001 - top-level SSE boundary: never let the
        # stream die silently (e.g. missing credentials raises TypeError, not APIError)
        yield {"event": "error", "data": {"message": f"Errore imprevisto: {exc}"}}
    finally:
        if provider is not None:
            await provider.aclose()


def _delta_event(delta: StreamDelta, final_text_parts: list[str]) -> dict:
    match delta.kind:
        case "tool_start":
            return {"event": "status", "data": {"message": STATUS_MESSAGES.get(delta.text, "Sto elaborando...")}}
        case "thinking":
            return {"event": "thinking", "data": {"delta": delta.text}}
        case _:
            final_text_parts.append(delta.text)
            return {"event": "text", "data": {"delta": delta.text}}
