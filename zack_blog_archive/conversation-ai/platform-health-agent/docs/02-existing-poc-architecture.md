# Existing Teacher Accreditation PoC — Architecture & Components

> **Created:** 2026-03-25  
> **AWS Account:** 315720945463 (Lab)  
> **Region:** ap-southeast-2 (Sydney)  
> **Deployed:** November 2024  

---

## 1. High-Level Architecture

```
                        ┌──────────────────────┐
                        │      End Users       │
                        │   (NESA Staff via     │
                        │    Web Browser)       │
                        └──────────┬───────────┘
                                   │ HTTPS
                        ┌──────────▼───────────┐
                        │   Cognito User Pool   │
                        │   (Authentication)    │
                        │   Stack: chatbot-     │
                        │   cognito-stack       │
                        └──────────┬───────────┘
                                   │
                        ┌──────────▼───────────┐
                        │   ALB + ECS Fargate   │
                        │   (Chatbot Frontend)  │
                        │   Stack: chatbot-     │
                        │   main-stack          │
                        │   Cluster: chatbot-   │
                        │   ecs-cluster         │
                        └──────────┬───────────┘
                                   │ Bedrock API
                        ┌──────────▼───────────┐
                        │   Bedrock Agent       │
                        │   "ta-agent-quick-    │
                        │    start-0mns4"       │
                        │   (CFE1VRZGDL)        │
                        │   Model: Claude 3.5   │
                        │   Sonnet v2           │
                        └──────────┬───────────┘
                                   │ RAG Retrieval
                        ┌──────────▼───────────┐
                        │   Knowledge Base      │
                        │   "teacher-           │
                        │    accreditation-     │
                        │    kb-01"             │
                        │   (0MHCHNAZTB)        │
                        └──────────┬───────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    │              │              │
              ┌─────▼─────┐ ┌────▼────┐  ┌──────▼──────┐
              │ OpenSearch │ │   S3    │  │  Web/Confl  │
              │ Serverless │ │  Docs   │  │  Crawlers   │
              │ (Vectors)  │ │  Store  │  │  (5 srcs)   │
              └───────────┘ └─────────┘  └─────────────┘
```

---

## 2. Component Inventory

### 2.1 Frontend & Auth

| Component | Type | Details |
|---|---|---|
| **chatbot-cognito-stack** | CloudFormation | Cognito User Pool + Client for auth |
| **chatbot-main-stack** | CloudFormation (CDK) | ECS Fargate service with ALB |
| **chatbot-ecs-cluster** | ECS Cluster | Runs the chatbot web application |
| **Fargate Service** | ECS Service | Auto-scaling (CPU + Memory targets) |
| **Security Group** | EC2 SG | `sg-0dca382f8b1e50b6e` — ALB → Fargate ingress |

**Infrastructure-as-Code:** CDK-based (CloudFormation stacks deployed Nov 2024).

### 2.2 Bedrock Agent — Teacher Accreditation

| Property | Value |
|---|---|
| **Agent Name** | `ta-agent-quick-start-0mns4` |
| **Agent ID** | `CFE1VRZGDL` |
| **Status** | PREPARED |
| **Model** | `anthropic.claude-3-5-sonnet-20241022-v2:0` |
| **Created** | 2024-11-01 |
| **Knowledge Base** | `teacher-accreditation-kb-01` (0MHCHNAZTB) |
| **Action Groups** | `UserInputAction` only (no custom tools) |

**Agent Instruction (System Prompt):**

The agent is configured as a NESA chatbot with these rules:
- Identifies as "NESA chatbot" — never mentions Claude/AI/LLM
- Consults knowledge base before every response
- Provides confidence indicators ("Based on current NESA guidelines...")
- Uses structured response format (summary → key points → references)
- Focuses on: accreditation processes, policies, compliance, professional standards
- **Excludes** documents titled with "ARCHIVE"
- **Excludes** documents about the 2021 COVID-19 pause on accreditation actions

### 2.3 Knowledge Base

| Property | Value |
|---|---|
| **KB Name** | `teacher-accreditation-kb-01` |
| **KB ID** | `0MHCHNAZTB` |
| **Status** | ACTIVE |
| **Vector Store** | OpenSearch Serverless |
| **Collection** | `bedrock-knowledge-base-x0l0jc` or similar |
| **Created** | 2024-11-01 |

### 2.4 Knowledge Base Data Sources (5 Sources)

#### Source 1: NESA Website — Accreditation Pages (Web Crawler)
| Property | Value |
|---|---|
| **ID** | `ALQCX2RR9R` |
| **Type** | WEB |
| **Seed URLs** | `nsw.gov.au/education-and-training/nesa/teacher-accreditation` |
| | `…/manage-accreditation/non-practising-accreditation` |
| | `…/manage-accreditation/non-teaching-options` |
| **Max Pages** | 25,000 |
| **Rate Limit** | 300 req/s |

#### Source 2: NESA Website — Accreditation Manual + Education NSW (Web Crawler)
| Property | Value |
|---|---|
| **ID** | `KGJW1QI4JY` |
| **Type** | WEB |
| **Seed URLs** | `…/resources/teacher-accreditation-manual` |
| | `education.nsw.gov.au/…/nesa-accreditation` |
| | `nsw.gov.au/…/teacher-accreditation` |
| **Max Pages** | 5,000 |
| **Rate Limit** | 200 req/s |

#### Source 3: Confluence — TSAA Space (Confluence Connector)
| Property | Value |
|---|---|
| **ID** | `OZPJSCZN0W` |
| **Type** | CONFLUENCE |
| **Host** | `educationstandards.atlassian.net` |
| **Auth** | Basic (credentials in Secrets Manager: `taabedrock-2JPZDH`) |
| **Space Filter** | `^TSAA$` (Teacher Standards and Accreditation) |
| **Exclusions** | Pages matching `.*ARCHIVE.*` |

#### Source 4: S3 — PDF Documents (S3 Bucket)
| Property | Value |
|---|---|
| **ID** | `UGIL5F2CMP` |
| **Type** | S3 |
| **Bucket** | `amazonbedrock-lab-datastore` |
| **Contents** | Accreditation PDFs — university reports (Alphacrucis, Avondale, CSU, etc.), fact sheets, applicant guides, accreditation procedure documents |
| **Note** | Some files in `Failed Files - Python upload/` subfolder — may have ingestion issues |

#### Source 5: NESA Website — Standards (Web Crawler)
| Property | Value |
|---|---|
| **ID** | `YPQRMBTLKC` |
| **Type** | WEB |
| **Seed URLs** | `…/teacher-accreditation/` |
| | `…/resources/standards` |
| **Max Pages** | 25,000 |
| **Rate Limit** | 300 req/s |

### 2.5 Other Bedrock Agents (Multi-Agent PoC)

A separate multi-agent system exists for **architecture design** workflows:

| Agent | ID | Model | Purpose | Tools |
|---|---|---|---|---|
| **Requirements** | `CNNAROMDWS` | Claude 3 Sonnet | Extract requirements from KB docs | RAG (KB) |
| **Architecture** | `VXWF1FN81U` | Claude 3 Sonnet | Design AWS solutions | MCP tools (searchDocs, readDocs, getPricing) |
| **Cost** | `KA1XLDIJSM` | Claude 3 Sonnet | Cost analysis & optimisation | MCP tools (getPricing, searchDocs, readDocs) |
| **Security** | `FJSECC9TML` | Claude 3 Sonnet | Security review & compliance | MCP tools (searchDocs, readDocs, getPricing) |

**Pattern:** Requirements Agent reads KB → feeds structured output → Architecture/Cost/Security agents consume and analyse.

This is a **multi-agent orchestration pattern** already in use — directly applicable to the agentic workflow we want to build.

### 2.6 Additional Agent
| Agent | ID | Model | Purpose |
|---|---|---|---|
| **sb-agent** | `ZEFGDHXRRV` | Claude 3 Sonnet | NESA courses expert (simple Q&A) |

### 2.7 Supporting Infrastructure

| Component | Details |
|---|---|
| **OpenSearch Serverless** | 3 collections for vector storage |
| **S3 Buckets** | `amazonbedrock-lab-datastore` (PDFs), `bedrock-agents-poc-*` (PoC docs) |
| **Secrets Manager** | Confluence credentials (`taabedrock-2JPZDH`) |
| **Cognito** | User pool + client for chatbot auth |
| **VPC** | Custom VPC with security groups for Fargate |
| **CloudWatch Logs** | Log group for Fargate tasks |
| **IAM** | Execution roles, task roles, Bedrock access policies |

---

## 3. Current Workflow (PoC — As-Is)

```
┌─────────────────────────────────────────────────────────────┐
│                    CURRENT PoC WORKFLOW                      │
│                                                             │
│  1. NESA staff member opens chatbot web UI                  │
│  2. Authenticates via Cognito                               │
│  3. Types a question about teacher accreditation            │
│     e.g., "What are the requirements for Proficient        │
│           Teacher accreditation?"                           │
│  4. Bedrock Agent receives question                         │
│  5. Agent queries Knowledge Base (RAG)                      │
│     - Searches OpenSearch Serverless vectors                │
│     - Retrieves relevant chunks from web/confluence/S3 docs │
│  6. Agent generates answer using Claude 3.5 Sonnet          │
│  7. Answer returned to user in chat UI                      │
│                                                             │
│  That's it. One-shot Q&A. No workflow. No actions.          │
└─────────────────────────────────────────────────────────────┘
```

### What It CAN Do
- ✅ Answer policy questions about teacher accreditation
- ✅ Reference NESA documentation, manuals, and standards
- ✅ Pull from Confluence internal knowledge (TSAA space)
- ✅ Handle basic follow-up questions within a conversation

### What It CANNOT Do
- ❌ Check a specific teacher's accreditation status
- ❌ Look up or create records in any system
- ❌ Guide a teacher through a multi-step process with state
- ❌ Validate documents or qualifications
- ❌ Trigger notifications or escalations
- ❌ Track progress against requirements
- ❌ Integrate with any internal NESA systems (eTAMS, etc.)
- ❌ Hand off to a human with conversation context
- ❌ Remember previous sessions or user preferences

---

## 4. Architecture Strengths & Gaps

### ✅ Strengths (Reusable)

| Component | Why It's Valuable |
|---|---|
| Knowledge Base (5 sources) | Rich corpus — web, Confluence, PDFs. Solid RAG foundation |
| OpenSearch Serverless | Production-grade vector store, already indexed |
| ECS Fargate + ALB | Scalable, production-ready frontend hosting |
| Cognito auth | Enterprise auth already wired |
| CDK/CloudFormation | Infrastructure as code — repeatable |
| Multi-agent pattern (4 PoC agents) | Proven orchestration pattern we can adapt |
| Claude 3.5 Sonnet | Strong model, supports tool calling natively |

### 🔴 Gaps (Need to Add)

| Gap | What's Needed |
|---|---|
| **Tool Calling** | Agent has only `UserInputAction` — no custom tools defined |
| **External System Integration** | No connection to eTAMS, databases, or internal APIs |
| **State Management** | No conversation checkpointing, no workflow state |
| **Multi-Step Workflows** | No ability to guide through processes step-by-step |
| **Human-in-the-Loop** | No approval gates or escalation paths |
| **Action Groups** | No Lambda-backed actions for the TA agent |
| **Monitoring & Eval** | No conversation logging, no quality metrics |
| **Agent Orchestration** | Multi-agent pattern exists but not applied to TA domain |

---

## 5. Data Landscape

### Documents in the Knowledge Base

| Source | Content Type | Examples |
|---|---|---|
| NESA Website | Public accreditation info | Requirements, processes, non-practising, non-teaching options |
| Accreditation Manual | Official procedures | Full teacher accreditation manual |
| Education NSW | Career/accreditation info | NESA accreditation for teaching roles |
| Confluence (TSAA) | Internal knowledge | Internal procedures, team documentation (excl. ARCHIVE pages) |
| S3 PDFs | Policy documents | University accreditation reports (Alphacrucis, Avondale, CSU), fact sheets, applicant guides, procedure docs |
| Standards | Professional standards | Teaching standards framework |

### Known Data Issues
- S3 bucket has files in `Failed Files - Python upload/` — suggests some PDF ingestion failures during setup
- Some PDFs have URL-encoded filenames (double-uploaded with different encoding)
- Confluence connector uses Basic auth — may need review for security posture

---

## 6. Summary: What We Have vs What We Need

```
HAVE (PoC - Nov 2024)                   NEED (Agentic - 2026)
─────────────────────                    ──────────────────────
✅ Knowledge Base (RAG)          →    ✅ Keep as one tool among many
✅ Bedrock Agent (Q&A)           →    🔄 Evolve into workflow orchestrator  
✅ Frontend (ECS/Fargate)        →    🔄 Enhance UI for multi-step flows
✅ Auth (Cognito)                →    ✅ Keep
✅ Multi-agent pattern           →    🔄 Apply to TA domain
❌ Tool calling                  →    🆕 Add Lambda-backed action groups
❌ System integration            →    🆕 Connect to eTAMS / internal APIs
❌ State management              →    🆕 Add LangGraph or Bedrock sessions
❌ Workflow orchestration         →    🆕 Multi-step accreditation flows
❌ Human-in-the-loop             →    🆕 Approval gates for sensitive actions
❌ Monitoring & evaluation       →    🆕 Conversation logging, quality KPIs
```

---

## 7. Next Steps

→ See next document for agentic workflow design and implementation plan.
