# Tutorial Step 6: Eligibility Workflow — Structured Multi-Step Agent Logic

> **Goal:** Understand how the eligibility check workflow uses conditional branching and state to go beyond simple tool calling  
> **Time:** ~25 minutes  
> **Prerequisites:** Step 5 (Multi-Tool Agent)  

---

## What We're Building in This Step

In Step 5, we saw Claude calling tools ad-hoc in a ReAct loop — ask a question, call a tool, read the result, maybe call another. That works great for general Q&A. But some tasks need **structure**.

Think of it like the difference between a conversation and a medical diagnosis:

- **Conversation** (general QA): flexible, any topic, any order → ReAct loop
- **Medical diagnosis** (eligibility check): gather symptoms → run tests → diagnose → prescribe → follow up. You wouldn't skip the tests and jump to prescribing.

Our eligibility workflow is a **structured pipeline**: gather info → check policy → branch based on result. Each step depends on the previous one, and the path forward depends on what we find.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Eligibility Workflow Architecture                  │
│                                                                      │
│  User: "Am I eligible with a B.Ed from NSW?"                        │
│       │                                                              │
│       ▼                                                              │
│  ┌─────────┐                                                         │
│  │ Router  │ ← "Is this about eligibility or general Q&A?"          │
│  └────┬────┘                                                         │
│       │ eligibility_check                                            │
│       ▼                                                              │
│  ┌─────────────┐                                                     │
│  │ gather_info │ ← LLM extracts: qualification, jurisdiction, level │
│  └──────┬──────┘                                                     │
│         │ workflow_data = {qualification: "B.Ed", ...}               │
│         ▼                                                            │
│  ┌──────────────┐                                                    │
│  │ check_policy │ ← Runs business rules + RAG search                │
│  └──────┬───────┘                                                    │
│         │ policy_result = {eligible: true/false/null, ...}           │
│         ▼                                                            │
│  ┌──────────────────┐                                                │
│  │ route_after_policy│ ← THE KEY BRANCHING DECISION                 │
│  └──┬───────┬───────┘                                                │
│     │       │       │                                                │
│     ▼       ▼       ▼                                                │
│  eligible  ineligible  uncertain                                     │
│     │       │           │                                            │
│     ▼       ▼           ▼                                            │
│  Create    Explain    Escalate to                                    │
│  checklist  gaps      human review                                   │
│     │       │           │                                            │
│     └───────┴───────────┘                                            │
│             │                                                        │
│             ▼                                                        │
│            END                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

**This is what makes it "agentic":** The agent doesn't just answer a question — it runs a multi-step process, carries state between steps, and makes decisions about what to do next based on intermediate results.

---

## Key Concepts (Explained for Beginners)

### Workflow vs Tool Calling — What's the Difference?

| Feature | Tool Calling (ReAct) | Workflow |
|---|---|---|
| Structure | Ad-hoc, flexible | Predefined steps in order |
| Who decides next step? | The LLM (Claude) | The code (graph edges) |
| State between steps | Only in message history | Explicit state object |
| Branching | LLM might or might not call tools | Deterministic branches based on data |
| Best for | General Q&A, open-ended | Structured processes, business rules |

**Analogy:** Tool calling is like a chef improvising a meal — they grab ingredients as needed. A workflow is like following a recipe — step 1, step 2, step 3, with "if it's too thick, add water" decision points.

### What Is "State"?

State is data that gets passed between workflow steps. Think of it as a clipboard that each step can read from and write to:

```
Step 1 (gather_info):  Writes → {qualification: "B.Ed", jurisdiction: "NSW"}
Step 2 (check_policy): Reads ← {qualification: "B.Ed", jurisdiction: "NSW"}
                       Writes → {eligible: true, confidence: 0.7}
Step 3 (branch):       Reads ← {eligible: true}
                       Routes → eligible_path
```

Without state, each step would have no idea what the previous step found. It's like playing a game of telephone — except instead of whispering, we write everything down.

---

## The State Object — `AgentState`

All state flows through one object defined in `agent/state.py`:

```python
# From agent/state.py
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # Conversation messages — add_messages APPENDS new messages (never overwrites)
    messages: Annotated[list, add_messages]

    # Workflow tracking — where are we in the process?
    current_workflow: str      # "general_qa" or "eligibility_check"
    workflow_step: int         # 0, 1, 2, 3...
    workflow_status: str       # "in_progress", "completed", "escalated"

    # Data passed between workflow nodes
    workflow_data: dict        # Set by gather_info, read by check_policy
    policy_result: dict        # Set by check_policy, read by branch nodes

    # Observability
    tool_calls_log: list[dict] # Every tool invocation, for debugging
    iteration_count: int       # Loop protection counter
```

**Key detail:** `Annotated[list, add_messages]` is LangGraph magic. It means "when a node returns `{"messages": [new_msg]}`, *append* it to the list instead of replacing it." This is how conversation history accumulates.

Every other field (like `workflow_data`, `policy_result`) uses **replace** semantics — when a node writes to it, the old value is overwritten. This is fine because each workflow step only needs to see the previous step's output.

---

## Node 1: The Router — Intent Classification

Before any workflow runs, we need to figure out *which* workflow to use. That's the router's job.

```python
# From agent/graph.py
async def router_node(state: AgentState) -> dict:
    """Classify user intent and route to the appropriate workflow."""
    from agent.prompts import ROUTER_PROMPT

    # Find the most recent human message
    messages = state["messages"]
    user_msg = ""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            user_msg = m.content
            break

    # Ask Claude to classify the intent
    llm = _get_llm()
    response = await llm.ainvoke([
        SystemMessage(content=ROUTER_PROMPT),     # "Classify this as general_qa or eligibility_check"
        HumanMessage(content=user_msg),
    ])

    # Parse Claude's response
    workflow = response.content.strip().lower().replace(" ", "_")

    if workflow in ("eligibility_check", "eligibility"):
        logger.info(f"Router → eligibility_check")
        return {"current_workflow": "eligibility_check"}
    else:
        logger.info(f"Router → general_qa")
        return {"current_workflow": "general_qa"}
```

**How it works:**

1. Extract the user's latest message
2. Send it to Claude with a special router prompt that says "classify this intent"
3. Claude responds with either `"eligibility_check"` or `"general_qa"`
4. The router writes `current_workflow` to state

**This is a lightweight LLM call** — we don't bind tools, we don't need a long system prompt. We just need a one-word classification. Fast and cheap.

**The conditional edge** in the graph then reads `current_workflow` and routes accordingly:

```python
# From create_agent_graph()
graph.add_conditional_edges(
    "router",
    lambda s: s.get("current_workflow", "general_qa"),  # Read the state
    {
        "general_qa": "llm",              # → ReAct loop (Step 5)
        "eligibility_check": "gather_info", # → Structured workflow (this step)
    },
)
```

```
User: "What is NESA?"
  → Router classifies: general_qa
  → Goes to llm node (ReAct loop)

User: "Am I eligible with a B.Ed?"
  → Router classifies: eligibility_check
  → Goes to gather_info node (workflow)
```

---

## Node 2: `gather_info_node` — LLM-Powered JSON Extraction

The first workflow step extracts structured data from the user's free-text message. This is a common pattern: **use the LLM as a parser**.

```python
# From agent/workflows/eligibility.py
async def gather_info_node(state: AgentState) -> dict:
    """Extract qualification details from the conversation."""

    # Get the user's message
    messages = state["messages"]
    user_msg = ""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            user_msg = m.content
            break

    # Ask Claude to extract structured data
    extraction_prompt = f"""Extract the following from the user's message.
If not mentioned, use "unknown".
Return ONLY valid JSON, no other text.

User message: "{user_msg}"

Return format:
{{"qualification": "...", "jurisdiction": "...", "accreditation_level": "..."}}

Rules:
- qualification: the teaching degree/qualification name
- jurisdiction: Australian state (NSW, VIC, etc.) or country if overseas
- accreditation_level: Provisional, Proficient, Highly Accomplished, or Lead (default: Provisional)
"""

    result = _call_llm([
        SystemMessage(content="You are a JSON extraction assistant. Return ONLY valid JSON."),
        HumanMessage(content=extraction_prompt),
    ])

    # Parse the JSON (with error handling)
    try:
        clean = result.strip()
        if clean.startswith("```"):           # Handle markdown code blocks
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        extracted = json.loads(clean)
    except (json.JSONDecodeError, IndexError):
        # If parsing fails, use safe defaults
        extracted = {
            "qualification": "unknown",
            "jurisdiction": "unknown",
            "accreditation_level": "Provisional",
        }

    # Write extracted data to state for the next node to read
    return {
        "current_workflow": "eligibility_check",
        "workflow_step": 1,
        "workflow_status": "gathering_info",
        "workflow_data": extracted,           # ← This is what check_policy reads
    }
```

**What happens with different messages:**

```
Message: "I have a Bachelor of Education from NSW"
Extracted: {"qualification": "Bachelor of Education", "jurisdiction": "NSW", "accreditation_level": "Provisional"}

Message: "Do I qualify for Proficient? I studied at UTS in Sydney"
Extracted: {"qualification": "unknown", "jurisdiction": "NSW", "accreditation_level": "Proficient"}

Message: "I got my teaching cert in London"
Extracted: {"qualification": "teaching cert", "jurisdiction": "UK", "accreditation_level": "Provisional"}
```

**Why use an LLM for this?** Because users write messages in infinite different ways. A regex or keyword parser would break on "I studied at UTS" vs "I have a B.Ed from UTS" vs "UTS grad here." The LLM understands meaning, not just keywords.

**The error handling is important:** If Claude returns malformed JSON (it happens!), we fall back to safe defaults rather than crashing. The `"unknown"` values will trigger the "uncertain" path later, which is exactly what we want — "I'm not sure, let me escalate."

---

## Node 3: `check_policy_node` — Applying Business Rules

This node takes the extracted data and runs the eligibility check:

```python
# From agent/workflows/eligibility.py
async def check_policy_node(state: AgentState) -> dict:
    """Run the eligibility check using the policy tool."""
    from tools.policy_tool import check_eligibility

    # Read data from the PREVIOUS node (gather_info wrote this)
    data = state.get("workflow_data", {})
    qualification = data.get("qualification", "unknown")
    jurisdiction = data.get("jurisdiction", "NSW")
    level = data.get("accreditation_level", "Provisional")

    # Call the policy tool (same one Claude can call in general QA)
    result = await check_eligibility(
        qualification=qualification,
        jurisdiction=jurisdiction,
        accreditation_level=level,
    )

    # Write the result to state for the branching node to read
    return {
        "workflow_step": 2,
        "workflow_status": "policy_checked",
        "policy_result": result.model_dump(),   # ← Pydantic model → dict
        "tool_calls_log": state.get("tool_calls_log", []) + [{
            "name": "check_eligibility",
            "input": {"qualification": qualification, "jurisdiction": jurisdiction, "level": level},
            "output_length": len(result.model_dump_json()),
            "latency_ms": 0,
        }],
    }
```

**This is the same `check_eligibility` function from Step 5!** The workflow doesn't duplicate logic — it reuses the same tool. The difference is that here, the *code* calls it directly (with data from state), instead of Claude deciding to call it.

**The `policy_result` dict** that gets written to state looks like:

```python
{
    "eligible": True,              # or False, or None
    "reason": "Eligibility assessment for Provisional...",
    "requirements_met": ["Teaching qualification provided: B.Ed", "Australian jurisdiction: NSW"],
    "requirements_missing": [],
    "confidence": 0.7,
    "next_steps": ["Apply via NESA portal", "Prepare documentation"]
}
```

---

## The Key Agentic Concept: `route_after_policy`

This is where the workflow becomes truly "agentic." After checking eligibility, the code **decides what to do next** based on the result:

```python
# From agent/workflows/eligibility.py
def route_after_policy(state: AgentState) -> str:
    """Branch based on eligibility result.

    This is the key branching logic:
    - eligible=True  → "eligible" path (create checklist, next steps)
    - eligible=False → "ineligible" path (explain gaps)
    - eligible=None  → "uncertain" path (escalate)
    """
    policy = state.get("policy_result", {})
    eligible = policy.get("eligible")

    if eligible is True:
        return "eligible"
    elif eligible is False:
        return "ineligible"
    else:
        return "uncertain"     # None or missing → escalate
```

**This is just 10 lines of code, but it's the heart of the workflow.** It creates three completely different user experiences based on one field:

```
                    policy_result.eligible
                           │
              ┌────────────┼────────────┐
              │            │            │
           True         False         None
              │            │            │
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Create   │ │ Explain  │ │ Escalate │
        │ checklist│ │ gaps &   │ │ to human │
        │ & next   │ │ suggest  │ │ reviewer │
        │ steps    │ │ options  │ │          │
        └──────────┘ └──────────┘ └──────────┘
```

**Why is this "agentic"?** Because the agent changes its behavior based on what it learns. It doesn't give the same response to everyone — it adapts. A teacher with a B.Ed from NSW gets a checklist and next steps. A teacher from overseas gets a different path. And when the agent isn't sure, it admits it and gets human help.

The graph wires this up with conditional edges:

```python
# From create_agent_graph()
graph.add_conditional_edges(
    "check_policy",
    route_after_policy,          # This function returns "eligible", "ineligible", or "uncertain"
    {
        "eligible": "eligible_path",
        "ineligible": "ineligible_path",
        "uncertain": "uncertain_path",
    },
)
```

---

## Path A: Eligible → Checklist + Next Steps

```python
# From agent/workflows/eligibility.py
async def eligible_path_node(state: AgentState) -> dict:
    """Handle eligible case — create checklist and provide next steps."""
    from tools.db_tool import create_checklist

    policy = state.get("policy_result", {})
    data = state.get("workflow_data", {})
    level = data.get("accreditation_level", "Provisional")

    # Get next steps from the policy result (or use defaults)
    next_steps = policy.get("next_steps", [])
    if not next_steps:
        next_steps = [
            f"Submit {level} accreditation application to NESA",
            "Prepare supporting documentation",
            "Complete Working with Children Check (WWCC)",
            "Provide certified copies of qualifications",
        ]

    # Create a REAL checklist in PostgreSQL
    checklist = await create_checklist(
        title=f"{level} Accreditation Checklist",
        items=next_steps,
    )

    # Use LLM to write a friendly response
    response_text = _call_llm([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""The user asked about eligibility for {level} accreditation.

Policy check result:
- Eligible: YES
- Requirements met: {policy.get('requirements_met', [])}
- Confidence: {policy.get('confidence', 0)}

A checklist has been created (ID: {checklist.id[:8]}) with {checklist.total} items:
{json.dumps(next_steps, indent=2)}

Provide a warm, helpful response confirming eligibility and listing the checklist items.
Mention the checklist ID so they can reference it later."""),
    ])

    return {
        "messages": [AIMessage(content=response_text)],
        "workflow_step": 3,
        "workflow_status": "completed",
    }
```

**Three things happen here:**

1. Read the policy result and workflow data from state
2. Create a real checklist in PostgreSQL (persistent action!)
3. Ask Claude to write a friendly response that includes the checklist

The user gets something like: *"Great news! You're eligible for Provisional accreditation. I've created a checklist (ID: abc123) with your next steps: 1. Submit application to NESA..."*

---

## Path B: Ineligible → Explain Gaps

```python
async def ineligible_path_node(state: AgentState) -> dict:
    """Handle ineligible case — explain gaps and suggest alternatives."""
    policy = state.get("policy_result", {})
    data = state.get("workflow_data", {})

    response_text = _call_llm([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""The user asked about eligibility for {data.get('accreditation_level', 'Provisional')} accreditation.

Policy check result:
- Eligible: NO
- Requirements met: {policy.get('requirements_met', [])}
- Requirements missing: {policy.get('requirements_missing', [])}
- Confidence: {policy.get('confidence', 0)}

Provide a supportive response explaining what requirements are missing and what steps they can take.
If applicable, suggest alternative pathways or lower accreditation levels they might qualify for."""),
    ])

    return {
        "messages": [AIMessage(content=response_text)],
        "workflow_step": 3,
        "workflow_status": "completed",
    }
```

**Notice:** No checklist created here. Instead, the LLM is prompted to be *supportive* — "here's what's missing, and here's how to fix it." The prompt even suggests recommending lower accreditation levels. This is thoughtful UX encoded in the workflow.

---

## Path C: Uncertain → Escalate to Human

```python
async def uncertain_path_node(state: AgentState) -> dict:
    """Handle uncertain case — escalate to human review."""
    from tools.escalation_tool import escalate

    data = state.get("workflow_data", {})

    # Create an escalation record in PostgreSQL
    result = await escalate(
        reason=f"Cannot determine eligibility for {data.get('accreditation_level', 'unknown')} — complex case",
        conversation_summary=f"User with {data.get('qualification', 'unknown')} from {data.get('jurisdiction', 'unknown')}",
        priority="medium",
    )

    # Write a response that includes the escalation ID
    response_text = _call_llm([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""I couldn't confidently determine the user's eligibility.
The case has been escalated to human review (ID: {result.escalation_id}).

Inform the user that their case requires individual assessment by a NESA staff member.
Provide the escalation reference number and expected next steps."""),
    ])

    return {
        "messages": [AIMessage(content=response_text)],
        "workflow_step": 3,
        "workflow_status": "escalated",
    }
```

**This triggers when `eligible` is `None`** — which happens when the qualification is "unknown" (extraction failed) or when the accreditation level wasn't recognized. The agent doesn't guess — it escalates.

---

## State Passing Between Nodes — The Full Picture

Let's trace the state through a complete workflow:

```
┌─────────────────────────────────────────────────────────────┐
│ Initial state (set by FastAPI endpoint):                    │
│   messages: [HumanMessage("Am I eligible with B.Ed from NSW?")]
│   current_workflow: "general_qa"   (default, router will change)
│   workflow_step: 0                                          │
│   workflow_data: {}                                         │
│   policy_result: {}                                         │
│   tool_calls_log: []                                        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ After router_node:                                          │
│   current_workflow: "eligibility_check"  ← CHANGED          │
│   (everything else unchanged)                               │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ After gather_info_node:                                     │
│   workflow_step: 1                     ← CHANGED            │
│   workflow_status: "gathering_info"    ← CHANGED            │
│   workflow_data: {                     ← CHANGED            │
│     "qualification": "B.Ed",                                │
│     "jurisdiction": "NSW",                                  │
│     "accreditation_level": "Provisional"                    │
│   }                                                         │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ After check_policy_node:                                    │
│   workflow_step: 2                     ← CHANGED            │
│   workflow_status: "policy_checked"    ← CHANGED            │
│   policy_result: {                     ← CHANGED            │
│     "eligible": true,                                       │
│     "requirements_met": ["Teaching qualification: B.Ed",    │
│                          "Australian jurisdiction: NSW"],    │
│     "requirements_missing": [],                             │
│     "confidence": 0.7,                                      │
│     "next_steps": ["Apply via NESA portal", ...]            │
│   }                                                         │
│   tool_calls_log: [{name: "check_eligibility", ...}]        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼  route_after_policy reads eligible=True
                          │
┌─────────────────────────────────────────────────────────────┐
│ After eligible_path_node:                                   │
│   messages: [..., AIMessage("Great news! You're eligible...")]
│   workflow_step: 3                     ← CHANGED            │
│   workflow_status: "completed"         ← CHANGED            │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
                         END
```

Each node reads what it needs from the previous step's output and writes its own results. The state object is the "glue" that holds the workflow together.

---

## How the Graph Is Wired Together

Here's the complete graph construction from `create_agent_graph()`:

```python
def create_agent_graph():
    from agent.workflows.eligibility import (
        gather_info_node, check_policy_node, route_after_policy,
        eligible_path_node, ineligible_path_node, uncertain_path_node,
    )

    graph = StateGraph(AgentState)

    # Register all nodes
    graph.add_node("router", router_node)
    graph.add_node("llm", llm_node)                        # General QA
    graph.add_node("tools", tool_node)                     # General QA
    graph.add_node("gather_info", gather_info_node)        # Eligibility workflow
    graph.add_node("check_policy", check_policy_node)      # Eligibility workflow
    graph.add_node("eligible_path", eligible_path_node)    # Branch: eligible
    graph.add_node("ineligible_path", ineligible_path_node) # Branch: ineligible
    graph.add_node("uncertain_path", uncertain_path_node)  # Branch: uncertain

    # Entry point — every request starts at the router
    graph.set_entry_point("router")

    # Router → either general QA or eligibility workflow
    graph.add_conditional_edges("router",
        lambda s: s.get("current_workflow", "general_qa"),
        {"general_qa": "llm", "eligibility_check": "gather_info"})

    # General QA: ReAct loop (llm ↔ tools)
    graph.add_conditional_edges("llm", should_continue,
        {"tools": "tools", "end": END})
    graph.add_edge("tools", "llm")

    # Eligibility: linear pipeline then 3-way branch
    graph.add_edge("gather_info", "check_policy")          # Always: gather → check
    graph.add_conditional_edges("check_policy",
        route_after_policy,                                 # Branch function
        {"eligible": "eligible_path",
         "ineligible": "ineligible_path",
         "uncertain": "uncertain_path"})

    # All 3 paths end the workflow
    graph.add_edge("eligible_path", END)
    graph.add_edge("ineligible_path", END)
    graph.add_edge("uncertain_path", END)

    return graph.compile()
```

**Two types of edges:**

1. **`add_edge(A, B)`** — Always go from A to B. Like a one-way street.
2. **`add_conditional_edges(A, func, mapping)`** — Call `func(state)`, use the return value to pick the next node from `mapping`. Like a traffic light that changes based on conditions.

---

## How This Pattern Scales

The eligibility workflow is one example, but the pattern works for any structured process:

```
┌─────────────────────────────────────────────────────┐
│          The Workflow Pattern (generalised)          │
│                                                     │
│  1. GATHER: Use LLM to extract structured data      │
│  2. PROCESS: Apply business rules / call APIs        │
│  3. BRANCH: Route based on results                   │
│  4. ACT: Take different actions per branch           │
│  5. RESPOND: Generate human-friendly output          │
│                                                     │
│  Examples of other workflows you could build:        │
│  • Application guidance workflow                     │
│  • Accreditation maintenance renewal workflow        │
│  • Complaint/feedback triage workflow                │
│  • Document verification workflow                    │
└─────────────────────────────────────────────────────┘
```

To add a new workflow, you would:

1. Add new nodes (gather, process, branch functions)
2. Add a new routing option in the router
3. Wire the edges in `create_agent_graph()`

The existing infrastructure (state management, logging, error handling) all comes for free.

---

## Testing: Walking Through Different Scenarios

### Scenario 1: Eligible Teacher (Happy Path)

```
Input:  "I have a Bachelor of Education from NSW"
Router: → eligibility_check
Gather: → {qualification: "Bachelor of Education", jurisdiction: "NSW", level: "Provisional"}
Policy: → {eligible: true, confidence: 0.7}
Branch: → eligible_path
Output: "Great news! You're eligible. Here's your checklist (ID: abc123)..."
```

### Scenario 2: Missing Requirements

```
Input:  "Can I get Proficient accreditation? I just graduated"
Router: → eligibility_check
Gather: → {qualification: "unknown", jurisdiction: "unknown", level: "Proficient"}
Policy: → {eligible: false, missing: ["Approved teaching qualification required"]}
Branch: → ineligible_path
Output: "Based on the information provided, there are some requirements to address..."
```

### Scenario 3: Overseas Qualification (Uncertain)

```
Input:  "I'm a qualified teacher from Brazil"
Router: → eligibility_check
Gather: → {qualification: "qualified teacher", jurisdiction: "Brazil", level: "Provisional"}
Policy: → {eligible: false, missing: ["Overseas qualification may require AITSL assessment"]}
Branch: → ineligible_path (Note: not uncertain because eligible=False, not None)
Output: "Your qualification from Brazil may need AITSL assessment. Here's what to do..."
```

### Scenario 4: Parse Failure (Safety Net)

```
Input:  "eligible???"
Router: → eligibility_check
Gather: → LLM can't extract anything → {qualification: "unknown", jurisdiction: "unknown", level: "Provisional"}
Policy: → qualification "unknown" has len ≤ 3 → eligible=False
Branch: → ineligible_path
Output: "I couldn't determine your eligibility. Could you tell me your qualification?"
```

### Scenario 5: General Question (Not a Workflow)

```
Input:  "What is NESA?"
Router: → general_qa
Path:   → llm_node (ReAct loop, Step 5)
Output: "NESA is the NSW Education Standards Authority..."
```

---

## What We Have Now

```
BEFORE this step:              AFTER this step:
──────────────────             ──────────────────
Ad-hoc tool calling            Structured multi-step workflow
Same response pattern          Three different paths based on results
No state between tools         Explicit state object passed between nodes
Claude decides everything      Code controls the workflow; LLM assists
```

---

## Key Takeaways

1. **Workflows are structured pipelines** — each step depends on the previous one, unlike ad-hoc tool calling
2. **The router classifies intent** — a quick LLM call decides which workflow to run
3. **`gather_info` uses LLM as a parser** — extracting structured JSON from free-text messages
4. **`check_policy` applies business rules** — deterministic logic, not LLM guessing
5. **`route_after_policy` is the key branching point** — three completely different paths from one function
6. **State flows through `AgentState`** — each node reads and writes to a shared state object
7. **The pattern scales** — add new workflows by adding nodes and edges

---

## Next Step

**Step 7: Production Patterns** — we'll look at the reliability, observability, and error handling patterns that make this agent safe to deploy to real users.
