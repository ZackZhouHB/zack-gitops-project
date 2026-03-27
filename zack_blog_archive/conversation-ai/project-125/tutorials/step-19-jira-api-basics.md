# Step 19: Jira Cloud API — From Zero to Ticket Creation

> **What you'll learn**: How to authenticate with Jira Cloud, create tickets, search with JQL, and update issues — all with plain Python.  
> **Why this matters**: Before building an MCP server or agent tool, you need to understand the raw API. No magic, no frameworks — just HTTP requests.  
> **Time**: ~20 minutes reading + 15 minutes hands-on  
> **Prerequisites**: Jira Cloud free tier set up, API token generated, `.env` configured

---

## 19.1 Why Start with Raw API?

When building agent tools, it's tempting to jump straight to the framework integration. Don't.

```
BAD:  "Let me find a LangChain Jira integration and plug it in"
      → You don't understand what it does, can't debug it, can't extend it

GOOD: "Let me call the Jira API directly, see what it returns, then wrap it"
      → You understand every field, every error, every edge case
```

**The pattern we follow throughout this project:**
1. **Understand the API** (this tutorial) — raw `requests.post()`
2. **Wrap as MCP server** (step 21) — standard protocol layer
3. **Wire into agent** (step 22) — LangGraph tool binding

---

## 19.2 Jira Cloud REST API Basics

### Authentication

Jira Cloud uses **Basic Auth** with your email + API token (not password):

```python
from base64 import b64encode

email = "your.email@example.com"
api_token = "your-api-token"

# Base64 encode "email:token"
token = b64encode(f"{email}:{api_token}".encode()).decode()

headers = {
    "Authorization": f"Basic {token}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}
```

> **Why not OAuth?** For personal/bot access, API tokens are simpler. OAuth is for apps that act on behalf of other users (marketplace apps). For an internal agent, Basic Auth is standard practice.

### Base URL

All API calls go to:
```
https://YOUR-SITE.atlassian.net/rest/api/3/
```

The `/rest/api/3/` is Jira Cloud's current API version. Version 2 still works but v3 uses the new document format (ADF) for rich text.

---

## 19.3 Core Operations

### Operation 1: Create a Ticket

```python
import requests

url = f"{JIRA_URL}/rest/api/3/issue"
payload = {
    "fields": {
        "project": {"key": "PLAT"},          # Your project key
        "summary": "API latency spike",       # Title
        "issuetype": {"name": "Task"},        # Task, Bug, Story, Epic
        "priority": {"name": "Medium"},       # Highest, High, Medium, Low, Lowest
        "labels": ["agent-created", "api"],   # Searchable tags
        "description": {                      # ADF format (Atlassian Document Format)
            "type": "doc",
            "version": 1,
            "content": [{
                "type": "paragraph",
                "content": [{
                    "type": "text",
                    "text": "Your description here."
                }]
            }]
        }
    }
}

resp = requests.post(url, headers=headers, json=payload)
# Returns: {"id": "10001", "key": "PLAT-1", "self": "..."}
```

> **ADF (Atlassian Document Format)**: Jira v3 uses a structured document format instead of plain text or Markdown. It's verbose but powerful — supports headings, lists, code blocks, mentions, and more. For our agent, we'll build a helper that converts plain text to ADF.

### Operation 2: Search with JQL

**JQL (Jira Query Language)** is how you find tickets programmatically:

```python
jql = 'project = PLAT AND status = "Open" AND priority = High ORDER BY created DESC'

resp = requests.get(
    f"{JIRA_URL}/rest/api/3/search",
    headers=headers,
    params={
        "jql": jql,
        "maxResults": 10,
        "fields": "summary,status,priority,labels"
    }
)
# Returns: {"total": 3, "issues": [{"key": "PLAT-1", "fields": {...}}, ...]}
```

**Common JQL patterns for an agent:**
```sql
-- Find duplicates before creating
project = PLAT AND summary ~ "API latency" AND status != Done

-- Recent P1/P2 incidents
project = PLAT AND priority in (Highest, High) AND created >= -7d

-- Agent-created tickets
project = PLAT AND labels = "agent-created"

-- Open tickets for a component
project = PLAT AND component = "API Gateway" AND status != Done
```

> **Why JQL matters for agents**: Before creating a ticket, the agent should ALWAYS search for duplicates. This is the **idempotency** pattern — asking twice shouldn't create two tickets.

### Operation 3: Get Ticket Details

```python
resp = requests.get(
    f"{JIRA_URL}/rest/api/3/issue/PLAT-1",
    headers=headers
)
issue = resp.json()
# issue["fields"]["summary"], issue["fields"]["status"]["name"], etc.
```

### Operation 4: Update a Ticket

```python
# Update fields
resp = requests.put(
    f"{JIRA_URL}/rest/api/3/issue/PLAT-1",
    headers=headers,
    json={
        "fields": {
            "priority": {"name": "High"},
            "labels": ["agent-created", "escalated"]
        }
    }
)
# Returns 204 No Content on success

# Add a comment
resp = requests.post(
    f"{JIRA_URL}/rest/api/3/issue/PLAT-1/comment",
    headers=headers,
    json={
        "body": {
            "type": "doc",
            "version": 1,
            "content": [{
                "type": "paragraph",
                "content": [{
                    "type": "text",
                    "text": "Agent update: KB search found root cause..."
                }]
            }]
        }
    }
)
```

### Operation 5: Transition (Change Status)

Transitions are workflow-specific. You must first list available transitions, then execute one:

```python
# List available transitions
resp = requests.get(
    f"{JIRA_URL}/rest/api/3/issue/PLAT-1/transitions",
    headers=headers
)
transitions = resp.json()["transitions"]
# [{"id": "21", "name": "In Progress"}, {"id": "31", "name": "Done"}]

# Execute transition
resp = requests.post(
    f"{JIRA_URL}/rest/api/3/issue/PLAT-1/transitions",
    headers=headers,
    json={"transition": {"id": "21"}}  # Move to "In Progress"
)
```

---

## 19.4 Error Handling

Jira returns helpful error messages. Common ones:

| Status | Meaning | Agent Should... |
|--------|---------|----------------|
| 400 | Bad request (invalid fields) | Parse error, fix payload, retry |
| 401 | Auth failed | Alert user — token expired or wrong |
| 403 | No permission | Alert user — check project roles |
| 404 | Issue/project not found | Handle gracefully — "Ticket doesn't exist" |
| 429 | Rate limited | Back off and retry (exponential backoff) |

```python
resp = requests.post(url, headers=headers, json=payload)
if resp.status_code == 201:
    return resp.json()  # Success
elif resp.status_code == 400:
    errors = resp.json().get("errors", {})
    # e.g., {"priority": "Priority name 'P2' is not valid"}
    return {"error": "invalid_fields", "details": errors}
elif resp.status_code == 429:
    retry_after = int(resp.headers.get("Retry-After", 60))
    time.sleep(retry_after)
    # Retry...
```

---

## 19.5 Real-World Issues We Hit

### Issue 1: Search Endpoint Migration (HTTP 410)

When we first ran the test, JQL search returned:
```
HTTP 410: "The requested API has been removed. Please migrate to the /rest/api/3/search/jql API."
```

**What happened**: Jira Cloud deprecated `/rest/api/3/search` and migrated to `/rest/api/3/search/jql` in 2026. Many tutorials and Stack Overflow answers still reference the old endpoint.

**Fix**: Change the URL:
```python
# OLD (deprecated, returns 410)
url = f"{JIRA_URL}/rest/api/3/search"

# NEW (current, works)
url = f"{JIRA_URL}/rest/api/3/search/jql"
```

The response format also changed — no longer returns `total` count, uses `isLast` boolean for pagination:
```python
# OLD response: {"total": 42, "issues": [...]}
# NEW response: {"issues": [...], "isLast": true}
total = data.get("total", len(issues))  # Fallback to count
```

> **Lesson**: Always check the Jira Cloud changelog (https://developer.atlassian.com/changelog/) before building integrations. APIs evolve.

### Issue 2: Project Key vs Project Name

We configured `JIRA_PROJECT_KEY=PLAT` because the project was named "PLAT". But:
```
GET /rest/api/3/project → Key: SCRUM, Name: PLAT
```

Jira auto-generates the **key** from the template (Scrum → `SCRUM`), not from the project name. The API uses the key.

**Fix**: Check your actual project key:
```bash
curl -s -u "email:token" https://your-site.atlassian.net/rest/api/3/project | python3 -m json.tool
```

> **Lesson**: Always verify via API. Don't assume the key matches the name.

---

## 19.6 Running the Test Script

We've built a comprehensive test script that exercises all these operations:

```bash
cd project-125

# Install dependencies (if not in a venv)
pip install requests python-dotenv

# Make sure .env has your Jira credentials
cat .env | grep JIRA

# Run the test suite
python scripts/jira_test.py
```

Expected output:
```
══════════════════════════════════════════════════════
  Jira Cloud API Test Suite — Project 125
══════════════════════════════════════════════════════
✅ Config loaded: https://your-site.atlassian.net (your.email@example.com)

── Test 1: Connectivity ──
✅ Connected to: https://your-site.atlassian.net

── Test 2: Get Project (PLAT) ──
✅ Project found: PLAT — Platform Health

── Test 3: Create Ticket ──
✅ Created: PLAT-1
   URL: https://your-site.atlassian.net/browse/PLAT-1

── Test 4: Search (JQL) ──
✅ Found 1 issue(s) matching JQL

── Test 5: Get Ticket (PLAT-1) ──
✅ PLAT-1: [TEST] API latency spike — connection pool exhaustion

── Test 6: Add Comment (PLAT-1) ──
✅ Comment added

── Test 7: Update Ticket (PLAT-1) ──
✅ Updated: priority → High, added 'escalated' label

── Test 8: Transitions (PLAT-1) ──
✅ Transitioned to: In Progress

══════════════════════════════════════════════════════
  ✅ All Jira API tests passed!
══════════════════════════════════════════════════════
```

---

## 19.7 What We Proved

After running `jira_test.py`, you've verified:

| Capability | API Call | Works? |
|-----------|---------|--------|
| Authentication | Basic Auth with API token | ✅ |
| Create ticket | POST /rest/api/3/issue | ✅ |
| Search (JQL) | GET /rest/api/3/search | ✅ |
| Get details | GET /rest/api/3/issue/{key} | ✅ |
| Add comment | POST /rest/api/3/issue/{key}/comment | ✅ |
| Update fields | PUT /rest/api/3/issue/{key} | ✅ |
| Transition status | POST /rest/api/3/issue/{key}/transitions | ✅ |

These are the exact operations our agent will need. In step 21, we'll wrap them in an MCP server. In step 22, the agent will call them as tools.

---

## 19.8 Key Takeaways

1. **Jira v3 API uses ADF** for rich text descriptions — not Markdown, not plain text
2. **JQL is powerful** — use it for duplicate detection before creating tickets
3. **Transitions are workflow-dependent** — list available ones first, then execute
4. **API tokens ≠ passwords** — generated separately, can be revoked, never expire (but should be rotated)
5. **Always check for 429 (rate limit)** — Jira Cloud has per-user rate limits

---

**Next**: [Step 20 — Slack API Basics](step-20-slack-api-basics.md) — same pattern, different API.

*Created 2026-03-26 — Project 125, Phase B*
