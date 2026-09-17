"""JSON-schema tool definitions sent to Claude. Human-readable status text shown
in the UI while each tool runs lives in STATUS_MESSAGES, keyed by tool name."""

TOOLS = [
    {
        "name": "list_categories",
        "description": "Restituisce l'elenco delle categorie di spesa dell'utente.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_monthly_spending",
        "description": (
            "Restituisce quanto è stato speso in un mese. Se 'category' è omessa, "
            "restituisce il totale e la ripartizione per ogni categoria."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Nome categoria (opzionale)."},
                "month": {
                    "type": "string",
                    "description": "Mese in formato YYYY-MM. Default: mese corrente.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_budget_status",
        "description": (
            "Restituisce budget, speso, residuo e percentuale utilizzata per una categoria "
            "in un mese. Se 'category' è omessa, restituisce lo stato di tutte le categorie."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Nome categoria (opzionale)."},
                "month": {"type": "string", "description": "Mese YYYY-MM. Default: mese corrente."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_savings_goal_status",
        "description": (
            "Restituisce l'obiettivo di risparmio mensile e se l'utente è in linea, calcolato "
            "confrontando il margine budgetato-non-speso del mese con l'obiettivo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "month": {"type": "string", "description": "Mese YYYY-MM. Default: mese corrente."},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_user_preferences",
        "description": "Restituisce le preferenze salvate dell'utente (es. priorità di taglio spese).",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "add_expense",
        "description": "Registra una nuova spesa in una categoria. Azione che modifica il database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Nome della categoria."},
                "amount": {"type": "number", "description": "Importo in euro, positivo."},
                "description": {"type": "string", "description": "Descrizione breve (opzionale)."},
                "date": {"type": "string", "description": "Data YYYY-MM-DD. Default: oggi."},
            },
            "required": ["category", "amount"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_or_update_budget",
        "description": (
            "Crea o aggiorna il budget mensile di una categoria. Azione che modifica il database."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Nome della categoria."},
                "amount_limit": {"type": "number", "description": "Limite di budget in euro."},
                "month": {"type": "string", "description": "Mese YYYY-MM. Default: mese corrente."},
            },
            "required": ["category", "amount_limit"],
            "additionalProperties": False,
        },
    },
    {
        "name": "set_savings_goal",
        "description": (
            "Imposta o aggiorna l'obiettivo di risparmio mensile dell'utente. "
            "Azione che modifica il database."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "monthly_target": {"type": "number", "description": "Obiettivo in euro al mese."},
                "name": {"type": "string", "description": "Etichetta opzionale per l'obiettivo."},
            },
            "required": ["monthly_target"],
            "additionalProperties": False,
        },
    },
    {
        "name": "move_funds_between_categories",
        "description": (
            "Sposta budget da una categoria a un'altra nello stesso mese. "
            "Azione che modifica il database."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "from_category": {"type": "string"},
                "to_category": {"type": "string"},
                "amount": {"type": "number", "description": "Importo in euro, positivo."},
                "month": {"type": "string", "description": "Mese YYYY-MM. Default: mese corrente."},
                "reason": {"type": "string", "description": "Motivo dello spostamento (opzionale)."},
            },
            "required": ["from_category", "to_category", "amount"],
            "additionalProperties": False,
        },
    },
    {
        "name": "update_user_preference",
        "description": (
            "Salva o aggiorna una preferenza utente per personalizzare le risposte future "
            "(es. key='cost_cutting_priority', value='[\"intrattenimento\",\"ristoranti\"]'). "
            "Azione che modifica il database."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "value": {"type": "string", "description": "Valore come stringa o stringa JSON."},
            },
            "required": ["key", "value"],
            "additionalProperties": False,
        },
    },
]

STATUS_MESSAGES = {
    "list_categories": "Sto recuperando le categorie...",
    "get_monthly_spending": "Sto controllando le spese del mese...",
    "get_budget_status": "Sto controllando il budget...",
    "get_savings_goal_status": "Sto controllando l'obiettivo di risparmio...",
    "get_user_preferences": "Sto recuperando le tue preferenze...",
    "add_expense": "Sto registrando la spesa...",
    "create_or_update_budget": "Sto aggiornando il budget...",
    "set_savings_goal": "Sto impostando l'obiettivo di risparmio...",
    "move_funds_between_categories": "Sto spostando i fondi tra categorie...",
    "update_user_preference": "Sto salvando la tua preferenza...",
}
