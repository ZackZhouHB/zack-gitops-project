# Step 18: Routing Design Patterns for Mixed-Content RAG

## The Problem

Our Knowledge Base contains very different content types:

| Source | Content Type | Example Query |
|--------|-------------|---------------|
| S3 PDFs | Infra docs (Terraform, Azure AD) | "What is the Azure AD group approach?" |
| Blog (technical) | EKS, Karpenter, CI/CD tutorials | "How does Karpenter work with EKS?" |
| Blog (personal) | Stories, letters, reflections | "Tell me about the letter to Matilda" |
| Confluence | Solution design, architecture | "How does the 2-staged pipeline work?" |

When a user asks a question, the system needs to:
1. Understand what the user wants (search? create checklist? report incident?)
2. Search the RIGHT content (or all content)
3. Return an answer grounded in the actual documents

Our current design has a **fundamental flaw** — let's understand it and fix it.

---

## 18.1 Current Design: Two Brains Fighting

```
User Message
     ↓
  [Router LLM]  ← Brain 1: "Is this an incident or a question?"
     ├── incident_triage → rigid pipeline (gather → search → fix/investigate/escalate)
     └── general_qa → [Tool-Calling LLM] ← Brain 2: "Which tool should I use?"
                         ├── rag_search → KB
                         ├── assess_incident → KB + pattern match
                         ├── create_checklist → DynamoDB
                         └── escalate_to_human → DynamoDB
```

### Why This Is Wrong

**Problem 1: The Router is a blunt instrument.**
It sees ONLY the user's message text. It doesn't search the KB first. It doesn't know what content exists. It makes a snap judgment based on keywords:
- "can you check" → sounds like incident → wrong path
- "what about the letter" → unclear → defaults to incident → wrong path

**Problem 2: `incident_triage` is a rigid pipeline.**
Once a message enters `incident_triage`, it goes through gather_symptoms → search_docs → branch. This makes sense for real incidents ("our API is down") but fails for everything else. There's no escape hatch.

**Problem 3: The general_qa path already has all the tools.**
The ReAct loop in `general_qa` can call `rag_search`, `assess_incident`, `create_checklist`, and `escalate_to_human`. It can decide dynamically. The router is redundant — it's just a worse version of what the LLM already does in the ReAct loop.

**Problem 4: All content is in ONE Knowledge Base.**
We don't have separate KBs for blog posts vs Confluence vs PDFs. Vector search handles relevance naturally — "Karpenter" finds the Karpenter blog post, "Azure AD" finds the PDF. The router adds no value for content-type routing.

---

## 18.2 Better Design: Single ReAct Loop (Recommended)

```
User Message
     ↓
  [LLM with Tools]  ← ONE brain makes ALL decisions
     │
     ├── Tool: kb_search(query) → Bedrock KB → returns chunks from ANY source
     ├── Tool: create_checklist(title, items) → DynamoDB
     ├── Tool: escalate_to_human(reason) → DynamoDB
     └── No tool → direct answer from LLM's own knowledge
     │
     ↓
  [LLM sees tool results] → generates answer with citations → END
```

### Why This Works

1. **ONE decision maker** — the LLM decides tools based on the full context (system prompt + message + tool descriptions)
2. **Vector search handles content routing** — "letter to Matilda" naturally matches the blog post, "Karpenter" matches the technical blog, "pipeline design" matches Confluence
3. **No misrouting** — there's no router to get wrong. Every question gets the ReAct loop.
4. **The LLM can multi-tool** — search KB, then create a checklist, then escalate, all in one conversation

### Implementation

Remove the router entirely. The graph becomes:

```python
# Before (complex, fragile):
graph.set_entry_point("router")
graph.add_conditional_edges("router", lambda s: s.get("current_workflow"), {
    "general_qa": "llm",
    "incident_triage": "gather_symptoms",
})

# After (simple, robust):
graph.set_entry_point("llm")
graph.add_conditional_edges("llm", should_continue, {
    "tools": "tools",
    "end": END,
})
graph.add_edge("tools", "llm")
```

### What About Incidents?

Instead of a separate `incident_triage` pipeline, add the incident assessment as a **tool**:

```python
{
    "name": "assess_and_triage_incident",
    "description": (
        "Use this when the user reports a SPECIFIC infrastructure problem, outage, or error. "
        "Gathers symptoms, searches the knowledge base for known fixes, and creates a "
        "diagnostic checklist. Do NOT use for general questions or lookups."
    ),
    "parameters": {
        "component": "Which system/service is affected",
        "symptoms": "What's happening (errors, behavior)",
        "severity": "low/medium/high/critical"
    }
}
```

The LLM decides when to use this tool — same way it decides to use `kb_search` or `create_checklist`.

---

## 18.3 When You DO Need Routing

Routing makes sense in specific cases:

### Case 1: Multiple Knowledge Bases
If you have SEPARATE KBs for different content types:
```
kb_search_infra(query)      → KB with infra docs only
kb_search_blog(query)       → KB with blog posts only
kb_search_confluence(query) → KB with Confluence pages only
```
Then the LLM's tool descriptions guide which KB to search:
- "Search infra docs for runbooks, Terraform, AWS architecture"
- "Search blog for tutorials, personal stories, learning notes"
- "Search Confluence for solution designs and POC proposals"

But this adds complexity. Usually ONE KB with good embeddings handles mixed content fine.

### Case 2: Different Response Formats
If different intents need fundamentally different output structures:
- Incident → structured report with severity, timeline, checklist
- Documentation → prose with citations
- Onboarding → step-by-step guide

Even here, you can handle this with prompt engineering rather than separate paths.

### Case 3: Different Security Contexts
If some content requires different access permissions:
- Public docs → anyone can search
- Internal docs → authenticated users only
- Classified docs → specific roles only

This is a real reason for routing, but it's better handled at the KB/API level than the agent level.

---

## 18.4 Tool Description Design (The Real Routing)

In the ReAct pattern, **tool descriptions ARE the routing logic**. The LLM reads descriptions and picks the right tool. This is where you invest your design effort:

### Bad Tool Descriptions (Vague)
```python
"name": "search",
"description": "Search the knowledge base"

"name": "incident",  
"description": "Handle an incident"
```
The LLM can't distinguish when to use each.

### Good Tool Descriptions (Specific with Examples)
```python
"name": "kb_search",
"description": (
    "Search the platform knowledge base for technical documentation, "
    "blog tutorials, Confluence design docs, and infrastructure runbooks. "
    "Use this for ANY question about: Terraform, EKS, Karpenter, Bedrock, "
    "Azure AD, Lakehouse, CI/CD, health analyzer, blog posts, personal stories, "
    "or any topic that might be in our documentation. "
    "When in doubt, ALWAYS search first before answering."
)

"name": "assess_incident",
"description": (
    "ONLY use when the user reports a SPECIFIC, ACTIVE infrastructure problem: "
    "service outage, error spike, deployment failure, or performance degradation. "
    "Do NOT use for general questions, lookups, or 'can you check' requests. "
    "Examples of when to use: 'our API is returning 500s', 'EKS nodes are not scaling'. "
    "Examples of when NOT to use: 'what is Karpenter?', 'tell me about the pipeline'."
)
```

### The Pattern
1. **Default tool** (kb_search): broad description, "when in doubt, use this"
2. **Specialized tools** (assess_incident, create_checklist): narrow descriptions with explicit examples of when to use AND when NOT to use
3. **System prompt reinforcement**: "Always search the knowledge base before answering. Use specialized tools only when clearly appropriate."

---

## 18.5 Mixed Content Strategy

For our specific mix (infra docs + technical blog + personal blog + Confluence):

### Option A: Single KB, Single Search Tool (Current + Simplified)
```
All content → ONE Bedrock KB → ONE kb_search tool
```
- **Pros**: Simplest, vector search handles relevance naturally
- **Cons**: "Letter to Matilda" competes with "Terraform modules" in the same index
- **When to use**: Content < 10,000 chunks, topics don't overlap confusingly

### Option B: Single KB, Metadata Filtering
```
All content → ONE KB → kb_search(query, filter={source_type: "blog"})
```
- **Pros**: Single KB but can scope searches by source type
- **Cons**: LLM needs to decide which filter to apply (another routing decision)
- **When to use**: Content types are clearly distinct and users ask source-specific questions

### Option C: Multiple KBs, Multiple Search Tools
```
Infra docs → KB1 → search_infra(query)
Blog posts → KB2 → search_blog(query)  
Confluence → KB3 → search_confluence(query)
```
- **Pros**: Each KB tuned for its content, no cross-contamination
- **Cons**: Most complex, 3x the infrastructure cost
- **When to use**: Large-scale production with clearly separated content domains

### Recommendation for Our Solution
**Option A** (current) is correct. Our content volume is small (<200 chunks), and vector search handles the diversity well. The "Matilda" issue is about the web crawler not indexing post/112, not about routing or tool design.

---

## 18.6 The Decision Tree for Designing Your Routes

```
Q: Do you have multiple KBs with different content?
├── YES → Give each KB its own search tool with clear descriptions
└── NO → Use single kb_search tool
         │
         Q: Do you need structured workflows (not just Q&A)?
         ├── YES → Add specialized tools (create_checklist, escalate, etc.)
         │         Let the LLM decide when to use them (ReAct pattern)
         │         Do NOT use a router — tool descriptions are enough
         └── NO → Just use kb_search + good system prompt
                  The simplest agent is often the best agent
```

---

## 18.7 Key Takeaways

1. **Vector search IS your content router.** Don't try to classify content types before searching — let embeddings handle relevance.

2. **Tool descriptions ARE your intent router.** Write them like instructions to a new team member: "Use this tool when X. Don't use it when Y. Examples: ..."

3. **One ReAct loop beats a complex routing graph.** Unless you have fundamentally different workflows that can't share a tool set.

4. **When in doubt, search first.** The worst case of searching and finding nothing is better than routing to the wrong pipeline and crashing.

5. **Router prompts are fragile.** They see only the raw message with no context. A single LLM call deciding the entire conversation path is a single point of failure.

6. **Test with adversarial queries.** "Can you check", "there is a story about", "I heard something about" — these are the queries that break naive routers.

## 18.8 Implementation Complete

The simplification described in Section 18.2 has been implemented. Here's what changed:

### Files Modified

| File | Change |
|------|--------|
| `agent/graph.py` | Removed `router_node` function. Removed all `incident_triage` workflow imports and nodes. Entry point changed from `router` to `llm`. Graph is now: `START → llm → should_continue → tools → llm → END` |
| `agent/prompts.py` | Removed `ROUTER_PROMPT` entirely. Updated `SYSTEM_PROMPT` with numbered response steps: "1. ALWAYS search KB first" |
| `agent/state.py` | Removed 5 fields: `current_workflow`, `workflow_step`, `workflow_status`, `workflow_data`, `incident_result`. State now has only: `messages`, `tool_calls_log`, `iteration_count` |
| `main.py` | Removed all references to deleted state fields in `/chat` and `/chat/stream` endpoints. Removed `workflow_status` from `ChatResponse` model |

### Tool Description Changes

The tool descriptions were rewritten to serve as routing logic:

**`rag_search`** (default tool):
> "Search the platform knowledge base for ANY information... ALWAYS use this tool first before answering any question. When in doubt, search."

**`assess_incident`** (restricted tool):
> "ONLY use when the user reports a SPECIFIC, ACTIVE infrastructure problem... Do NOT use for general questions, lookups, or 'can you check' requests."

**`create_checklist`** (explicit trigger):
> "Only use when the user explicitly asks for a checklist or action plan."

### Before vs After

```
# BEFORE: Two decision points, fragile routing
User → Router LLM → "incident or general?" → different paths

# AFTER: One decision point, robust tool selection  
User → LLM with tools → "which tool(s) do I need?" → execute → respond
```

### Verification

After redeployment to ECS:
- Health endpoint: ✅ `{"status":"healthy","agent":true}`
- All queries now go through single ReAct loop
- "Can you check" queries no longer misroute to incident triage
- Tool descriptions guide the LLM to search KB first for every question
