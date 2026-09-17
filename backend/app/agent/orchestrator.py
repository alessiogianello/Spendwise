import json
import time
from collections.abc import AsyncGenerator

import anthropic
from sqlalchemy.orm import Session

from app.agent.memory import get_preferences
from app.agent.pricing import estimate_cost_usd
from app.agent.prompts import build_context_prefix, build_system_blocks
from app.agent.tool_impls import execute_tool
from app.agent.tools import STATUS_MESSAGES, TOOLS
from app.config import get_settings
from app.models import ConversationMessage, ConversationSession

settings = get_settings()
MAX_TOOL_ITERATIONS = 6
MAX_TOKENS = 4096


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
    """Runs one agentic turn against Claude, yielding SSE-ready event dicts:
    status, thinking, tool_call, tool_result, text, error, done."""
    start = time.monotonic()
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

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
    final_text_parts: list[str] = []

    try:
        for _ in range(MAX_TOOL_ITERATIONS):
            async with client.messages.stream(
                model=settings.claude_model,
                max_tokens=MAX_TOKENS,
                system=build_system_blocks(),
                thinking={"type": "adaptive", "display": "summarized"},
                tools=TOOLS,
                messages=messages,
            ) as stream:
                async for event in stream:
                    if event.type == "content_block_start" and event.content_block.type == "tool_use":
                        yield {
                            "event": "status",
                            "data": {
                                "message": STATUS_MESSAGES.get(
                                    event.content_block.name, "Sto elaborando..."
                                )
                            },
                        }
                    elif event.type == "content_block_delta":
                        if event.delta.type == "thinking_delta":
                            yield {"event": "thinking", "data": {"delta": event.delta.thinking}}
                        elif event.delta.type == "text_delta":
                            final_text_parts.append(event.delta.text)
                            yield {"event": "text", "data": {"delta": event.delta.text}}

                response = await stream.get_final_message()

            usage = response.usage
            total_input_tokens += usage.input_tokens
            total_output_tokens += usage.output_tokens
            total_cache_creation += getattr(usage, "cache_creation_input_tokens", 0) or 0
            total_cache_read += getattr(usage, "cache_read_input_tokens", 0) or 0

            assistant_content = [block.model_dump() for block in response.content]
            messages.append({"role": "assistant", "content": assistant_content})
            _save_message(
                db, session_id, "assistant", assistant_content, usage.input_tokens, usage.output_tokens
            )

            if response.stop_reason != "tool_use":
                break

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            tool_results = []
            for block in tool_use_blocks:
                yield {"event": "tool_call", "data": {"name": block.name, "input": block.input}}
                try:
                    result = execute_tool(db, user_id, block.name, block.input)
                    is_error = False
                except ValueError as exc:
                    result = {"error": str(exc)}
                    is_error = True
                yield {
                    "event": "tool_result",
                    "data": {"name": block.name, "output": result, "is_error": is_error},
                }
                tool_result_block = {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str, ensure_ascii=False),
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
        cost_usd = estimate_cost_usd(
            settings.claude_model,
            total_input_tokens,
            total_output_tokens,
            total_cache_creation,
            total_cache_read,
        )
        yield {
            "event": "done",
            "data": {
                "session_id": session_id,
                "final_text": "".join(final_text_parts),
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
    except anthropic.APIError as exc:
        yield {"event": "error", "data": {"message": f"Errore Claude API: {exc}"}}
    except Exception as exc:  # noqa: BLE001 - top-level SSE boundary: never let the
        # stream die silently (e.g. missing credentials raises TypeError, not APIError)
        yield {"event": "error", "data": {"message": f"Errore imprevisto: {exc}"}}
    finally:
        await client.close()
