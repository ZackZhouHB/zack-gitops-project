# Goal Clarification — From PoC Chatbot to Agentic Workflow

> **Created:** 2026-03-26  
> **Purpose:** Clear alignment on what exists, what we're doing, and why  

---

## 1. What the Existing PoC Does (Lab Account)

### What It Was Designed For

The PoC was built to answer a simple question: **"Can AI help NESA staff find information about teacher accreditation faster?"**

It is a **Q&A chatbot** — staff type a question, the system searches documents, and an LLM generates an answer.

### What It Covers

```
INPUT:  A question about teacher accreditation policy
PROCESS: Search knowledge base (RAG) → Generate answer (LLM)
OUTPUT: A text response with information from NESA documents
```

**Knowledge sources:** NESA website pages, accreditation manual, Confluence internal docs (TSAA space), PDF policy documents, professional standards.

### What It Achieves

- ✅ Staff can ask natural language questions about accreditation
- ✅ Answers are grounded in official NESA documentation
- ✅ Deployed on production-grade infrastructure (ECS Fargate, ALB, Cognito)
- ✅ Knowledge base combines 5 different data sources into one searchable index
- ✅ Proved the concept — validated that AI can assist with accreditation queries

### What It Does NOT Do

- ❌ Cannot perform any actions (no tool calling)
- ❌ Cannot look up a teacher's accreditation status
- ❌ Cannot guide someone through a multi-step process
- ❌ Cannot create, update, or track anything
- ❌ Cannot remember previous conversations
- ❌ Cannot hand off to a human when it's stuck
- ❌ Has no connection to any internal NESA system

**In one sentence:** The PoC proves AI can read your documents. It does not prove AI can do your work.

---

## 2. What We're Trying to Enhance

### The Core Problem

The PoC is a **pipeline** — question in, answer out, done. But teacher accreditation is a **workflow** — it has steps, decisions, dependencies, and actions that need to happen in order.

```
PoC (Pipeline):        Question → Answer → End

What's Needed (Agent): Goal → Plan → Act → Observe → Decide → Act → ... → Complete
```

### What We Want to Build

An **AI agent** that doesn't just answer questions about accreditation, but **assists with accreditation workflows**:

| PoC Capability | Agent Capability |
|---|---|
| "What are the requirements for Proficient Teacher?" | "Check if Teacher X meets all Proficient requirements and tell me what's missing" |
| "What's the process for accreditation renewal?" | "Guide me through renewing my accreditation step by step" |
| "What documents do I need?" | "Here's your checklist — items 1, 3, 5 are complete, items 2, 4 still needed" |
| "Who do I contact about my application?" | "I've escalated your case to the accreditation team with a summary" |

### Specific Gaps We're Addressing

| Gap | What It Means | How We Fix It |
|---|---|---|
| **No tool calling** | Agent can only talk, not act | Add tools: DB queries, policy checks, notifications |
| **No state management** | Every conversation starts from zero | Add LangGraph checkpointing + PostgreSQL |
| **No multi-step workflows** | Can't guide through processes | Build LangGraph state machines with loops/branches |
| **No system integration** | Isolated from real NESA systems | Add tool functions that connect to APIs/databases |
| **No human-in-the-loop** | Can't escalate or ask for approval | Add escalation tool with pause/resume |
| **No memory** | Forgets everything between sessions | Add conversation history in PostgreSQL |

---

## 3. Why Not Just Fix the PoC in the Lab Account?

### Option A: Enhance the Existing PoC in Lab

| Pros | Cons |
|---|---|
| Infrastructure already exists | Shared org account — risk of breaking things |
| Knowledge base already populated | Tied to Bedrock Agent (limited orchestration) |
| Frontend already deployed | OpenSearch Serverless costs $350/month |
| | 3 of 5 data sources are broken (FAILED/STOPPED) |
| | CDK stacks are someone else's code |
| | Bedrock Agents have limited control vs LangGraph |
| | Can't experiment freely in a shared environment |

### Option B: Replicate Full AWS Stack in Sandbox

| Pros | Cons |
|---|---|
| Your own account, full control | Still ~$450-500/month in AWS costs |
| Clean deployment | Still heavy AWS infrastructure work |
| | 80% of time spent on infra, 20% on agent logic |
| | ECS, ALB, VPC, Cognito are not what we're learning |

### Option C: Go Local-First ✅ (What We Chose)

| Pros | Cons |
|---|---|
| ~$5-15/month (Bedrock API only) | Not production-ready (but that's not the goal) |
| 90% time on agent logic, 10% on infra | Need to set up Docker Compose |
| Full control, experiment freely | No real users testing it |
| `docker-compose up` and go | |
| LangGraph gives full orchestration control | |
| All agent code is cloud-portable | |
| Learn the hard skills (agents, tools, state) | |
| No risk to org infrastructure | |

---

## 4. What We're Doing Locally and Why

### What We Keep From the PoC

| Component | What We Reuse | Why |
|---|---|---|
| **RAG pattern** | Same idea — embed documents, search, retrieve | It works; RAG becomes one tool |
| **Embedding model** | Titan Embed V2 (1024d) via Bedrock API | Same model, just called remotely |
| **LLM** | Claude via Bedrock API | Same provider, newer model |
| **System prompt** | NESA chatbot identity and response guidelines | Good prompt engineering, adapt for agent |
| **Domain knowledge** | Teacher accreditation use case | Same business context |

### What We Replace

| Original (AWS) | Local Replacement | Why |
|---|---|---|
| OpenSearch Serverless | Weaviate (Docker) | Free, you know it, same capability |
| ECS Fargate | Docker Compose | Free, instant, no deploy pipeline |
| ALB + VPC | localhost | Not needed for dev |
| Cognito | None | Not needed for dev |
| Bedrock Agent (managed) | LangGraph (code) | Full control over orchestration |
| CloudFormation/CDK | docker-compose.yml | Simpler, faster iteration |

### What We Add (New — The Agent Skills)

| New Component | Purpose | This Is the Learning Goal |
|---|---|---|
| **LangGraph** | Agent orchestration — state machine with loops, branches, checkpoints | Core agent engineering skill |
| **Tool calling** | Agent decides which function to call and when | Core agent engineering skill |
| **PostgreSQL** | Workflow state, conversation history, checkpoints | State management |
| **Multiple tools** | RAG, DB, policy check, email, escalation | Agent-tool integration |
| **Human-in-the-loop** | Pause workflow, ask human, resume | Production agent pattern |
| **Error recovery** | Retry, compensate, escalate on failures | Production reliability |
| **MCP (later)** | Standard protocol for tool discovery | Industry standard |

---

## 5. What Success Looks Like

### Before (PoC)

```
User: "What are the requirements for Proficient Teacher accreditation?"
Bot:  "Based on NESA guidelines, Proficient Teacher accreditation requires..."
      (A paragraph of information. End of interaction.)
```

### After (Agent)

```
User: "I'm a provisional teacher. Help me understand what I need to 
       do to get Proficient Teacher accreditation."

Agent: I'll help you work through this. Let me check the requirements.
       [Tool: rag_search("Proficient Teacher accreditation requirements")]
       
       For Proficient Teacher accreditation, you need to:
       1. Complete your provisional period (usually 1-2 years)
       2. Document evidence against the Australian Professional Standards
       3. Have your supervisor complete observation reports
       4. Submit your accreditation application
       
       Let me check which standards you'll need evidence for.
       [Tool: policy_check("proficient_teacher_standards")]
       
       There are 7 standards across 3 domains. Would you like me to 
       create a checklist you can track your progress against?

User: Yes please.

Agent: [Tool: create_checklist(teacher_id, "proficient_accreditation")]
       
       I've created your checklist. Here's where you stand:
       ☐ Standard 1: Know students and how they learn
       ☐ Standard 2: Know the content and how to teach it
       ☐ Standard 3: Plan for and implement effective teaching
       ...
       
       Would you like guidance on what evidence to collect for any 
       specific standard?

User: Standard 1 — what kind of evidence works?

Agent: [Tool: rag_search("Standard 1 evidence examples Proficient")]
       
       For Standard 1 at Proficient level, common evidence includes:
       • Lesson plans showing differentiation for diverse learners
       • Student work samples with your feedback annotations
       • Records of parent/carer communication
       ...
       
       Should I save this guidance to your checklist for Standard 1?
```

**The difference:** The agent doesn't just tell you about accreditation. It **works with you through** accreditation — step by step, tracking state, using tools, adapting to your situation.

---

## 6. Summary

```
WHERE WE STARTED:   A PoC chatbot that answers questions (Lab account)
WHAT'S MISSING:     Tool calling, workflows, state, integration, actions
WHY NOT FIX IN AWS: Cost ($500/mo), complexity, shared account risk, infra distraction
WHAT WE DO:         Build locally (Docker), call Bedrock API ($5-15/mo)
WHAT WE LEARN:      LangGraph, tool calling, state management, multi-step workflows
WHAT WE PROVE:      AI can assist with accreditation WORKFLOWS, not just answer questions
CLOUD-READY:        Agent code is 100% portable — swap Docker for ECS when ready
```
