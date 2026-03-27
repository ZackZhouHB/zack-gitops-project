# Multi-Agent Supervisor — Design & Implementation Plan

> **Project**: P3 from FUTURE-ROADMAP.md — Multi-Agent Supervisor Pattern  
> **Approach**: Extend project-125 in-place (not a clone)  
> **Why in-place**: ~90% code reuse, same Docker stack, current agent becomes a sub-agent  
> **Prerequisite**: P1 (Action Agent) ✅, P2 (HITL) ✅, P5 (Eval & Guardrails) ✅

---

## 1. Problem Statement

Our current project-125 is a **single monolithic agent** with 11 tools. It works well, but has limitations:

| Limitation | Why It Matters |
|-----------|---------------|
| One agent juggles everything | Research, action-taking, and summarisation compete for context window |
| No task decomposition | "Investigate X, create ticket, notify team" is 3 distinct tasks handled as one |
| Tool selection noise | 11 tools in one prompt → LLM sometimes picks wrong tool |
| No specialisation | RAG queries and Jira writes require different reasoning strategies |
| No parallelism | Research and reporting could happen concurrently in some flows |

**Multi-agent solves this** by splitting one generalist into specialised agents coordinated by a supervisor.

---

## 2. Target Architecture

### 2.1 Agent Topology

```
                    ┌─────────────────────────┐
                    │     User Request         │
                    │  (Streamlit / Slack / API)│
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    SUPERVISOR AGENT      │
                    │                          │
                    │  • Understands intent    │
                    │  • Decomposes into tasks │
                    │  • Routes to sub-agents  │
                    │  • Aggregates results    │
                    │  • Decides when DONE     │
                    └──┬─────────┬──────────┬─┘
                       │         │          │
          Command(goto)│         │          │ Command(goto)
                       │         │          │
          ┌────────────▼──┐  ┌──▼────────┐  ┌▼────────────┐
          │ RESEARCH AGENT│  │ACTION AGENT│  │ REPORT AGENT│
          │               │  │            │  │             │
          │ Tools:        │  │ Tools:     │  │ Tools:      │
          │ • rag_search  │  │ • create_  │  │ • (none —   │
          │ • search_     │  │   ticket   │  │   LLM-only) │
          │   issues      │  │ • update_  │  │             │
          │ • get_ticket  │  │   ticket   │  │ Capabilities│
          │               │  │ • add_     │  │ • Summarise │
          │ Capabilities: │  │   comment  │  │   findings  │
          │ • KB search   │  │ • send_    │  │ • Format    │
          │ • Issue lookup │  │   message  │  │   reports   │
          │ • Context     │  │ • create_  │  │ • Generate  │
          │   gathering   │  │   thread   │  │   Slack     │
          │               │  │ • reply_   │  │   messages  │
          │               │  │   in_thread│  │             │
          │               │  │            │  │             │
          │               │  │ HITL:      │  │             │
          │               │  │ interrupt()│  │             │
          │               │  │ on writes  │  │             │
          └───────────────┘  └────────────┘  └─────────────┘
                │                   │               │
                └───────────────────┼───────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │   SHARED STATE     │
                          │                    │
                          │ • findings: []     │
                          │ • actions_taken: []│
                          │ • plan: str        │
                          │ • final_report: str│
                          └────────────────────┘
```

### 2.2 How It Differs from Current Single Agent

```
BEFORE (single agent — graph.py):
  User → LLM (11 tools) → tool_node → LLM → ... → END
  
  Problem: LLM sees ALL 11 tools, must decide everything alone

AFTER (multi-agent — supervisor.py):
  User → Supervisor → route to Research/Action/Report → return → Supervisor → next? → END
  
  Benefit: Each sub-agent sees only its 3-4 tools, specialised prompt
```

### 2.3 Data Flow Example

**User**: "Investigate the high error rate on payment API, create an incident ticket, and notify the team"

```
Step 1: Supervisor decomposes
  → Task 1: Research the payment API error rate (→ Research Agent)
  → Task 2: Create Jira incident ticket (→ Action Agent)
  → Task 3: Notify team in Slack (→ Report Agent)

Step 2: Research Agent runs
  → rag_search("payment API error rate high")
  → search_issues("payment API", status="Open")
  → Returns findings: { kb_context: "...", related_tickets: [...] }

Step 3: Supervisor reviews Research findings, routes to Action Agent
  → create_ticket({ summary: "P2: High error rate on payment API", ...})
  → HITL interrupt() → User approves → Ticket SCRUM-21 created
  → Returns action: { ticket_key: "SCRUM-21" }

Step 4: Supervisor routes to Report Agent
  → LLM formats: summary of findings + ticket link + recommended actions
  → send_message(channel: "#all-platform-health-lab", message: formatted_report)
  → HITL interrupt() → User approves → Slack message sent

Step 5: Supervisor returns final response to user
```

---

## 3. Technology Alignment (What We Reuse vs. What's New)

### 3.1 Full Reuse (Zero Changes)

| Component | Where | Why It Works As-Is |
|-----------|-------|-------------------|
| Bedrock Claude Sonnet | LLM | Same model for all agents — each gets its own prompt |
| Weaviate (198 chunks) | Vector DB | Research Agent calls same `rag_search` |
| Jira client | MCP Server | Action Agent calls same 5 Jira tools |
| Slack client | MCP Server | Action/Report Agent calls same 5 Slack tools |
| HITL interrupt() | LangGraph | Works identically — supervisor graph has same interrupt mechanism |
| Guardrails | eval/ | Same input/output checks wrap the supervisor entry point |
| Docker stack | compose | No new containers — multi-agent is Python code in agent-backend/ |
| Streamlit UI | :8502 | Same chat + approval panel, just shows which agent is active |
| PostgreSQL | :5432 | Same DB (can use PostgresSaver for persistent checkpoints later) |

### 3.2 New Code (Additive, Non-Breaking)

| Component | Location | Effort | Description |
|-----------|----------|--------|-------------|
| Supervisor graph | `agent/supervisor.py` | ~200 lines | Parent StateGraph that routes to sub-agents |
| Research Agent | `agent/research_agent.py` | ~100 lines | Sub-graph with RAG + Jira read tools |
| Report Agent | `agent/report_agent.py` | ~80 lines | LLM-only agent that formats findings |
| Shared state | `agent/multi_state.py` | ~30 lines | Extended TypedDict with findings/plan/report |
| Supervisor prompt | `agent/prompts.py` | ~50 lines | New constant: SUPERVISOR_PROMPT |
| API endpoint | `main.py` | ~40 lines | `/chat/multi` — uses supervisor graph |
| Tests | `scripts/multi_agent_test.py` | ~150 lines | E2E tests for supervisor routing |
| Tutorial | `tutorials/step-26-*.md` | ~300 lines | Learning doc |

**Total new code**: ~950 lines | **Code modified**: ~50 lines (prompts.py + main.py)

### 3.3 What Does NOT Change

- `agent/graph.py` — stays exactly as-is, serves `/chat` endpoint (single-agent mode)
- MCP servers — no changes
- Frontend — minor additions to show active agent name
- Docker compose — no new services
- Existing tests — all 17 still pass

---

## 4. Implementation Phases

### Phase G: Supervisor Foundation

**Goal**: Supervisor can route to Research Agent and get back findings

| Step | Task | Details |
|------|------|---------|
| G1 | Create `agent/multi_state.py` | Shared state: messages, findings, actions_taken, plan, current_agent, final_report |
| G2 | Create `agent/research_agent.py` | Sub-graph with `rag_search`, `search_issues`, `get_ticket` tools + focused prompt |
| G3 | Create `agent/supervisor.py` | Parent graph: `supervisor_node → route → research/action/report → supervisor_node → end` |
| G4 | Add supervisor prompt to `prompts.py` | Task decomposition instructions, routing rules |
| G5 | Add `/chat/multi` endpoint in `main.py` | New endpoint, existing `/chat` untouched |
| G6 | Test: supervisor routes research queries correctly | "What does our KB say about EKS autoscaling?" → Research Agent |

### Phase H: Action + Report Agents

**Goal**: Full 3-agent pipeline works end-to-end

| Step | Task | Details |
|------|------|---------|
| H1 | Integrate existing graph.py as Action Agent sub-graph | Wrap current agent as callable sub-graph with write tools only |
| H2 | Create `agent/report_agent.py` | Takes findings + actions, formats summary, optionally sends to Slack |
| H3 | Wire HITL through supervisor | interrupt() in Action Agent propagates up to supervisor correctly |
| H4 | Test: full E2E "investigate + create ticket + notify" | Multi-step flow across all 3 agents |
| H5 | Test: partial failure handling | Research succeeds, Action fails → graceful degradation |

### Phase I: Testing & Polish

**Goal**: Comprehensive validation, documentation, Docker verification

| Step | Task | Details |
|------|------|---------|
| I1 | Create `scripts/multi_agent_test.py` | 10+ test scenarios covering routing, handoff, HITL, failures |
| I2 | Verify all 17 existing Docker tests still pass | Regression check |
| I3 | Test in Docker containers | Build, up, validate multi-agent via Docker |
| I4 | Update architecture doc | New diagrams showing multi-agent topology |
| I5 | Write `tutorials/step-26-multi-agent-supervisor.md` | Full tutorial |
| I6 | Update SESSION-HANDOFF.md | M8 milestone |

---

## 5. Key Design Decisions

### 5.1 Supervisor Routing Strategy

**Option A: LLM-based routing** (chosen)
- Supervisor LLM reads user request, decides which agent(s) to call
- Flexible — handles novel requests
- Cost: extra LLM call per routing decision

**Option B: Rule-based routing**
- Keyword matching to determine agent
- Fast, no LLM cost
- Brittle — breaks on novel phrasing

**Decision**: Option A. The supervisor IS an LLM agent. This matches LangGraph's `Command(goto=...)` pattern and is the industry standard.

### 5.2 Agent Communication

**Option A: Shared state dict** (chosen)
- All agents read/write to same `AgentState` TypedDict
- Research writes `findings`, Action reads `findings` and writes `actions_taken`, Report reads both
- Simple, no serialisation needed

**Option B: Message passing**
- Agents send messages to each other via a queue
- More decoupled but adds complexity

**Decision**: Option A. LangGraph's `StateGraph` is designed for shared state. Message passing adds unnecessary complexity for 3 agents.

### 5.3 Sub-Agent Implementation

**Option A: Sub-graphs (LangGraph nested graphs)** (chosen)
- Each agent is its own `StateGraph` compiled graph
- Supervisor calls them via `Command(goto="research_agent")`
- Clean separation, independent testing

**Option B: Function calls**
- Each agent is a Python function the supervisor calls
- Simpler but loses LangGraph features (checkpointing, interrupt, streaming)

**Decision**: Option A. Sub-graphs get free checkpointing, interrupt propagation, and streaming — all of which we already depend on.

### 5.4 Backward Compatibility

**Principle**: Adding multi-agent MUST NOT break existing single-agent mode.

| Endpoint | Behavior |
|----------|----------|
| `GET /health` | Unchanged |
| `POST /chat` | Unchanged — still uses `graph.py` single agent |
| `POST /chat/multi` | **NEW** — uses supervisor graph |
| `POST /approve` | Works for both modes (same checkpointer) |
| `POST /reject` | Works for both modes |

User can choose single-agent or multi-agent mode. Streamlit UI gets a toggle.

---

## 6. Supervisor Graph Structure (LangGraph)

```python
# Simplified structure — actual implementation will have error handling, logging, etc.

from langgraph.graph import StateGraph, END
from langgraph.types import Command

def supervisor_node(state: MultiAgentState) -> Command:
    """LLM decides next step: research, action, report, or done."""
    response = llm.invoke(messages + [supervisor_prompt])
    
    if response.next_agent == "research":
        return Command(goto="research_agent", update={"plan": response.plan})
    elif response.next_agent == "action":
        return Command(goto="action_agent", update={"plan": response.plan})
    elif response.next_agent == "report":
        return Command(goto="report_agent", update={"plan": response.plan})
    else:
        return Command(goto=END, update={"final_report": response.summary})

# Build graph
graph = StateGraph(MultiAgentState)
graph.add_node("supervisor", supervisor_node)
graph.add_node("research_agent", research_subgraph)
graph.add_node("action_agent", action_subgraph)
graph.add_node("report_agent", report_subgraph)

# All sub-agents return to supervisor after completing
graph.add_edge("research_agent", "supervisor")
graph.add_edge("action_agent", "supervisor")
graph.add_edge("report_agent", "supervisor")

graph.set_entry_point("supervisor")
```

---

## 7. Expected Outcomes

### 7.1 What We'll Demonstrate

| Capability | Single Agent (current) | Multi-Agent (new) |
|-----------|----------------------|-------------------|
| Task decomposition | ❌ One shot | ✅ Supervisor breaks into sub-tasks |
| Specialised reasoning | ❌ One prompt for all | ✅ Focused prompts per agent |
| Agent handoff | ❌ N/A | ✅ Research → Action → Report |
| Shared state | ❌ N/A | ✅ findings flow between agents |
| Parallel potential | ❌ Sequential only | ✅ Research + Report could run in parallel |
| Failure isolation | ❌ Whole agent fails | ✅ One agent fails, others continue |
| Observability | Basic | ✅ Per-agent logging, "current_agent" in UI |

### 7.2 Test Scenarios (Preview)

1. **Pure research**: "What does our KB say about Terraform module versioning?" → Research Agent only
2. **Pure action**: "Create a P3 ticket for updating the EKS addon versions" → Action Agent only (with HITL)
3. **Full pipeline**: "Investigate API latency, create a ticket, notify team" → All 3 agents
4. **Research + Report**: "Summarise all open P1 incidents and post to Slack" → Research → Report
5. **Failure recovery**: Research finds nothing → Supervisor tells user "No relevant KB articles found"
6. **HITL in multi-agent**: Action Agent pauses for approval → Supervisor waits → Resume flows correctly

### 7.3 Performance Expectations

| Metric | Single Agent | Multi-Agent (estimated) |
|--------|-------------|----------------------|
| Simple query | 5-10s | 8-15s (extra supervisor hop) |
| Complex multi-step | 20-30s | 30-50s (3 agents + routing) |
| LLM calls per request | 2-4 | 5-10 (supervisor + sub-agents) |
| Cost per request | ~$0.01-0.03 | ~$0.03-0.08 |

Trade-off: Slightly slower and more expensive, but much better at complex multi-step tasks and more maintainable as we add capabilities.

---

## 8. Risk & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Supervisor routes incorrectly | Wrong agent runs, wastes time | Detailed routing prompt + test suite |
| Sub-agent loops (infinite back-and-forth) | Hung request, high cost | Max handoff count (default: 5) |
| HITL interrupt doesn't propagate | Action runs without approval | Test interrupt in nested graph specifically |
| State gets corrupted between agents | Wrong data passed | Strict TypedDict, validation at handoff |
| Bedrock latency compounds | 50s+ for complex flows | Streaming, progress indicators in UI |
| Existing tests break | Regression | Run all 17 Docker tests before/after |

---

## 9. What This Unlocks Next

Completing P3 (Multi-Agent) positions us for:

| Future Project | How Multi-Agent Helps |
|---------------|---------------------|
| **P4: Scheduled/Long-Running** | Supervisor can be triggered by cron, delegates to agents |
| **P6: Memory** | Each agent can have its own memory namespace |
| **P7: Multi-Modal** | Vision Agent becomes another sub-agent the supervisor routes to |
| **Custom Agent Marketplace** | Teams add new specialist agents without changing supervisor |

---

*Created 2026-03-27 — Multi-Agent Supervisor extension plan for project-125*
