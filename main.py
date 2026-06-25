import sys
from uuid import uuid4

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from graph_supervisor import get_app, get_message_content


def build_initial_state(ticket: str) -> dict:
    return {
        "messages": [ticket],
        "resolved_categories": [],
        "needs_followup": False,
        "followup_category": None,
        "runbook_context": "",
    }


def ask_security_approval(interrupts) -> bool:
    interrupt_value = interrupts[0].value if interrupts else {}

    print("\n=== Human Approval Required ===")
    print("Action:", interrupt_value.get("action"))
    print("Ticket summary:", interrupt_value.get("ticket_summary"))
    print("Proposed action:", interrupt_value.get("proposed_action"))

    while True:
        answer = input("Approve action? [y/n]: ").strip().lower()
        if answer in {"y", "yes"}:
            return True
        if answer in {"n", "no"}:
            return False
        print("Please answer y or n.")


def run_ticket(ticket: str) -> dict:
    thread_id = f"main-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    with SqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        app = get_app(checkpointer)
        result = app.invoke(build_initial_state(ticket), config=config)

        while "__interrupt__" in result:
            approved = ask_security_approval(result["__interrupt__"])
            result = app.invoke(
                Command(resume={"approved": approved}),
                config=config,
            )

        return result


def main():
    if len(sys.argv) < 2:
        print('Usage: python main.py "isi ticket di sini"')
        raise SystemExit(1)

    ticket = " ".join(sys.argv[1:])
    result = run_ticket(ticket)

    print("\n=== Final Response ===")
    print("Category:", result.get("category"))
    print("Resolved categories:", result.get("resolved_categories", []))
    print(get_message_content(result["messages"][-1]))


if __name__ == "__main__":
    main()
