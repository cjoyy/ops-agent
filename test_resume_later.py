from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from graph_supervisor import get_app, get_message_content


config = {"configurable": {"thread_id": "persist-test-1"}}

with SqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
    app = get_app(checkpointer)
    result = app.invoke(Command(resume={"approved": True}), config=config)

    print("Resume result:", result)
    print("Final message:", get_message_content(result["messages"][-1]))
    print("Final state:", app.get_state(config))
