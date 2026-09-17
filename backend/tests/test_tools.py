import pytest

from app.agent.tool_impls import execute_tool
from app.services import budget_service

USER_ID = 1


def test_budget_status_for_category(db_session):
    result = execute_tool(db_session, USER_ID, "get_budget_status", {"category": "Ristoranti"})
    assert result["budget_limit"] == 150.0
    assert result["spent"] == 90.0
    assert result["remaining"] == 60.0


def test_monthly_spending_total(db_session):
    result = execute_tool(db_session, USER_ID, "get_monthly_spending", {})
    assert result["total_spent"] == 640.0


def test_savings_goal_status_on_track(db_session):
    result = execute_tool(db_session, USER_ID, "get_savings_goal_status", {})
    assert result["total_budgeted"] == 1030.0
    assert result["total_spent"] == 640.0
    assert result["projected_savings"] == 390.0
    assert result["on_track"] is True
    assert result["margin"] == 90.0


def test_add_expense_reduces_remaining(db_session):
    result = execute_tool(
        db_session, USER_ID, "add_expense", {"category": "Trasporti", "amount": 20, "description": "Taxi"}
    )
    assert result["category_remaining_after"] == 40.0  # 100 - 40 - 20

    spending = execute_tool(db_session, USER_ID, "get_monthly_spending", {"category": "Trasporti"})
    assert spending["total_spent"] == 60.0


def test_add_expense_rejects_non_positive_amount(db_session):
    with pytest.raises(ValueError):
        execute_tool(db_session, USER_ID, "add_expense", {"category": "Trasporti", "amount": -5})


def test_create_or_update_budget(db_session):
    execute_tool(db_session, USER_ID, "create_or_update_budget", {"category": "Ristoranti", "amount_limit": 200})
    status = execute_tool(db_session, USER_ID, "get_budget_status", {"category": "Ristoranti"})
    assert status["budget_limit"] == 200.0
    assert status["remaining"] == 110.0  # 200 - 90


def test_set_savings_goal_updates_on_track(db_session):
    execute_tool(db_session, USER_ID, "set_savings_goal", {"monthly_target": 500})
    status = execute_tool(db_session, USER_ID, "get_savings_goal_status", {})
    assert status["monthly_target"] == 500.0
    assert status["on_track"] is False
    assert status["margin"] == -110.0  # 390 - 500


def test_move_funds_between_categories(db_session):
    result = execute_tool(
        db_session,
        USER_ID,
        "move_funds_between_categories",
        {"from_category": "Shopping", "to_category": "Ristoranti", "amount": 20},
    )
    assert result["from_category_new_limit"] == 80.0  # 100 - 20
    assert result["to_category_new_limit"] == 170.0  # 150 + 20

    status = execute_tool(db_session, USER_ID, "get_budget_status", {"category": "Ristoranti"})
    assert status["remaining"] == 80.0  # 170 - 90


def test_move_funds_insufficient_source_budget_raises(db_session):
    with pytest.raises(ValueError):
        execute_tool(
            db_session,
            USER_ID,
            "move_funds_between_categories",
            {"from_category": "Shopping", "to_category": "Ristoranti", "amount": 500},
        )


def test_unknown_category_raises_with_available_list(db_session):
    with pytest.raises(ValueError, match="non trovata"):
        execute_tool(db_session, USER_ID, "get_budget_status", {"category": "Vacanze"})


def test_user_preference_round_trip(db_session):
    execute_tool(
        db_session,
        USER_ID,
        "update_user_preference",
        {"key": "cost_cutting_priority", "value": '["Ristoranti", "Shopping"]'},
    )
    prefs = execute_tool(db_session, USER_ID, "get_user_preferences", {})
    assert prefs["preferences"]["cost_cutting_priority"] == ["Ristoranti", "Shopping"]


def test_current_month_helper_matches_today_format():
    assert len(budget_service.current_month()) == 7  # "YYYY-MM"
