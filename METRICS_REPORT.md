# Ops Agent — Metrics Summary Report

## 1. Agent Types & Ticket Categories

| Metric | Count | Details | Source |
|--------|-------|---------|--------|
| **Agent types** | 3 | `technical_agent`, `billing_agent`, `security_agent` | `graph_supervisor.py:315-320` |
| **Ticket categories** | 3 | `technical`, `billing`, `security` | `graph_supervisor.py:17-28` |
| **Routing destinations** | 3 | `retrieve_runbook` (technical), `billing_agent`, `security_agent` | `graph_supervisor.py:289-297` |
| **Available tools** | 3 | `restart_service`, `check_invoice`, `refund_policy` | `graph_supervisor.py:64-79` |
| **Follow-up handoff** | Yes | LLM-driven multi-agent handoff via `detect_followup()` | `graph_supervisor.py:101-131` |

## 2. Routing / Classification Accuracy

| Metric | Value | Source |
|--------|-------|--------|
| **Golden dataset size** | 30 tickets (10 technical, 10 billing, 10 security) | `eval/golden_dataset.json` |
| **Last measured accuracy** | 90% (27/30) | `README.md:128-132` |
| **Accuracy measurement method** | `eval_routing.py` — compares `supervisor()` output against `expected_category` | `eval_routing.py:29-51` |
| **Known misclassifications** | 3 tickets: password reset, account lockout, billing portal display error | `eval_routing.py:57-61`, `README.md:134-138` |
| **Timing instrumentation** | Added `[TIMING]` prints to `supervisor()`, each agent, RAG retrieval, and follow-up detection | `graph_supervisor.py:83-98, 101-131, 134-181, 184-200, 203-253, 262-286` |
| **Per-item latency tracking** | Added per-classification timing in eval | `eval_routing.py:38-42, 62-77` |

## 3. Human-in-the-Loop Interrupt Scenarios

| Scenario | Count | Details | Source |
|----------|-------|---------|--------|
| **Security action approval** | 1 | `security_agent()` calls `interrupt()` with `action`, `ticket_summary`, `proposed_action`. Human must approve/reject via `Command(resume={"approved": bool})` | `graph_supervisor.py:262-286` |
| **Total HITL scenarios** | **1** | | |
| **HITL entry points** | 2 | CLI (`main.py:20-34`), Gradio UI (`app.py:11-72`) | |
| **Interrupt resume paths** | 2 | Approved: account locked + notified. Rejected: escalated to manual review | `graph_supervisor.py:273-276` |

## 4. Latency / Throughput

| Metric | Status | Source |
|--------|--------|--------|
| **Per-node timing** | Instrumented — each graph node reports `[TIMING] <node>: X.XXXs` | `graph_supervisor.py:83, 101, 134, 184, 203, 262` |
| **Classification latency eval** | Added per-item timing with P50/P95/P99 in `eval_routing.py` | `eval_routing.py:62-77` |
| **Benchmark suite** | `benchmark.py` measures: classification latency (all 30 tickets), end-to-end latency (technical + billing), throughput (tickets/s), per-category breakdown | `benchmark.py` |
| **Throughput measurement** | Added — `benchmark.py` computes throughput = `n / total_time` tickets/s | `benchmark.py:66` |
| **Historical latency numbers** | **Not yet captured** — requires running benchmark against a live Groq API key | |

## 5. Checkpointing / State Persistence

| Metric | Coverage | Source |
|--------|----------|--------|
| **Persistence mechanism** | `SqliteSaver` with `checkpoints.sqlite` | `app.py:39-41`, `main.py:41-43` |
| **Checkpointing test 1** | Security ticket triggers interrupt, state persisted in SQLite | `test_persistence.py:9-24` |
| **Checkpointing test 2** | Cross-process resume: persisted state can be loaded in a new process and resumed | `test_resume_later.py:9-14` |
| **Pytest test coverage** | `tests/test_system.py` — 14 tests covering graph structure, routing logic, Pydantic schemas, accuracy threshold, latency threshold, HITL interrupt, approve/reject flows | `tests/test_system.py` |
| **State schema resilience** | Tests verify `GraphState` has all 7 required keys; route mapping for all 3 categories; follow-up edge cases | `tests/test_system.py:43-85` |

## 6. Test Coverage (New)

| Category | Tests | Source |
|----------|-------|--------|
| Graph structure | 4 tests (nodes, edges, routing, follow-up) | `tests/test_system.py:30-67` |
| Pydantic schemas | 3 tests (valid categories, invalid, follow-up defaults) | `tests/test_system.py:73-86` |
| State schema | 1 test (required keys) | `tests/test_system.py:92-97` |
| Utility functions | 2 tests (`get_message_content`) | `tests/test_system.py:103-112` |
| Integration (API) | 6 tests (routing accuracy, latency, HITL x3) | `tests/test_system.py:118-173` |
| **Total tests** | **16** (8 unit, 8 integration) | |

## Summary of Implemented Features

| Feature | Previously | Now |
|---------|-----------|-----|
| Latency measurement | Not measured | `[TIMING]` in all 6 node functions |
| Throughput measurement | Not measured | `benchmark.py` with tickets/s metric |
| Eval with timing | Accuracy only | Accuracy + P50/P95/P99 latency |
| Test suite | 3 ad-hoc scripts | 16 pytest tests |
| Routing accuracy tracking | 90% in README | Programmatic eval with latency |
| Per-category latency breakdown | Not available | Added in `benchmark.py` |

Run `python benchmark.py` to generate live latency and throughput numbers.
Run `python -m pytest tests/ -v` to execute the test suite.
