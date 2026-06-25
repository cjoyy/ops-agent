from typing import Annotated, Literal, Optional, TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from pydantic import BaseModel, Field

from rag_setup import get_retriever


class TicketClassification(BaseModel):
    category: Literal["technical", "billing", "security"] = Field(
        description=(
            "Classify the ticket into exactly one category. "
            "Use technical for technical problems, system errors, downtime, bugs, "
            "access denied errors, login/access errors, or service restart issues. "
            "If a ticket mentions a billing portal but the main problem is an error "
            "or inability to access it, classify it as technical first. Use billing "
            "for invoices, payments, refunds, charges, or subscriptions. Use security for "
            "security incidents, suspicious logins, account access concerns, "
            "permissions, or sensitive data issues."
        )
    )


class FollowupDecision(BaseModel):
    needs_followup: bool = Field(
        description="True if another agent category still needs to handle part of the ticket."
    )
    followup_category: Optional[Literal["technical", "billing", "security"]] = Field(
        default=None,
        description=(
            "The next category that should handle the ticket. Use null if no follow-up "
            "is needed."
        ),
    )


class GraphState(TypedDict):
    messages: Annotated[list, add_messages]
    category: str
    security_approval: str
    needs_followup: bool
    followup_category: Optional[str]
    resolved_categories: list
    runbook_context: str


load_dotenv()

model = init_chat_model(
    "llama-3.3-70b-versatile",
    model_provider="groq",
)
classifier = model.with_structured_output(TicketClassification)
followup_classifier = model.with_structured_output(FollowupDecision)


@tool
def restart_service(service_name: str) -> str:
    """Restart a service by service name."""
    return f"Service {service_name} berhasil di-restart"


@tool
def check_invoice(invoice_id: str) -> str:
    """Check invoice status by invoice ID."""
    return f"Invoice {invoice_id}: total Rp500.000, status: paid"


@tool
def refund_policy(reason: str) -> str:
    """Check refund policy for a refund reason."""
    return f"Refund untuk alasan '{reason}' disetujui, proses 3-5 hari kerja"


def supervisor(state: GraphState) -> dict:
    if state.get("needs_followup") and state.get("followup_category"):
        category = state["followup_category"]
        print("[DEBUG] supervisor pakai followup_category:", category)
        return {"category": category}

    result = classifier.invoke(state["messages"])
    print("Debug classification:", result)
    return {"category": result.category}


def detect_followup(state: GraphState, agent_category: str, final_answer: str) -> dict:
    original_ticket = get_message_content(state["messages"][0])
    prompt = (
        "Berdasarkan ticket asli dan jawaban yang sudah diberikan, apakah ada "
        "aspek lain dari ticket ini yang perlu ditangani agent kategori lain? "
        "Jika ya sebutkan kategorinya (technical/billing/security), jika tidak "
        "jawab 'tidak ada'.\n\n"
        f"Ticket asli: {original_ticket}\n"
        f"Kategori yang baru selesai ditangani: {agent_category}\n"
        f"Jawaban yang sudah diberikan: {final_answer}"
    )
    decision = followup_classifier.invoke(prompt)
    resolved_categories = state.get("resolved_categories", []) + [agent_category]

    if not decision.needs_followup or decision.followup_category in resolved_categories:
        needs_followup = False
        followup_category = None
    else:
        needs_followup = decision.needs_followup
        followup_category = decision.followup_category

    print("[DEBUG] followup decision:", decision)
    print("[DEBUG] resolved_categories:", resolved_categories)
    return {
        "needs_followup": needs_followup,
        "followup_category": followup_category,
        "resolved_categories": resolved_categories,
    }


def technical_agent(state: GraphState) -> dict:
    print("[DEBUG] masuk ke technical_agent")
    original_ticket = get_message_content(state["messages"][0]).lower()
    should_bind_restart_tool = "restart" in original_ticket
    runbook_context = state.get("runbook_context") or "Tidak ada referensi runbook yang ditemukan."
    system_prompt = SystemMessage(
        content=(
            "Kamu adalah technical_agent untuk IT/ops. Gunakan runbook_context "
            "sebagai referensi utama sebelum menjawab. Jika runbook_context tidak "
            "relevan atau kosong, katakan bahwa tidak ada referensi spesifik dan "
            "beri saran umum secara hati-hati.\n\n"
            f"runbook_context:\n{runbook_context}"
        )
    )
    agent_messages = [system_prompt] + state["messages"]
    model_with_tools = model.bind_tools([restart_service])
    response = (
        model_with_tools.invoke(agent_messages)
        if should_bind_restart_tool
        else model.invoke(agent_messages)
    )

    if response.tool_calls:
        tool_messages = []
        print("[DEBUG] tool triggered:", True)

        for tool_call in response.tool_calls:
            args = tool_call["args"]
            print("[DEBUG] tool args:", args)
            tool_result = restart_service.invoke(args)
            tool_messages.append(
                ToolMessage(
                    content=tool_result,
                    tool_call_id=tool_call["id"],
                )
            )

        final_response = model.invoke(agent_messages + [response] + tool_messages)
    else:
        print("[DEBUG] tool triggered:", False)
        final_response = response

    print("[DEBUG] final answer:", final_response.content)
    followup_state = detect_followup(state, "technical", final_response.content)
    return {"messages": [final_response], **followup_state}


def retrieve_runbook(state: GraphState) -> dict:
    print("[DEBUG] masuk ke retrieve_runbook")
    ticket = get_message_content(state["messages"][0])
    retriever = get_retriever()
    docs = retriever.invoke(ticket)
    context_parts = []

    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        context_parts.append(f"Source: {source}\n{doc.page_content}")

    runbook_context = "\n\n---\n\n".join(context_parts)
    print("[DEBUG] runbook_context:\n", runbook_context)
    return {"runbook_context": runbook_context}


def billing_agent(state: GraphState) -> dict:
    print("[DEBUG] masuk ke billing_agent")
    tools = [check_invoice, refund_policy]
    tools_by_name = {tool.name: tool for tool in tools}
    model_with_tools = model.bind_tools(tools)
    response = model_with_tools.invoke(state["messages"])

    if response.tool_calls:
        tool_messages = []
        print("[DEBUG] tool triggered:", True)

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            args = tool_call["args"]
            print("[DEBUG] tool name:", tool_name)
            print("[DEBUG] tool args:", args)
            tool_result = tools_by_name[tool_name].invoke(args)
            tool_messages.append(
                ToolMessage(
                    content=tool_result,
                    tool_call_id=tool_call["id"],
                )
            )

        final_response = model.invoke(
            state["messages"] + [response] + tool_messages
        )
    else:
        print("[DEBUG] tool triggered:", False)
        final_response = response

    if not final_response.content:
        final_response = model.invoke(
            state["messages"]
            + [
                HumanMessage(
                    content=(
                        "Kamu adalah billing_agent. Berikan jawaban singkat untuk "
                        "aspek billing dari ticket ini, terutama kebutuhan cek invoice "
                        "di portal billing."
                    )
                )
            ]
        )

    print("[DEBUG] final answer:", final_response.content)
    followup_state = detect_followup(state, "billing", final_response.content)
    return {"messages": [final_response], **followup_state}


def get_message_content(message) -> str:
    if isinstance(message, str):
        return message
    return message.content


def security_agent(state: GraphState) -> dict:
    print("[DEBUG] masuk ke security_agent")
    ticket_summary = get_message_content(state["messages"][-1])
    approval_result = interrupt(
        {
            "action": "approve_security_action",
            "ticket_summary": ticket_summary,
            "proposed_action": "lock account sementara dan kirim notifikasi",
        }
    )
    if approval_result.get("approved"):
        approval_message = "Action approved, account locked dan notifikasi dikirim"
    else:
        approval_message = "Action dibatalkan, tiket di-escalate ke manual review"

    followup_state = detect_followup(state, "security", approval_message)
    return {
        "security_approval": str(approval_result),
        "messages": [approval_message],
        **followup_state,
    }


def route_to_agent(state: GraphState) -> str:
    category = state["category"]
    if category == "technical":
        return "retrieve_runbook"
    if category == "billing":
        return "billing_agent"
    if category == "security":
        return "security_agent"
    raise ValueError(f"Unknown category: {category}")


def check_followup(state: GraphState) -> str:
    followup_category = state.get("followup_category")
    resolved_categories = state.get("resolved_categories", [])
    if (
        state.get("needs_followup")
        and followup_category
        and followup_category not in resolved_categories
    ):
        print("[DEBUG] followup detected, balik ke supervisor:", followup_category)
        return "supervisor"

    print("[DEBUG] no followup, selesai")
    return END


graph = StateGraph(GraphState)
graph.add_node("supervisor", supervisor)
graph.add_node("retrieve_runbook", retrieve_runbook)
graph.add_node("technical_agent", technical_agent)
graph.add_node("billing_agent", billing_agent)
graph.add_node("security_agent", security_agent)
graph.add_edge(START, "supervisor")
graph.add_conditional_edges(
    "supervisor",
    route_to_agent,
    {
        "technical_agent": "technical_agent",
        "retrieve_runbook": "retrieve_runbook",
        "billing_agent": "billing_agent",
        "security_agent": "security_agent",
    },
)
graph.add_edge("retrieve_runbook", "technical_agent")
graph.add_conditional_edges(
    "technical_agent",
    check_followup,
    {"supervisor": "supervisor", END: END},
)
graph.add_conditional_edges(
    "billing_agent",
    check_followup,
    {"supervisor": "supervisor", END: END},
)
graph.add_conditional_edges(
    "security_agent",
    check_followup,
    {"supervisor": "supervisor", END: END},
)

checkpointer = MemorySaver()
app = graph.compile(checkpointer=checkpointer)

ticket = "Service auth-api saya stuck, gimana cara restart yang benar?"
config = {"configurable": {"thread_id": "rag-technical-test"}}
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

print("\n=== RAG Technical Agent Result ===")
print("Ticket:", ticket)
print("Final category:", result["category"])
print("Runbook context:", result["runbook_context"])
print("Needs followup:", result["needs_followup"])
print("Followup category:", result["followup_category"])
print("Resolved categories:", result["resolved_categories"])
print("Final message:", get_message_content(result["messages"][-1]))
print("Final state:", app.get_state(config))
