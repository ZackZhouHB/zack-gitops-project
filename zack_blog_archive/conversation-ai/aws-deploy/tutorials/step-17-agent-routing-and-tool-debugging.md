# Step 17: Agent Routing, Tool Selection & Debugging

## Why This Matters

When a user asks a question and gets the wrong answer (or no answer), the problem is almost never the LLM itself — it's usually **routing**, **tool selection**, or **data quality**. This tutorial walks through a real debugging session where a simple blog question returned an empty response, and how we traced it through the entire agent pipeline.

---

## 17.1 How the Agent Makes Decisions

The agent is a **state machine** built with LangGraph. Every user message flows through a decision tree:

```
User Message
    ↓
┌─────────┐
│  Router  │ ← LLM reads message + ROUTER_PROMPT
└────┬────┘   Outputs: "general_qa" or "incident_triage"
     │
     ├── general_qa ──→ LLM Node ──→ [has tool calls?]
     │                                  ├── YES → Tool Node → LLM Node → ... (loop)
     │                                  └── NO  → END (final answer)
     │
     └── incident_triage ──→ gather_symptoms → search_docs → [branch]
                                                              ├── known_fix → END
                                                              ├── investigate → END
                                                              └── escalate → END
```

### The Two Paths Explained

**Path 1: general_qa (ReAct Loop)**
- LLM sees the question + available tools (kb_search, create_checklist, escalate, assess_incident)
- LLM decides which tool to call (or answer directly)
- Tool executes, returns results
- LLM sees results, decides: call another tool or give final answer
- This is the **correct path** for most questions

**Path 2: incident_triage (Linear Workflow)**
- Fixed pipeline: gather symptoms → search docs → decide severity → create checklist
- Designed for "my service is down" type problems
- **Wrong path** for general questions, lookups, or "can you check" queries

### The Key Insight

> The router is a **single LLM call** that reads ONLY the user's message and the ROUTER_PROMPT.
> It does NOT search the knowledge base first. It decides the path based purely on the message text.

This means the router prompt is **critical** — a vague prompt causes misrouting.

---

## 17.2 The Real Bug: "Letter to Matilda"

### What Happened

User asked: `"there is a story about a letter to matilda, can you check"`

Expected: Agent searches KB → finds blog post/112 → returns answer with source citation

Actual: Empty response, frontend showed "complete" with nothing displayed

### Step-by-Step Debug Trace

#### Step 1: Check HTTP Response
```bash
curl -v -X POST http://ALB_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "there is a story about a letter to matilda, can you check"}'
```
**Result**: `HTTP 500 Internal Server Error` — backend crashed

#### Step 2: Check Backend Logs
```bash
AWS_PROFILE=sandboxtest aws logs tail /ecs/platform-health/agent-backend --since 5m
```
**First error found**: `ModuleNotFoundError: No module named 'tools.db_tool'`

**Root cause**: `incident_triage.py` imported `tools.db_tool` (the local solution name) instead of `tools.dynamodb_tool` (the AWS name). This file was copied from the local solution but not all imports were updated.

#### Step 3: Fix Imports, Rebuild, Redeploy
Fixed:
- `from tools.db_tool import create_checklist` → `from tools.dynamodb_tool import create_checklist`
- `from tools.rag_tool import rag_search` → `from tools.kb_tool import kb_search`
- `checklist.id` → `checklist.checklist_id` (different field name in AWS version)
- `checklist.total` → `len(checklist.items)` (no `.total` attribute)

#### Step 4: Retest After Fix
```bash
curl -X POST http://ALB_URL/chat -H "Content-Type: application/json" \
  -d '{"message": "there is a story about a letter to matilda, can you check"}'
```
**Result**: Got a response, but it was WRONG — returned an incident triage response about "diagnostic investigation" instead of a blog post answer.

#### Step 5: Check Routing Decision
```bash
aws logs tail /ecs/platform-health/agent-backend --since 5m | grep "Router"
```
**Found**: `Router → incident_triage (raw: incident_triage)`

The router classified "can you check" as an incident report. **This is a routing problem, not a search problem.**

#### Step 6: Check If KB Even Has the Content
```bash
aws bedrock-agent-runtime retrieve --knowledge-base-id II5KAPFHJP \
  --retrieval-query '{"text": "letter to matilda story"}'
```
**Found**: Low scores (0.37), no web results for post/112. The web crawler indexed 64 pages but missed post/112. **This is also a data quality problem.**

#### Step 7: Fix Router Prompt
Changed from vague:
```
1. incident_triage — User reports a problem, error, or unexpected behavior
2. general_qa — General architecture, design, or technical question
```

To explicit:
```
1. incident_triage — User reports a SPECIFIC infrastructure problem, error, outage
   Examples: "our API is returning 500 errors", "the EKS cluster is down"

2. general_qa — EVERYTHING else. Questions, searches, lookups, "can you check"
   When in doubt, choose general_qa.
```

#### Step 8: Rebuild, Push, Redeploy, Retest
After fixing the router prompt and redeploying, the question now routes to `general_qa`, calls `kb_search`, and returns whatever the KB has.

---

## 17.3 Three Layers of Problems (and How to Debug Each)

### Layer 1: Routing — Did the Message Go to the Right Path?

**Symptoms**: Wrong type of response (incident response for a question, or search for an incident)

**How to check**:
```bash
# Check CloudWatch logs for routing decision
aws logs tail /ecs/platform-health/agent-backend --since 5m | grep "Router"
```

**Common fixes**:
- Make router prompt more explicit with examples
- Add "when in doubt, use general_qa" as default
- Check if message wording triggers wrong classification

### Layer 2: Tool Selection — Did the LLM Pick the Right Tool?

**Symptoms**: Right path (general_qa) but wrong tool called, or no tool called

**How to check**:
```bash
# Check tool execution in logs
aws logs tail /ecs/platform-health/agent-backend --since 5m | grep "Tool"
```

In the response JSON:
```json
{
  "tool_calls": [
    {"name": "rag_search", "input": {"query": "..."}, "latency_ms": 338}
  ]
}
```

**Common fixes**:
- Tool descriptions in graph.py determine when LLM picks each tool
- If LLM never calls tools: check that `llm.bind_tools([...])` includes all tools
- If LLM calls wrong tool: improve tool docstrings/descriptions

### Layer 3: Data Quality — Does the KB Have the Right Content?

**Symptoms**: Right tool called but answer is wrong, irrelevant, or low confidence

**How to check**:
```bash
# Direct KB retrieve — bypass the agent entirely
aws bedrock-agent-runtime retrieve --knowledge-base-id II5KAPFHJP \
  --retrieval-query '{"text": "your question here"}' \
  --retrieval-configuration '{"vectorSearchConfiguration": {"numberOfResults": 10}}'
```

**Score interpretation**:
| Score Range | Meaning | Action |
|-------------|---------|--------|
| > 0.6 | Strong match | Content exists, answer should be good |
| 0.4 - 0.6 | Moderate | Content exists but may be partial |
| 0.3 - 0.4 | Weak | Barely relevant, may hallucinate |
| < 0.3 | No match | Content not in KB — check data source sync |

**Common fixes**:
- Document not indexed: check ingestion job status, re-sync
- Low scores: try different query wording, check chunk size settings
- Wrong document returned: chunk overlap or embedding quality issue

---

## 17.4 Debugging Commands Cheat Sheet

### Trace a Question End-to-End
```bash
# 1. Send question and save response
curl -s -X POST http://ALB_URL/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "your question", "session_id": "debug-001"}' > /tmp/response.json

# 2. Check response
python3 -c "
import json
r = json.load(open('/tmp/response.json'))
print('Answer:', r.get('response', 'EMPTY')[:200])
print('Tools:', [t['name'] for t in r.get('tool_calls', [])])
for t in r.get('tool_calls', []):
    for s in t.get('rag_results', []):
        print(f'  Source: {s[\"title\"]} ({s[\"source_type\"]}) score={s[\"score\"]:.1%}')
"

# 3. Check routing decision
aws logs tail /ecs/platform-health/agent-backend --since 2m | grep "Router"

# 4. Check tool execution
aws logs tail /ecs/platform-health/agent-backend --since 2m | grep "Tool"

# 5. Compare with direct KB retrieve
aws bedrock-agent-runtime retrieve --knowledge-base-id II5KAPFHJP \
  --retrieval-query '{"text": "your question"}'

# 6. Check if document exists in source
aws s3 ls s3://platform-health-kb-documents-615299759525/documents/
# or check web crawler indexed pages count
aws bedrock-agent list-ingestion-jobs --knowledge-base-id II5KAPFHJP \
  --data-source-id G0QLXXLD5B --query 'ingestionJobSummaries[0].statistics'
```

### Common Patterns

| User Says | Expected Route | Risk of Misroute |
|-----------|---------------|------------------|
| "What is X?" | general_qa | Low |
| "Tell me about X" | general_qa | Low |
| "Can you check X" | general_qa | **HIGH** — sounds like incident |
| "There is a problem with X" | incident_triage | Low |
| "X is not working" | incident_triage | Low |
| "How does X work" | general_qa | Low |
| "Fix X" | incident_triage | Medium |
| "Is there info about X" | general_qa | Low |

---

## 17.5 The Fix Cycle: Build → Test → Log → Fix → Repeat

Every agent bug follows the same debug loop:

```
1. Reproduce the problem
   └─ curl -X POST /chat with the exact message

2. Check HTTP status
   └─ 500 = code crash, 200 = logic/data problem

3. Read backend logs
   └─ aws logs tail /ecs/platform-health/agent-backend

4. Identify which layer failed
   ├─ Router logs: wrong path?
   ├─ Tool logs: wrong tool or tool error?
   └─ KB retrieve: missing/wrong content?

5. Fix the code
   ├─ prompts.py: routing issues
   ├─ graph.py: tool binding or flow issues
   ├─ tools/*.py: tool execution issues
   └─ Bedrock KB: data source sync issues

6. Rebuild and redeploy
   └─ docker build → tag → push → ecs update-service --force-new-deployment

7. Wait for steady state (60-90s)
   └─ aws ecs describe-services --query 'services[0].events[0].message'

8. Retest
   └─ curl -X POST /chat with the same message

9. Repeat until correct
```

---

## 17.6 Lessons Learned

### 1. Import Names Must Match AWS Versions
When migrating from local to AWS, every `from tools.X import Y` must be updated:
| Local | AWS |
|-------|-----|
| `tools.db_tool` | `tools.dynamodb_tool` |
| `tools.rag_tool` | `tools.kb_tool` |
| `rag_search()` | `kb_search()` |
| `result.id` | `result.checklist_id` |
| `result.total` | `len(result.items)` |

### 2. Router Prompt Defaults Matter
Always make the "safe" path the default. In our case, `general_qa` should be the default because:
- It uses the ReAct loop (LLM decides tools dynamically)
- It can handle ANY question type
- `incident_triage` is a rigid linear pipeline — only appropriate for clear incidents

### 3. Test Each Layer Independently
Don't just test end-to-end. Test:
- KB retrieve directly (bypass agent): Does the content exist?
- Router decision (check logs): Is the path correct?
- Tool execution (check logs): Did the right tool run?
- LLM response quality: Given the right context, is the answer good?

### 4. Frontend Shows Nothing on 500
When the backend returns HTTP 500, the frontend's SSE stream gets no events, so it shows "complete" with an empty response. Always check the HTTP status code first — the frontend hides backend crashes.

### 5. Rolling Deployments Take Time
After `force-new-deployment`, the old task keeps serving for 30-60s while the new task starts and passes health checks. During this window, you might still hit the old (buggy) code. Wait for "steady state" before testing.

---

## 17.7 What's Next

- If routing is wrong → fix `prompts.py` (ROUTER_PROMPT)
- If tool is wrong → fix tool descriptions in `graph.py`
- If content is missing → check data source sync, re-trigger ingestion
- If answer is low quality → improve system prompt or chunk settings
- If frontend shows nothing → check backend logs for 500 errors
