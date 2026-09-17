# Spendwise

A personal-finance agent that **takes real actions on a database** instead of just talking about them — built with Claude tool use, a FastAPI backend streaming over SSE, a Flutter client that surfaces the agent's reasoning, and an offline eval suite that scores every change.

The agent handles requests like *"posso permettermi una cena da 80€ questo weekend?"* by planning a multi-step lookup across budgets, month-to-date spending, and the user's savings goal — then answers with the actual numbers and a recommendation shaped by that user's stored preferences.

---

## Why this is not a chatbot wrapper

| Capability | How it works |
|---|---|
| **Real actions** | 10 tools backed by SQLAlchemy writes — adding an expense, creating a budget, setting a savings goal, and moving funds between categories all mutate the database |
| **Multi-step reasoning** | Affordability questions require chaining several lookups; the agent decides which ones on its own, and the eval suite asserts it actually did |
| **Persistent structured memory** | User preferences (habitual categories, cost-cutting priority) and full conversation history live in the DB and shape later answers |
| **Streaming with visible reasoning** | SSE emits thinking, tool calls, and tool results as separate event types, so the UI can show *how* the answer was reached, distinct from the answer |
| **Offline evaluation** | 10 cases scored against ground truth (DB state or deterministic tool output), with accuracy, cost per request, and latency — rerunnable after every change |

### A real trace

From an actual run against the seeded demo data (budget Ristoranti 150€, 90€ already spent, savings target 300€/month):

```
thinking   → "check the budget status for Ristoranti, review monthly spending,
              and see where things stand with the savings goal"
tool_call  → get_budget_status(category="Ristoranti")   → remaining: 60.0
tool_call  → get_monthly_spending()                     → total_spent: 640.0
tool_call  → get_savings_goal_status()                  → on_track: true, margin: 90.0
text       → "80 € sfondano il budget Ristoranti di 20 €. […] Sposto 20 € da
              Intrattenimento a Ristoranti (Intrattenimento è la tua prima
              priorità di taglio): copri gli 80 € senza toccare il risparmio."
done       → 1043 in + 684 out tokens · $0.039 · 12.0s
```

The transfer suggestion is not hardcoded — it comes from the `cost_cutting_priority` preference stored for that user.

---

## Architecture

```
Flutter client  ──POST /chat/stream──▶  FastAPI
     ▲                                     │
     └────── SSE event stream ─────────────┤
              status / thinking /          │
              tool_call / tool_result /    ▼
              text / done / error     Agent orchestrator
                                           │  manual tool-use loop
                                           ├──▶ Claude (adaptive thinking, streaming)
                                           └──▶ tool impls ──▶ services ──▶ SQLite
```

### Key decisions

**Manual agentic loop over the SDK's tool runner.** The loop is written out explicitly so each stage can be mapped to a custom SSE event. A batteries-included runner would drive the conversation but hide the seams where "I'm checking the restaurant budget…" and the tool result need to be pushed to the client mid-turn.

**SSE, not WebSockets.** The flow is one-directional (client asks, server streams back). SSE is simpler to implement, trivial to test with `curl`, and needs no connection lifecycle management.

**Conversation history stored as raw content blocks.** `conversation_messages.content_json` holds the exact Anthropic block list, including `tool_use` and `tool_result`. One representation serves both replaying context to the API and rendering the reasoning trail in the UI — no parallel schema to keep in sync.

**Envelope budgeting instead of income tracking.** Savings progress is derived as `total_budgeted − total_spent` for the month, compared against the monthly target. This keeps the model free of income data while still supporting genuine affordability reasoning.

**Preferences as a JSON key/value store.** New personalization dimensions can be added without a migration, and the agent can write them itself via `update_user_preference`.

**Prompt caching on the system prompt.** The static instruction block is marked `cache_control: ephemeral`; volatile context (today's date, current preferences) goes after it. Across the two API calls of a single tool-using turn, the cached prefix is read back rather than re-billed at full rate.

---

## Agent tools

| Tool | Type | Purpose |
|---|---|---|
| `list_categories` | read | Available spending categories |
| `get_monthly_spending` | read | Month total, or per-category breakdown |
| `get_budget_status` | read | Limit, spent, remaining, % used |
| `get_savings_goal_status` | read | Target vs. projected savings, on-track flag |
| `get_user_preferences` | read | Stored personalization data |
| `add_expense` | **write** | Record a transaction |
| `create_or_update_budget` | **write** | Set a category's monthly limit |
| `set_savings_goal` | **write** | Set the monthly savings target |
| `move_funds_between_categories` | **write** | Reallocate budget, logged as a transfer |
| `update_user_preference` | **write** | Persist a preference for future turns |

Tool failures (unknown category, negative amount, insufficient budget) return `is_error: true` with an explanation, letting the agent recover in-conversation rather than crashing the turn.

---

## Evaluation

Run against real API calls, resetting to a deterministic fixture before each case:

```bash
cd backend
python -m evaluation.run_eval                      # full suite
python -m evaluation.run_eval --case reasoning     # one case
python -m evaluation.run_eval --model claude-sonnet-5   # compare cost/quality
```

Latest run (`claude-opus-5`):

| Metric | Result |
|---|---|
| Accuracy | **10/10** — read 3/3, action 4/4, reasoning 1/1, memory 1/1, edge case 1/1 |
| Cost | $0.219 total · **$0.0219 per request** |
| Tokens | 1,797 average per request |
| Latency | 9.3s average · 15.9s p95 |

Every run writes a timestamped JSON report to `backend/evaluation/reports/`, and the process exits non-zero if any case fails, so it drops straight into CI.

**How cases are scored.** Checks assert against ground truth, never the phrasing of the reply: write actions are verified by querying the database independently of the tool's own return value, and read/reasoning cases are verified against the deterministic tool output plus the presence of the correct figure in the answer. A case passes because the agent did the right thing, not because it worded something a particular way.

The harness itself is unit-tested (`tests/test_eval_harness.py`) by feeding synthetic outcomes to each check — a mis-specified expectation gets caught for free rather than during a paid run.

---

## Getting started

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # then add your ANTHROPIC_API_KEY
python seed_data.py         # deterministic demo data
uvicorn app.main:app --reload
```

API at `http://127.0.0.1:8000` (interactive docs at `/docs`).

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"Posso permettermi una cena da 80 euro questo weekend?"}'
```

### Frontend

```bash
cd frontend
flutter pub get
flutter run          # -d chrome / -d macos / a simulator
```

The client points at `http://127.0.0.1:8000` by default (`lib/services/agent_api_client.dart`). On an Android emulator, change the base URL to `http://10.0.2.2:8000`.

---

## API

| Endpoint | Purpose |
|---|---|
| `POST /chat/stream` | Run one agent turn, streamed as SSE |
| `GET /chat/sessions` | List conversation sessions |
| `GET /chat/sessions/{id}/messages` | Replay a session's stored turns |
| `GET /budgets` · `/budgets/categories` | Budget status and categories |
| `GET /transactions` | Recorded expenses |
| `GET /goals/status` | Savings goal progress |
| `GET /health` | Liveness check |

### SSE event types

| Event | Payload |
|---|---|
| `status` | Human-readable note shown while a tool runs |
| `thinking` | Summarized reasoning, token by token |
| `tool_call` | Tool name and arguments |
| `tool_result` | Tool output and error flag |
| `text` | Final answer, token by token |
| `done` | Session id, token usage, estimated cost, latency |
| `error` | Failure message (the stream always closes cleanly) |

---

## Project structure

```
backend/
  app/
    agent/          orchestrator (tool-use loop + SSE), tools, prompts, memory, pricing
    api/            chat (SSE), budgets, transactions, goals
    services/       budget and savings-goal business logic
    models.py       SQLAlchemy schema
  evaluation/       eval cases, fixtures, metrics, runner, JSON reports
  tests/            24 pytest tests (tools, API, eval harness)
  seed_data.py      deterministic demo/fixture data
frontend/
  lib/
    services/       SSE client
    state/          streaming chat state
    widgets/        reasoning trail + final answer (visually distinct)
    screens/        chat screen
```

## Database schema

`users` · `categories` · `budgets` (per category per month) · `transactions` · `savings_goals` · `category_transfers` · `user_preferences` · `conversation_sessions` · `conversation_messages`

## Testing

```bash
cd backend && pytest        # 24 tests, no API calls, fully deterministic
cd frontend && flutter test
```

The pytest suite covers tool logic, endpoints, and the eval harness without touching the network; the eval suite is the separate, paid layer that exercises the model itself.

---

## Scope and limitations

Deliberately out of scope, to keep the focus on agent design: authentication (a single seeded demo user), income tracking (savings are derived from budget headroom), and multi-currency support. SQLite and synchronous SQLAlchemy are used throughout — sufficient at this scale, and the business logic sits behind a service layer, so moving to Postgres is a configuration change rather than a rewrite.
