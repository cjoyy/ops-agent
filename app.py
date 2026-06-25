from uuid import uuid4

import gradio as gr
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from graph_supervisor import get_app, get_message_content
from main import build_initial_state


def format_interrupt(interrupts) -> str:
    if not interrupts:
        return "Graph paused, but no interrupt payload was returned."

    payload = interrupts[0].value
    return (
        "Security approval required\n\n"
        f"Action: {payload.get('action')}\n"
        f"Ticket summary: {payload.get('ticket_summary')}\n"
        f"Proposed action: {payload.get('proposed_action')}"
    )


def format_final_result(result: dict) -> str:
    return (
        f"Category: {result.get('category')}\n"
        f"Resolved categories: {result.get('resolved_categories', [])}\n\n"
        f"{get_message_content(result['messages'][-1])}"
    )


def run_ticket(ticket: str):
    if not ticket.strip():
        return "Please enter a ticket.", None, gr.update(visible=False), gr.update(visible=False)

    thread_id = f"space-{uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    with SqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        app = get_app(checkpointer)
        result = app.invoke(build_initial_state(ticket), config=config)

    if "__interrupt__" in result:
        return (
            format_interrupt(result["__interrupt__"]),
            thread_id,
            gr.update(visible=True),
            gr.update(visible=True),
        )

    return format_final_result(result), None, gr.update(visible=False), gr.update(visible=False)


def resume_ticket(thread_id: str, approved: bool):
    if not thread_id:
        return "No paused security ticket to resume.", None, gr.update(visible=False), gr.update(visible=False)

    config = {"configurable": {"thread_id": thread_id}}

    with SqliteSaver.from_conn_string("checkpoints.sqlite") as checkpointer:
        app = get_app(checkpointer)
        result = app.invoke(Command(resume={"approved": approved}), config=config)

    if "__interrupt__" in result:
        return (
            format_interrupt(result["__interrupt__"]),
            thread_id,
            gr.update(visible=True),
            gr.update(visible=True),
        )

    return format_final_result(result), None, gr.update(visible=False), gr.update(visible=False)


with gr.Blocks(title="Ops Agent") as demo:
    gr.Markdown("# Ops Agent")
    gr.Markdown(
        "Multi-agent IT/ops assistant with LangGraph routing, RAG runbooks, tools, "
        "human approval, and SQLite checkpointing."
    )

    ticket = gr.Textbox(
        label="Ticket",
        placeholder="Service auth-api saya stuck, gimana cara restart yang benar?",
        lines=4,
    )
    submit = gr.Button("Run Ticket", variant="primary")
    output = gr.Textbox(label="Result", lines=14)
    thread_state = gr.State(None)

    with gr.Row():
        approve = gr.Button("Approve Security Action", visible=False)
        reject = gr.Button("Reject Security Action", visible=False)

    submit.click(
        run_ticket,
        inputs=[ticket],
        outputs=[output, thread_state, approve, reject],
    )
    approve.click(
        lambda thread_id: resume_ticket(thread_id, True),
        inputs=[thread_state],
        outputs=[output, thread_state, approve, reject],
    )
    reject.click(
        lambda thread_id: resume_ticket(thread_id, False),
        inputs=[thread_state],
        outputs=[output, thread_state, approve, reject],
    )


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
