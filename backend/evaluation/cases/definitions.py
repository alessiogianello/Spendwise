"""8-10 eval cases covering: read/multi-step reasoning, write actions, personalization
memory, and an edge case. Each check asserts against ground truth - either the DB
(for actions) or the deterministic tool output (for reads) - never against free text
alone, so a pass/fail is never dependent on the LLM's exact wording."""

from app.services.budget_service import current_month
from evaluation.cases.helpers import (
    approx,
    category_count,
    count_transactions,
    get_budget_limit,
    preference_value,
    savings_goal_target,
    transaction_exists,
)
from evaluation.types import ConversationOutcome, EvalCase

MONTH = current_month()


def _budget_remaining_for(o: ConversationOutcome, category_name: str) -> float | None:
    """The agent may inspect several categories in one turn, and may query them one by
    one or all at once - so look up the value by category rather than by call order."""
    for tc in o.all_tool_calls:
        if tc.name != "get_budget_status" or not isinstance(tc.output, dict):
            continue
        requested = (tc.input or {}).get("category")
        if requested and requested.strip().lower() == category_name.lower():
            return tc.output.get("remaining")
        for row in tc.output.get("categories", []):
            if str(row.get("category", "")).lower() == category_name.lower():
                return row.get("remaining")
    return None


def _spending_for(o: ConversationOutcome, category_name: str) -> float | None:
    for tc in o.all_tool_calls:
        if tc.name != "get_monthly_spending" or not isinstance(tc.output, dict):
            continue
        requested = (tc.input or {}).get("category")
        if requested and requested.strip().lower() == category_name.lower():
            return tc.output.get("total_spent")
        for row in tc.output.get("breakdown", []):
            if str(row.get("category", "")).lower() == category_name.lower():
                return row.get("spent")
    return None


def _check_read_monthly_spending(o: ConversationOutcome) -> tuple[bool, str]:
    if not o.tool_was_called("get_monthly_spending"):
        return False, "get_monthly_spending non è stato chiamato"
    spent = _spending_for(o, "Ristoranti")
    if spent is None:
        return False, "nessuna chiamata ha restituito la spesa della categoria Ristoranti"
    if not approx(spent, 90.0):
        return False, f"spesa Ristoranti attesa 90.0, ottenuta {spent}"
    return True, f"spesa Ristoranti={spent} corretta"


def _check_read_budget_status(o: ConversationOutcome) -> tuple[bool, str]:
    if not o.tool_was_called("get_budget_status"):
        return False, "get_budget_status non è stato chiamato"
    remaining = _budget_remaining_for(o, "Spesa")
    if remaining is None:
        return False, "nessuna chiamata ha restituito il budget della categoria Spesa"
    if not approx(remaining, 150.0):
        return False, f"residuo Spesa atteso 150.0, ottenuto {remaining}"
    return True, f"residuo Spesa={remaining} corretto"


def _check_read_savings_goal(o: ConversationOutcome) -> tuple[bool, str]:
    call = o.find_tool_call("get_savings_goal_status")
    if call is None:
        return False, "get_savings_goal_status non è stato chiamato"
    if call.output.get("on_track") is not True:
        return False, f"on_track atteso True, ottenuto {call.output.get('on_track')}"
    if not approx(call.output.get("margin", -999), 90.0):
        return False, f"margin atteso 90.0, ottenuto {call.output.get('margin')}"
    return True, "on_track=True, margin=90.0 corretti"


def _check_action_add_expense(o: ConversationOutcome) -> tuple[bool, str]:
    if not o.tool_was_called("add_expense"):
        return False, "add_expense non è stato chiamato"
    if not transaction_exists(o.db, "Spesa", 25.0):
        return False, "nessuna transazione da 25.0€ in Spesa trovata nel DB"
    if count_transactions(o.db) != 12:  # 11 seedate + 1 nuova
        return False, f"numero transazioni atteso 12, trovato {count_transactions(o.db)}"
    return True, "transazione da 25€ in Spesa creata correttamente"


def _check_action_create_budget(o: ConversationOutcome) -> tuple[bool, str]:
    if not o.tool_was_called("create_or_update_budget"):
        return False, "create_or_update_budget non è stato chiamato"
    limit = get_budget_limit(o.db, "Trasporti", MONTH)
    if not approx(limit if limit is not None else -1, 250.0):
        return False, f"budget Trasporti atteso 250.0, trovato {limit}"
    return True, f"budget Trasporti aggiornato a {limit}"


def _check_action_set_savings_goal(o: ConversationOutcome) -> tuple[bool, str]:
    if not o.tool_was_called("set_savings_goal"):
        return False, "set_savings_goal non è stato chiamato"
    target = savings_goal_target(o.db)
    if not approx(target if target is not None else -1, 350.0):
        return False, f"monthly_target atteso 350.0, trovato {target}"
    return True, f"obiettivo di risparmio aggiornato a {target}"


def _check_action_move_funds(o: ConversationOutcome) -> tuple[bool, str]:
    if not o.tool_was_called("move_funds_between_categories"):
        return False, "move_funds_between_categories non è stato chiamato"
    shopping = get_budget_limit(o.db, "Shopping", MONTH)
    ristoranti = get_budget_limit(o.db, "Ristoranti", MONTH)
    if not approx(shopping if shopping is not None else -1, 80.0):
        return False, f"budget Shopping atteso 80.0, trovato {shopping}"
    if not approx(ristoranti if ristoranti is not None else -1, 170.0):
        return False, f"budget Ristoranti atteso 170.0, trovato {ristoranti}"
    return True, f"fondi spostati: Shopping={shopping}, Ristoranti={ristoranti}"


def _check_reasoning_afford_dinner(o: ConversationOutcome) -> tuple[bool, str]:
    checked_budget = o.tool_was_called("get_budget_status")
    checked_goal = o.tool_was_called("get_savings_goal_status")
    if not checked_budget or not checked_goal:
        return False, (
            "reasoning multi-step incompleto: "
            f"get_budget_status={'ok' if checked_budget else 'MANCANTE'}, "
            f"get_savings_goal_status={'ok' if checked_goal else 'MANCANTE'}"
        )
    remaining = _budget_remaining_for(o, "Ristoranti")
    if remaining is None:
        return False, "l'agente non ha controllato il budget della categoria Ristoranti"
    if not approx(remaining, 60.0):
        return False, f"residuo Ristoranti atteso 60.0, ottenuto {remaining}"
    if "60" not in o.last.final_text:
        return False, "la risposta finale non cita il residuo di budget (60€) su cui si basa il ragionamento"
    return True, "l'agente ha controllato budget + obiettivo di risparmio e citato il residuo corretto (60€)"


def _check_memory_preference_recall(o: ConversationOutcome) -> tuple[bool, str]:
    # The seeded priority is [Intrattenimento, Shopping, Ristoranti]; turn 1 asks for a
    # *different* order, so the agent has to actually write it - otherwise the agent
    # could pass by doing nothing and reading back the stale seeded value in turn 2.
    stored = preference_value(o.db, "cost_cutting_priority")
    if not isinstance(stored, list) or not stored:
        return False, f"cost_cutting_priority non salvata come lista nel DB (trovato: {stored})"
    if stored[0].strip().lower() != "shopping":
        return False, f"priorità di taglio attesa con Shopping al primo posto, trovata {stored}"

    # The agent may read the preference back either via get_user_preferences or from the
    # context prefix the orchestrator injects, so this asserts the *behaviour*: the turn-2
    # answer must lead with the newly stored priority, not the stale seeded one.
    answer = o.last.final_text
    shopping_at = answer.find("Shopping")
    intrattenimento_at = answer.find("Intrattenimento")
    if shopping_at == -1:
        return False, "la risposta del turno 2 non riflette la nuova priorità di taglio (Shopping)"
    if intrattenimento_at != -1 and intrattenimento_at < shopping_at:
        return False, "la risposta cita per prima la vecchia priorità (Intrattenimento) invece di Shopping"
    return True, f"preferenza aggiornata a {stored} nel turno 1 e usata per personalizzare il turno 2"


def _check_edge_case_unknown_category(o: ConversationOutcome) -> tuple[bool, str]:
    if category_count(o.db) != 6:
        return False, f"il numero di categorie è cambiato (atteso 6, trovato {category_count(o.db)})"
    if count_transactions(o.db) != 11:
        return False, "è stata creata una transazione nonostante la categoria non esistesse"
    return True, "nessuna categoria/transazione spuria creata per 'Vacanze'"


CASES: list[EvalCase] = [
    EvalCase(
        id="read_monthly_spending_ristoranti",
        description="Quanto ho speso finora in Ristoranti questo mese?",
        user_messages=["Quanto ho speso finora in Ristoranti questo mese?"],
        check=_check_read_monthly_spending,
        category="read",
    ),
    EvalCase(
        id="read_budget_status_spesa",
        description="Quanto budget mi resta nella categoria Spesa questo mese?",
        user_messages=["Quanto budget mi resta nella categoria Spesa questo mese?"],
        check=_check_read_budget_status,
        category="read",
    ),
    EvalCase(
        id="read_savings_goal_status",
        description="Sono in linea con il mio obiettivo di risparmio questo mese?",
        user_messages=["Sono in linea con il mio obiettivo di risparmio mensile?"],
        check=_check_read_savings_goal,
        category="read",
    ),
    EvalCase(
        id="action_add_expense",
        description="Registra una spesa di 25€ per la spesa al supermercato",
        user_messages=["Aggiungi una spesa di 25€ nella categoria Spesa per la spesa al supermercato"],
        check=_check_action_add_expense,
        category="action",
    ),
    EvalCase(
        id="action_create_budget",
        description="Imposta un budget di 250€ per Trasporti questo mese",
        user_messages=["Imposta un budget di 250€ per Trasporti questo mese"],
        check=_check_action_create_budget,
        category="action",
    ),
    EvalCase(
        id="action_set_savings_goal",
        description="Cambia l'obiettivo di risparmio mensile a 350€",
        user_messages=["Voglio risparmiare 350€ al mese, aggiorna il mio obiettivo"],
        check=_check_action_set_savings_goal,
        category="action",
    ),
    EvalCase(
        id="action_move_funds",
        description="Sposta 20€ dalla categoria Shopping alla categoria Ristoranti",
        user_messages=["Sposta 20€ dal budget Shopping al budget Ristoranti"],
        check=_check_action_move_funds,
        category="action",
    ),
    EvalCase(
        id="reasoning_afford_dinner",
        description="Posso permettermi una cena da 80€ questo weekend? (reasoning multi-step)",
        user_messages=[
            "Posso permettermi una cena da 80€ questo weekend? Sarebbe una spesa nella categoria Ristoranti."
        ],
        check=_check_reasoning_afford_dinner,
        category="reasoning",
    ),
    EvalCase(
        id="memory_preference_recall",
        description="Salva una preferenza di taglio spese e verifica che venga riusata in un turno successivo",
        user_messages=[
            "D'ora in poi cambia le mie priorità di taglio spese: prima Shopping, poi Trasporti, poi Intrattenimento.",
            "Dove dovrei tagliare 50€ questo mese per restare in linea con l'obiettivo di risparmio?",
        ],
        check=_check_memory_preference_recall,
        category="memory",
    ),
    EvalCase(
        id="edge_case_unknown_category",
        description="Chiede di registrare una spesa in una categoria inesistente",
        user_messages=["Aggiungi una spesa di 15€ per Vacanze"],
        check=_check_edge_case_unknown_category,
        category="edge_case",
    ),
]
