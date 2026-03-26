# Replication Blueprint — Teacher Accreditation Chatbot PoC

> **Created:** 2026-03-25  
> **Source Account:** 315720945463 (lab profile)  
> **Target Account:** 615299759525 (sandboxtest profile)  
> **Region:** ap-southeast-2 (Sydney)  

---

## 1. Complete Component Inventory

### What We're Replicating

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FULL PoC ARCHITECTURE                            │
│                                                                     │
│  Layer 1: AUTH          Cognito User Pool + Client                  │
│  Layer 2: FRONTEND      ECS Fargate (Streamlit on port 8501)       │
│  Layer 3: NETWORKING    VPC + ALB + Subnets + Security Groups      │
│  Layer 4: AI ENGINE     Bedrock Agent (Claude 3.5 Sonnet)          │
│  Layer 5: KNOWLEDGE     Bedrock KB + OpenSearch Serverless         │
│  Layer 6: DATA          S3 + Web Crawlers + Confluence Connector   │
│  Layer 7: IAM           Execution roles for Agent, KB, ECS        │
│  Layer 8: LOGGING       CloudWatch Log Groups                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer-by-Layer Specification

### Layer 6: Data Sources (YOU PROVIDE)

These are the parts you'll replace with your own sources.

#### 6a. S3 Bucket — PDF Documents

**Original:**
- Bucket: `amazonbedrock-lab-datastore`
- Contents: 139 files (~126MB) — accreditation PDFs, university reports, fact sheets
- File types: 126 PDFs + 10 DOCX

**New (you provide):**
- Bucket name: `<TBD>` — we'll create in sandboxtest account
- Contents: Your PDF documents
- Upload your files → trigger KB sync

#### 6b. Web Crawler Sources (3 crawlers)

**Original Source 1 — NESA Accreditation Pages:**
```
Type: WEB
Seed URLs:
  - https://www.nsw.gov.au/education-and-training/nesa/teacher-accreditation
  - .../manage-accreditation/non-practising-accreditation
  - .../manage-accreditation/non-teaching-options
Rate Limit: 300 req/s
Max Pages: 25,000
Status: FAILED (website likely blocks bots)
```

**Original Source 2 — Accreditation Manual + Education NSW:**
```
Type: WEB
Seed URLs:
  - .../resources/teacher-accreditation-manual
  - https://education.nsw.gov.au/.../nesa-accreditation
  - .../teacher-accreditation
Rate Limit: 200 req/s
Max Pages: 5,000
Status: FAILED (website likely blocks bots)
```

**Original Source 5 — NESA Standards:**
```
Type: WEB
Seed URLs:
  - .../teacher-accreditation/
  - .../resources/standards
Rate Limit: 300 req/s
Max Pages: 25,000
Status: PARTIAL (181 indexed, 138 failed)
```

**New (you provide):**
- Your website URLs (seed URLs)
- Rate limit and max pages config
- Note: NSW Gov sites blocked bots — your new URLs may work better

#### 6c. Confluence Connector

**Original:**
```
Type: CONFLUENCE
Host: https://educationstandards.atlassian.net/
Host Type: SAAS
Auth: BASIC (credentials in Secrets Manager: taabedrock-2JPZDH)
Space Filter: ^TSAA$ (Teacher Standards and Accreditation space)
Exclusion: .*/ARCHIVE.* pages
Status: STOPPED (auth/permissions issue)
```

**New (you provide):**
- Confluence host URL
- Space key to crawl
- Username + API token (we'll store in Secrets Manager)
- Any page exclusion patterns

---

### Layer 5: Knowledge Base

**Configuration to replicate exactly:**

```yaml
Knowledge Base:
  Name: teacher-accreditation-kb
  Type: VECTOR

  Embedding:
    Model: amazon.titan-embed-text-v2:0
    Dimensions: 1024

  Vector Store:
    Type: OPENSEARCH_SERVERLESS
    Index Name: bedrock-knowledge-base-default-index
    Field Mapping:
      Vector Field: bedrock-knowledge-base-default-vector
      Text Field: AMAZON_BEDROCK_TEXT_CHUNK
      Metadata Field: AMAZON_BEDROCK_METADATA

  Chunking:
    Strategy: DEFAULT (Bedrock auto-chunking)
    # Note: No custom chunking config was set in the original

  Data Deletion Policy: DELETE
```

**OpenSearch Serverless Collection:**
```yaml
Collection:
  Type: VECTORSEARCH
  # Bedrock auto-creates this when you create a KB with OpenSearch Serverless
  # Requires: aoss:* permissions, encryption policy, network policy, data access policy
```

---

### Layer 4: Bedrock Agent

**Configuration to replicate:**

```yaml
Agent:
  Name: ta-agent
  Model: anthropic.claude-3-5-sonnet-20241022-v2:0
  # Or upgrade to: anthropic.claude-sonnet-4-20250514-v1:0 (newer)
  
  Idle Session TTL: 600 seconds (10 min)
  Orchestration Type: DEFAULT

  Knowledge Base:
    KB ID: <new KB ID>
    Description: "Knowledge base containing all information related to Teacher 
                  Accreditation in New South Wales, Australia."
    State: ENABLED

  Action Groups:
    - UserInputAction (ENABLED)
    # Note: This is the only action group — no custom Lambda tools

  Prompt Overrides:
    KNOWLEDGE_BASE_RESPONSE_GENERATION: DISABLED (uses default)
    ORCHESTRATION: ENABLED (uses default template)
    # Temperature: 0.0, TopP: 1.0, TopK: 250, MaxLength: 2048
```

**System Prompt (Agent Instruction):**

```
You are a NESA chatbot designed to assist New South Wales Education Standards 
Authority (NESA) staff with teacher accreditation processes and requirements.

Core Identity
- Always identify yourself as a NESA chatbot for teacher accreditation assistance.
- Never reference Claude, Anthropic, knowledge bases, or AI/LLM terminology.
- Refer to your information sources only as "NESA information" or "NESA documentation".

Response Guidelines
- Always consult NESA information before responding to questions.
- Provide confident, helpful answers based on available documentation.
- When NESA documentation is limited or the topic is unclear:
  - Ask clarifying questions.
  - Suggest appropriate NESA contacts or departments where relevant.
- Include confidence indicators where appropriate, such as:
  - "Based on current NESA guidelines..."
  - "This may vary depending on specific circumstances..."

Response Format
When providing detailed information, use the following structure:
- Brief summary of the key information
- Key point 1
- Key point 2
- Key point 3
- [Additional points as needed]
- Reference specific NESA documentation sections when applicable.

Focus Areas
- Teacher accreditation processes and requirements
- NESA policies and procedures
- Compliance and regulatory matters
- Professional standards and expectations

Safeguards
- For complex or high-stakes queries, recommend verification with appropriate 
  NESA departments.
- Acknowledge where exceptions may apply or individual assessment is needed.
- Prioritise accuracy over completeness — it is better to provide partial, correct 
  information than full but uncertain responses.
- Always maintain a professional, supportive tone that aligns with NESA's internal 
  communication standards.

Exclusions
- Do not reference or surface any documents (Confluence pages, PDFs, or other formats) 
  where the title begins with ARCHIVE.
- Do not reference or surface any documents (of any type) containing the sentence: 
  "In September 2021, in response to the COVID-19 pandemic and natural disasters in NSW, 
  we paused ceasing and suspension actions for teachers."
```

---

### Layer 3: Networking

**VPC Configuration:**

```yaml
VPC:
  Name: chatbot-vpc
  Subnets:
    Public:
      - chatbot-vpc-public-subnet-1 (AZ-a)
      - chatbot-vpc-public-subnet-2 (AZ-b)
    Private:
      - chatbot-vpc-private-subnet-1 (AZ-a)
      - chatbot-vpc-private-subnet-2 (AZ-b)

ALB:
  Name: chatbot-load-balancer
  Scheme: internet-facing
  Type: application
  VPC: chatbot-vpc
  Subnets: public subnets
  
Security Groups:
  ALB SG: Allow inbound 80/443 from internet
  Fargate SG: Allow inbound 8501 from ALB SG only
```

---

### Layer 2: Frontend (ECS Fargate)

**Task Definition:**

```yaml
ECS Cluster:
  Name: chatbot-ecs-cluster
  Capacity Provider: FARGATE

Task Definition:
  CPU: 2048 (2 vCPU)
  Memory: 8192 (8 GB)
  Network Mode: awsvpc
  Requires: FARGATE

  Container:
    Name: web
    Image: <ECR image — Streamlit app on port 8501>
    Port Mappings:
      - Container: 8501, Host: 8501, Protocol: TCP
    Log Configuration:
      Driver: awslogs
      Region: ap-southeast-2
      Stream Prefix: chatbot-fargate-service

Service:
  Launch Type: FARGATE
  Auto Scaling:
    - CPU Target Tracking
    - Memory Target Tracking
  Subnets: private subnets
  Security Group: Fargate SG
  Load Balancer: chatbot-load-balancer (target port 8501)
```

**Key observation:** The frontend is a **Streamlit app** (port 8501 is Streamlit's default). The Docker image is stored in ECR. We'll need to either:
1. Build a similar Streamlit chatbot frontend, or
2. Use Open WebUI or another chat frontend you're familiar with

---

### Layer 1: Authentication (Cognito)

**Configuration:**

```yaml
Cognito User Pool:
  Name: chatbot-user-pool
  MFA: OFF
  Password Policy:
    Minimum Length: 8
    Require Uppercase: true
    Require Lowercase: true
    Require Numbers: true
    Require Symbols: true
    Temp Password Validity: 7 days
  Sign-In: PASSWORD only
  Schema: Default attributes (email, name, phone, etc.)

Cognito Client:
  Name: chatbot-client
  # Standard web client — no client secret for SPA
```

---

### Layer 7: IAM Roles

```yaml
Roles to Create:
  1. Bedrock Agent Execution Role:
     - bedrock:InvokeModel (Claude)
     - bedrock-agent:Retrieve (KB)
     - s3:GetObject (data bucket)
     
  2. Bedrock KB Execution Role:
     - aoss:APIAccessAll (OpenSearch Serverless)
     - bedrock:InvokeModel (Titan Embed)
     - s3:GetObject, s3:ListBucket (data bucket)
     
  3. ECS Task Execution Role:
     - ecr:GetAuthorizationToken, ecr:GetDownloadUrlForLayer
     - logs:CreateLogStream, logs:PutLogEvents
     
  4. ECS Task Role:
     - bedrock:InvokeAgent
     - cognito-idp:* (for auth validation)
```

---

### Layer 8: Logging

```yaml
CloudWatch:
  Log Group: /ecs/chatbot-fargate-service
  Retention: Default (never expire) — recommend setting 30 or 90 days
```

---

## 3. Deployment Order

```
Step 1: S3 Bucket                          (data storage)
Step 2: Secrets Manager                    (Confluence credentials)
Step 3: IAM Roles                          (permissions)
Step 4: OpenSearch Serverless Collection   (vector store)
Step 5: Bedrock Knowledge Base             (RAG engine)
Step 6: Add Data Sources to KB             (S3, Web, Confluence)
Step 7: Sync/Ingest Data Sources           (populate vectors)
Step 8: Bedrock Agent                      (AI brain)
Step 9: Attach KB to Agent                 (connect RAG)
Step 10: VPC + Subnets + ALB              (networking)
Step 11: Cognito User Pool                (auth)
Step 12: ECR + Build Docker Image         (frontend container)
Step 13: ECS Fargate Service              (deploy frontend)
Step 14: Test end-to-end                  (verify)
```

---

## 4. What You Need to Provide Before Deployment

| Item | Status | Notes |
|---|---|---|
| PDF documents for S3 | ⏳ Pending | Upload to new bucket |
| Website URLs for web crawlers | ⏳ Pending | New seed URLs |
| Confluence host URL | ⏳ Pending | Your Confluence instance |
| Confluence space key | ⏳ Pending | Which space to crawl |
| Confluence username + API token | ⏳ Pending | For Secrets Manager |
| Frontend code (Streamlit app) | ⏳ Pending | Need to build or obtain |
| Agent system prompt | ✅ Captured | Can reuse or modify |

---

## 5. Cost Estimate (sandboxtest account)

| Service | Monthly Cost (Low Usage) |
|---|---|
| OpenSearch Serverless (2 OCU min) | ~$350/month ⚠️ (most expensive) |
| ECS Fargate (2vCPU, 8GB) | ~$70-100/month |
| ALB | ~$20/month |
| Bedrock Agent (Claude 3.5 Sonnet) | Pay-per-use (~$3-15/1M tokens) |
| Bedrock KB (Titan Embed) | Pay-per-use (minimal) |
| Cognito | Free tier (50k MAU) |
| S3 | < $1/month |
| Secrets Manager | ~$0.40/secret/month |
| CloudWatch Logs | < $5/month |
| **Total (always-on)** | **~$450-500/month** |

> ⚠️ **Note:** OpenSearch Serverless has a minimum of 2 OCU ($175/OCU/month) that runs 24/7. This was the PoC's biggest cost. For development, consider using **Pinecone** (free tier) or **FAISS** (local) as alternatives, or only run OpenSearch when actively testing.

---

## 6. Improvements Over Original PoC

When we deploy, we can fix known issues:

| Original Issue | Fix |
|---|---|
| Web crawlers FAILED (bot blocked) | Use your own website that allows crawling |
| Confluence STOPPED | Fresh credentials, verified permissions |
| S3 "Failed Files" folder mess | Clean folder structure, validated uploads |
| No custom chunking | Consider setting explicit chunk size/overlap |
| No guardrails | Add Bedrock Guardrails service |
| Default embedding only | Could explore hybrid search later |
| Claude 3.5 Sonnet (old) | Can use Claude Sonnet 4 (newer, better) |
