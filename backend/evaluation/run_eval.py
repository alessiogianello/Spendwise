"""Offline eval runner for the Spendwise agent.

Runs every case in evaluation/cases/definitions.py against a fresh, deterministic
DB, checks the result against ground truth (DB state or tool output - never free
text alone), and reports accuracy, cost per request, and latency.

Usage:
    python -m evaluation.run_eval
    python -m evaluation.run_eval --model anthropic/claude-sonnet-5
    python -m evaluation.run_eval --model openai/gpt-5.4-mini
    python -m evaluation.run_eval --case reasoning_afford_dinner
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Spendwise agent offline eval suite")
    parser.add_argument("--model", help="Override LLM_MODEL for this run (e.g. anthropic/claude-sonnet-5, openai/gpt-5.4-mini)")
    parser.add_argument("--case", help="Only run cases whose id contains this substring")
    parser.add_argument("--output", help="Path for the JSON report", default=None)
    args = parser.parse_args()

    if args.model:
        os.environ["LLM_MODEL"] = args.model

    # Imported after the env override above, so app.config.Settings picks it up.
    from app.agent.orchestrator import get_or_create_session, stream_agent_turn
    from app.config import get_settings
    from evaluation.cases.definitions import CASES
    from evaluation.fixtures import EVAL_USER_ID, fresh_eval_session
    from evaluation.metrics import compute_metrics, print_report
    from evaluation.types import CaseResult, ConversationOutcome, ToolCallRecord, TurnOutcome

    settings = get_settings()
    if not settings.openrouter_api_key:
        print(
            "OPENROUTER_API_KEY is not set. Set it in backend/.env or the environment "
            "before running the eval suite (it makes real API calls).",
            file=sys.stderr,
        )
        return 2

    cases = [c for c in CASES if not args.case or args.case in c.id]
    if not cases:
        print(f"No case matches '{args.case}'", file=sys.stderr)
        return 2

    async def run_turn(db, session_id: int, message: str) -> TurnOutcome:
        tool_calls: list[ToolCallRecord] = []
        pending_call: dict | None = None
        final_text = ""
        input_tokens = output_tokens = 0
        cost_usd = latency_ms = 0.0

        async for event in stream_agent_turn(db, EVAL_USER_ID, session_id, message):
            if event["event"] == "tool_call":
                pending_call = {"name": event["data"]["name"], "input": event["data"]["input"]}
            elif event["event"] == "tool_result" and pending_call is not None:
                tool_calls.append(
                    ToolCallRecord(
                        name=pending_call["name"],
                        input=pending_call["input"],
                        output=event["data"]["output"],
                        is_error=event["data"]["is_error"],
                    )
                )
                pending_call = None
            elif event["event"] == "done":
                final_text = event["data"]["final_text"]
                usage = event["data"]["usage"]
                input_tokens = usage["input_tokens"]
                output_tokens = usage["output_tokens"]
                cost_usd = event["data"]["cost_usd"]
                latency_ms = event["data"]["latency_ms"]
            elif event["event"] == "error":
                raise RuntimeError(event["data"]["message"])

        return TurnOutcome(
            final_text=final_text,
            tool_calls=tool_calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )

    async def run_case(case) -> CaseResult:
        db = fresh_eval_session()
        try:
            session = get_or_create_session(db, EVAL_USER_ID, None)
            turns = [await run_turn(db, session.id, msg) for msg in case.user_messages]
            outcome = ConversationOutcome(turns=turns, db=db)
            try:
                passed, detail = case.check(outcome)
            except Exception as exc:  # a broken check counts as a failed case, not a crash
                return CaseResult(case=case, passed=False, detail=f"eccezione nel check: {exc}", outcome=outcome)
            return CaseResult(case=case, passed=passed, detail=detail, outcome=outcome)
        except Exception as exc:
            return CaseResult(case=case, passed=False, detail="errore durante l'esecuzione", error=str(exc))
        finally:
            db.close()

    results = [asyncio.run(run_case(case)) for case in cases]
    metrics = compute_metrics(results)
    print_report(results, metrics, f"openrouter:{settings.model}")

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": "openrouter",
        "model": settings.model,
        "metrics": {
            "accuracy": metrics.accuracy,
            "passed": metrics.passed,
            "total": metrics.total,
            "total_cost_usd": metrics.total_cost_usd,
            "avg_cost_usd": metrics.avg_cost_usd,
            "avg_tokens": metrics.avg_tokens,
            "avg_latency_ms": metrics.avg_latency_ms,
            "p95_latency_ms": metrics.p95_latency_ms,
            "by_category": metrics.by_category,
        },
        "cases": [
            {
                "id": r.case.id,
                "category": r.case.category,
                "passed": r.passed,
                "detail": r.detail,
                "error": r.error,
                "cost_usd": r.outcome.total_cost_usd if r.outcome else None,
                "tokens": r.outcome.total_tokens if r.outcome else None,
                "latency_ms": r.outcome.total_latency_ms if r.outcome else None,
                "final_text": r.outcome.last.final_text if r.outcome else None,
                "tool_calls": (
                    [{"name": tc.name, "input": tc.input} for tc in r.outcome.all_tool_calls]
                    if r.outcome
                    else []
                ),
            }
            for r in results
        ],
    }

    output_path = Path(args.output) if args.output else Path(__file__).parent / "reports" / (
        f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nReport salvato in {output_path}")

    return 0 if metrics.passed == metrics.total else 1


if __name__ == "__main__":
    raise SystemExit(main())
