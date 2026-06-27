import json
import time
from pathlib import Path

from graph_supervisor import supervisor, get_app, get_message_content
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command


DATASET_PATH = Path("eval/golden_dataset.json")
CHECKPOINT_DB = "checkpoints.sqlite"


def load_dataset():
    with DATASET_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def bench_classification_latency(dataset):
    print("[bench] classification latency ...")
    latencies = []
    results = []
    for item in dataset:
        ticket = item["ticket"]
        expected = item["expected_category"]
        t0 = time.perf_counter()
        actual = supervisor({
            "messages": [ticket],
            "resolved_categories": [],
            "needs_followup": False,
            "followup_category": None,
            "runbook_context": "",
            "debug": False,
        })["category"]
        elapsed = time.perf_counter() - t0
        latencies.append(elapsed)
        results.append((ticket, expected, actual, elapsed))
    return latencies, results


def bench_end_to_end_latency(dataset):
    print("[bench] end-to-end latency (technical & billing only, security skipped due to HITL) ...")
    latencies = []
    results = []
    with SqliteSaver.from_conn_string(CHECKPOINT_DB) as saver:
        app = get_app(saver)
        for item in dataset:
            if item["expected_category"] == "security":
                continue
            ticket = item["ticket"]
            t0 = time.perf_counter()
            try:
                result = app.invoke({
                    "messages": [ticket],
                    "resolved_categories": [],
                    "needs_followup": False,
                    "followup_category": None,
                    "runbook_context": "",
                }, {"configurable": {"thread_id": f"bench-e2e-{hash(ticket) % 10**8}"}})
                elapsed = time.perf_counter() - t0
                latencies.append(elapsed)
                results.append((ticket, elapsed, get_message_content(result["messages"][-1])[:80]))
            except Exception as e:
                print(f"  [SKIP] {ticket[:60]}... -> {e}")
    return latencies, results


def print_stats(label, latencies):
    if not latencies:
        print(f"  {label}: no data")
        return
    n = len(latencies)
    avg = sum(latencies) / n
    mn = min(latencies)
    mx = max(latencies)
    sorted_l = sorted(latencies)
    p50 = sorted_l[int(n * 0.50)]
    p95 = sorted_l[int(n * 0.95)]
    p99 = sorted_l[int(n * 0.99)]
    throughput = n / sum(latencies) if sum(latencies) > 0 else 0
    print(f"  {label}:")
    print(f"    Count:       {n}")
    print(f"    Avg latency: {avg:.3f}s")
    print(f"    Min latency: {mn:.3f}s")
    print(f"    Max latency: {mx:.3f}s")
    print(f"    P50 latency: {p50:.3f}s")
    print(f"    P95 latency: {p95:.3f}s")
    print(f"    P99 latency: {p99:.3f}s")
    print(f"    Throughput:  {throughput:.1f} tickets/s")
    print()


def main():
    print("=" * 60)
    print("OPS AGENT BENCHMARK")
    print("=" * 60)
    print()

    dataset = load_dataset()
    print(f"Dataset: {len(dataset)} tickets")
    print()

    cls_lat, cls_results = bench_classification_latency(dataset)
    print_stats("Classification Latency", cls_lat)

    e2e_lat, e2e_results = bench_end_to_end_latency(dataset)
    print_stats("End-to-End Latency (technical + billing)", e2e_lat)

    correct = sum(1 for _, exp, act, _ in cls_results if exp == act)
    total = len(cls_results)
    print(f"Routing Accuracy: {correct}/{total} = {correct/total:.0%}")

    by_cat = {}
    for ticket, exp, act, lat in cls_results:
        by_cat.setdefault(exp, []).append(lat)
    print()
    print("Per-Category Classification Latency:")
    for cat in ["technical", "billing", "security"]:
        if cat in by_cat:
            vals = by_cat[cat]
            avg_cat = sum(vals) / len(vals)
            print(f"  {cat}: avg={avg_cat:.3f}s  n={len(vals)}")


if __name__ == "__main__":
    main()
