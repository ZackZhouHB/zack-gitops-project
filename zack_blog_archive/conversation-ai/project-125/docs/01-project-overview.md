# Project 125 — Action Agent + Human-in-the-Loop + Eval Pipeline

> **Scope**: Projects 1 (Jira/Slack Action Agent), 2 (HITL Approval), and 5 (Eval & Guardrails)  
> **Foundation**: Built on top of the local RAG agent (`platform-health-agent`)  
> **Goal**: Evolve from "chatbot that answers questions" → "agent that takes action safely"

---

## 1. Why This Project

The Platform Health Insight Assistant (completed) proves we can build:
- ✅ RAG pipeline (chunk → embed → search → generate)
- ✅ Agentic ReAct loop (LLM decides tools dynamically)
- ✅ Multi-tool orchestration (5 tools, description-based routing)
- ✅ Streaming UX (SSE, live tokens, source citations)

**What's missing** — and what every production agent needs:

| Gap | Why It Matters |
|-----|---------------|
| **Action-taking** | Agents that only read are chatbots. Agents that write (create tickets, send messages) are useful. |
| **Human approval** | Production agents MUST pause for human review before destructive/high-risk actions. |
| **Evaluation** | "How do you know it works?" — every hiring manager's question. Automated quality testing. |
| **MCP integration** | Industry-standard protocol for tool interoperability. Shows you can build portable, reusable components. |

---

## 2. What We're Building

An **action-taking agent** that can:
1. **Search knowledge** (existing RAG via Weaviate — reused from platform-health-agent)
2. **Create Jira tickets** enriched with KB context (via MCP server)
3. **Send Slack notifications** with incident summaries (via MCP server)
4. **Pause for human approval** before any write action (LangGraph interrupt)
5. **Measure quality** with automated evaluation pipeline (RAGAS + guardrails)

### Example Interaction
```
User: "Create a ticket for the API latency issue and notify the team"

Agent:
  1. rag_search("API latency") → finds past incidents, root cause, runbook
  2. search_jira("API latency") → checks for duplicates (none open)
  3. PAUSE → "I'll create this P2 ticket. Approve?"
     ┌─────────────────────────────────────────┐
     │ Project: PLAT                           │
     │ Summary: API latency — connection pool  │
     │ Priority: P2                            │
     │ Sources: 3 KB matches, runbook linked   │
     │                                         │
     │ [✅ Approve] [✏️ Edit] [❌ Reject]       │
     └─────────────────────────────────────────┘
  4. User approves → create_jira_ticket() → PLAT-87
  5. send_slack("#platform-alerts", summary) → message sent
  6. "Done. PLAT-87 created, team notified in #platform-alerts."
```

---

## 3. Scope — What's In / What's Out

### In Scope (P1 + P2 + P5)
- Jira Cloud integration (create, search, update tickets)
- Slack integration (send messages, create threads)
- MCP server pattern (Jira + Slack as MCP servers)
- Human-in-the-loop approval workflow (LangGraph interrupt/resume)
- Confirmation flow for all write actions
- Idempotency (duplicate detection before creating)
- Error recovery (partial failure handling)
- Evaluation pipeline (golden test set, RAGAS metrics)
- Bedrock Guardrails (PII, topic filtering, hallucination detection)
- Token budget guardrails

### Out of Scope (Future Projects)
- Multi-agent supervisor pattern (P3)
- Scheduled/long-running agents (P4)
- Memory & personalisation (P6)
- Multi-modal: vision, code execution (P7)

---

## 4. Key Concepts

### Agent vs Tool vs MCP
| Concept | Role | Analogy |
|---------|------|---------|
| **Agent** | The brain — reasons, plans, decides which tools to use | The engineer |
| **Tool/Skill** | A specific capability the agent calls | A skill (search, create ticket) |
| **MCP** | Standard protocol for exposing tools to any agent | USB-C port — universal connector |

### Read vs Write Actions
| Type | Examples | Approval Needed? |
|------|----------|-----------------|
| **Read** | rag_search, search_jira, list_channels | ❌ No |
| **Write** | create_ticket, send_message, update_ticket | ✅ Yes — human confirms |

### Evaluation Metrics
| Metric | What It Measures |
|--------|-----------------|
| **Faithfulness** | Does the answer match the retrieved context? (no hallucination) |
| **Relevancy** | Are the retrieved chunks relevant to the question? |
| **Answer Correctness** | Does the answer match the expected answer? |
| **Context Precision** | Are the top-k results actually useful? |

---

## 5. Relationship to Existing Projects

```
platform-health-agent/          ← Foundation (LOCAL RAG + LangGraph)
├── Weaviate (vector store)     ← Reused as rag_search tool
├── PostgreSQL (state)          ← Reused for conversation history
├── LangGraph (agent)           ← Extended with new tools + HITL
└── Streamlit (frontend)        ← Extended with approval UI

project-125/                    ← This project (NEW capabilities)
├── Jira MCP Server             ← New: action-taking
├── Slack MCP Server            ← New: notifications
├── HITL Approval Flow          ← New: safety layer
├── Eval Pipeline               ← New: quality measurement
└── Extended Agent Graph        ← New: combines all of the above
```

The local RAG stack runs via Docker Compose on the same machine. project-125 adds new services alongside it and extends the agent with new tools.

---

*Created 2026-03-26 — Project 125 combines roadmap items P1, P2, P5 for maximum learning impact.*
