# Tutorial Step 5: Multi-Tool Agent — Giving Claude a Toolbox

> **Goal:** Understand how our agent uses multiple tools and how Claude decides which ones to call  
> **Time:** ~20 minutes  
> **Prerequisites:** Steps 1–4 completed, basic Python familiarity  

---

## What We're Building in This Step

So far, you might have seen AI chatbots that just answer questions from text. Our agent is different — it can **do things**. It has four tools it can use, and it decides *on its own* which tool(s) to call based on what the user asks.

Think of it like giving a new employee a desk with four drawers:

```
┌─────────────────────────────────────────────────────┐
│              Claude's Toolbox (4 Tools)              │
│                                                     │
│  🔍 rag_search         → Search policy documents    │
│  ✅ check_eligibility  → Run eligibility rules      │
│  📋 create_checklist   → Save a to-do list to DB    │
│  🚨 escalate_to_human  → Hand off to a real person  │
│                                                     │
│  Claude reads the user's question, then CHOOSES     │
│  which drawer(s) to open. No human tells it which.  │
└─────────────────────────────────────────────────────┘
```

This is what **"multi-tool"** means: the agent has access to multiple capabilities and **autonomously** selects which to use. That's the core of what makes it an "agent" rather than just a chatbot.

---

## Key Concepts (Explained for Beginners)

### What Is a "Tool" in AI Terms?

A tool is just a Python function that the LLM can ask to run. The LLM doesn't execute Python directly — instead it says *"I want to call `rag_search` with query='NSW requirements'"* and our code actually runs the function, then feeds the result back to the LLM.

```
User: "What are the requirements for Provisional accreditation?"
  │
  ▼
Claude thinks: "This is a factual question → I should search the knowledge base"
  │
  ▼
Claude outputs: tool_call(name="rag_search", args={"query": "Provisional accreditation requirements"})
  │
  ▼
Our Python code: runs rag_search("Provisional accreditation requirements")
  │
  ▼
Result sent back to Claude → Claude writes a human-friendly answer
```

### Why Multi-Tool Matters (Agent Autonomy)

A single-tool agent is like a calculator — useful, but limited. A multi-tool agent is like an assistant who can search files, check databases, create documents, and call for help. The **autonomy** part is key:

- **Without autonomy:** The programmer hard-codes "if user says X, call tool Y"
- **With autonomy:** The LLM reads the question and *decides* which tool fits best

This means the agent can handle questions it was never explicitly programmed for, as long as the right tool exists.

### How Does Claude Know What Tools Exist?

We send Claude a **JSON schema** describing each tool — its name, what it does, and what parameters it expects. Claude reads this like a menu at a restaurant. It knows the options, picks what it needs, and fills in the parameters.

---

## Tool Definitions — The Menu Claude Reads

All four tool definitions live in `agent/graph.py` in a list called `TOOLS`. Each tool follows the same JSON structure. Let's walk through each one.

### Tool 1: `rag_search` — Search the Knowledge Base

```python
# From agent/graph.py — TOOLS list
{
    "type": "function",
    "function": {
        "name": "rag_search",                      # What Claude calls this tool
        "description": (
            "Search the knowledge base for relevant documents about accreditation, "
            "policies, technical documentation, blog posts, and Confluence pages. "
            "Use this whenever the user asks a factual question."
            # ↑ This description is CRITICAL. Claude reads it to decide when to use
            #   this tool. If the description said "search for recipes", Claude would
            #   never use it for accreditation questions.
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query — rephrase the user's question for optimal retrieval",
                    # ↑ Telling Claude to REPHRASE is a subtle prompt engineering trick.
                    #   Users write messy queries; Claude rewrites them to get better search results.
                },
                "top_k": {
                    "type": "integer",
                    "description": "Number of results to return (default 5)",
                    "default": 5,       # Claude can override this, but usually doesn't
                },
            },
            "required": ["query"],      # Must provide a query; top_k is optional
        },
    },
},
```

**When Claude uses this:** Any factual question — "What documents do I need?", "How does maintenance work?", "What is NESA?"

### Tool 2: `check_eligibility` — Run Business Rules

```python
{
    "type": "function",
    "function": {
        "name": "check_eligibility",
        "description": (
            "Check if a teacher is eligible for a specific accreditation level "
            "based on their qualification and jurisdiction. Use when a user asks "
            "about eligibility or whether they qualify."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "qualification": {
                    "type": "string",
                    "description": "The teacher's qualification, e.g. 'Bachelor of Education'",
                },
                "jurisdiction": {
                    "type": "string",
                    "description": "Where the qualification was obtained, e.g. 'NSW', 'UK'",
                    "default": "NSW",
                    # ↑ Smart default — most users are in NSW, so if they don't mention
                    #   a state, we assume NSW rather than failing
                },
                "accreditation_level": {
                    "type": "string",
                    "description": "Target level: Provisional, Proficient, Highly Accomplished, or Lead",
                    "default": "Provisional",
                },
            },
            "required": ["qualification"],  # Only qualification is required
        },
    },
},
```

**When Claude uses this:** "Am I eligible with a Bachelor of Education?", "Do I qualify for Proficient?"

### Tool 3: `create_checklist` — Save a To-Do List

```python
{
    "type": "function",
    "function": {
        "name": "create_checklist",
        "description": (
            "Create a checklist to track accreditation requirements. "
            "Use when a user needs a step-by-step list of things to complete."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Name of the checklist, e.g. 'Provisional Accreditation Checklist'",
                },
                "items": {
                    "type": "array",           # An array of strings
                    "items": {"type": "string"},
                    "description": "List of requirement descriptions to track",
                },
            },
            "required": ["title", "items"],
        },
    },
},
```

**When Claude uses this:** "Can you give me a checklist for Proficient accreditation?", "What are the steps I need to complete?"

**This tool is special** — it's a *write* operation. It creates a real record in PostgreSQL that the user can come back to later. The agent isn't just answering questions; it's taking action.

### Tool 4: `escalate_to_human` — Know When to Stop

```python
{
    "type": "function",
    "function": {
        "name": "escalate_to_human",
        "description": (
            "Escalate the conversation to a human reviewer when you cannot "
            "confidently answer, the user requests a human, or the situation "
            "requires human judgement."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Why this needs human review",
                },
                "conversation_summary": {
                    "type": "string",
                    "description": "Brief summary of the conversation so far",
                    # ↑ Claude writes this summary itself — the LLM generates a recap
                    #   of the conversation for the human reviewer to read
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],  # Restricted to these 3 values
                    "description": "Urgency level",
                    "default": "medium",
                },
            },
            "required": ["reason", "conversation_summary"],
        },
    },
},
```

**When Claude uses this:** "I want to talk to a person", unusual edge cases, or when the agent's confidence is too low.

**Why this matters for production:** A good agent knows its limits. Saying "I don't know, let me connect you with a human" is infinitely better than confidently giving wrong information about accreditation requirements.

---

## The Tool Dispatch — `execute_tool()`

When Claude says "I want to call tool X with arguments Y," our code needs to actually run the right Python function. That's what `execute_tool()` does in `agent/graph.py`:

```python
# From agent/graph.py
async def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name and return the result as a string."""

    # Each tool name maps to a specific Python function
    if name == "rag_search":
        from tools.rag_tool import rag_search, format_context_for_llm
        result = await rag_search(
            query=args.get("query", ""),       # Pull "query" from Claude's args
            top_k=args.get("top_k", 5),        # Pull "top_k" with default of 5
        )
        # If search found results, format them nicely for the LLM to read
        if result.success and result.results:
            return format_context_for_llm(result)
        return result.message                   # Otherwise return error/empty message

    elif name == "check_eligibility":
        from tools.policy_tool import check_eligibility
        result = await check_eligibility(
            qualification=args.get("qualification", ""),
            jurisdiction=args.get("jurisdiction", "NSW"),
            accreditation_level=args.get("accreditation_level", "Provisional"),
        )
        return result.model_dump_json(indent=2)  # Convert Pydantic model → JSON string

    elif name == "create_checklist":
        from tools.db_tool import create_checklist
        result = await create_checklist(
            title=args.get("title", "Untitled Checklist"),
            items=args.get("items", []),
        )
        return result.model_dump_json(indent=2)

    elif name == "escalate_to_human":
        from tools.escalation_tool import escalate
        result = await escalate(
            reason=args.get("reason", ""),
            conversation_summary=args.get("conversation_summary", ""),
            priority=args.get("priority", "medium"),
        )
        return result.model_dump_json(indent=2)

    return f"Unknown tool: {name}"  # Safety net — shouldn't happen
```

**Pattern to notice:** This is a simple **dispatch pattern** (also called a router). It's like a switchboard operator — the call comes in with a name, and the operator connects it to the right department.

```
Claude says: "call check_eligibility"
                    │
execute_tool() ─────┤
                    │
    if "rag_search"?        → No, skip
    elif "check_eligibility"? → YES! Run check_eligibility()
    elif "create_checklist"?  → Not reached
    elif "escalate_to_human"? → Not reached
```

**Why lazy imports?** Notice the `from tools.xxx import yyy` lines are *inside* the if-blocks, not at the top of the file. This is intentional — we only import the tool module when we actually need it. This speeds up startup and avoids importing database code when we only need search.

---

## Deep Dive: What Each Tool Does Under the Hood

### `rag_search` — Semantic Search via Weaviate

This tool searches the Weaviate vector database we set up in Step 1. When you call `rag_search(query="NSW requirements")`, it:

1. Converts "NSW requirements" into an embedding (a list of 1024 numbers)
2. Searches Weaviate for documents with similar embeddings
3. Returns the top-k most relevant chunks

The result goes back to Claude, who reads the documents and writes a human-friendly answer. This is the **RAG** (Retrieval Augmented Generation) pattern.

### `check_eligibility` — Business Rules + RAG

This is the most complex tool. Let's walk through `tools/policy_tool.py`:

```python
# From tools/policy_tool.py

# Structured output — every eligibility check returns this exact shape
class PolicyResult(BaseModel):
    eligible: bool | None     # True, False, or None (can't determine)
    reason: str               # Human-readable explanation
    requirements_met: list[str]      # What they have ✅
    requirements_missing: list[str]  # What they're missing ❌
    confidence: float         # 0.0 to 1.0 — how sure we are
    next_steps: list[str]     # What to do next

# Hardcoded business rules — these don't come from the LLM
LEVEL_REQUIREMENTS = {
    "Provisional": {
        "qualifications": ["approved teaching qualification"],
        "experience": "none required",
        "pd_hours": 0,
        "description": "Entry-level accreditation for new teachers",
    },
    "Proficient": {
        "qualifications": ["approved teaching qualification"],
        "experience": "demonstrated proficiency in classroom",
        "pd_hours": 100,
        "description": "Standard accreditation demonstrating competence",
    },
    # ... Highly Accomplished, Lead ...
}
```

The function does two things:

1. **RAG search** for relevant policy documents (gives context)
2. **Business rules** to check qualification and jurisdiction

```python
async def check_eligibility(qualification, jurisdiction="NSW", accreditation_level="Provisional"):
    # Step 1: Look up the level's requirements
    level = accreditation_level.strip().title()
    reqs = LEVEL_REQUIREMENTS.get(level)

    # Step 2: Search for relevant policy documents
    search = await rag_search(
        f"accreditation eligibility {level} qualification requirements {jurisdiction}",
        top_k=3,
    )

    # Step 3: Apply business rules
    met = []
    missing = []

    # Check if qualification was provided and seems real (>3 chars)
    if qualification and len(qualification) > 3:
        met.append(f"Teaching qualification provided: {qualification}")
    else:
        missing.append("Approved teaching qualification required")

    # Check if jurisdiction is Australian
    if jurisdiction.upper() in ("NSW", "ACT", "VIC", "QLD", "SA", "WA", "TAS", "NT"):
        met.append(f"Australian jurisdiction: {jurisdiction}")
    else:
        missing.append(f"Overseas qualification from {jurisdiction} may require AITSL assessment")

    eligible = len(missing) == 0
    confidence = 0.7 if eligible else 0.5

    return PolicyResult(eligible=eligible, reason="...", ...)
```

**Key insight:** This combines AI (RAG search) with traditional code (if/else business rules). The LLM is great at understanding questions, but we don't trust it to evaluate eligibility rules — that's deterministic logic that must be correct every time.

### `create_checklist` — Write to PostgreSQL

From `tools/db_tool.py`:

```python
async def create_checklist(title: str, items: list[str]) -> Checklist:
    checklist_id = str(uuid.uuid4())   # Generate a unique ID

    conn = _get_conn()                 # Connect to PostgreSQL
    try:
        cur = conn.cursor()
        # Create the parent checklist record
        cur.execute(
            "INSERT INTO checklists (id, title, checklist_type, created_at) VALUES (%s::uuid, %s, %s, NOW())",
            (checklist_id, title, "accreditation"),
        )
        # Create each item as a separate row
        checklist_items = []
        for desc in items:
            cur.execute(
                "INSERT INTO checklist_items (checklist_id, description, status) "
                "VALUES (%s::uuid, %s, 'pending') RETURNING id",
                (checklist_id, desc),
            )
            item_id = cur.fetchone()[0]
            checklist_items.append({
                "id": str(item_id),
                "description": desc,
                "status": "pending",    # All items start as "pending"
                "notes": "",
            })
        conn.commit()                   # Save to database
    finally:
        conn.close()

    return Checklist(
        id=checklist_id,
        title=title,
        items=checklist_items,
        completed=0,
        total=len(checklist_items),
    )
```

**This is an agent *acting*, not just answering.** The checklist persists in the database. The user can come back next week and check their progress. This is the difference between a chatbot and an agent.

### `escalate_to_human` — The Safety Net

From `tools/escalation_tool.py`:

```python
async def escalate(reason, conversation_summary, priority="medium"):
    escalation_id = str(uuid.uuid4())[:8]   # Short ID for easy reference

    conn = _get_conn()
    try:
        cur = conn.cursor()
        # Create the escalations table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS escalations (
                id TEXT PRIMARY KEY,
                reason TEXT NOT NULL,
                context_summary TEXT,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Insert the escalation record
        cur.execute(
            "INSERT INTO escalations (id, reason, context_summary, priority) VALUES (%s, %s, %s, %s)",
            (escalation_id, reason, conversation_summary, priority),
        )
        conn.commit()
    except Exception:
        conn.rollback()     # If DB write fails, don't crash — just log it
    finally:
        conn.close()

    return EscalationResult(
        escalation_id=escalation_id,
        reason=reason,
        context_summary=conversation_summary,
        priority=priority,
        status="pending",
    )
```

**Notice the error handling:** If the database write fails, the tool doesn't crash. It rolls back and still returns a result. In production, you don't want a database hiccup to prevent the user from getting help.

---

## How Claude Decides Which Tool to Call

This is the magic part. When Claude receives a message with tools bound, it sees something like:

```
System: You are an accreditation assistant...

Available tools:
1. rag_search — Search knowledge base for factual questions
2. check_eligibility — Check if teacher qualifies
3. create_checklist — Create a step-by-step list
4. escalate_to_human — Hand off to human

User: "I have a Bachelor of Education from NSW. Am I eligible for Provisional?"
```

Claude reads the user's question, reads the tool descriptions, and decides:

```
"This is about eligibility → check_eligibility is the best fit"
"qualification = Bachelor of Education"
"jurisdiction = NSW"
"accreditation_level = Provisional"
```

It outputs a **tool call** — a structured JSON object:

```json
{
    "name": "check_eligibility",
    "args": {
        "qualification": "Bachelor of Education",
        "jurisdiction": "NSW",
        "accreditation_level": "Provisional"
    }
}
```

The tool call goes through `execute_tool()`, the result comes back, and Claude writes a final answer based on the tool's output.

### How the LLM Node Sends Tools to Claude

In `agent/graph.py`, the `llm_node` function binds the tools:

```python
async def llm_node(state: AgentState) -> dict:
    llm = _get_llm()

    messages = list(state["messages"])
    if not messages or not isinstance(messages[0], SystemMessage):
        messages.insert(0, SystemMessage(content=SYSTEM_PROMPT))

    # THIS LINE is what makes Claude aware of the tools
    llm_with_tools = llm.bind_tools(TOOLS)

    # Call Claude with messages + tool awareness
    response = await llm_with_tools.ainvoke(messages)
    # ...
```

`bind_tools(TOOLS)` takes our list of JSON tool definitions and includes them in the API call to Claude. Without this line, Claude wouldn't know any tools exist.

---

## Testing: Tool Selection Patterns

Here's what Claude would do for different questions:

### Pattern 1: Single Tool — Factual Question

```
User: "What documents do I need for Proficient accreditation?"

Claude thinks: "Factual question about requirements → rag_search"
Tool call: rag_search(query="documents required Proficient accreditation")
Result: [relevant policy chunks from Weaviate]
Claude: "For Proficient accreditation, you'll need..."
```

### Pattern 2: Single Tool — Eligibility Check

```
User: "I have a Master of Teaching from VIC. Do I qualify?"

Claude thinks: "They want to know if they're eligible → check_eligibility"
Tool call: check_eligibility(
    qualification="Master of Teaching",
    jurisdiction="VIC",
    accreditation_level="Provisional"   ← defaults because user didn't specify
)
Result: {eligible: true, requirements_met: [...], ...}
Claude: "Great news! With a Master of Teaching from VIC, you're eligible for..."
```

### Pattern 3: Multi-Tool — Complex Request

```
User: "Am I eligible for Proficient with a B.Ed from NSW? And give me a checklist."

Claude thinks: "Two things needed: eligibility check AND a checklist"
Tool call 1: check_eligibility(qualification="B.Ed", jurisdiction="NSW", accreditation_level="Proficient")
Tool call 2: create_checklist(title="Proficient Checklist", items=["..."])
Results come back → Claude combines both into one response
```

**Claude can call multiple tools in a single turn!** This is handled in `tool_node`, which loops through all tool calls:

```python
async def tool_node(state: AgentState) -> dict:
    last_message = messages[-1]
    tool_messages = []

    # Loop through ALL tool calls (there can be multiple)
    for tool_call in last_message.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        result = await execute_tool(name, args)
        tool_messages.append(ToolMessage(content=result, tool_call_id=tool_call["id"]))

    return {"messages": tool_messages}  # All results go back to Claude
```

### Pattern 4: Escalation

```
User: "I got my teaching degree in Argentina. What do I do?"

Claude thinks: "Overseas qualification, complex case → check_eligibility first"
Tool call: check_eligibility(qualification="teaching degree", jurisdiction="Argentina")
Result: {eligible: None, requirements_missing: ["Overseas qualification may require AITSL assessment"]}
Claude thinks: "Confidence is low, complex case → escalate"
Tool call: escalate_to_human(
    reason="Overseas qualification requires individual AITSL assessment",
    conversation_summary="Teacher with Argentine qualification seeking accreditation guidance",
    priority="medium"
)
Result: {escalation_id: "abc12345", status: "pending"}
Claude: "Your case needs individual assessment. I've created a referral (ID: abc12345)..."
```

**This is a multi-turn tool sequence:** Claude calls one tool, reads the result, decides it needs another tool, and calls that too. This is the **ReAct loop** — Reason, Act, Observe, repeat.

### Pattern 5: No Tool Needed

```
User: "Thanks for your help!"

Claude thinks: "This is a polite closing, no tool needed"
Tool calls: none
Claude: "You're welcome! Good luck with your accreditation journey."
```

Not every message needs a tool. Claude only calls tools when they'd be useful.

---

## The Full Flow — Putting It All Together

```
┌──────────────────────────────────────────────────────────────┐
│                     Request Lifecycle                         │
│                                                              │
│  User message                                                │
│       │                                                      │
│       ▼                                                      │
│  llm_node: Claude reads message + TOOLS definitions          │
│       │                                                      │
│       ▼                                                      │
│  should_continue: Does Claude want to call a tool?           │
│       │                    │                                 │
│      YES                  NO                                 │
│       │                    │                                 │
│       ▼                    ▼                                 │
│  tool_node:            Return final                          │
│  execute_tool()        response to user                      │
│       │                                                      │
│       ▼                                                      │
│  Back to llm_node                                            │
│  (Claude reads tool result,                                  │
│   decides: call another tool? or respond?)                   │
│       │                                                      │
│      ... (loop continues until Claude has enough info) ...   │
└──────────────────────────────────────────────────────────────┘
```

---

## What We Have Now

```
BEFORE this step:           AFTER this step:
──────────────────          ──────────────────
Agent could search          Agent has 4 tools
Only RAG answers            Can check eligibility
No actions                  Can create checklists
No safety net               Can escalate to humans
Hard-coded behavior         Claude chooses autonomously
```

---

## Key Takeaways

1. **Tools are just functions with JSON descriptions** — Claude reads the descriptions to decide when to use them
2. **`execute_tool()` is a simple dispatcher** — it maps tool names to Python functions
3. **Claude decides autonomously** — we don't hard-code "if user says X, call tool Y"
4. **Multi-tool calls happen in one turn** — Claude can call multiple tools simultaneously
5. **The ReAct loop** allows multi-turn tool usage — call a tool, read result, call another
6. **Escalation is a feature, not a failure** — knowing when to hand off to a human is a sign of a well-designed agent

---

## Next Step

**Step 6: Eligibility Workflow** — we'll see how these tools get wired into a *structured* multi-step workflow with conditional branching, going beyond the ad-hoc ReAct loop.
