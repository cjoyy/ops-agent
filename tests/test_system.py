import json
from pathlib import Path

import pytest

from graph_supervisor import (
    GraphState,
    TicketClassification,
    FollowupDecision,
    route_to_agent,
    supervisor,
    check_followup,
    get_message_content,
)
from langgraph.graph import END

DATASET_PATH = Path("eval/golden_dataset.json")


def load_dataset():
    with DATASET_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Graph structure
# ---------------------------------------------------------------------------

def test_graph_nodes_exist():
    from graph_supervisor import graph
    expected_nodes = {"supervisor", "retrieve_runbook", "technical_agent", "billing_agent", "security_agent"}
    assert expected_nodes.issubset(set(graph.nodes)), f"Missing nodes: {expected_nodes - set(graph.nodes)}"


def test_graph_edges_exist():
    from graph_supervisor import graph
    assert ("__start__", "supervisor") in graph._edges or any(
        e[0] == "__start__" and e[1] == "supervisor" for e in graph._edges
    ), "START -> supervisor edge missing"


def test_route_to_agent_maps_all_categories():
    for cat in ["technical", "billing", "security"]:
        node = route_to_agent({"category": cat})
        assert node is not None, f"route_to_agent returned None for {cat}"


def test_route_to_agent_unknown_raises():
    with pytest.raises(ValueError, match="Unknown category"):
        route_to_agent({"category": "unknown"})


def test_check_followup_no_followup_returns_end():
    state = {"needs_followup": False, "followup_category": None, "resolved_categories": []}
    assert check_followup(state) == END


def test_check_followup_already_resolved_returns_end():
    state = {"needs_followup": True, "followup_category": "billing", "resolved_categories": ["billing"]}
    assert check_followup(state) == END


def test_check_followup_new_category_returns_supervisor():
    state = {"needs_followup": True, "followup_category": "billing", "resolved_categories": ["technical"]}
    assert check_followup(state) == "supervisor"


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

def test_ticket_classification_valid_categories():
    for cat in ["technical", "billing", "security"]:
        tc = TicketClassification(category=cat)
        assert tc.category == cat


def test_ticket_classification_invalid_category():
    with pytest.raises(Exception):
        TicketClassification(category="invalid")


def test_followup_decision_defaults():
    fd = FollowupDecision(needs_followup=False)
    assert fd.followup_category is None


# ---------------------------------------------------------------------------
# GraphState schema shape
# ---------------------------------------------------------------------------

def test_graphstate_has_required_keys():
    required = {"messages", "category", "security_approval", "needs_followup", "followup_category", "resolved_categories", "runbook_context"}
    import typing
    hints = typing.get_type_hints(GraphState)
    assert required.issubset(hints.keys()), f"Missing keys: {required - hints.keys()}"


# ---------------------------------------------------------------------------
# get_message_content
# ---------------------------------------------------------------------------

def test_get_message_content_with_string():
    assert get_message_content("hello") == "hello"


def test_get_message_content_with_message_object():
    class FakeMsg:
        def __init__(self, content):
            self.content = content
    assert get_message_content(FakeMsg("world")) == "world"


# ---------------------------------------------------------------------------
# Routing accuracy (integration, requires Groq API)
# ---------------------------------------------------------------------------

@pytest.mark.api
def test_routing_accuracy_meets_threshold():
    dataset = load_dataset()
    correct = 0
    for item in dataset:
        result = supervisor({
            "messages": [item["ticket"]],
            "resolved_categories": [],
            "needs_followup": False,
            "followup_category": None,
            "runbook_context": "",
            "debug": False,
        })
        if result["category"] == item["expected_category"]:
            correct += 1
    accuracy = correct / len(dataset)
    assert accuracy >= 0.70, f"Routing accuracy {accuracy:.0%} < 70% threshold"


# ---------------------------------------------------------------------------
# Latency threshold (integration, requires Groq API)
# ---------------------------------------------------------------------------

@pytest.mark.api
def test_classification_latency_threshold():
    dataset = load_dataset()[:5]
    import time
    for item in dataset:
        t0 = time.perf_counter()
        supervisor({
            "messages": [item["ticket"]],
            "resolved_categories": [],
            "needs_followup": False,
            "followup_category": None,
            "runbook_context": "",
            "debug": False,
        })
        elapsed = time.perf_counter() - t0
        assert elapsed < 30.0, f"Classification took {elapsed:.1f}s for: {item['ticket'][:60]}"


# ---------------------------------------------------------------------------
# HITL / interrupt scenario
# ---------------------------------------------------------------------------

@pytest.mark.api
def test_security_ticket_triggers_interrupt():
    from langgraph.checkpoint.sqlite import SqliteSaver
    from graph_supervisor import get_app
    ticket = "Ada yang coba login ke akun saya dari lokasi asing"
    with SqliteSaver.from_conn_string("checkpoints.sqlite") as saver:
        app = get_app(saver)
        result = app.invoke({
            "messages": [ticket],
            "resolved_categories": [],
            "needs_followup": False,
            "followup_category": None,
            "runbook_context": "",
        }, {"configurable": {"thread_id": "test-hitl-interrupt"}})
    assert "__interrupt__" in result, "Security ticket did not trigger interrupt"


@pytest.mark.api
def test_resume_approve_completes():
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.types import Command
    from graph_supervisor import get_app
    thread_id = "test-hitl-approve"
    ticket = "Ada percobaan login dari lokasi asing ke akun saya"
    with SqliteSaver.from_conn_string("checkpoints.sqlite") as saver:
        app = get_app(saver)
        app.invoke({
            "messages": [ticket],
            "resolved_categories": [],
            "needs_followup": False,
            "followup_category": None,
            "runbook_context": "",
        }, {"configurable": {"thread_id": thread_id}})
        result = app.invoke(
            Command(resume={"approved": True}),
            {"configurable": {"thread_id": thread_id}},
        )
    assert "__interrupt__" not in result, "Resume with approval still interrupted"
    msg = get_message_content(result["messages"][-1])
    assert "approved" in msg.lower() or "approve" in msg.lower(), f"Unexpected message: {msg}"


@pytest.mark.api
def test_resume_reject_escalates():
    from langgraph.checkpoint.sqlite import SqliteSaver
    from langgraph.types import Command
    from graph_supervisor import get_app
    thread_id = "test-hitl-reject"
    ticket = "Ada percobaan login dari lokasi asing ke akun saya"
    with SqliteSaver.from_conn_string("checkpoints.sqlite") as saver:
        app = get_app(saver)
        app.invoke({
            "messages": [ticket],
            "resolved_categories": [],
            "needs_followup": False,
            "followup_category": None,
            "runbook_context": "",
        }, {"configurable": {"thread_id": thread_id}})
        result = app.invoke(
            Command(resume={"approved": False}),
            {"configurable": {"thread_id": thread_id}},
        )
    msg = get_message_content(result["messages"][-1])
    assert "dibatalkan" in msg.lower() or "escalate" in msg.lower() or "manual review" in msg.lower(), f"Unexpected message: {msg}"
