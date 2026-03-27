# Troubleshooting Guide — Project 125

> **Convention**: Each issue is numbered and follows the pattern:  
> **Symptoms → Root Cause → How Found → Fix → Verification → Prevention**

---

## Issues Index

| # | Category | Summary | Status |
|---|----------|---------|--------|
| 1 | Jira API | Search endpoint migrated to /search/jql | ✅ Fixed |
| 2 | Jira Config | Project key vs project name mismatch | ✅ Fixed |
| 3 | LangChain AWS | Tool schema key: 'parameters' not 'input_schema' | ✅ Fixed |
| 4 | Jira API | Priority field can be null — NoneType.get() | ✅ Fixed |
| 5 | Port Config | main.py hardcoded port 8001 instead of 8010 | ✅ Fixed |
| 6 | HITL | System prompt prevented LLM from calling write tools | ✅ Fixed |
| 7 | Eval | Faithfulness scoring heuristic gives inconsistent results | ⚠️ Known |
| 8 | Guardrails | Topic filter misses semantically off-topic queries | ⚠️ Known |
| 9 | Docker | Weaviate image has no curl — healthcheck fails | ✅ Fixed |
| 10 | Docker | AWS SSO cache needs writable ~/.aws mount | ✅ Fixed |
| 11 | Docker | MCP FastMCP.run() doesn't accept host/port kwargs | ✅ Fixed |
| 12 | Docker | rag_tool connect_to_local fails for Docker DNS names | ✅ Fixed |

---

## Issue #1: Jira Search Endpoint Migration

**Category**: Jira API

### Symptoms
JQL search returned HTTP 410 (Gone) with message: "The requested API has been removed. Please migrate to the /rest/api/3/search/jql API."

### Root Cause
Jira Cloud deprecated `/rest/api/3/search` and migrated to `/rest/api/3/search/jql` in 2026. The new endpoint also changed the response format — no longer returns `total` count, uses `isLast` boolean instead.

### How Found
Running `scripts/jira_test.py` — Test 4 (Search) returned 410.

### Fix
Updated both `scripts/jira_test.py` and `mcp-servers/jira-server/jira_client.py`:
- Changed endpoint from `/rest/api/3/search` to `/rest/api/3/search/jql`
- Changed `total` parsing to fallback: `data.get("total", len(issues))`

### Verification
Re-ran `jira_test.py` — Test 4 now returns results correctly.

### Prevention
Check Jira Cloud changelog for API deprecations: https://developer.atlassian.com/changelog/

---

## Issue #2: Jira Project Key vs Name Mismatch

**Category**: Jira Config

### Symptoms
Test 2 (Get Project) returned 404 for project key `PLAT`.

### Root Cause
User created a Scrum project with **name** "PLAT", but Jira auto-assigned the **key** as `SCRUM`. The API uses the key, not the name.

### How Found
Called `/rest/api/3/project` to list all projects — showed `Key: SCRUM, Name: PLAT`.

### Fix
Updated `.env`: `JIRA_PROJECT_KEY=SCRUM`

### Verification
All 8 Jira tests pass with key `SCRUM`.

### Prevention
When creating Jira projects, explicitly set the project key (don't rely on auto-generation). Check via API: `GET /rest/api/3/project`.

---

## Issue #3: LangChain AWS Tool Schema Key Mismatch

**Category**: LangGraph / LangChain AWS

### Symptoms
Agent returned 500 on `/chat` with: `KeyError: 'parameters'` in `bedrock_converse.py _format_tools()`.

### Root Cause
`ChatBedrockConverse` expects tool definitions with `parameters` key (LangChain format), but we used `input_schema` (raw Bedrock API format). The LangChain adapter converts `parameters` → Bedrock's `inputSchema` internally.

### How Found
Stack trace pointed to `_format_tools` in `langchain_aws/chat_models/bedrock_converse.py` line 2555.

### Fix
Changed all tool definitions in `agent/graph.py`:
```python
# WRONG (raw Bedrock format)
"input_schema": {"type": "object", "properties": {...}}

# CORRECT (LangChain format — auto-converted to Bedrock)
"parameters": {"type": "object", "properties": {...}}
```

### Verification
Agent starts, /chat returns responses with tool calls.

### Prevention
When using `ChatBedrockConverse`, always use LangChain tool format (`parameters`), not raw Bedrock format (`input_schema`). The adapter handles the conversion.

---

## Issue #4: Jira Priority Field Can Be Null

**Category**: Jira API

### Symptoms
`AttributeError: 'NoneType' object has no attribute 'get'` when calling `jira_client.search()` — some Jira issues return `priority: null`.

### Root Cause
Jira Cloud returns `"priority": null` (not an empty object) for issues where no priority scheme is configured or the issue type doesn't have a default priority. The code used `f.get("priority", {}).get("name", "Unknown")` — when `priority` is `null`, `.get()` returns `None` (not `{}`), so the chained `.get("name")` fails.

### How Found
E2E test suite hit the error when the agent searched for existing tickets (SCRUM-1 through SCRUM-4 had no priority set).

### Fix
```python
# WRONG — .get("priority", {}) returns None when value is explicitly null
f.get("priority", {}).get("name", "Unknown")

# CORRECT — (value or {}) handles both None and missing
(f.get("priority") or {}).get("name", "Unknown")
```

### Verification
All 15 E2E scenarios pass. Agent correctly shows "Unknown" priority for tickets without a priority.

### Prevention
Always use the `(value or {})` pattern instead of `.get(key, {})` when the API can return explicit `null` values.

---

## Issue #5: Agent Port Hardcoded to 8001

**Category**: Configuration

### Symptoms
`OSError: [Errno 48] address already in use` when starting agent-backend — port 8001 occupied by platform-health-agent.

### Root Cause
`main.py` had `uvicorn.run(app, host="0.0.0.0", port=8001)` hardcoded. Port 8001 is used by platform-health-agent.

### Fix
Changed to `port=8010` in `main.py`.

### Prevention
Use environment variable for port: `int(os.getenv("PORT", "8010"))`. Document port assignments centrally (SESSION-HANDOFF.md Known Issues).

---

## Issue #6: System Prompt Prevented HITL from Activating

**Category**: HITL / LangGraph

### Symptoms
After adding `interrupt()` to `tool_node`, the agent NEVER triggered an interrupt. It always returned `status: "complete"` even when asked to create tickets or send messages.

### Root Cause
The Phase D system prompt included: *"For ANY write action, you MUST: 1. Present what you plan to do. 2. Ask the user to confirm. 3. Only execute after explicit confirmation."*

The LLM followed this instruction perfectly — it presented a plan and stopped, never calling the write tool. Since `interrupt()` is inside `tool_node`, it only fires when the LLM actually calls a tool. No tool call = no interrupt.

### How Found
Tested HITL flow: `create_ticket` was never in the `tool_calls` list. The response always ended with "Here's my plan... shall I proceed?"

### Fix
Updated system prompt to tell the LLM that write tools have built-in approval:
```
### Write Actions — Proceed With Confidence
- Write tools have a built-in approval system
- When asked to create a ticket, GO AHEAD and call the tool
- The system will automatically pause and ask the user for approval
- You do NOT need to ask for confirmation yourself
```

### Verification
After prompt change, `create_ticket` appears in tool_calls and returns `pending_approval`.

### Prevention
When adding infrastructure-level safety (like HITL `interrupt()`), audit the system prompt for conflicting instructions. Prompt-level "confirm before acting" and graph-level `interrupt()` are mutually exclusive — use one or the other.

---

<!-- Template for new issues:

## Issue #N: [Short Title]

**Category**: [Jira API / Slack API / MCP Server / LangGraph / HITL / Eval / Docker / Config]

### Symptoms
What you observed (error messages, unexpected behaviour).

### Root Cause
Why it happened (the actual bug or misconfiguration).

### How Found
Investigation steps that led to the root cause.

### Fix
```bash
# or python, json, etc.
The exact fix applied.
```

### Verification
How to confirm the fix worked.

### Prevention
What to do differently in the future to avoid this.

---

-->

## Issue #7: Faithfulness Scoring Is Heuristic-Based

### Symptoms
Faithfulness metric varies wildly (0.05 to 1.0) for responses that are clearly correct and well-grounded.

### Root Cause
Word-overlap heuristic doesn't understand semantics. "EKS cluster" and "Elastic Kubernetes Service" are semantically identical but share no words.

### How Found
Observed during eval runner testing — correct RAG responses about EKS architecture scored 0.21 faithfulness despite being accurate.

### Fix
Known limitation. For production, upgrade to:
- LLM-as-judge (call a second LLM to assess grounding)
- RAGAS framework with embedding-based similarity
- DeepEval faithfulness metric

### Prevention
Document as informational metric; rely on tool_accuracy + keyword_coverage + safety for pass/fail decisions.

---

## Issue #8: Topic Filter Misses Semantically Off-Topic Queries

### Symptoms
"Search KB for quantum computing" passes the topic filter because "quantum computing" isn't in the off-topic keyword list.

### Root Cause
Keyword-based topic filtering only catches explicit off-topic signals. Doesn't understand that "quantum computing" is unrelated to platform health.

### How Found
Edge case test `edge-02` — query passed guardrails and hit the agent (11.4s) instead of being blocked instantly.

### Fix
Known limitation. For production, use an LLM classifier or embedding similarity to the domain corpus for topic filtering.

### Prevention
In the current system, the agent correctly reports "no relevant results" — so the failure mode is latency, not incorrect answers.

---

## Issue #9: Weaviate Docker Image Has No curl

### Symptoms
Docker healthcheck `curl -f http://localhost:8080/v1/.well-known/ready` fails. Container marked unhealthy despite Weaviate running fine.

### Root Cause
Weaviate's image is based on Alpine/scratch — `curl` is not installed. The healthcheck command fails with "command not found".

### How Found
`docker compose up -d` reported vectordb as unhealthy. `docker exec project-125-vectordb which curl` returned nothing.

### Fix
```yaml
# docker-compose.yml — use wget instead of curl
healthcheck:
  test: ["CMD-SHELL", "wget -q --spider http://localhost:8080/v1/.well-known/ready"]
```

### Prevention
Always check what tools are available in third-party images before writing healthchecks. Alpine-based images typically have `wget` but not `curl`.

---

## Issue #10: AWS SSO Cache Needs Writable Mount

### Symptoms
`OSError: [Errno 30] Read-only file system: '/root/.aws/sso/cache/tmpr287lh3q.tmp'`

### Root Cause
`~/.aws` was mounted as `:ro` (read-only). AWS SSO refreshes tokens and writes to `sso/cache/` — fails on read-only filesystem.

### Fix
```yaml
volumes:
  - ~/.aws:/root/.aws  # Remove :ro — SSO needs writable cache
```

### Prevention
For AWS profiles using SSO (Identity Center), always mount `~/.aws` read-write. For static access key profiles, `:ro` is fine.

---

## Issue #11: MCP FastMCP.run() API Changed

### Symptoms
`TypeError: FastMCP.run() got an unexpected keyword argument 'host'`

### Root Cause
In newer MCP SDK versions, `host` and `port` are constructor parameters on `FastMCP.__init__()`, not `run()`. The `run()` method only accepts `transport` and `mount_path`.

### Fix
```python
# Set host/port via settings before calling run()
mcp.settings.host = "0.0.0.0"
mcp.settings.port = args.port
mcp.run(transport="streamable-http")
```

### Prevention
Check `inspect.signature(FastMCP.run)` when the MCP SDK version changes.

---

## Issue #12: Weaviate connect_to_local Fails for Docker DNS

### Symptoms
`Connection refused` when agent connects to `vectordb:8080` inside Docker network.

### Root Cause
`weaviate.connect_to_local()` hardcodes gRPC connection to `localhost:50051`. When the hostname is `vectordb` (Docker DNS), gRPC still tries localhost and fails.

### Fix
```python
if host in ("localhost", "127.0.0.1"):
    return weaviate.connect_to_local(host=host, port=port)
else:
    return weaviate.connect_to_custom(
        http_host=host, http_port=port, http_secure=False,
        grpc_host=host, grpc_port=50051, grpc_secure=False,
    )
```

### Prevention
Always use `connect_to_custom()` for non-localhost Weaviate connections. `connect_to_local()` is convenience-only for development.

---

## General Debugging Commands

```bash
# Check all services
docker compose ps

# Agent backend logs
docker compose logs agent-backend --tail 50

# MCP server logs (when running)
docker compose logs jira-mcp --tail 50
docker compose logs slack-mcp --tail 50

# Test agent health
curl http://localhost:8001/health

# Test Jira connectivity
python scripts/jira_test.py

# Test Slack connectivity
python scripts/slack_test.py

# Check Weaviate
curl http://localhost:8080/v1/meta

# Check PostgreSQL
docker compose exec postgres psql -U agent -d agent_db -c "SELECT count(*) FROM conversations;"
```

---

*Created 2026-03-26 — Issues will be added as they occur during development.*
