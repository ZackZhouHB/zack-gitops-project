# Future Learning Roadmap — From RAG Chatbot to Production AI Agent Engineer

> **Current Coverage**: ~40-50% of real-world AI agent engineering  
> **What We've Nailed**: RAG pipeline, ReAct loop, multi-tool orchestration, streaming UX, cloud deployment  
> **What's Missing**: Action-taking agents, multi-agent, HITL, long-running tasks, external APIs, memory, eval, multi-modal

---

## ✅ Completed (This Project)

- [x] RAG pipeline end-to-end (chunk → embed → search → generate)
- [x] Agentic ReAct loop (LLM decides tools dynamically)
- [x] Multi-tool orchestration (5 tools, description-based routing)
- [x] Structured workflow with branching (incident triage)
- [x] Architecture evolution (router → single ReAct loop, and why)
- [x] Streaming UX (SSE, live tokens, source citations)
- [x] Cloud deployment (Terraform, ECS Fargate, ALB, Bedrock KB)
- [x] Multi-source ingestion (S3, web crawler, Confluence)
- [x] Production patterns (logging, observability, loop protection, error handling)
- [x] Cost analysis and destroy/rebuild playbook

---

## 🔲 Project 1: Jira/Slack Action Agent (HIGH PRIORITY)

**Why**: Moves you from "chatbot that answers questions" to "agent that gets work done" — this is what the JD and industry demands.

**What you'd learn**: Write tools, confirmation flows, OAuth2, error recovery, idempotency

### Tasks

- [ ] Set up Jira Cloud free tier + API token
- [ ] Build `create_jira_ticket` tool (project, summary, description, priority, labels)
- [ ] Build `search_jira_issues` tool (JQL queries — find duplicates before creating)
- [ ] Build `update_jira_ticket` tool (add comments, change status, assign)
- [ ] Set up Slack workspace + bot token (OAuth2 scope: `chat:write`, `channels:read`)
- [ ] Build `send_slack_message` tool (channel, message, thread reply)
- [ ] Build `create_slack_thread` tool (post incident summary, pin to channel)
- [ ] Implement **confirmation flow** — agent proposes action, waits for user "yes" before executing
- [ ] Implement **rollback pattern** — if Jira create succeeds but Slack fails, log partial state
- [ ] Implement **idempotency** — same request doesn't create duplicate tickets
- [ ] Build end-to-end flow: "Create a P2 for API latency spike and notify #incidents channel"
- [ ] Handle API errors gracefully (rate limiting, 401/403, network timeouts)
- [ ] Write tutorial: `step-19-action-agent-jira-slack.md`

### Test Scenarios
- [ ] "Create a ticket for the database connection timeout issue"
- [ ] "Find all open P1 incidents from this week"
- [ ] "Notify the team in #platform-alerts about the EKS scaling issue"
- [ ] "Create a ticket and notify Slack" (multi-tool chain with confirmation)
- [ ] Error case: invalid project key, expired token, rate limited

---

## 🔲 Project 2: Human-in-the-Loop Approval Workflow

**Why**: Production agents MUST pause for human approval on destructive or high-risk actions.

**What you'd learn**: LangGraph `interrupt()`, persistent checkpoints, `Command(resume=...)`, state serialisation

### Tasks

- [ ] Study LangGraph `interrupt()` and `Command` patterns (docs + examples)
- [ ] Build a "database cleanup" workflow that pauses for approval:
  - Agent identifies 500 stale records
  - Presents summary to user: "Delete 500 records? [Approve / Modify / Reject]"
  - User can modify: "Yes, but exclude last 7 days"
  - Agent adjusts and re-presents, then executes on approval
- [ ] Implement persistent checkpointing (state survives container restart)
- [ ] Build approval dashboard (simple Streamlit page showing pending approvals)
- [ ] Add timeout handling — if no approval in 24h, auto-cancel with notification
- [ ] Build multi-step approval: Step 1 → Human approves → Step 2 → Human approves → Execute
- [ ] Write tutorial: `step-20-human-in-the-loop.md`

### Test Scenarios
- [ ] Approve flow (happy path)
- [ ] Reject flow (agent acknowledges and stops)
- [ ] Modify flow (user changes parameters, agent re-plans)
- [ ] Timeout flow (no response in X minutes)
- [ ] Resume after container restart (checkpoint recovery)

---

## 🔲 Project 3: Multi-Agent Supervisor Pattern

**Why**: Complex tasks need specialised agents collaborating, not one agent doing everything.

**What you'd learn**: Agent handoff, shared state, supervisor/coordinator pattern, LangGraph `Command(goto=...)`

### Tasks

- [ ] Study LangGraph multi-agent patterns (supervisor, swarm, hierarchical)
- [ ] Design a 3-agent system:
  ```
  Supervisor Agent (coordinator)
  ├── Research Agent (KB search, web search, API queries)
  ├── Action Agent (Jira, Slack, deployments)
  └── Report Agent (summarise findings, generate reports, format output)
  ```
- [ ] Implement supervisor that routes sub-tasks to specialist agents
- [ ] Implement shared state between agents (findings from Research flow to Action)
- [ ] Implement agent handoff with context passing
- [ ] Build an end-to-end scenario:
  "Investigate the high error rate on the payment API, create an incident ticket, and send a summary to the team"
  → Supervisor → Research (searches KB + monitoring) → Action (creates Jira) → Report (Slack summary)
- [ ] Handle partial failures (one agent fails, others continue)
- [ ] Write tutorial: `step-21-multi-agent-supervisor.md`

---

## 🔲 Project 4: Scheduled & Long-Running Agent

**Why**: Real agents don't just respond to chat — they run in the background, on schedule, proactively.

**What you'd learn**: Background execution, EventBridge/cron triggers, checkpointing, email/report output

### Tasks

- [ ] Build a "nightly documentation freshness" agent:
  - Scans all KB sources (S3, Confluence, blog)
  - Identifies docs not updated in >90 days
  - Generates a freshness report with recommendations
  - Emails report to stakeholders (SES or SMTP)
- [ ] Build a "weekly cost analysis" agent:
  - Queries AWS Cost Explorer API
  - Compares to previous week
  - Flags anomalies (>20% increase)
  - Posts summary to Slack
- [ ] Implement EventBridge scheduled rule to trigger agent
- [ ] Implement checkpointing for long-running tasks (agent can resume after failure)
- [ ] Implement progress reporting (agent posts intermediate updates)
- [ ] Write tutorial: `step-22-scheduled-agents.md`

---

## 🔲 Project 5: Evaluation & Guardrails Pipeline

**Why**: You can't improve what you can't measure. Production RAG needs automated quality testing.

**What you'd learn**: RAGAS, DeepEval, hallucination detection, Bedrock Guardrails, A/B testing

### Tasks

- [ ] Set up RAGAS evaluation framework
- [ ] Create a **golden test set** (50 questions with expected answers and sources)
- [ ] Implement automated metrics:
  - [ ] **Faithfulness**: Does the answer match the retrieved context? (no hallucination)
  - [ ] **Relevancy**: Are the retrieved chunks relevant to the question?
  - [ ] **Answer correctness**: Does the answer match the expected answer?
  - [ ] **Context precision**: Are the top-k results actually useful?
- [ ] Set up Bedrock Guardrails:
  - [ ] PII detection and masking
  - [ ] Topic filtering (block off-topic questions)
  - [ ] Hallucination detection (cross-check answer vs context)
- [ ] Implement token budget guardrails (max tokens per conversation, alert on runaway loops)
- [ ] Build A/B test framework: compare chunking strategies (default vs semantic vs hierarchical)
- [ ] Integrate eval into CI/CD — fail deployment if quality drops below threshold
- [ ] Write tutorial: `step-23-evaluation-and-guardrails.md`

---

## 🔲 Project 6: Memory & Personalisation

**Why**: Stateless agents repeat themselves. Users expect the agent to remember past interactions.

**What you'd learn**: LangGraph `Store`, cross-session memory, user profiles, conversation summarisation

### Tasks

- [ ] Study LangGraph `Store` API (namespace, key-value, cross-thread persistence)
- [ ] Implement **conversation summary memory**:
  - After each conversation, LLM generates a 2-sentence summary
  - Stored in LangGraph Store under user namespace
  - Next conversation starts with "Previous context: ..."
- [ ] Implement **user preference memory**:
  - Track: preferred response format, role, team, common topics
  - "You usually ask about Terraform and EKS — here's what's new since last time"
- [ ] Implement **shared team memory**:
  - "The team decided to migrate to Karpenter on March 15" — all users see this
  - Stored in shared namespace, editable by any team member
- [ ] Implement **knowledge graph** (optional, advanced):
  - Entities and relationships extracted from conversations
  - "Last time, user asked about Karpenter autoscaling for GPU workloads"
  - Neo4j or DynamoDB-backed graph
- [ ] Write tutorial: `step-24-memory-and-personalisation.md`

---

## 🔲 Project 7: Multi-Modal Agent (Vision + Code Execution)

**Why**: Text-only agents can't handle screenshots, CSVs, diagrams, or code analysis.

**What you'd learn**: Claude Vision API, sandboxed code execution, file upload handling, chart generation

### Tasks

- [ ] Implement **image understanding**:
  - User uploads error screenshot → Claude Vision reads it → agent diagnoses
  - User uploads architecture diagram → agent describes components
- [ ] Implement **CSV/data analysis**:
  - User uploads CSV → agent writes Python to analyse it → returns insights
  - Sandboxed execution (Docker container or AWS Lambda)
- [ ] Implement **code execution tool**:
  - Agent generates Python code, executes in sandbox, returns output
  - Supports: data analysis, chart generation, API testing
- [ ] Implement **chart/diagram generation**:
  - Agent generates Mermaid diagrams or matplotlib charts as part of answers
  - Frontend renders inline
- [ ] Implement **voice input** (stretch goal):
  - Audio → Bedrock/Whisper transcription → agent processes → text response
  - This is the "car sales phone call robot" pattern from your experience
- [ ] Write tutorial: `step-25-multimodal-agent.md`

---

## Priority Map

```
                        HIGH IMPACT
                            │
            ┌───────────────┼───────────────┐
            │               │               │
    Project 1          Project 3       Project 5
    Jira/Slack         Multi-Agent     Eval/Guardrails
    Action Agent       Supervisor      Pipeline
            │               │               │
LOW ────────┼───────────────┼───────────────┼──────── HIGH
EFFORT      │               │               │        EFFORT
            │               │               │
    Project 2          Project 6       Project 7
    HITL Approval      Memory &        Multi-Modal
    Workflow           Personalisation  (Vision+Code)
            │               │               │
            └───────────────┼───────────────┘
                            │
                        LOW IMPACT
                     (still valuable)
```

**Recommended order**: 1 → 2 → 5 → 3 → 4 → 6 → 7

- **Project 1** (Jira/Slack) is the single highest-value next step — proves you can build agents that take action, not just answer questions
- **Project 2** (HITL) is quick and essential for any write-action agent
- **Project 5** (Eval) is the "how do you know it works?" answer every hiring manager asks
- **Projects 3-7** round out the full skill set

---

## Coverage After Completing All 7

| Capability | Current | After All 7 |
|-----------|---------|-------------|
| RAG & Knowledge Retrieval | ✅ | ✅ |
| Agentic ReAct + Tool Calling | ✅ | ✅ |
| Cloud Deployment | ✅ | ✅ |
| Action-Taking (Write APIs) | ❌ | ✅ |
| Human-in-the-Loop | ❌ | ✅ |
| Multi-Agent Collaboration | ❌ | ✅ |
| Long-Running / Scheduled | ❌ | ✅ |
| External API Integration | ❌ | ✅ |
| Memory & Personalisation | ❌ | ✅ |
| Evaluation & Guardrails | ❌ | ✅ |
| Multi-Modal (Vision, Code) | ❌ | ✅ |
| **Overall Coverage** | **~40-50%** | **~90%+** |

---

*Created 2026-03-26 — based on gaps identified after completing Platform Health Insight Assistant (local + AWS deployment).*
