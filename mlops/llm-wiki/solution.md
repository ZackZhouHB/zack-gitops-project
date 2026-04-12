# Solution Architecture — LLM Wiki

## Background

### The Pattern (Karpathy)

The LLM Wiki pattern replaces traditional RAG with a **persistent, LLM-maintained knowledge base**. Instead of re-deriving understanding from raw chunks on every query, an LLM incrementally builds a structured wiki — a collection of interlinked markdown files with entity pages, concept summaries, source digests, and cross-references. The wiki compounds over time: every source ingested and every question asked makes it richer.

Three architectural layers:

1. **Raw sources** — immutable input documents (articles, papers, notes). The LLM reads from these but never modifies them. Source of truth.
2. **The wiki** — LLM-generated markdown files. Summaries, entity pages, concept pages, comparisons, synthesis. The LLM owns this layer entirely.
3. **The schema** — a configuration document (e.g. `CLAUDE.md`) that tells the LLM how to structure the wiki, what conventions to follow, and what workflows to execute.

Three core operations:

- **Ingest**: Process a new source → extract key info → write summary → update entity/concept pages → update index → append to log. One source may touch 10–15 wiki pages.
- **Query**: Search index → read relevant pages → synthesize answer → optionally file answer back into wiki as a new page.
- **Lint**: Health-check the wiki → find contradictions, orphan pages, stale claims, missing cross-references, gaps.

Two navigation files:

- **index.md**: Content catalog. Every page listed with summary and metadata. LLM reads this first to find relevant pages.
- **log.md**: Chronological append-only record of all operations. Parseable with unix tools.

### The Critique (Steph Ango / Community Insights)

Key concerns raised about the pattern:

1. **Hallucination compounding**: If the LLM writes a subtly wrong synthesis, future ingests and queries build on top of that error. Unlike RAG (which goes back to source every time), the wiki amplifies both good and bad synthesis.

2. **Two-vault separation** (Steph Ango, Obsidian CEO): Maintain two independent vaults — one for AI-compiled content, one for human-curated knowledge. This prevents AI hallucination from polluting high-quality human notes.

3. **Scaling ceiling**: The `index.md`-as-search approach works at ~100–200 pages. Beyond that, you need proper search infrastructure (e.g., qmd with BM25 + vector search), at which point you're essentially doing RAG over your own wiki.

4. **Multi-session continuity**: Each new LLM session starts cold. The schema + index help orient the LLM, but it doesn't truly "remember" its reasoning from prior sessions.

### Design Decisions for This Implementation

| Decision | Rationale |
|----------|-----------|
| **Two-vault architecture** (`wiki/` + `trusted/`) | Adopt Ango's recommendation. AI draft layer vs. human-verified layer. |
| **Git as safety net** | Every ingest = a commit. Hallucinations are diffable and revertible. Cheaper than building a verification system. |
| **Schema-first approach** | `CLAUDE.md` is the real product. The rules that produce consistent, well-linked wiki pages are where the value is. |
| **Lint as first-class operation** | Combine automated checks (orphan links, missing index entries) with LLM-driven checks (contradictions, stale claims). |
| **Progressive search** | Start with index.md + grep. Upgrade to qmd when scale demands it. Don't over-engineer early. |

---

## Phase 1 — POC (Local, Manual, Minimal)

**Goal**: Validate the pattern works. Build a functional wiki on this machine using only an LLM agent, markdown files, and Obsidian. No custom code, no infra.

### Architecture

```
llm-wiki/                          # Project root = Obsidian vault
├── raw/                           # Source documents (immutable)
│   ├── articles/                  # Web articles (via Obsidian Web Clipper)
│   ├── papers/                    # PDFs, research papers
│   ├── notes/                     # Personal notes, meeting notes
│   └── assets/                    # Images, attachments
├── wiki/                          # AI-compiled vault (LLM-owned)
│   ├── index.md                   # Master catalog of all wiki pages
│   ├── log.md                     # Chronological operation log
│   ├── entities/                  # Entity pages (people, orgs, products, tools)
│   ├── concepts/                  # Concept/topic pages
│   ├── sources/                   # One summary page per ingested source
│   └── analysis/                  # Filed query results, comparisons, syntheses
├── trusted/                       # Human-curated (promoted from wiki/)
│   └── ...                        # Same structure as wiki/, but human-verified
├── CLAUDE.md                      # Schema — LLM conventions and workflows
├── llm-wiki.md                    # Original pattern document (reference)
├── README.md                      # Project introduction
└── solution.md                    # This file
```

### Tool Stack

| Tool | Purpose | Setup |
|------|---------|-------|
| **LLM Agent** (Claude Code / Copilot CLI) | Reads sources, writes wiki, answers queries | Already available |
| **Obsidian** | Browse wiki, graph view, Dataview queries | Open this folder as vault |
| **Obsidian Web Clipper** | Capture web articles as markdown | Browser extension |
| **Git** | Version control, rollback, diff review | `git init` in project root |
| **grep / ripgrep** | Search within wiki pages | Already available |

### Schema (CLAUDE.md) — Key Rules

The schema should define:

1. **Page format conventions**:
   - YAML frontmatter on every wiki page (title, tags, sources, created, updated)
   - Obsidian-style `[[wikilinks]]` for cross-references
   - Each page starts with a one-paragraph summary

2. **Ingest workflow**:
   - Read source → discuss with user → write `wiki/sources/<source-name>.md`
   - Update or create relevant entity/concept pages
   - Update `wiki/index.md` with new entries
   - Append to `wiki/log.md`
   - Git commit with descriptive message

3. **Query workflow**:
   - Read `wiki/index.md` to find relevant pages
   - Read those pages, synthesize answer
   - If answer is substantive, file as `wiki/analysis/<topic>.md`
   - Append query to `wiki/log.md`

4. **Lint workflow**:
   - Check for orphan pages (not in index, no inbound links)
   - Check for broken `[[wikilinks]]`
   - Check for stale source summaries
   - LLM reviews for contradictions across pages
   - Append lint results to `wiki/log.md`

5. **Promotion workflow**:
   - User reviews `git diff wiki/` after each ingest
   - Manually copies verified pages to `trusted/`
   - LLM never modifies `trusted/`

### Success Criteria for POC

- [ ] Ingest 5–10 diverse sources (articles, notes, a PDF)
- [ ] Wiki has 20+ interlinked pages with working cross-references
- [ ] Can answer synthesis questions that span multiple sources
- [ ] Lint pass finds and fixes real issues
- [ ] Obsidian graph view shows meaningful structure
- [ ] At least 2–3 pages promoted to `trusted/`
- [ ] Full git history of every LLM operation

### Estimated Effort

Minimal. Setup is ~30 minutes. The ongoing work is ingesting sources and iterating on the schema.

---

## Phase 2 — Product (Dockerized, CLI + Web UI, Search)

**Goal**: Package the POC into a self-contained, portable solution. Add a CLI for scriptable operations, a web UI for browsing/querying, and proper search for scale.

### Architecture

```
┌──────────────────────────────────────────────────────────┐
│                      Web UI (Frontend)                    │
│  React / Next.js                                         │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────────┐  │
│  │ Browse   │ │ Search   │ │ Query   │ │ Graph View   │  │
│  │ Wiki     │ │ Pages    │ │ Chat    │ │ (D3/Cytoscape)│  │
│  └─────────┘ └──────────┘ └─────────┘ └──────────────┘  │
└──────────────────────┬───────────────────────────────────┘
                       │ REST API / WebSocket
┌──────────────────────▼───────────────────────────────────┐
│                    Backend (API Server)                    │
│  Python (FastAPI) or Node (Express)                      │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Ingest       │  │ Query        │  │ Lint          │  │
│  │ Pipeline     │  │ Engine       │  │ Engine        │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────┘  │
│         │                 │                  │           │
│  ┌──────▼─────────────────▼──────────────────▼────────┐  │
│  │              LLM Orchestration Layer                │  │
│  │  - Prompt management (schema → system prompt)      │  │
│  │  - Multi-step workflows (ingest touches N pages)   │  │
│  │  - Git auto-commit after each operation            │  │
│  └──────┬─────────────────┬──────────────────┬────────┘  │
│         │                 │                  │           │
│  ┌──────▼───────┐  ┌─────▼──────┐  ┌───────▼────────┐  │
│  │ LLM API      │  │ Search     │  │ File Manager   │  │
│  │ (Anthropic / │  │ (qmd or    │  │ (read/write    │  │
│  │  OpenAI)     │  │  custom)   │  │  markdown)     │  │
│  └──────────────┘  └────────────┘  └────────────────┘  │
└──────────────────────────────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│                      Storage Layer                        │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ raw/        │  │ wiki/        │  │ trusted/       │  │
│  │ (sources)   │  │ (AI wiki)    │  │ (human-vetted) │  │
│  └─────────────┘  └──────────────┘  └────────────────┘  │
│                                                          │
│  ┌─────────────┐  ┌──────────────┐                      │
│  │ SQLite      │  │ Search Index │                      │
│  │ (metadata,  │  │ (BM25 +     │                      │
│  │  user prefs)│  │  vector)     │                      │
│  └─────────────┘  └──────────────┘                      │
└──────────────────────────────────────────────────────────┘
```

### Components

#### CLI Tool (`wiki-cli`)

```bash
# Core operations
wiki ingest <source-file>           # Ingest a single source
wiki ingest --batch raw/articles/   # Batch ingest a directory
wiki query "What are the key themes across all sources?"
wiki lint                           # Run health checks
wiki lint --fix                     # Auto-fix what's possible

# Navigation
wiki search "keyword or phrase"     # Search wiki pages
wiki list --orphans                 # List orphan pages
wiki list --recent 10               # Last 10 operations from log

# Maintenance
wiki promote <wiki-page>            # Copy to trusted/ after review
wiki diff                           # Show uncommitted wiki changes
wiki history <page>                 # Git log for a specific page
```

#### Web UI

- **Wiki browser**: Render markdown pages with working `[[wikilinks]]`, sidebar navigation
- **Search**: Full-text + semantic search across wiki pages
- **Query chat**: Conversational interface, answers cite wiki pages, option to file answers back
- **Graph view**: Interactive graph of page links (D3.js or Cytoscape.js)
- **Ingest UI**: Drag-and-drop source upload, URL paste for web articles
- **Diff/review**: Side-by-side view of wiki changes, approve/promote to trusted

#### Search Engine

Two options:

1. **qmd** (recommended if it works well): Already built, supports BM25 + vector + LLM reranking, has MCP server. Drop-in solution.
2. **Custom** (fallback): SQLite FTS5 for BM25, sentence-transformers for embeddings, stored in a local vector file. More control, more work.

### Docker Composition

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - ./data:/data          # raw/, wiki/, trusted/
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]

  search:
    build: ./search           # qmd or custom search service
    ports: ["8001:8001"]
    volumes:
      - ./data/wiki:/wiki:ro
      - ./data/trusted:/trusted:ro
```

### Key Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend language | **Python (FastAPI)** | Best LLM SDK support (Anthropic, OpenAI), fast prototyping |
| Frontend | **Next.js** | SSR for markdown rendering, good DX, React ecosystem |
| Database | **SQLite** | No separate DB server, portable, sufficient for single-user |
| Search | **qmd → fallback to custom** | Try qmd first; build custom only if needed |
| LLM provider | **Anthropic (Claude) primary, OpenAI fallback** | Multi-provider support from day one |
| Auth | **None (local only)** | Phase 2 is single-user. Auth comes in Phase 3. |

### Success Criteria for Phase 2

- [ ] `docker compose up` starts the full stack
- [ ] CLI can ingest, query, and lint without manual LLM interaction
- [ ] Web UI renders wiki with working links and graph view
- [ ] Search returns relevant results across 200+ pages
- [ ] Git history tracks every automated operation
- [ ] Obsidian can still open the same data directory side-by-side

---

## Phase 3 — Team (AWS Serverless, Multi-User, 3–4 People)

**Goal**: Move the solution to AWS so a small team (3–4 people) can share a wiki. Serverless to keep costs near-zero when idle. Each team member can ingest sources, query, and browse.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          AWS Cloud                                   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    CloudFront + S3                            │    │
│  │              (Static frontend hosting)                       │    │
│  └──────────────────────┬──────────────────────────────────────┘    │
│                         │                                           │
│  ┌──────────────────────▼──────────────────────────────────────┐    │
│  │                  API Gateway (HTTP API)                       │    │
│  │            + Cognito Authorizer (team auth)                  │    │
│  └──────┬──────────┬──────────┬──────────┬─────────────────────┘    │
│         │          │          │          │                           │
│  ┌──────▼───┐ ┌────▼────┐ ┌──▼────┐ ┌───▼──────┐                   │
│  │ Ingest   │ │ Query   │ │ Lint  │ │ Search   │                   │
│  │ Lambda   │ │ Lambda  │ │ Lambda│ │ Lambda   │                   │
│  │          │ │         │ │       │ │          │                   │
│  │ (long:   │ │ (calls  │ │(sched-│ │(OpenSrch │                   │
│  │  Step    │ │  Bedrock│ │ uled  │ │ Server-  │                   │
│  │  Func-   │ │  or     │ │ via   │ │ less or  │                   │
│  │  tions)  │ │  direct │ │ Event-│ │ custom)  │                   │
│  │          │ │  API)   │ │ Bridge│ │          │                   │
│  └────┬─────┘ └────┬────┘ └───┬───┘ └────┬─────┘                   │
│       │            │          │           │                          │
│  ┌────▼────────────▼──────────▼───────────▼─────────────────────┐   │
│  │                     Shared Services                           │   │
│  │                                                               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐  │   │
│  │  │ S3           │  │ DynamoDB     │  │ Amazon Bedrock     │  │   │
│  │  │              │  │              │  │ (Claude /Titan)    │  │   │
│  │  │ raw/         │  │ - Page meta  │  │                    │  │   │
│  │  │ wiki/        │  │ - Index      │  │ OR direct API call │  │   │
│  │  │ trusted/     │  │ - Log        │  │ to Anthropic /     │  │   │
│  │  │ (markdown    │  │ - User prefs │  │ OpenAI             │  │   │
│  │  │  files)      │  │ - Lock state │  │                    │  │   │
│  │  └──────────────┘  └──────────────┘  └────────────────────┘  │   │
│  │                                                               │   │
│  │  ┌──────────────┐  ┌──────────────┐                          │   │
│  │  │ CodeCommit / │  │ OpenSearch   │                          │   │
│  │  │ S3 versioning│  │ Serverless   │                          │   │
│  │  │ (git history)│  │ (BM25+vector │                          │   │
│  │  │              │  │  search)     │                          │   │
│  │  └──────────────┘  └──────────────┘                          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Cognito User Pool                          │   │
│  │           (3–4 team members, email/password)                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    EventBridge                                │   │
│  │  - Scheduled lint (daily/weekly)                             │   │
│  │  - S3 event → auto-ingest trigger                           │   │
│  │  - Notification on wiki update (SNS → email/Slack)          │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### AWS Service Mapping

| Function | AWS Service | Why |
|----------|-------------|-----|
| **Frontend hosting** | S3 + CloudFront | Static Next.js export. Near-zero cost. |
| **API** | API Gateway (HTTP API) | Serverless, pay-per-request, WebSocket support for streaming |
| **Auth** | Cognito | Simple user pool for 3–4 people. Email/password. |
| **Compute** | Lambda | Per-operation invocation. No idle cost. |
| **Long operations** | Step Functions | Ingest touches many files — orchestrate as a state machine |
| **LLM** | Amazon Bedrock (Claude) | Native AWS integration, no API key management. Or direct Anthropic API via Lambda. |
| **File storage** | S3 | Markdown files stored as objects. Versioning enabled = git-like history. |
| **Metadata** | DynamoDB | Page index, log entries, user state. Serverless, pay-per-request. |
| **Search** | OpenSearch Serverless | BM25 + vector search. Auto-scales to zero. |
| **Scheduling** | EventBridge | Scheduled lint, auto-ingest triggers |
| **Notifications** | SNS → Email/Slack | Alert team when wiki is updated |
| **IaC** | CDK (TypeScript) or SAM | Infrastructure as code, reproducible deploys |

### Multi-User Considerations

**Concurrency control**: When two users ingest simultaneously, wiki pages could conflict. Solutions:
- **Optimistic locking** in DynamoDB (version counter per page)
- **Queue ingests** through SQS → process one at a time (simpler, slight latency)
- Recommended: **SQS queue** for Phase 3. Ingests are not latency-sensitive.

**Permissions model** (simple for 3–4 people):
- All team members can: ingest sources, query, browse
- All team members can: promote pages to trusted/
- Admin can: run lint, modify schema, manage users
- LLM can: modify wiki/ only (never raw/, never trusted/)

**Promotion workflow on AWS**:
- Wiki page changes trigger SNS notification to team
- Any team member can review and approve promotion to trusted/
- DynamoDB tracks review status per page

### Cost Estimate (3–4 users, moderate use)

| Service | Estimated Monthly Cost |
|---------|----------------------|
| Lambda (100 invocations/day) | ~$1 |
| API Gateway | ~$1 |
| S3 (10 GB markdown + sources) | ~$0.25 |
| DynamoDB (on-demand) | ~$1 |
| Bedrock / LLM API (heavy use) | $20–50 (this is the real cost) |
| OpenSearch Serverless | ~$7 (minimum when active) |
| CloudFront | ~$1 |
| Cognito (< 50k MAU free) | $0 |
| **Total** | **~$30–60/month** |

The LLM API cost dominates. Everything else is near-free at this scale.

### Success Criteria for Phase 3

- [ ] `cdk deploy` provisions the full stack
- [ ] 3–4 team members can log in and use the system
- [ ] Ingests are queued and processed without conflicts
- [ ] Wiki is browsable via web UI with search
- [ ] Scheduled lint runs weekly, sends summary to team
- [ ] Auto-ingest: drop file in S3 raw/ → wiki updates automatically
- [ ] Cost stays under $60/month for normal usage
- [ ] Can tear down and redeploy from scratch in < 10 minutes

---

## Migration Path Between Phases

```
Phase 1 → Phase 2:
  - Same markdown files, just add Docker wrapper
  - CLI codifies the manual LLM commands
  - Web UI replaces Obsidian (Obsidian can still be used alongside)
  - Add qmd or custom search

Phase 2 → Phase 3:
  - S3 replaces local file system
  - DynamoDB replaces SQLite
  - Lambda replaces FastAPI server
  - OpenSearch replaces qmd
  - Cognito adds auth
  - Step Functions replaces in-process ingest pipeline
  - CDK wraps everything as IaC
```

Key principle: **the markdown files are the same across all phases.** The data format never changes. Only the infrastructure around it evolves. You can always `aws s3 sync` the wiki back to local and open it in Obsidian.

---

## Open Questions

1. **LLM provider for Phase 3**: Bedrock (simpler AWS integration, fewer models) vs. direct Anthropic/OpenAI API (more models, manage keys yourself)?
2. **Search engine for Phase 2**: qmd (pre-built, well-suited) vs. custom (more control)?
3. **Frontend framework**: Next.js (SSR, full-featured) vs. simpler SPA (lighter)?
4. **Obsidian compatibility**: Should Phase 2/3 maintain Obsidian vault compatibility, or is web UI sufficient?
5. **Source types**: Text-only for POC? Or handle PDFs, images, audio transcripts from the start?

---

## References

- [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/1dd0294ef9567971c1e4348a90d69285)
- [qmd — local markdown search engine](https://github.com/tobi/qmd)
- [Obsidian](https://obsidian.md/)
- Steph Ango's two-vault recommendation (Obsidian CEO, discussion on Karpathy's gist)
- Vannevar Bush, "As We May Think" (1945) — the Memex concept
