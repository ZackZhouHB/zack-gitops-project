# RAG Agent Patterns

## What is an Agent in RAG?

An agent extends RAG beyond simple document Q&A by adding **tools** that can take actions, not just retrieve information.

```
Basic RAG:     Question → Search Docs → Answer
Agent RAG:     Question → Think → Use Tools → Observe → Answer
```

---

## Our Implementation (rag-v1)

### Available Tools

| Tool | Description | Trigger Keywords |
|------|-------------|------------------|
| `search_docs` | Search knowledge base | what, how, why, explain, about |
| `list_sources` | List all documents | list, all documents, all sources |
| `calculate` | Math operations | calculate, numbers with +/-/*// |
| `get_date` | Current date/time | today, date, time, now, current |
| `compare_docs` | Compare documents | compare, difference, versus, vs |

### How It Works

```python
# Rule-based tool selection (reliable)
def _plan(self, query: str) -> str:
    tools = []
    if "today" in query.lower():
        tools.append("get_date")
    if re.search(r'\d+\s*[+\-*/]\s*\d+', query):
        tools.append("calculate")
    if "list" in query.lower():
        tools.append("list_sources")
    # Default to search
    if not tools:
        tools.append("search_docs")
    return tools
```

### Testing

```bash
# Get token
TOKEN=$(curl -s -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin"}' | jq -r '.token')

# Test date tool
curl -s -X POST http://localhost:8001/agent \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is todays date?"}' | jq .
# Result: tools_used: ["search_docs", "get_date", "answer"]

# Test calculate tool
curl -s -X POST http://localhost:8001/agent \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Calculate 25 * 4"}' | jq .
# Result: tools_used: ["calculate", "answer"], answer includes "100"

# Test list sources
curl -s -X POST http://localhost:8001/agent \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "List all documents"}' | jq .
# Result: tools_used: ["list_sources", "answer"]

# Test multi-tool
curl -s -X POST http://localhost:8001/agent \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What documents were uploaded today?"}' | jq .
# Result: tools_used: ["search_docs", "list_sources", "get_date", "answer"]
```

---

## Enterprise Agent Patterns

### 1. Multi-Tool Agents

Real-world agents have many tools for different actions:

```
┌─────────────────────────────────────────────────────────────┐
│                      AGENT ORCHESTRATOR                      │
│                                                              │
│  Tools Available:                                            │
│  ├── search_documents    (RAG retrieval)                    │
│  ├── search_database     (SQL queries)                      │
│  ├── call_api            (REST/GraphQL)                     │
│  ├── send_email          (Notifications)                    │
│  ├── create_ticket       (Jira/ServiceNow)                  │
│  ├── run_code            (Python sandbox)                   │
│  └── human_handoff       (Escalation)                       │
└─────────────────────────────────────────────────────────────┘
```

### 2. Multi-Agent Systems

Specialized agents for different domains:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Router     │────▶│  Specialist  │────▶│  Specialist  │
│   Agent      │     │  Agent A     │     │  Agent B     │
│              │     │  (Finance)   │     │  (HR)        │
└──────────────┘     └──────────────┘     └──────────────┘
       │
       ▼
┌──────────────┐
│  Specialist  │
│  Agent C     │
│  (IT Support)│
└──────────────┘
```

### 3. AWS Bedrock Agents (Managed)

```
┌─────────────────────────────────────────────────────────────┐
│                    BEDROCK AGENT                             │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Knowledge   │  │   Action    │  │   Action    │         │
│  │ Base (RAG)  │  │  Group 1    │  │  Group 2    │         │
│  │             │  │  (Lambda)   │  │  (Lambda)   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
│  Guardrails: Content filtering, PII redaction               │
└─────────────────────────────────────────────────────────────┘
```

---

## Real-World Use Cases

| Use Case | Tools | Flow |
|----------|-------|------|
| **IT Helpdesk** | search_kb, create_ticket, check_status | User asks → Search KB → No answer? → Create ticket |
| **HR Assistant** | search_policies, lookup_employee, submit_request | "What's my PTO balance?" → Query HR system |
| **Sales Copilot** | search_docs, query_crm, draft_email | "Summarize account X" → Pull CRM data + docs |
| **Code Assistant** | search_docs, run_code, create_pr | "Fix this bug" → Search → Generate → Test → PR |

---

## Enterprise Patterns

### Tool Authorization

```python
# Tools have permission levels
tools = {
    "search_docs": {"roles": ["*"]},           # Everyone
    "query_database": {"roles": ["analyst"]},   # Restricted
    "create_ticket": {"roles": ["support"]},    # Role-based
    "human_handoff": {"roles": ["*"]}           # Escalation
}
```

### Guardrails

```python
# Before tool execution
if tool == "send_email":
    validate_recipient(params["to"])
    check_content_policy(params["body"])
    require_approval_if_external()
```

### Audit Trail

```python
# Log every agent action
audit_log.record({
    "user": user_id,
    "agent_action": "call_api",
    "tool": "create_ticket",
    "params": sanitized_params,
    "result": "success",
    "timestamp": now()
})
```

---

## Options for Extending

| Option | Effort | Value |
|--------|--------|-------|
| **Keep current** | None | Basic ReAct works for doc Q&A |
| **Add more tools** | Low | Add web search, code execution |
| **Bedrock Agents** | Medium | Managed, built-in guardrails |
| **Multi-agent** | High | Complex workflows, specialists |

### Quick Win - Add More Tools

```python
TOOLS = {
    "search_documents": search_docs,
    "calculate": lambda expr: eval(expr),
    "get_current_date": lambda: datetime.now().isoformat(),
    "summarize_url": fetch_and_summarize,
    "web_search": search_web,  # Add web search
}
```

### Production - Use Bedrock Agents

- Knowledge Base = Your vector store
- Action Groups = Lambda functions for business logic
- Built-in: Guardrails, tracing, versioning

---

## Key Differences: RAG vs Agent

| Capability | RAG | Agent |
|------------|-----|-------|
| Answer from docs | ✅ | ✅ |
| Call APIs/tools | ❌ | ✅ |
| Multi-step reasoning | ❌ | ✅ |
| Create/update data | ❌ | ✅ |
| Take actions | ❌ | ✅ |

---

## Files

- `backend/app/agents/rag_agent.py` - Agent implementation
- `backend/app/api/routes.py` - `/agent` endpoint
