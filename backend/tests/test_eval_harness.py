"""Validates the eval harness itself (fixtures, helpers, check functions) without
calling Claude - each check function is exercised against a synthetic outcome built
from ground truth, so a logic bug in a check (e.g. a wrong expected number) is
caught here rather than silently passing/failing a real, costly eval run."""

from evaluation.cases import definitions as defs
from evaluation.cases.helpers import category_count, get_budget_limit, savings_goal_target, transaction_exists
from evaluation.fixtures import fresh_eval_session
from evaluation.types import ConversationOutcome, ToolCallRecord, TurnOutcome


def _turn(text: str = "", tool_calls=None) -> TurnOutcome:
    return TurnOutcome(
        final_text=text,
        tool_calls=tool_calls or [],
        input_tokens=100,
        output_tokens=50,
        cost_usd=0.001,
        latency_ms=500,
    )


def test_fresh_eval_session_matches_fixture_numbers():
    db = fresh_eval_session()
    assert category_count(db) == 6
    assert get_budget_limit(db, "Ristoranti", defs.MONTH) == 150.0
    assert savings_goal_target(db) == 300.0
    db.close()


def test_read_monthly_spending_check_pass_and_fail():
    db = fresh_eval_session()
    good_call = ToolCallRecord(
        "get_monthly_spending", {"category": "Ristoranti"}, {"total_spent": 90.0}, False
    )
    outcome = ConversationOutcome(turns=[_turn(tool_calls=[good_call])], db=db)
    passed, _ = defs._check_read_monthly_spending(outcome)
    assert passed is True

    # An unfiltered query that reports Ristoranti in its breakdown is equally valid
    bulk_call = ToolCallRecord(
        "get_monthly_spending",
        {},
        {"total_spent": 640.0, "breakdown": [{"category": "Ristoranti", "spent": 90.0}]},
        False,
    )
    bulk = ConversationOutcome(turns=[_turn(tool_calls=[bulk_call])], db=db)
    assert defs._check_read_monthly_spending(bulk)[0] is True

    bad_call = ToolCallRecord(
        "get_monthly_spending", {"category": "Ristoranti"}, {"total_spent": 999.0}, False
    )
    outcome_bad = ConversationOutcome(turns=[_turn(tool_calls=[bad_call])], db=db)
    passed_bad, _ = defs._check_read_monthly_spending(outcome_bad)
    assert passed_bad is False
    db.close()


def test_reasoning_afford_dinner_requires_both_tools_and_correct_number():
    db = fresh_eval_session()
    budget_call = ToolCallRecord("get_budget_status", {"category": "Ristoranti"}, {"remaining": 60.0}, False)
    goal_call = ToolCallRecord("get_savings_goal_status", {}, {"on_track": True, "margin": 90.0}, False)

    # Missing the savings-goal tool call -> fail (multi-step reasoning wasn't done)
    incomplete = ConversationOutcome(turns=[_turn("...", [budget_call])], db=db)
    passed, detail = defs._check_reasoning_afford_dinner(incomplete)
    assert passed is False
    assert "MANCANTE" in detail

    # Both tools called but the final answer never cites the number -> fail
    silent = ConversationOutcome(turns=[_turn("Sì, puoi permettertela.", [budget_call, goal_call])], db=db)
    assert defs._check_reasoning_afford_dinner(silent)[0] is False

    # Both tools called and the answer cites the 60€ residual -> pass
    complete = ConversationOutcome(
        turns=[_turn("Nella categoria Ristoranti ti restano solo 60€ questo mese.", [budget_call, goal_call])],
        db=db,
    )
    assert defs._check_reasoning_afford_dinner(complete)[0] is True

    # The agent legitimately inspects a second category to suggest a transfer: the check
    # must still read Ristoranti's value, not whichever budget call happened to come last.
    other_call = ToolCallRecord(
        "get_budget_status", {"category": "Intrattenimento"}, {"remaining": 20.0}, False
    )
    with_extra_lookup = ConversationOutcome(
        turns=[
            _turn(
                "Ti restano 60€ su Ristoranti; posso spostare 20€ da Intrattenimento.",
                [budget_call, goal_call, other_call],
            )
        ],
        db=db,
    )
    assert defs._check_reasoning_afford_dinner(with_extra_lookup)[0] is True

    # An all-categories query must work too
    bulk_call = ToolCallRecord(
        "get_budget_status",
        {},
        {"categories": [{"category": "Ristoranti", "remaining": 60.0}, {"category": "Spesa", "remaining": 150.0}]},
        False,
    )
    bulk = ConversationOutcome(
        turns=[_turn("Su Ristoranti ti restano 60€.", [bulk_call, goal_call])], db=db
    )
    assert defs._check_reasoning_afford_dinner(bulk)[0] is True
    db.close()


def test_memory_preference_recall_requires_a_real_write_and_updated_personalization():
    db = fresh_eval_session()

    # Seeded priority still in place (agent never wrote the new order) -> fail
    stale = ConversationOutcome(turns=[_turn(), _turn("Taglia su Shopping.")], db=db)
    assert defs._check_memory_preference_recall(stale)[0] is False

    # Simulate the agent actually persisting the new priority order
    from app.agent.memory import set_preference

    set_preference(db, 1, "cost_cutting_priority", '["Shopping", "Trasporti", "Intrattenimento"]')

    # Stored, but the answer still leads with the stale priority -> fail
    stale_answer = ConversationOutcome(
        turns=[_turn(), _turn("Taglia prima su Intrattenimento, poi Shopping.")], db=db
    )
    assert defs._check_memory_preference_recall(stale_answer)[0] is False

    # Stored and the answer leads with the new priority -> pass
    ok = ConversationOutcome(
        turns=[_turn(), _turn("Ti conviene tagliare prima su Shopping, poi Trasporti.")], db=db
    )
    assert defs._check_memory_preference_recall(ok)[0] is True
    db.close()


def test_edge_case_unknown_category_detects_spurious_writes():
    db = fresh_eval_session()
    outcome_clean = ConversationOutcome(turns=[_turn("Non trovo la categoria Vacanze.")], db=db)
    assert defs._check_edge_case_unknown_category(outcome_clean)[0] is True

    # Simulate a bug where the agent (or a tool) created a stray category/transaction
    from app.models import Category

    db.add(Category(user_id=1, name="Vacanze"))
    db.commit()
    outcome_dirty = ConversationOutcome(turns=[_turn("Aggiunta categoria Vacanze.")], db=db)
    assert defs._check_edge_case_unknown_category(outcome_dirty)[0] is False
    db.close()


def test_all_case_ids_unique():
    ids = [c.id for c in defs.CASES]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 8


def test_transaction_exists_helper():
    db = fresh_eval_session()
    assert transaction_exists(db, "Ristoranti", 35.0) is True
    assert transaction_exists(db, "Ristoranti", 12345.0) is False
    db.close()
