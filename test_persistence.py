from langgraph.checkpoint.sqlite import SqliteSaver

from graph_supervisor import get_app


config = {"configurable": {"thread_id": "persist-test-1"}}
ticket = "Ada yang coba login ke akun saya dari lokasi asing"

with SqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
    app = get_app(checkpointer)
    result = app.invoke(
        {
            "messages": [ticket],
            "resolved_categories": [],
            "needs_followup": False,
            "followup_category": None,
            "runbook_context": "",
        },
        config=config,
    )

    print("Ticket:", ticket)
    print("Interrupted:", "__interrupt__" in result)
    print("Interrupt payload:", result.get("__interrupt__"))
    print("State after interrupt:", app.get_state(config))
