# Troubleshooting Guide — Build, Test, Fix, Retest

> **Purpose:** Document every issue encountered during the build, how it was found,
> the thinking process to diagnose it, and the exact commands used to fix and verify.
>
> This is the most valuable learning resource — real debugging is how engineers grow.

---

## Table of Contents

1. [Debugging Mindset](#1-debugging-mindset)
2. [Testing Methodology](#2-testing-methodology)
3. [Issue Log — Step by Step](#3-issue-log--step-by-step)
4. [Reusable Diagnostic Commands](#4-reusable-diagnostic-commands)
5. [Common Patterns and Anti-Patterns](#5-common-patterns-and-anti-patterns)

---

## 1. Debugging Mindset

Before diving into specific issues, here's the mental model used throughout the build:

### The Debug Loop

```
┌──────────────┐
│  1. BUILD    │  Write code / config
└──────┬───────┘
       ▼
┌──────────────┐
│  2. TEST     │  Run it, observe output
└──────┬───────┘
       ▼
┌──────────────┐     ┌──────────────────────────┐
│  3. OBSERVE  │────▶│  Works? → Commit & move on│
└──────┬───────┘     └──────────────────────────┘
       │ Fails
       ▼
┌──────────────┐
│  4. ISOLATE  │  Narrow down: which layer failed?
└──────┬───────┘
       ▼
┌──────────────┐
│  5. DIAGNOSE │  Read error message, check assumptions
└──────┬───────┘
       ▼
┌──────────────┐
│  6. FIX      │  Smallest change that resolves it
└──────┬───────┘
       ▼
       └──────────▶ Back to step 2 (RETEST)
```

### Key Principles

| Principle | What It Means |
|-----------|---------------|
| **Test one thing at a time** | Don't change 3 things then test. Change 1, test, repeat. |
| **Read the error message** | 80% of bugs tell you exactly what's wrong in the error text. |
| **Isolate the layer** | Is it network? Config? Code? API? Test each independently. |
| **Test outside the stack first** | Before testing in Docker, test locally. Before testing via API, test the function directly. |
| **Check your assumptions** | "I assumed the schema had `source_url`" — it didn't. Always verify. |

---

## 2. Testing Methodology

### How Each Step Was Tested

For every build step, I followed this pattern:

```
1. Write the code
2. Test the smallest unit first (a single function)
3. Test the integration (function + dependencies)
4. Test via the API (curl to the endpoint)
5. Verify side effects (check the database, check Weaviate)
```

### Example: Testing the RAG Tool

```bash
# Level 1: Can I connect to Weaviate?
python3 -c "
import weaviate
client = weaviate.connect_to_local(host='localhost', port=8080)
print(client.is_ready())
client.close()
"

# Level 2: Can I embed a query?
python3 -c "
import boto3, json
bedrock = boto3.Session(profile_name='sandboxtest').client('bedrock-runtime', region_name='ap-southeast-2')
body = json.dumps({'inputText': 'test', 'dimensions': 1024, 'normalize': True})
resp = bedrock.invoke_model(modelId='amazon.titan-embed-text-v2:0', body=body)
vec = json.loads(resp['body'].read())['embedding']
print(f'Embedding dimensions: {len(vec)}')
"

# Level 3: Can I search Weaviate with a vector?
# (combines level 1 + 2)

# Level 4: Does the rag_search() function work end-to-end?
python3 -c "
import asyncio
from tools.rag_tool import rag_search
result = asyncio.run(rag_search('How does RAG work?'))
print(f'Results: {len(result.results)}')
"

# Level 5: Does it work via the API?
curl -X POST http://localhost:8001/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "How does RAG work with Bedrock?"}'
```

**Why this order matters:** If Level 4 fails, you already know Levels 1-3 work, so the bug must be in the `rag_search()` function itself — not in Weaviate or Bedrock.

---

## 3. Issue Log — Step by Step

### Step 1: Infrastructure

#### Issue 1.1: Port 8000 Already in Use

**Symptom:** Docker Compose failed to start the agent backend.

**How I found it:**
```bash
docker compose up -d
# Error: port 8000 already allocated
```

**Diagnosis:**
```bash
lsof -i :8000
# Found: django-blog process using port 8000
```

**Thinking:** The default FastAPI port (8000) conflicts with an existing service. Rather than kill the other service, change our port.

**Fix:** Changed `docker-compose.yml` and all references from 8000 → 8001.

**Retest:**
```bash
docker compose up -d
curl http://localhost:8001/health
# {"status": "healthy"}  ✅
```

---

#### Issue 1.2: Docker Compose `version` Attribute Warning

**Symptom:** Warning message on every `docker compose` command:
```
WARN[0000] docker-compose.yml: `version` is obsolete
```

**Diagnosis:** Docker Compose v2+ deprecated the top-level `version` field. It's harmless but noisy.

**Fix:** Removed `version: "3.8"` from the top of `docker-compose.yml`.

**Lesson:** Warnings aren't errors, but they clutter output and hide real problems. Fix them.

---

#### Issue 1.3: PostgreSQL init.sql Only Runs Once

**Symptom:** After deleting and recreating tables manually, they didn't come back on restart.

**Diagnosis:** Docker's entrypoint for PostgreSQL only runs `init.sql` when the data volume is empty (first start). If `./data/postgres/` exists, the init script is skipped.

**Workaround:**
```bash
# Nuclear option: delete the data and restart
docker compose down -v   # -v removes volumes
docker compose up -d     # Fresh start, init.sql runs again

# Gentle option: run the SQL manually
docker exec -i teacher-accreditation-agent-postgres-1 \
  psql -U agent -d agent_db < agent-backend/init.sql
```

**Lesson:** Know the lifecycle of your init scripts. Docker init = first boot only.

---

### Step 2: Data Ingestion

#### Issue 2.1: `python -m ingestion` — No `__main__.py`

**Symptom:**
```
No module named ingestion.__main__; 'ingestion' is a package and cannot be directly executed
```

**Diagnosis:** Python's `-m` flag expects a `__main__.py` file in the package. We had `__init__.py` with a `main()` function but no `__main__.py`.

**Fix:** Created `ingestion/__main__.py`:
```python
"""Allow running: python -m ingestion"""
from ingestion import main
main()
```

**Lesson:** The `-m` module execution mechanism requires `__main__.py`. This is a Python packaging rule, not obvious if you're new to it.

---

#### Issue 2.2: Weaviate Hostname Resolution — `vectordb` Not Found

**Symptom:**
```
weaviate.exceptions.WeaviateConnectionError: Connection to Weaviate failed.
Error: [Errno 8] nodename nor servname provided, or not known.
Is Weaviate running and reachable at http://vectordb:8080?
```

**How I found it:** Ran `python -m ingestion` from the host machine (not inside Docker).

**Diagnosis:** The `.env` file had `WEAVIATE_URL=http://vectordb:8080`. The hostname `vectordb` is a Docker internal DNS name — it only resolves inside the Docker network. Running Python locally on the host, it can't resolve `vectordb`.

**Thinking process:**
1. Error says "nodename nor servname" → DNS resolution failure
2. `vectordb` is the Docker Compose service name → only works inside Docker
3. When running locally, need `localhost` instead

**Fix:** Updated `weaviate_store.py` to detect and remap Docker hostnames:
```python
def get_client():
    host = WEAVIATE_URL.replace("http://", "").split(":")[0]
    if host in ("vectordb", "localhost", "127.0.0.1"):
        host = "localhost"
    return weaviate.connect_to_local(host=host, port=port)
```

**Retest:**
```bash
python -m ingestion
# ✅ Created collection 'DocumentChunk'
# ✅ Loaded 24 documents, 198 chunks
```

**Lesson:** Docker service names only work inside the Docker network. When developing locally outside Docker, always resolve to `localhost`. A good pattern: have the code detect and remap.

---

#### Issue 2.3: PyPDF2 Not Installed

**Symptom:** Would have failed when trying to load PDF files.

**How I found it:** Pre-emptive — checked `requirements.txt` before running and noticed PyPDF2 was missing.

**Fix:** Added `PyPDF2>=3.0.0` to `requirements.txt`.

**Lesson:** Trace your imports. Every `import` in your code needs a matching line in `requirements.txt`.

---

#### Issue 2.4: pip Blocked by PEP 668 (Externally Managed Python)

**Symptom:**
```
error: externally-managed-environment
This environment is externally managed
```

**Diagnosis:** macOS Homebrew Python (3.12+) blocks system-wide pip installs to prevent breaking the OS Python.

**Fix:** Created a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Lesson:** Always use virtual environments. Never `pip install` into system Python.

---

### Step 3: RAG Tool

#### Issue 3.1: Weaviate Schema Mismatch — `source_url` Not Found

**Symptom:**
```
WeaviateQueryError: no such prop with name 'source_url' found in class 'DocumentChunk'
```

**How I found it:** RAG search returned 0 results. Tested the function directly, got a GRPC error.

**Diagnosis process:**
```bash
# Step 1: Does the collection exist and have data?
python3 -c "
import weaviate
client = weaviate.connect_to_local(host='localhost', port=8080)
col = client.collections.get('DocumentChunk')
print(col.aggregate.over_all(total_count=True).total_count)
# Output: 198  ← Data exists, so the issue is in the query
"

# Step 2: What properties does the schema actually have?
python3 -c "
config = col.config.get()
for p in config.properties:
    print(f'{p.name}: {p.data_type}')
"
# Output:
#   content: TEXT
#   title: TEXT
#   source: TEXT       ← NOT 'source_url'!
#   url: TEXT           ← NOT 'source_url'!
#   source_type: TEXT
#   chunk_index: INT
```

**Root cause:** I wrote the RAG tool assuming the property was called `source_url`, but the ingestion code created separate `source` and `url` properties.

**Thinking:** The error message was very specific — "no such prop with name 'source_url'". Once I listed the actual schema, the fix was obvious.

**Fix:** Changed `return_properties` in the query from `"source_url"` to `"source"` and `"url"` separately. Updated the result formatting to match.

**Retest:**
```bash
python3 -c "
import asyncio
from tools.rag_tool import rag_search
result = asyncio.run(rag_search('How does RAG work?'))
print(f'Results: {len(result.results)}, Latency: {result.latency_ms}ms')
"
# ✅ Results: 5, Latency: 754ms
```

**Lesson:** Never assume schema field names. Always verify with `col.config.get()`. The ingestion code and the query code must agree on property names — this is a contract.

---

#### Issue 3.2: `local_file` Count Showing 0

**Symptom:** After ingestion, queried counts by source_type:
```
blog: 60
confluence: 30
local_file: 0    ← Expected ~100+
```

**Diagnosis:**
```python
# Check what source_type values actually exist
for st in ['local_file', 'local', 'pdf', 'file', 'markdown']:
    r = col.aggregate.over_all(total_count=True,
        filters=Filter.by_property('source_type').equal(st))
    print(f'{st}: {r.total_count}')
# Output:
#   local_file: 0
#   file: 108  ← Found them!
```

**Root cause:** The loader code used `source_type='file'`, not `'local_file'`. The query used `'local_file'`. Mismatch.

**Impact:** Cosmetic only — data was there, just labelled differently. Total was correct (60 + 30 + 108 = 198).

**Lesson:** When counts don't add up, check the actual values in the data. Don't trust your assumptions about enum/category values.

---

### Step 4: Basic Agent (LangGraph)

#### Issue 4.1: AWS Bedrock Model ID Requires Inference Profile Prefix

**Symptom:** (From earlier testing, before the agent build)
```
ValidationException: Could not resolve the foundation model from the provided model identifier.
```

**Diagnosis:** Direct model ID `anthropic.claude-sonnet-4-20250514-v1:0` doesn't work. AWS Bedrock in ap-southeast-2 requires a regional inference profile prefix.

**How I found the correct ID:**
```bash
aws bedrock list-inference-profiles --profile sandboxtest \
  --query "InferenceProfileSummaries[?contains(InferenceProfileName,'claude')].InferenceProfileId" \
  --output text
# Output: apac.anthropic.claude-sonnet-4-20250514-v1:0
```

**Fix:** Set `BEDROCK_MODEL_ID=apac.anthropic.claude-sonnet-4-20250514-v1:0` in `.env`.

**Key insight:** Embeddings (Titan) work with direct model ID. LLMs (Claude) need the inference profile prefix. This inconsistency is an AWS quirk.

---

#### Issue 4.2: Server Dies Between Tests

**Symptom:** `curl` to localhost:8001 returned exit code 7 (connection refused).

**Diagnosis:**
```bash
curl -s http://localhost:8001/health
# exit code 7 = connection refused

# Check if process is running
lsof -ti :8001
# Nothing — server died
```

**Root cause:** The background `nohup` process was started in a subshell that exited. The `&` background process was killed when the parent shell closed.

**Fix:** Restart the server and verify:
```bash
cd agent-backend && source ../.venv/bin/activate
AWS_PROFILE=sandboxtest nohup uvicorn main:app --host 0.0.0.0 --port 8001 > /tmp/agent-server.log 2>&1 &
sleep 4 && curl -s http://localhost:8001/health
```

**Prevention:** Always verify the server is alive before running API tests. Check with `curl /health` first.

---

### Step 5: Multi-Tool Agent

#### Issue 5.1: Checklist Not Saving to PostgreSQL

**Symptom:** Claude called `create_checklist`, returned a response, but the `checklists` table was empty.

**Diagnosis:**
```python
# Check existing table schema
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='checklists'")
# Output:
#   id: uuid         ← Not TEXT!
#   trace_id: uuid   ← Has FK constraint
#   title: text
#   checklist_type: text  ← Required, but we weren't setting it
```

**Root cause:** The `db_tool.py` tried to create its own `checklists` table with a different schema (TEXT id, JSONB items), but the table already existed from `init.sql` with UUID types and different columns. The INSERT silently failed due to type mismatch.

**Fix:** Rewrote `db_tool.py` to work with the existing schema:
```python
# Use UUID for id, set checklist_type, use checklist_items table for items
cur.execute(
    "INSERT INTO checklists (id, title, checklist_type) VALUES (%s::uuid, %s, %s)",
    (checklist_id, title, "accreditation"),
)
```

**Retest:**
```python
cur.execute('SELECT id, title FROM checklists')
# ✅ ('080c80ea-...', 'Provisional Accreditation Checklist')
```

**Lesson:** When you have an existing schema (from init.sql), your code MUST match it. Don't assume you can CREATE TABLE — check what's already there first.

---

### Step 6: Eligibility Workflow (now Incident Triage)

#### Issue 6.1: Router Misclassifying Questions

**Symptom:** Eligibility question went to `general_qa` instead of `eligibility_check`.

**How I found it:** The API response showed `rag_search` tool calls instead of `check_eligibility`, and `workflow_status` was `in_progress` instead of `completed`.

**Diagnosis:** Tested the router function directly:
```python
# Isolate the router — test it independently from the graph
result = await router_node({
    'messages': [HumanMessage(content='Am I eligible?')],
    'current_workflow': 'general_qa',
})
print(result)  # {'current_workflow': 'eligibility_check'}  ← Works!
```

**Root cause:** It was actually a stale server issue — the old code was still running. The router worked correctly in isolation.

**Fix:** Kill old server, restart fresh:
```bash
lsof -ti :8001 | xargs kill
# Restart server
```

**Lesson:** When testing via API, make sure the server is running your LATEST code. With `uvicorn --reload` it auto-reloads, but `nohup` processes don't.

---

### Reskin: Platform Health Insight

#### Issue R.1: No Code Bugs — But Wrong Domain

**Symptom:** The agent worked perfectly but answered "Based on NESA guidelines..." for infrastructure questions. The data was about EventBridge and Terraform, but the prompts were about teacher accreditation.

**This isn't a bug — it's a design mismatch.** The same realization you had: the data doesn't match the domain.

**Fix:** Reskinned prompts, tools, and workflows. The architecture stayed identical.

**Lesson:** Domain-specific prompts matter enormously. The same RAG pipeline + agent architecture produces very different results depending on the system prompt and tool descriptions. Always align your prompts with your actual data.

---

## 4. Reusable Diagnostic Commands

### Check if Services Are Running

```bash
# Docker containers
docker compose ps

# Specific port
lsof -ti :8001      # What's on port 8001?
curl -s http://localhost:8001/health   # Is the API alive?
curl -s http://localhost:8080/v1/.well-known/ready  # Is Weaviate ready?
```

### Inspect Weaviate

```python
import weaviate
client = weaviate.connect_to_local(host='localhost', port=8080)

# Total chunks
col = client.collections.get('DocumentChunk')
print(col.aggregate.over_all(total_count=True).total_count)

# Schema properties
config = col.config.get()
for p in config.properties:
    print(f'{p.name}: {p.data_type}')

# Count by source type
from weaviate.classes.query import Filter
for src in ['blog', 'confluence', 'file']:
    r = col.aggregate.over_all(total_count=True,
        filters=Filter.by_property('source_type').equal(src))
    print(f'{src}: {r.total_count}')

# Test a search
results = col.query.near_vector(near_vector=your_vector, limit=3,
    return_properties=['title', 'source_type'])

client.close()  # Always close!
```

### Inspect PostgreSQL

```python
import psycopg2
conn = psycopg2.connect(host='localhost', port=5432, user='agent', password='agent', dbname='agent_db')
cur = conn.cursor()

# List all tables
cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
print([r[0] for r in cur.fetchall()])

# Check a table's schema
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='checklists'")
for r in cur.fetchall():
    print(f'  {r[0]}: {r[1]}')

# Check data
cur.execute('SELECT id, title FROM checklists')
for r in cur.fetchall():
    print(r)

conn.close()
```

### Test a Tool in Isolation

```python
# Always test tools OUTSIDE the graph first
import asyncio, sys
sys.path.insert(0, '.')

# Test RAG
from tools.rag_tool import rag_search
result = asyncio.run(rag_search('EventBridge schedule'))
print(f'Results: {len(result.results)}, Success: {result.success}')

# Test incident assessment
from tools.incident_tool import assess_incident
result = asyncio.run(assess_incident('Lambda', 'timeout after 3 seconds'))
print(f'Known: {result.known_pattern}, Confidence: {result.confidence}')
```

### Test the Graph Without the API

```python
from agent.graph import create_agent_graph
from langchain_core.messages import HumanMessage, AIMessage

graph = create_agent_graph()
result = asyncio.run(graph.ainvoke({
    'messages': [HumanMessage(content='your question here')],
    'current_workflow': 'general_qa',
    'workflow_step': 0, 'workflow_status': 'in_progress',
    'workflow_data': {}, 'incident_result': {},
    'tool_calls_log': [], 'iteration_count': 0,
}))

# Inspect result
print(f'Workflow: {result["current_workflow"]}')
print(f'Tools: {len(result["tool_calls_log"])}')
for msg in reversed(result['messages']):
    if isinstance(msg, AIMessage) and msg.content:
        print(msg.content[:300])
        break
```

### Test via API (curl)

```bash
# Health check
curl -s http://localhost:8001/health | python3 -m json.tool

# Chat
curl -s -X POST http://localhost:8001/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "How does EventBridge work?"}' | python3 -m json.tool

# Parse specific fields
curl -s -X POST http://localhost:8001/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "test"}' \
  | python3 -c "
import sys,json; d=json.load(sys.stdin)
print(f'Tools: {len(d[\"tool_calls\"])}')
print(f'Response: {d[\"response\"][:200]}')
"
```

### Check Server Logs

```bash
# If using nohup
tail -20 /tmp/agent-server.log

# If using uvicorn directly
# Logs appear in the terminal
```

---

## 5. Common Patterns and Anti-Patterns

### ✅ Good Patterns

| Pattern | Example |
|---------|---------|
| **Test smallest unit first** | Test `_embed_query()` before testing `rag_search()` |
| **Isolate failures** | If API returns empty, test the graph directly. If graph works, the bug is in the API layer. |
| **Read the error message** | `no such prop with name 'source_url'` tells you exactly what's wrong |
| **Check the schema** | Always verify DB/Weaviate schema matches your code's expectations |
| **Kill and restart** | When API behavior is stale, kill the server process and restart fresh |
| **Verify side effects** | After "create checklist", query PostgreSQL to confirm it's actually there |
| **Use `python3 -c`** | Quick inline tests without creating test files |

### ❌ Anti-Patterns

| Anti-Pattern | Why It's Bad |
|--------------|-------------|
| **Testing via API first** | If it fails, you don't know which layer broke (API? Graph? Tool? DB?) |
| **Changing multiple things** | If you change the tool + the graph + the schema, which fix actually worked? |
| **Ignoring warnings** | The Docker Compose version warning was harmless; a Weaviate deprecation warning about `vectorizer_config` could cause future breakage |
| **Assuming schema matches** | The #1 bug source was schema mismatches (source_url vs source/url, checklist UUID vs TEXT) |
| **Not closing connections** | Weaviate and PostgreSQL connections that aren't closed cause resource warnings and potential leaks |
| **Using stale server** | `nohup` processes don't auto-reload. Always restart after code changes. |

---

## Summary: The Most Important Debugging Skill

> **Isolate the layer, then fix the smallest thing.**

When something fails, ask: **Which layer broke?**

```
User → API → Graph → Router → Tool → External Service (Bedrock/Weaviate/PostgreSQL)
```

Test from right to left:
1. Can I reach Weaviate/PostgreSQL/Bedrock directly? (External)
2. Does the tool function work by itself? (Tool)
3. Does the graph work without the API? (Graph)
4. Does the API endpoint work? (API)

The answer is always in the **first layer that fails**.

---

## 6. Streaming UX Issues (Milestone 5)

These issues were encountered while implementing SSE streaming, source citations, and timing display.

### Issue 12: Router Tokens Leaking Into Stream

**Symptom:** When testing `/chat/stream`, the first tokens received were `general` and `_qa` — the router's classification output, not the actual answer.

```
data: {"step": "token", "content": [{"type": "text", "text": "general", "index": 0}]}
data: {"step": "token", "content": [{"type": "text", "text": "_qa", "index": 0}]}
```

**Root Cause:** `astream_events` streams ALL `on_chat_model_stream` events from every node in the graph. The router node calls the LLM to classify intent, and those tokens were being forwarded to the client.

**How Found:** Tested with `curl -s -N` and examined the first few SSE events. The content "general_qa" was clearly the router's output, not an answer.

**Fix:** Filter events by `langgraph_node` metadata:
```python
node = event.get("metadata", {}).get("langgraph_node", "")
if node in ("router", "gather_symptoms", "search_docs"):
    continue  # Skip non-answer nodes
```

**Diagnostic Command:**
```bash
# Debug which nodes produce which events
python3 -c "
async for event in graph.astream_events(state, config, version='v2'):
    kind = event.get('event', '')
    node = event.get('metadata', {}).get('langgraph_node', '')
    print(f'{kind} | node={node}')
"
```

**Lesson:** When streaming LangGraph graphs, ALWAYS check which node produced the event. Multi-node graphs have multiple LLM calls, and you only want to stream the final answer.

---

### Issue 13: `response.content` Is a List, Not a String

**Symptom:** `AttributeError: 'list' object has no attribute 'strip'` in `router_node` at line 411.

```python
workflow = response.content.strip().lower()  # CRASH — content is a list!
```

**Root Cause:** When using `astream_events`, the Bedrock Converse API returns content as a list of content blocks:
```python
[{"type": "text", "text": "general_qa", "index": 0}]
```
Instead of a plain string `"general_qa"`. This is a Bedrock Converse API behavior — it returns structured content blocks.

**How Found:** Server crash immediately on first streaming request. The traceback pointed directly to `response.content.strip()`.

**Fix:** Handle both formats everywhere content is used:
```python
raw = response.content
if isinstance(raw, list):
    raw = "".join(
        block.get("text", "") if isinstance(block, dict) else str(block)
        for block in raw
    )
workflow = raw.strip().lower()
```

**Files affected:** 3 places needed the same fix:
1. `agent/graph.py` — `router_node()` (classification)
2. `agent/graph.py` — `router_node()` logger lines
3. `agent/workflows/incident_triage.py` — `_call_llm()` return value

**Lesson:** When using AWS Bedrock Converse with LangChain, ALWAYS check if `response.content` is `str` or `list`. The format can change depending on whether you're using `invoke()` vs `ainvoke()` vs streaming. Defensive coding: always normalize.

---

### Issue 14: No Tool Events in Streaming (on_tool_start Never Fired)

**Symptom:** Streaming worked for tokens but `tool_start` and `tool_end` events never appeared. The frontend showed no "🔧 Calling rag_search..." indicator.

**Root Cause:** Our tools are custom async functions called manually in `tool_node`, not LangChain-native tools (decorated with `@tool`). LangGraph only emits `on_tool_start`/`on_tool_end` for native LangChain tools.

**How Found:** Dumped all unique event types:
```python
seen = set()
async for event in graph.astream_events(state, config, version='v2'):
    kind = event.get('event', '')
    node = event.get('metadata', {}).get('langgraph_node', '')
    key = (kind, node)
    if key not in seen:
        seen.add(key)
        print(f'{kind} | node={node}')
```
Output showed `on_chain_start | node=tools` and `on_chain_end | node=tools` but NO `on_tool_start` events.

**Fix:** Use `on_chain_start`/`on_chain_end` for the "tools" node instead:
```python
if kind == "on_chain_start" and node == "tools":
    yield tool_start event
elif kind == "on_chain_end" and node == "tools":
    # Extract sources from tool_calls_log in output
    output = event.get("data", {}).get("output", {})
    tool_log = output.get("tool_calls_log", [])
```

**Lesson:** LangGraph event types depend on HOW tools are implemented. Custom functions → chain events. Native LangChain tools → tool events. Always dump actual events before writing event handlers.

---

### Issue 15: Sources Not Appearing in Stream

**Symptom:** After fixing tool events, the `sources` SSE event was emitted but always empty `[]`.

**Root Cause:** Initial approach tried to parse source lines from raw tool output text (fragile regex on `[Source 1: Title (type) — relevance: 0.53]`). But the `on_chain_end` event for the tools node includes the node's return dict, which has `tool_calls_log` with structured `rag_results`.

**Fix:** Extract sources from the structured output instead of parsing text:
```python
elif kind == "on_chain_end" and node == "tools":
    output = event.get("data", {}).get("output", {})
    tool_log = output.get("tool_calls_log", []) if isinstance(output, dict) else []
    for tc in tool_log:
        if tc.get("name") == "rag_search" and "rag_results" in tc:
            for r in tc["rag_results"]:
                all_sources.append({...})
```

**Lesson:** Always prefer structured data over text parsing. The tool_calls_log was already designed to carry rag_results — use it instead of regex.

---

### Debugging Commands Added

```bash
# Test streaming with curl (tokens appear in real-time)
curl -s -N -X POST http://localhost:8001/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"What is Weaviate?"}' | head -30

# Filter for specific event types
curl -s -N -X POST http://localhost:8001/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"test"}' | grep -E "(tool_|sources|complete)"

# Check server logs for errors after streaming request
tail -20 /tmp/agent-server.log

# Kill and restart backend after code changes
lsof -ti :8001  # find PID
kill <PID>
cd agent-backend && AWS_PROFILE=sandboxtest uvicorn main:app --port 8001
```
