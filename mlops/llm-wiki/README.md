# LLM Wiki — Personal Knowledge Base Powered by LLM

A local-first, LLM-maintained personal knowledge base that replaces traditional RAG with a **persistent, compounding wiki**. Instead of re-deriving knowledge on every query, an LLM incrementally builds and maintains a structured collection of interlinked markdown files — summarizing sources, cross-referencing entities, flagging contradictions, and keeping everything consistent over time.

## Why not RAG?

| | RAG | LLM Wiki |
|---|---|---|
| **Knowledge** | Re-derived per query from chunks | Pre-compiled, persistent, interlinked |
| **Synthesis** | Fragmented, query-dependent | Accumulated, cross-referenced |
| **Artifact** | None (answers vanish into chat) | Browsable wiki that compounds over time |
| **Maintenance** | Automatic (re-index) | LLM-maintained (ingest/lint cycles) |
| **Risk** | Stale index | Hallucination compounding |

## Core Concept

Based on [Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/1dd0294ef9567971c1e4348a90d69285), with key additions:

- **Two-vault architecture** (per Obsidian CEO Steph Ango's recommendation): AI-compiled wiki is kept separate from human-curated trusted content, preventing hallucination from polluting verified knowledge.
- **Git as safety net**: Every LLM operation is a git commit. Hallucinations are diffable and revertible.
- **Three-phase evolution**: From local POC → Dockerized solution → AWS serverless for small teams.

## Architecture Overview

```
project-root/
├── raw/                    # Immutable source documents (human-owned)
├── wiki/                   # AI-compiled knowledge base (LLM-owned)
│   ├── index.md            # Content catalog
│   ├── log.md              # Chronological operation log
│   ├── entities/           # Entity pages (people, orgs, tools)
│   ├── concepts/           # Concept/topic pages
│   ├── sources/            # Per-source summaries
│   └── analysis/           # Filed query results
├── trusted/                # Human-curated verified content
├── CLAUDE.md               # Schema — LLM behavior rules
└── README.md               # This file
```

## Operations

- **Ingest** — Add a source → LLM reads, summarizes, cross-references, updates wiki
- **Query** — Ask questions → LLM searches wiki, synthesizes answers, optionally files them back
- **Lint** — Health-check → Find contradictions, orphan pages, stale claims, missing links

## Project Phases

| Phase | Scope | Target |
|-------|-------|--------|
| **1 — POC** | Local markdown + LLM agent + Obsidian | Solo use, this machine |
| **2 — Product** | Dockerized app with CLI, web UI, search | Solo/local, portable |
| **3 — Team** | AWS serverless, multi-user, shared wikis | 3–4 person team |

See [solution.md](./solution.md) for detailed architecture and implementation plan.

## Quick Start (Phase 1)

1. Open this folder in Obsidian as a vault
2. Drop source files into `raw/`
3. Use an LLM agent (Claude Code, Codex, etc.) to ingest and query
4. Browse the wiki in Obsidian, review AI output, promote trusted content

## Tech Stack

- **LLM Agent**: Claude Code / OpenAI Codex / any coding agent
- **Browsing**: Obsidian (graph view, Dataview, Marp)
- **Source Capture**: Obsidian Web Clipper
- **Search**: index.md + grep → qmd (BM25 + vector, local)
- **Version Control**: Git
- **Containerization** (Phase 2): Docker
- **Cloud** (Phase 3): AWS Lambda, S3, DynamoDB, Bedrock

## License

Personal project. Pattern credit: [Andrej Karpathy](https://gist.github.com/karpathy/1dd0294ef9567971c1e4348a90d69285).
