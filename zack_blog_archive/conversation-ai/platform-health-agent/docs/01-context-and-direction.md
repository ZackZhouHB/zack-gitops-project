# Context & Direction: From Conversational AI to Agentic Workflows

> **Created:** 2026-03-25  
> **Author:** Hongbo Zhou  
> **Location:** ~/zz/Documents/conversation-ai/teacher-accreditation-agent/

---

## 1. How We Got Here

### Starting Point: A Conversational AI Job Description

We reviewed a JD for **AI Engineer – Conversational** at 4WD Supacentre (Sydney). The role focused on building AI chatbots and AI voice agents for ecommerce customer service, integrated with Salesforce CRM.

### Skills Gap Analysis

| Area | Our Experience | JD Requirement |
|---|---|---|
| LLM / GenAI | ✅ AWS Bedrock, RAG pipelines | ✅ Match |
| Infrastructure | ✅ Docker, EKS, K8s | ✅ Match |
| Conversational AI platforms | ❌ No Lex/Einstein/Genesys experience | 🔴 Gap |
| Voice/Telephony | ❌ No TTS/STT/phone integration | 🔴 Gap |
| Salesforce CRM | ❌ None | 🔴 Gap |
| Intent-based NLU | ❌ No intent/slot/dialogue design | 🔴 Gap |

### Decision: Pass on the Role

- Company is in early stage of AI adoption (catching up, not innovating)
- 5 days in-office is not ideal
- Conversational AI (chatbots, voice bots) is a **mature, saturating field** — not the cutting edge

### The Real Opportunity: Agentic Workflows

Key insight from industry analysis:

> *"The chatbot industry is saturating, but Agentic Engineering — building systems that actually work — is where the real complexity (and the real money) is."*
>
> *"Building a RAG app proves you can handle Data. Building an Agent proves you can handle Workflow."*

**AI Hype Hierarchy (2026):**

```
🔥🔥🔥 AI Agents (autonomous, multi-step reasoning)     ← WHERE WE WANT TO BE
🔥🔥🔥 AI Coding (Copilot, Cursor, Devin-style)
🔥🔥  RAG / Enterprise Knowledge Systems                ← WHERE WE ARE
🔥🔥  Multi-modal AI (vision + voice + text)
🔥    Conversational AI (chatbots, voice bots)           ← THE JD WE PASSED ON
```

---

## 2. The Paradigm Shift: RAG → Agent

### What We've Been Building (Pipeline)

```
User Question → Retrieve from Docs → LLM Generates Answer → Response
```

- Fixed flow, one-shot, stateless
- Answers questions about things
- No actions, no side effects

### What We Need to Build (Agent)

```
User Goal → LLM Reasons & Plans → Picks Tool → Executes → Observes Result
                    ↑                                            │
                    └──── Loops until task is complete ───────────┘
```

- Dynamic flow, multi-step, stateful
- Actually **does** things (creates records, sends emails, updates systems)
- Handles errors, retries, escalates

### The Key Differences

| Dimension | RAG (What We Have) | Agent (What We Need) |
|---|---|---|
| Input | A question | A goal / task |
| Output | An answer | A completed workflow |
| Flow | Linear pipeline | Loop with branching |
| State | Stateless | Checkpointed state |
| Tools | Just retrieval | Multiple (DB, API, email, RAG, etc.) |
| Errors | Retry search | Recover, compensate, escalate |
| Side effects | None | Real actions with consequences |

---

## 3. Why NESA Teacher Accreditation Is the Perfect Project

Instead of building a fake ecommerce demo, we discovered that **our own organisation (NESA)** has an existing PoC that needs to be matured:

> *"Building on the success of last year's proof of concept for teacher accreditation chatbot to support business workflows, it is time to mature the PoC product into an operationalised application."*

### Why This Is Better Than a Demo Project

| Factor | Fake Demo | NESA Teacher Accreditation |
|---|---|---|
| Real data | Mock data | Actual NESA policy documents, Confluence, web pages |
| Real users | Imagined personas | NESA staff, teachers, principals |
| Real infrastructure | Build from scratch | Existing AWS Bedrock agents, KB, ECS, Cognito |
| Real business mandate | Self-motivated | Executive sponsorship to operationalise |
| Career impact | Portfolio piece | Actual delivery for your employer |
| Complexity | Simplified | Real-world edge cases, compliance, multi-stakeholder |

### The Vision

**Current state:** A chatbot that answers questions about teacher accreditation policy.

**Target state:** An AI agent that assists with the teacher accreditation **workflow** end-to-end — checking eligibility, tracking requirements, guiding through processes, updating records, and escalating when needed.

---

## 4. What We're Going to Do

### Phase 1: Understand the Existing PoC
- Document current architecture and components (see `02-existing-poc-architecture.md`)
- Identify what works, what's missing, and what to reuse

### Phase 2: Design the Agentic Architecture
- Map the teacher accreditation workflow into agent tasks
- Define tools the agent needs (KB search, DB lookup, case management, etc.)
- Design the LangGraph state machine with loops, branches, and checkpoints

### Phase 3: Build Iteratively
- Start with one workflow (e.g., "Check my accreditation status")
- Add tool calling, then multi-step flows, then error recovery
- Evolve from single agent to multi-agent orchestration

### Skills We'll Gain

| Skill | How We Learn It |
|---|---|
| LangGraph (loops, checkpoints, state) | Building the agent orchestration |
| Tool calling (function calling API) | Connecting agent to real systems |
| MCP (Model Context Protocol) | Exposing tools in a standard way |
| Multi-agent patterns | Leveraging existing 4-agent PoC pattern |
| Human-in-the-loop | Approval gates for sensitive actions |
| Production agent deployment | ECS/Fargate (already have infra) |
| Agent evaluation & monitoring | KPIs for workflow completion, accuracy |

---

## 5. Success Criteria

When done, we should be able to say:

> "I evolved a NESA teacher accreditation chatbot PoC from a simple RAG Q&A system into a production agentic workflow that handles multi-step accreditation processes. The agent uses LangGraph with tool calling via MCP, includes human-in-the-loop for compliance decisions, checkpoints state across conversation turns, and orchestrates multiple sub-agents for requirements analysis, policy lookup, and case management."

That's a fundamentally different story from "I built a RAG chatbot."
