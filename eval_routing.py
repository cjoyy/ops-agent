import json
import time
from pathlib import Path

from graph_supervisor import supervisor

DATASET_PATH = Path("eval/golden_dataset.json")


def load_dataset():
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def classify_ticket(ticket: str) -> str:
    result = supervisor(
        {
            "messages": [ticket],
            "resolved_categories": [],
            "needs_followup": False,
            "followup_category": None,
            "runbook_context": "",
            "debug": False,
        }
    )
    return result["category"]


def main():
    dataset = load_dataset()
    mistakes = []
    latencies = []

    for item in dataset:
        ticket = item["ticket"]
        expected = item["expected_category"]
        t0 = time.perf_counter()
        actual = classify_ticket(ticket)
        elapsed = time.perf_counter() - t0
        latencies.append(elapsed)

        if actual != expected:
            mistakes.append(
                {
                    "ticket": ticket,
                    "expected": expected,
                    "actual": actual,
                    "latency_s": round(elapsed, 3),
                }
            )

    total = len(dataset)
    correct = total - len(mistakes)
    accuracy = correct / total if total else 0

    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)
    avg_lat = sum(latencies) / n
    min_lat = latencies_sorted[0]
    max_lat = latencies_sorted[-1]
    p50 = latencies_sorted[int(n * 0.50)]
    p95 = latencies_sorted[int(n * 0.95)]
    p99 = latencies_sorted[int(n * 0.99)]

    print("=" * 60)
    print("ROUTING ACCURACY EVALUATION")
    print("=" * 60)
    print(f"Accuracy:  {accuracy:.0%} ({correct}/{total})")
    print()
    print("Classification Latency:")
    print(f"  Average:  {avg_lat:.3f}s")
    print(f"  Min:      {min_lat:.3f}s")
    print(f"  Max:      {max_lat:.3f}s")
    print(f"  P50:      {p50:.3f}s")
    print(f"  P95:      {p95:.3f}s")
    print(f"  P99:      {p99:.3f}s")
    print()

    if mistakes:
        print(f"Misclassified tickets ({len(mistakes)}):")
        for m in mistakes:
            print(f"  - [{m['latency_s']:.3f}s] expected={m['expected']} actual={m['actual']}")
            print(f"    Ticket: {m['ticket']}")
    else:
        print("All tickets classified correctly.")


if __name__ == "__main__":
    main()
