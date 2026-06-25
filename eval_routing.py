import json
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

    for item in dataset:
        ticket = item["ticket"]
        expected = item["expected_category"]
        actual = classify_ticket(ticket)

        if actual != expected:
            mistakes.append(
                {
                    "ticket": ticket,
                    "expected": expected,
                    "actual": actual,
                }
            )

    total = len(dataset)
    correct = total - len(mistakes)
    accuracy = correct / total if total else 0

    print(f"Accuracy: {accuracy:.0%} ({correct}/{total})")

    if not mistakes:
        print("No misclassified tickets.")
        return

    print("\nMisclassified tickets:")
    for mistake in mistakes:
        print("- Ticket:", mistake["ticket"])
        print("  Expected:", mistake["expected"])
        print("  Actual:", mistake["actual"])


if __name__ == "__main__":
    main()
