# Step 9: Architecture & Design Decisions

> **Tutorial Series:** Deploying the Platform Health Insight Assistant on AWS
> **Part 1 of 8** (Steps 9–16) · Estimated reading time: 25 minutes

Welcome to the AWS deployment series! In Steps 1–8, you built a working AI assistant on your laptop using Docker Compose. It answered questions about platform documentation using **RAG** (Retrieval-Augmented Generation) — a technique where you *retrieve* relevant documents first, then *augment* the LLM's prompt with those documents so it can *generate* a grounded, accurate answer.

That local setup was great for learning. But it had real limitations. In this step, we'll design the cloud architecture that solves every one of those limitations — and explain *why* we chose each piece.

No code changes in this step — just understanding. By the end, you'll have a crystal-clear mental model of where everything lives in AWS and how data flows from a user's question to a sourced answer.

Let's go! 🚀

---

## 9.1 Why Move to AWS?

Your local setup (Docker Compose with Weaviate, PostgreSQL, FastAPI + LangGraph, and Streamlit) works — on your machine. Here's why that's not enough for a real team:

### Local Limitations

| Limitation | What Happens |
|---|---|
| **Manual document upload** | Every time your team publishes a new runbook, someone has to manually chunk it, embed it, and insert it into Weaviate. That's a Python script you run by hand. |
| **No auto-sync** | If a Confluence page gets updated at 2 AM, your assistant doesn't know. It still answers with stale information. |
| **Single user** | Only the person running `docker compose up` can use it. Your teammate across the hall can't access `localhost:8501`. |
| **No persistence across restarts** | Run `docker compose down` and your chat history might vanish. Docker volumes help, but they're tied to one machine. |
| **No authentication to AWS** | You're using `AWS_PROFILE=sandboxtest` — a local credential file. That doesn't work inside a container running in the cloud. |
| **Manual scaling** | Got 50 engineers who want to use this during an incident? Your laptop can't handle it. |

### What AWS Gives Us

| Benefit | How |
|---|---|
| **Auto-sync from S3** | Drop a PDF into an S3 bucket → a Lambda function automatically triggers the Knowledge Base to re-index. No human involved. |
| **Web crawler** | Bedrock Knowledge Base can crawl your documentation site on a schedule, pulling in new pages automatically. |
| **Confluence integration** | Same idea — the KB connects to your Confluence space and stays in sync. |
| **Managed vector search** | OpenSearch Serverless replaces Weaviate. AWS manages the cluster, scaling, and backups. |
| **Durable storage** | EFS (Elastic File System) and DynamoDB survive container restarts, redeployments, even AZ failures. |
| **Public access** | An ALB (Application Load Balancer) gives you a URL anyone on your network (or the internet) can reach. |
| **IAM-based auth** | No more credential files. Your containers get permissions through IAM (Identity and Access Management) roles attached to the task. |

> **Think of it this way:** Local is your prototype. AWS is your production deployment.

---

## 9.2 Architecture Overview

Let's visualize the whole system. We'll start with the big picture, then zoom into each data flow.

### 9.2.1 Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS CLOUD                                      │
│                                                                             │
│  ┌──────────────┐     ┌─────────────────────────────────────────────┐       │
│  │   USERS       │     │              DEFAULT VPC                    │       │
│  │  (Browser)    │     │                                             │       │
│  │    🧑‍💻 🧑‍💻 🧑‍💻    │     │  ┌──────────────────────────────────────┐  │       │
│  └──────┬───────┘     │  │     ALB (Application Load Balancer)    │  │       │
│         │              │  │                                        │  │       │
│         │ HTTPS        │  │   /        → Frontend (port 8501)     │  │       │
│         ▼              │  │   /chat    → Backend  (port 8000)     │  │       │
│  ┌──────────────┐     │  │   /health  → Backend  (port 8000)     │  │       │
│  │     ALB       │─────│──│                                        │  │       │
│  └──────────────┘     │  └──────────┬───────────────┬─────────────┘  │       │
│                        │            │               │                │       │
│                        │            ▼               ▼                │       │
│                        │  ┌─────────────┐  ┌────────────────┐       │       │
│                        │  │  FRONTEND   │  │   BACKEND      │       │       │
│                        │  │  (Streamlit)│  │ (FastAPI +     │       │       │
│                        │  │  ECS Fargate│  │  LangGraph)    │       │       │
│                        │  │             │  │  ECS Fargate   │       │       │
│                        │  └─────────────┘  └───────┬────────┘       │       │
│                        │                           │                │       │
│                        │         ┌─────────────────┼──────────┐     │       │
│                        │         ▼                 ▼          ▼     │       │
│                        │  ┌──────────┐   ┌──────────┐  ┌─────────┐ │       │
│                        │  │  EFS     │   │ DynamoDB │  │ Bedrock │ │       │
│                        │  │ (Chat    │   │(Checklists│  │  KB     │ │       │
│                        │  │  History)│   │Escalation)│  │         │ │       │
│                        │  └──────────┘   └──────────┘  └────┬────┘ │       │
│                        │                                    │      │       │
│                        │         ┌──────────────────────────┘      │       │
│                        │         ▼                                  │       │
│                        │  ┌──────────────────┐  ┌───────────────┐  │       │
│                        │  │ OpenSearch        │  │ Bedrock       │  │       │
│                        │  │ Serverless        │  │ Claude Sonnet │  │       │
│                        │  │ (Vector Index)    │  │ (LLM)        │  │       │
│                        │  └──────────────────┘  └───────────────┘  │       │
│                        │                                            │       │
│                        └────────────────────────────────────────────┘       │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                     DATA SOURCES                                     │   │
│  │                                                                      │   │
│  │  ┌──────────┐    ┌──────────────┐    ┌────────────────┐              │   │
│  │  │   S3     │    │  Web Crawler │    │  Confluence    │              │   │
│  │  │ (PDFs,  │    │ (Docs site)  │    │  (Wiki pages)  │              │   │
│  │  │  docs)   │    │              │    │                │              │   │
│  │  └─────┬────┘    └──────┬───────┘    └───────┬────────┘              │   │
│  │        │                │                    │                       │   │
│  │        │     ┌──────────┴────────────────────┘                       │   │
│  │        ▼     ▼                                                       │   │
│  │  ┌──────────────────┐                                                │   │
│  │  │  Bedrock KB      │──── auto-chunk ──── auto-embed ──── auto-index │   │
│  │  │  (Ingestion)     │                                                │   │
│  │  └──────────────────┘                                                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  SUPPORTING SERVICES                                                 │   │
│  │  ECR (images)  ·  Cloud Map (DNS)  ·  Secrets Manager  ·  KMS       │   │
│  │  Lambda (S3 trigger)  ·  CloudWatch (logs)  ·  IAM (permissions)    │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 9.2.2 Data Flow: User Query → Answer

This is the "happy path" — what happens when a user asks a question.

```
  🧑‍💻 User types: "How do I restart the payment service?"
   │
   ▼
┌──────────┐  GET /     ┌───────────┐
│ Browser  │──────────►│ ALB       │
└──────────┘            └─────┬─────┘
                              │ Routes to frontend target group
                              ▼
                       ┌───────────┐
                       │ Frontend  │  Streamlit renders the chat UI
                       │ (Fargate) │
                       └─────┬─────┘
                             │ POST /chat  (via Cloud Map DNS:
                             │              backend.platform-health:8000)
                             ▼
                       ┌───────────┐
                       │ Backend   │  FastAPI receives the request
                       │ (Fargate) │
                       └─────┬─────┘
                             │ Creates LangGraph ReAct agent
                             ▼
                       ┌───────────┐
                       │ LLM Node  │  Claude decides which tool to call
                       │ (ReAct)   │  based on tool descriptions
                       └─────┬─────┘
                             │ Calls rag_search tool
                             ▼
                       ┌───────────┐
                       │ Bedrock   │  RetrieveAndGenerate API
                       │ KB API    │
                       └─────┬─────┘
                             │ Searches vector index
                             ▼
                       ┌───────────┐
                       │ OpenSearch│  Finds top-K chunks by
                       │ Serverless│  cosine similarity
                       └─────┬─────┘
                             │ Returns chunks + scores
                             ▼
                       ┌───────────┐
                       │ Claude    │  Generates answer using
                       │ Sonnet 4  │  retrieved chunks as context
                       └─────┬─────┘
                             │ Streams response tokens (SSE)
                             ▼
                       ┌───────────┐
                       │ Frontend  │  Displays streaming answer
                       │           │  with source citations
                       └─────┬─────┘
                             │ Saves to EFS
                             ▼
                       ┌───────────┐
                       │ EFS       │  Chat history persisted
                       │           │  as JSON files
                       └───────────┘
```

### 9.2.3 Data Ingestion: S3 Upload → Searchable Index

This is how new documents become searchable — **automatically**.

```
  📄 Engineer uploads "payment-runbook-v3.pdf" to S3
   │
   ▼
┌──────────┐  PutObject event
│ S3 Bucket│──────────────────────┐
└──────────┘                      │
                                  ▼
                           ┌──────────┐
                           │ Lambda   │  kb_sync_trigger.py
                           │ Function │  Calls bedrock.start_ingestion_job()
                           └────┬─────┘
                                │
                                ▼
                         ┌────────────┐
                         │ Bedrock KB │  Ingestion pipeline:
                         │ Ingestion  │
                         └────┬───────┘
                              │
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
              ┌──────────┐ ┌───────┐ ┌──────────┐
              │ Parse &  │ │Embed  │ │ Index    │
              │ Chunk    │ │(Titan │ │(OpenSearch│
              │ document │ │ V2)   │ │Serverless)│
              └──────────┘ └───────┘ └──────────┘

  The whole pipeline runs automatically. No Python scripts.
  No manual chunking. No Weaviate client code.
```

### 9.2.4 Web Crawler Flow

Bedrock Knowledge Base includes a built-in web crawler data source. You configure it once, and it periodically crawls your documentation site.

```
  ⏰ Scheduled sync (e.g., every 24 hours)
   │
   ▼
┌──────────────┐
│ Bedrock KB   │  Web crawler data source configured with:
│ Web Crawler  │    - Seed URL: https://docs.yourplatform.com
│              │    - Scope: same-host only
│              │    - Depth: 3 levels
└──────┬───────┘
       │ Crawls pages, follows links
       ▼
┌──────────────┐
│ HTML → Text  │  Strips navigation, headers, footers
│ Extraction   │  Keeps meaningful content
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Chunk        │  Splits long pages into ~300-token chunks
│              │  with overlap for context continuity
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Embed        │  Each chunk → 1024-dimension vector
│ (Titan V2)   │  using Bedrock Titan Embed V2
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Index        │  Vectors stored in OpenSearch Serverless
│ (OpenSearch) │  Ready for similarity search
└──────────────┘
```

### 9.2.5 Confluence Flow

Confluence is an enterprise wiki. Many teams store runbooks, post-mortems, and architecture docs there. Bedrock KB has a native Confluence connector.

```
  ⏰ Scheduled sync (e.g., every 12 hours)
   │
   ▼
┌──────────────────┐
│ Bedrock KB       │  Confluence data source configured with:
│ Confluence       │    - Host: https://yourteam.atlassian.net
│ Connector        │    - Space key: PLATFORM
│                  │    - Auth: API token from Secrets Manager
└──────┬───────────┘
       │ Fetches pages via Confluence REST API
       │ (authenticated with encrypted token)
       ▼
┌──────────────┐
│ Page → Text  │  Converts Confluence storage format
│ Extraction   │  (a kind of HTML/XML) to plain text
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Chunk        │  Same chunking strategy as other sources
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Embed        │  Titan V2 creates vectors
│ (Titan V2)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Index        │  Stored alongside S3 and web content
│ (OpenSearch) │  in the same vector index
└──────────────┘

  All three data sources feed into ONE vector index.
  When the agent searches, it searches across all sources at once.
```

---

## 9.3 AWS Service Selection — Why Each Service?

Here's the key question for every service: **"Why this one and not something else?"**

Let's walk through each service, explain what it is in plain English, why we chose it, and what alternative we considered.

### ECS Fargate — Run Containers Without Servers

**What is it?** ECS (Elastic Container Service) is AWS's container orchestration service. Fargate is the "serverless" launch type — you give AWS a Docker image, and it runs it. You never see or manage the underlying server (called an EC2 instance).

**Why we chose it:** Our local setup already uses Docker. Moving to ECS Fargate means we keep our Dockerfiles almost unchanged. We just push images to ECR (see below) and tell ECS to run them.

**Why not EKS (Elastic Kubernetes Service)?** EKS is Kubernetes on AWS. It's more powerful but dramatically more complex. You'd need to learn Kubernetes concepts (pods, deployments, services, ingress controllers, helm charts). For two containers (frontend + backend), that's massive overkill. Fargate with ECS is the right tool for this scale.

**Why not Lambda for the backend?** Lambda has a 15-minute timeout and cold start latency. Our LangGraph agent can take 30+ seconds for complex workflows, and we want persistent connections for SSE (Server-Sent Events) streaming. Lambda doesn't support that well.

---

### Bedrock Knowledge Base — Auto-Chunk, Auto-Embed, Auto-Index

**What is it?** A managed RAG pipeline. You point it at data sources (S3, web URLs, Confluence), and it automatically:
1. **Parses** documents (PDF, HTML, TXT, DOCX, CSV, and more)
2. **Chunks** them into smaller pieces (using configurable strategies)
3. **Embeds** each chunk into a vector (using the model you choose)
4. **Indexes** the vectors into a vector store (OpenSearch Serverless)

**Why we chose it:** In the local setup, you wrote Python code for every one of those steps — `RecursiveCharacterTextSplitter` for chunking, a Bedrock API call for embedding, and Weaviate client code for indexing. That's fragile, hard to maintain, and doesn't scale. Bedrock KB replaces *all of it* with a managed service.

**Why not keep doing it manually?** You could. But then you're responsible for parsing every file format, handling chunking edge cases, managing embedding API rate limits, retrying failures, and keeping your index in sync. Bedrock KB does all this for you.

---

### OpenSearch Serverless — Vector Database

**What is it?** OpenSearch is AWS's managed search and analytics engine (based on the open-source OpenSearch project, which forked from Elasticsearch). The "Serverless" flavor means you don't manage clusters, nodes, or shards — AWS auto-scales based on usage.

**Why we chose it:** Bedrock Knowledge Base requires a vector store. OpenSearch Serverless is the default and best-integrated option. It supports the **HNSW** (Hierarchical Navigable Small World) algorithm for fast approximate nearest-neighbor search — the same type of algorithm Weaviate uses internally.

**Why not self-hosted Weaviate on ECS?** You could run Weaviate in a container on Fargate. But then *you* manage backups, scaling, index corruption, and availability. OpenSearch Serverless handles all of that. Since Bedrock KB has native OpenSearch integration, it's the path of least friction.

**Why not Pinecone or another third-party vector DB?** Bedrock KB doesn't natively integrate with Pinecone. You'd have to build a custom integration. Keeping everything in AWS simplifies IAM permissions, networking, and billing.

---

### Bedrock Claude Sonnet 4 — The LLM Brain

**What is it?** Claude Sonnet 4 is a large language model made by Anthropic, available through AWS Bedrock. It's the "reasoning engine" — the part that reads your retrieved documents and writes a helpful, coherent answer.

**Why we chose it:** Same model as local. The only change is *how* we authenticate. Locally, you used `profile_name="sandboxtest"` in the Boto3 client. On AWS, the ECS task has an IAM role, so authentication is automatic — no credentials in code.

**Why not GPT-4 or another model?** You absolutely could swap models. Bedrock also offers Meta Llama, Mistral, and Amazon's own models. We chose Claude Sonnet 4 because it excels at following instructions, citing sources accurately, and generating structured output. It's also what we validated in the local setup.

---

### Bedrock Titan Embed V2 — The Embedding Model

**What is it?** An embedding model converts text into a vector (a list of numbers). Titan Embed V2 produces 1024-dimensional vectors. Two pieces of text that mean similar things will have vectors that are close together in that 1024-dimensional space — that's how semantic search works.

**Why we chose it:** Bedrock Knowledge Base manages the embedding model for you. When it chunks a document, it calls Titan V2 to create the vector, then stores it in OpenSearch. You don't write embedding code.

**Why 1024 dimensions?** It's a balance between accuracy and cost. Larger vectors (e.g., 4096) capture more nuance but use more storage and slower search. 1024 is the sweet spot for most use cases.

---

### ALB (Application Load Balancer) — Public Access + Routing

**What is it?** An ALB sits in front of your containers and routes incoming HTTP requests to the right service based on the URL path.

**Why we chose it:** We have two services that need to be reachable at one URL:
- `https://your-alb-url.com/` → Frontend (Streamlit on port 8501)
- `https://your-alb-url.com/chat` → Backend (FastAPI on port 8000)
- `https://your-alb-url.com/health` → Backend health check

The ALB handles this path-based routing. It also does health checks — if a container crashes, the ALB stops sending traffic to it and ECS launches a replacement.

**Why not API Gateway?** API Gateway is designed for REST/HTTP APIs, not for serving a full web application with WebSocket-like streaming. ALB is simpler and cheaper for our use case.

---

### EFS (Elastic File System) — Persistent Chat History

**What is it?** EFS is a managed network file system. Think of it like a shared hard drive that multiple containers can read and write to simultaneously. It survives container restarts, redeployments, and even AZ (Availability Zone) failures.

**Why we chose it:** Chat history is stored as JSON files on disk. In Docker, that was a local volume. On AWS, we mount an EFS volume into the backend container at the same path. The code doesn't change — it still reads and writes files. But now those files persist.

**Why not RDS PostgreSQL (like local)?** We could. But RDS has a minimum cost (~$15/month for the smallest instance) and adds operational complexity (backups, patching, connection pooling). For JSON file storage, EFS is simpler and cheaper. Pay only for what you store.

**Why not DynamoDB for chat history?** DynamoDB is great for structured data with known access patterns. Chat history is semi-structured (variable-length message lists) and read as a whole conversation. File-based storage on EFS is a natural fit and requires zero code changes from the local setup.

---

### DynamoDB — Checklists and Escalation Data

**What is it?** DynamoDB is AWS's serverless NoSQL database. You create tables, and AWS handles capacity, replication, and backups. You pay per request — if nobody uses it, it costs nothing.

**Why we chose it:** The agent can create incident checklists and escalation records. These are structured data with clear primary keys (e.g., `checklist_id`, `escalation_id`). DynamoDB is perfect for this — fast single-item lookups, no server to manage, and it scales to millions of items.

**Why not PostgreSQL?** For two simple tables with key-value access patterns, PostgreSQL is overkill. You'd pay for an always-on instance and manage connections. DynamoDB's pay-per-request model is ideal.

---

### S3 — Document Storage + Auto-Trigger

**What is it?** S3 (Simple Storage Service) is AWS's object storage. Think of it as a cloud hard drive with unlimited capacity. You organize files in "buckets" (like top-level folders).

**Why we chose it:** S3 is the primary data source for Bedrock Knowledge Base. Upload a PDF, and the KB can ingest it. Combined with S3 event notifications → Lambda, we get automatic re-indexing on every upload.

**Why not just use the web crawler for everything?** Not all documents are on a website. Internal runbooks, architecture diagrams, and incident reports might only exist as PDFs or Word docs. S3 is the catch-all for anything that isn't on the web or in Confluence.

---

### Lambda — Event-Driven S3 → KB Sync

**What is it?** Lambda lets you run code without managing servers. You upload a function (a Python file, in our case), and AWS runs it in response to events. You pay only for the milliseconds your function runs.

**Why we chose it:** When a file lands in S3, we want the Knowledge Base to re-sync immediately. Lambda watches for S3 `PutObject` events and calls `bedrock.start_ingestion_job()`. The entire function is ~30 lines of Python.

**Why not a cron job on ECS?** A cron job would poll S3 periodically, adding delay. Lambda reacts instantly to events and costs nothing when idle. It's the right tool for event-driven triggers.

---

### Cloud Map — Service Discovery

**What is it?** Cloud Map is AWS's service discovery mechanism. It creates DNS (Domain Name System) entries that your services can use to find each other by name instead of IP address.

**Why we chose it:** The frontend needs to call the backend. In Docker Compose, you used `http://backend:8000`. On AWS, Cloud Map gives you `backend.platform-health` (a DNS name that resolves to the backend container's IP). The concept is the same — service names instead of IP addresses.

**Why not hardcode IPs?** Container IPs change every time ECS launches a new task. Hardcoding breaks immediately. Cloud Map keeps the DNS record updated automatically.

---

### Secrets Manager + KMS — Secure Credential Storage

**What is it?** Secrets Manager stores sensitive values (API keys, tokens, passwords) encrypted at rest using KMS (Key Management Service). Your application retrieves secrets at runtime — they're never stored in code, environment variables, or config files.

**Why we chose it:** The Confluence connector needs an API token to authenticate. That token must be stored securely. Secrets Manager encrypts it, audits access, and lets you rotate it without redeploying.

**Why not environment variables?** Environment variables in ECS task definitions are visible in the AWS Console and in CloudWatch logs. Anyone with ECS read access could see them. Secrets Manager provides encryption, access control, and audit logging.

---

### ECR (Elastic Container Registry) — Docker Image Storage

**What is it?** ECR is AWS's Docker image registry. It's like Docker Hub, but private and integrated with AWS IAM for access control.

**Why we chose it:** ECS Fargate pulls container images from a registry. ECR is the native choice — no extra authentication setup, no external dependencies, and images stay in your AWS account.

**Why not Docker Hub?** Docker Hub works but adds an external dependency. If Docker Hub has an outage, your deployments fail. ECR is within AWS, so it's available whenever AWS is available.

---

## 9.4 Local vs AWS: Side-by-Side Comparison

This table is your Rosetta Stone between the local and AWS setups. When you're confused about what replaces what, come back here.

| Feature | Local (Steps 1–8) | AWS (Steps 9–16) | Why the Change |
|---|---|---|---|
| **Vector Database** | Weaviate (Docker container) | OpenSearch Serverless | Managed by AWS, auto-scales, no cluster ops |
| **Document Chunking** | Manual Python (`RecursiveCharacterTextSplitter`) | Bedrock KB auto-chunk | No custom chunking code to maintain |
| **Embeddings** | Manual API call to Bedrock Titan V2 | Bedrock KB auto-embed | KB handles embedding as part of ingestion |
| **Indexing** | Manual Weaviate client insert | Bedrock KB auto-index to OpenSearch | No indexing code, no Weaviate client |
| **LLM** | Bedrock Claude (with `profile_name`) | Bedrock Claude (IAM task role) | Same model, different auth mechanism |
| **Chat History** | PostgreSQL (Docker container) | EFS JSON files | Simpler, no database to manage, zero code change |
| **Frontend Access** | `localhost:8501` | ALB public URL | Anyone can access, not just your machine |
| **Auth to AWS** | `AWS_PROFILE=sandboxtest` (local creds) | IAM task role (automatic) | No credentials in code, automatic rotation |
| **Data Sources** | Manual file upload + Python script | S3 auto-trigger + web crawler + Confluence | Three data sources, all automatic |
| **Networking** | Docker bridge network | Default VPC + Cloud Map | Real networking with DNS service discovery |
| **Persistence** | Docker volumes (lost on `docker compose down -v`) | EFS + DynamoDB (durable) | Data survives container restarts and redeployments |
| **Container Orchestration** | Docker Compose | ECS Fargate | Managed scheduling, health checks, auto-restart |
| **Secrets** | `.env` file or environment variables | Secrets Manager + KMS | Encrypted, audited, rotatable |
| **Logs** | `docker compose logs` | CloudWatch Logs | Centralized, searchable, persistent |
| **Scaling** | Not possible (single machine) | ECS desired count + ALB | Scale to multiple containers with a number change |

---

## 9.5 Folder Structure Explained

Here's every file in the `aws-deploy/` directory and what it does. If you ever feel lost, come back to this map.

```
aws-deploy/
│
├── agent-backend/              # 🧠 The AI agent — FastAPI + LangGraph
│   ├── agent/                  #    The "brain" of the system
│   │   ├── graph.py            #    The agent's ReAct loop.
│   │   │                       #    Defines: llm node → should_continue → tools → llm.
│   │   │                       #    No router — the LLM decides via tool descriptions.
│   │   ├── state.py            #    Defines AgentState — the data that flows between
│   │   │                       #    graph nodes (messages, tool results, metadata).
│   │   ├── prompts.py          #    System prompts that tell Claude how to behave.
│   │   │                       #    "You are a platform health assistant..."
│   │   # No separate workflows/ directory — incident assessment is just
│   │   # a tool (assess_incident) the LLM can call in the ReAct loop.
│   │
│   ├── tools/                  #    What the agent can DO (its "hands")
│   │   ├── kb_tool.py          #    Search Bedrock Knowledge Base for docs
│   │   ├── dynamodb_tool.py    #    Create and manage incident checklists
│   │   ├── escalation_tool.py  #    Escalate issues to on-call teams
│   │   ├── history.py          #    Read/write chat history on EFS
│   │   └── incident_tool.py    #    Assess incident severity
│   │
│   ├── config.py               #    All environment variables in one place.
│   │                           #    KB_ID, AWS_REGION, EFS paths, DynamoDB table names.
│   ├── main.py                 #    FastAPI server — defines /chat, /health, /sessions
│   │                           #    endpoints. Entry point for the backend container.
│   ├── Dockerfile              #    How to build the backend Docker image.
│   │                           #    Base: python:3.12-slim → install deps → copy code.
│   └── requirements.txt        #    Python packages: langchain, boto3, fastapi, etc.
│
├── frontend/                   # 💬 Streamlit chat interface
│   ├── app.py                  #    The web UI. Session sidebar, chat input,
│   │                           #    streaming response display with sources.
│   ├── Dockerfile              #    Frontend container image definition.
│   └── requirements.txt        #    streamlit, requests
│
├── lambda/                     # ⚡ Serverless functions
│   └── kb_sync_trigger.py      #    Triggered by S3 upload. Calls
│                               #    bedrock.start_ingestion_job() to re-index.
│                               #    ~30 lines of Python. Simple and focused.
│
├── terraform/                  # 🏗️ Infrastructure as Code (IaC)
│   │                           #    Terraform files define ALL AWS resources.
│   │                           #    Run `terraform apply` and everything is created.
│   │
│   ├── main.tf                 #    Provider config (AWS region, version constraints)
│   │                           #    and VPC data sources (existing networking).
│   ├── variables.tf            #    Configurable parameters: region, project name,
│   │                           #    KB settings, instance sizes. Change these,
│   │                           #    not the other files.
│   ├── ecr.tf                  #    Two ECR repositories: one for backend image,
│   │                           #    one for frontend image.
│   ├── s3.tf                   #    Document storage bucket + event notification
│   │                           #    config for Lambda trigger.
│   ├── efs.tf                  #    EFS file system + mount targets in each
│   │                           #    subnet + access point for the backend.
│   ├── dynamodb.tf             #    DynamoDB tables: Checklists, Escalations.
│   │                           #    Pay-per-request billing.
│   ├── secrets.tf              #    Secrets Manager secret for Confluence token
│   │                           #    + KMS key for encryption.
│   ├── iam.tf                  #    IAM roles and policies. Defines WHO can do WHAT.
│   │                           #    ECS task role, Lambda role, KB role.
│   ├── bedrock-kb.tf           #    The Knowledge Base definition:
│   │                           #    - OpenSearch Serverless collection + index
│   │                           #    - Bedrock KB with S3 data source
│   │                           #    - Embedding model config (Titan V2, 1024-dim)
│   ├── lambda.tf               #    Lambda function + S3 event trigger +
│   │                           #    IAM role + CloudWatch log group.
│   ├── ecs.tf                  #    ECS cluster + task definitions + services
│   │                           #    for frontend and backend. Cloud Map config.
│   ├── alb.tf                  #    ALB + target groups + listener rules
│   │                           #    for path-based routing.
│   └── outputs.tf              #    Values printed after `terraform apply`:
│                               #    ALB URL, KB ID, ECR repo URIs, etc.
│
├── tutorials/                  # 📚 This tutorial series (Steps 9–16)
│   └── step-09-architecture-and-design.md   # ← You are here!
│
├── TROUBLESHOOTING.md          # 🔧 Real issues encountered and their fixes.
│                               #    "OpenSearch 403? Check the data access policy."
│
└── SESSION-HANDOFF.md          # 📋 Quick reference for picking up where you left off.
                                #    Current status, resource IDs, next steps.
```

---

## 9.6 How Data Flows (End-to-End Walkthrough)

Let's trace a complete user interaction, step by step. Imagine you're an engineer during an incident, and you need to know how to restart the payment service.

### Step 1: Open the Browser

You navigate to the ALB's public URL — something like:
```
http://platform-health-alb-123456.us-east-1.elb.amazonaws.com
```

The ALB receives this request on port 80. It checks the path (`/`) and routes it to the **frontend target group**.

### Step 2: ALB → Frontend

The frontend target group contains one (or more) Streamlit containers running on ECS Fargate. The ALB forwards the request to port 8501 on the container.

Streamlit renders the chat interface: a sidebar with session history, a main area with a text input box, and any previous messages.

### Step 3: Type Your Question

You type: *"How do I restart the payment service?"* and press Enter.

The frontend JavaScript sends a **POST** request to the backend. But how does the frontend know where the backend is?

**Cloud Map DNS.** The frontend is configured with the backend's service discovery name — something like `backend.platform-health`. Cloud Map resolves this to the backend container's private IP address within the VPC (Virtual Private Cloud). The request goes to:
```
http://backend.platform-health:8000/chat
```

The request body includes your question and the session ID (so the agent knows your conversation history).

### Step 4: Backend Receives the Request

FastAPI receives the POST at the `/chat` endpoint. It:
1. Loads chat history from EFS (if this is a continuing conversation)
2. Creates a LangGraph agent with the conversation context
3. Invokes the graph

### Step 5: LLM Decides (ReAct Loop)

The LangGraph graph is a **single ReAct loop** — there is no separate router node. The flow is:

```
START → llm → [should_continue] → tools → llm → ... → END
```

The LLM looks at your question and decides which tool to call based on **tool descriptions**, which serve as the routing logic:

- `rag_search` — *"Always call this first to search platform documentation."* → handles doc questions
- `assess_incident` — *"Only for active outages with real symptoms."* → handles incident analysis
- `create_checklist` — creates structured checklists in DynamoDB
- `escalate_to_human` — escalates to on-call teams

The LLM reads these descriptions and picks the right tool. For *"How do I restart the payment service?"*, it calls `rag_search`. No classification step needed — the tool descriptions **are** the routing logic.

> **Evolution note:** The original design had a separate router node that classified user intent before dispatching to different workflow paths. This was simplified to a single ReAct loop after discovering that the router misclassified ambiguous queries like "can you check the payment service" (search? or incident?). See Step 17 and Step 18 for the full debugging story and design analysis.

### Step 6: Search the Knowledge Base

The agent calls `kb_tool.py`, which invokes the **Bedrock KB Retrieve API**:
```python
bedrock_agent.retrieve(
    knowledgeBaseId="YOUR_KB_ID",
    retrievalQuery={"text": "How do I restart the payment service?"},
    retrievalConfiguration={
        "vectorSearchConfiguration": {
            "numberOfResults": 5  # top-K
        }
    }
)
```

This API call does two things behind the scenes:
1. **Embeds** your question using Titan V2 (same model used to embed the documents)
2. **Searches** OpenSearch Serverless for the 5 most similar document chunks

### Step 7: OpenSearch Vector Search

OpenSearch receives the query vector (1024 dimensions) and performs an **approximate nearest-neighbor** (ANN) search using the HNSW algorithm.

It compares your question's vector against every indexed chunk's vector and returns the top 5 closest matches, each with:
- The chunk **text** (e.g., "To restart the payment service, SSH into the bastion host and run...")
- The **source** (e.g., `s3://my-docs-bucket/payment-runbook-v3.pdf`, page 12)
- A **relevance score** (e.g., 0.87 — higher is more similar)

### Step 8: Generate the Answer

The agent now has:
- Your question
- 5 relevant document chunks
- The conversation history
- A system prompt ("You are a platform health assistant. Cite your sources...")

It sends all of this to **Claude Sonnet 4** via the Bedrock InvokeModel API. Claude reads the chunks, synthesizes an answer, and includes citations pointing back to the source documents.

### Step 9: Stream the Response

The response doesn't come back all at once. It **streams** via SSE (Server-Sent Events). Each token (word or word-piece) is sent as it's generated:

```
data: {"token": "To"}
data: {"token": " restart"}
data: {"token": " the"}
data: {"token": " payment"}
data: {"token": " service"}
data: {"token": ","}
data: {"token": " follow"}
...
```

The frontend reads these tokens and renders them in real-time, creating the "typing" effect you see in ChatGPT-like interfaces.

### Step 10: Display with Sources

Once streaming is complete, the frontend displays:
- The full answer
- Source citations (clickable links back to the original documents in S3 or the original web page)

### Step 11: Save Chat History

The backend saves the conversation (your question + the agent's answer) to a JSON file on EFS:
```
/mnt/efs/chat_history/session_abc123.json
```

This file persists across container restarts. If you come back tomorrow and open the same session, your history is still there.

---

## 9.7 Prerequisites Checklist

Before you move on to **Step 10: Terraform Infrastructure**, make sure you have everything below. Don't skip this — missing one item will cause confusing errors later.

### ✅ AWS Account with Admin Access

You need an AWS account where you can create resources. Ideally, use a sandbox or development account — not production. You'll need permissions to create:
- ECS clusters and services
- Bedrock Knowledge Bases
- OpenSearch Serverless collections
- S3 buckets
- Lambda functions
- IAM roles and policies
- ALB, EFS, DynamoDB, ECR, Secrets Manager, Cloud Map

> **Tip:** If you're using an organization account, ask your admin for a sandbox account or an IAM user with `AdministratorAccess` policy.

### ✅ AWS CLI Installed and Configured

The AWS CLI (Command Line Interface) lets you interact with AWS from your terminal.

```bash
# Check if installed
aws --version
# Should output something like: aws-cli/2.x.x Python/3.x.x ...

# Configure with your credentials
aws configure
# It will ask for:
#   AWS Access Key ID: (from your IAM user)
#   AWS Secret Access Key: (from your IAM user)
#   Default region name: us-east-1
#   Default output format: json
```

Verify it works:
```bash
aws sts get-caller-identity
# Should show your account ID and user ARN
```

### ✅ Terraform Installed

Terraform is an Infrastructure as Code (IaC) tool. It reads `.tf` files and creates AWS resources.

```bash
# Check if installed
terraform --version
# Should output: Terraform v1.x.x

# If not installed (macOS):
brew install terraform
```

> **What is Terraform?** Instead of clicking through the AWS Console to create each resource (click "Create S3 Bucket", click "Create ECS Cluster", etc.), you write code that describes what you want. Then `terraform apply` creates everything at once. This is repeatable, version-controlled, and reviewable.

### ✅ Docker Desktop Running

You'll build container images locally and push them to ECR.

```bash
# Check if Docker is running
docker info
# Should show "Server: Docker Desktop" and other details

# If you see "Cannot connect to the Docker daemon",
# open Docker Desktop from your Applications folder.
```

### ✅ Python 3.12+

Some local scripts (like testing the Lambda function) require Python.

```bash
python3 --version
# Should output: Python 3.12.x or higher
```

### ✅ Steps 1–8 Completed (Recommended)

While you *can* start here, the AWS steps assume familiarity with:
- How LangGraph agents work (graph, state, tools, ReAct loop)
- How RAG works (chunk → embed → index → retrieve → generate)
- What the agent does (rag_search, checklists, escalations, incident assessment)

If you haven't done Steps 1–8, at least read through the code to understand the agent's capabilities.

### Quick Verification Checklist

Run these commands and confirm they all succeed:

```bash
aws --version                    # AWS CLI v2.x
terraform --version              # Terraform v1.x
docker info | head -5            # Docker running
python3 --version                # Python 3.12+
aws sts get-caller-identity      # AWS credentials work
```

---

## What's Next?

You now understand:
- **Why** we're moving to AWS (automatic ingestion, managed services, public access)
- **What** each AWS service does and why we picked it
- **How** data flows from a user's question to a sourced answer
- **Where** every file lives and what it does

In **Step 10: Terraform Infrastructure**, we'll write the actual Terraform code to create all of these resources. You'll run `terraform apply` and watch your entire cloud infrastructure come to life.

See you there! 🎉

---

> **📌 Bookmark this page.** You'll reference the architecture diagrams and service comparison table throughout Steps 10–16. When something doesn't make sense later, come back here for the "why."
