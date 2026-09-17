from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.orm import Session


@dataclass
class ToolCallRecord:
    name: str
    input: dict
    output: dict
    is_error: bool


@dataclass
class TurnOutcome:
    """Everything observable from one user turn, handed to a case's check function."""

    final_text: str
    tool_calls: list[ToolCallRecord]
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float


@dataclass
class ConversationOutcome:
    """All turns of a (possibly multi-turn) case, plus the DB session to assert against."""

    turns: list[TurnOutcome]
    db: Session

    @property
    def last(self) -> TurnOutcome:
        return self.turns[-1]

    @property
    def all_tool_calls(self) -> list[ToolCallRecord]:
        return [tc for turn in self.turns for tc in turn.tool_calls]

    def tool_was_called(self, name: str) -> bool:
        return any(tc.name == name for tc in self.all_tool_calls)

    def find_tool_call(self, name: str) -> ToolCallRecord | None:
        for tc in reversed(self.all_tool_calls):
            if tc.name == name:
                return tc
        return None

    @property
    def total_cost_usd(self) -> float:
        return round(sum(t.cost_usd for t in self.turns), 6)

    @property
    def total_latency_ms(self) -> float:
        return round(sum(t.latency_ms for t in self.turns), 1)

    @property
    def total_tokens(self) -> int:
        return sum(t.input_tokens + t.output_tokens for t in self.turns)


CheckFn = Callable[[ConversationOutcome], tuple[bool, str]]


@dataclass
class EvalCase:
    id: str
    description: str
    user_messages: list[str]
    check: CheckFn
    category: str = "general"  # "read" | "action" | "reasoning" | "memory" | "edge_case"


@dataclass
class CaseResult:
    case: EvalCase
    passed: bool
    detail: str
    outcome: ConversationOutcome | None = None
    error: str | None = None
