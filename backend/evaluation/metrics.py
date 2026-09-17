import statistics
from dataclasses import dataclass, field

from evaluation.types import CaseResult


@dataclass
class Metrics:
    total: int
    passed: int
    accuracy: float
    total_cost_usd: float
    avg_cost_usd: float
    avg_tokens: float
    avg_latency_ms: float
    p95_latency_ms: float
    by_category: dict[str, dict] = field(default_factory=dict)


def compute_metrics(results: list[CaseResult]) -> Metrics:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    costs = [r.outcome.total_cost_usd for r in results if r.outcome]
    tokens = [r.outcome.total_tokens for r in results if r.outcome]
    latencies = [r.outcome.total_latency_ms for r in results if r.outcome]

    by_category: dict[str, dict] = {}
    for r in results:
        cat = r.case.category
        bucket = by_category.setdefault(cat, {"total": 0, "passed": 0})
        bucket["total"] += 1
        bucket["passed"] += 1 if r.passed else 0
    for bucket in by_category.values():
        bucket["accuracy"] = round(bucket["passed"] / bucket["total"], 3) if bucket["total"] else 0.0

    return Metrics(
        total=total,
        passed=passed,
        accuracy=round(passed / total, 3) if total else 0.0,
        total_cost_usd=round(sum(costs), 6),
        avg_cost_usd=round(statistics.mean(costs), 6) if costs else 0.0,
        avg_tokens=round(statistics.mean(tokens), 1) if tokens else 0.0,
        avg_latency_ms=round(statistics.mean(latencies), 1) if latencies else 0.0,
        p95_latency_ms=round(sorted(latencies)[int(len(latencies) * 0.95) - 1], 1) if latencies else 0.0,
        by_category=by_category,
    )


def print_report(results: list[CaseResult], metrics: Metrics, model: str) -> None:
    print(f"\nSpendwise agent eval — model: {model}")
    print("=" * 78)
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        cost = f"${r.outcome.total_cost_usd:.4f}" if r.outcome else "n/a"
        latency = f"{r.outcome.total_latency_ms:.0f}ms" if r.outcome else "n/a"
        print(f"[{status}] {r.case.id:<32} {cost:>10} {latency:>8}  {r.detail}")
        if r.error:
            print(f"        error: {r.error}")
    print("=" * 78)
    print(f"Accuracy: {metrics.passed}/{metrics.total} ({metrics.accuracy:.0%})")
    for cat, bucket in metrics.by_category.items():
        print(f"  - {cat:<10} {bucket['passed']}/{bucket['total']} ({bucket['accuracy']:.0%})")
    print(f"Cost: total ${metrics.total_cost_usd:.4f}, avg/request ${metrics.avg_cost_usd:.4f}")
    print(f"Tokens: avg/request {metrics.avg_tokens:.0f}")
    print(f"Latency: avg {metrics.avg_latency_ms:.0f}ms, p95 {metrics.p95_latency_ms:.0f}ms")
