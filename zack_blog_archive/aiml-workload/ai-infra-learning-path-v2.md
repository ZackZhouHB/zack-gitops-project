# AI Platform Engineer - Modern Learning Path (2025-2026)

> **Goal:** Transition from Senior Cloud Engineer to AI Platform Engineer  
> **Strategy:** Master production AI tooling that companies actually hire for  
> **Differentiator:** You're not learning to build models - you're learning to ship AI systems

---

## The 2026 AI Engineer Reality

What HR/recruiters actually look for (based on current job postings):

| Skill Category | What They Want | Your Advantage |
|----------------|----------------|----------------|
| **Agent Frameworks** | LangGraph, CrewAI, Google ADK | You'll build with all three |
| **RAG Production** | LlamaIndex for data, evaluation with Ragas | Already started custom-rag |
| **Structured Output** | PydanticAI, type-safe agents | Production reliability |
| **Observability** | LangSmith, Arize Phoenix, OpenTelemetry | LLMOps is the new MLOps |
| **Tool Integration** | MCP (Model Context Protocol) | The "USB for AI" standard |
| **Cloud AI** | Bedrock, Vertex AI, Azure OpenAI | Your existing AWS strength |

---

## Your Environment (Unchanged)

| Resource | Specs | Role |
|----------|-------|------|
| **MacBook Pro M4** | 16GB RAM | Primary dev, Ollama, all frameworks |
| **Desktop PC** | RTX 5070 Ti | Heavy inference, vLLM, GPU workloads |
| **AWS Account** | Personal | Production deployment, Bedrock |

---

## Month 1: Modern AI Frameworks (Weeks 1-4)

**Theme:** Learn the tools that appear on every AI engineer job posting

### Week 1: LlamaIndex for RAG (Not LangChain)

**Why LlamaIndex over LangChain for RAG:**
- LlamaIndex = purpose-built for RAG, better data connectors
- LangChain = general orchestration, agents
- 2025 consensus: Use LlamaIndex for data/retrieval, LangGraph for agents

**Tasks:**
- [ ] `pip install llama-index llama-index-llms-bedrock llama-index-embeddings-bedrock`
- [ ] Build RAG pipeline with LlamaIndex: load → chunk → embed → query
- [ ] Use `SimpleDirectoryReader` for your LLD PDFs
- [ ] Implement `SentenceSplitter` with semantic chunking
- [ ] Connect to Bedrock (Claude + Titan Embeddings)
- [ ] Add `CitationQueryEngine` for source attribution

**Deliverable:** LlamaIndex RAG that cites sources, using Bedrock

### Week 2: LangGraph for Agents

**Why LangGraph:**
- LangChain's production evolution - stateful graphs
- Used by Klarna, Replit, Uber, LinkedIn
- Explicit state management, cyclical execution, fault tolerance

**Tasks:**
- [ ] `pip install langgraph langchain-aws`
- [ ] Understand the graph paradigm: nodes, edges, state
- [ ] Build a ReAct agent with tool calling
- [ ] Implement human-in-the-loop approval flow
- [ ] Add checkpointing for long-running agents
- [ ] Connect to Bedrock Claude as the LLM

**Deliverable:** LangGraph agent that can search, calculate, and ask for human approval

### Week 3: PydanticAI for Type-Safe Agents

**Why PydanticAI:**
- Created by Pydantic team (same folks behind FastAPI validation)
- Type-safe inputs/outputs - catches errors at dev time, not runtime
- Built-in dependency injection for tools
- OpenTelemetry native (works with any observability platform)

**Tasks:**
- [ ] `pip install pydantic-ai`
- [ ] Build agent with structured output (Pydantic models)
- [ ] Implement tool with dependency injection
- [ ] Add retry logic with validation
- [ ] Compare: PydanticAI vs raw Bedrock invoke

**Deliverable:** Type-safe agent that returns validated, structured JSON

### Week 4: Google ADK (Agent Development Kit)

**Why Google ADK:**
- Google's answer to agent frameworks (released early 2025)
- Multi-agent orchestration: sequential, parallel, hierarchical
- Works with Gemini, but also supports other LLMs
- Shows you're not locked into one ecosystem

**Tasks:**
- [ ] `pip install google-adk`
- [ ] Build single agent with tools
- [ ] Create multi-agent workflow (researcher → writer → reviewer)
- [ ] Implement callbacks for lifecycle control
- [ ] Add session/memory for stateful conversations

**Deliverable:** Multi-agent content pipeline using Google ADK

---

## Month 2: Production AI Infrastructure (Weeks 5-8)

**Theme:** The infrastructure that makes AI systems reliable at scale

### Week 5: MCP (Model Context Protocol)

**Why MCP:**
- Anthropic's open standard (Nov 2024), adopted by OpenAI, Google
- "USB for AI" - standardized tool integration
- Every major AI IDE (Cursor, Windsurf, Claude) supports it
- Shows you understand the emerging standards

**Tasks:**
- [ ] Understand MCP architecture: clients, servers, tools, resources
- [ ] Build an MCP server that exposes your RAG as a tool
- [ ] Create MCP server for AWS resource queries (S3, DynamoDB)
- [ ] Test with Claude Desktop or Cursor
- [ ] Implement proper auth (OAuth2 for production)

**Deliverable:** MCP server that lets any AI assistant query your knowledge base

### Week 6: LLMOps & Observability

**Why This Matters:**
- "Companies need engineers who can maintain, monitor, version, deploy, and govern AI at scale"
- LLMOps is the new MLOps - specific to LLM workloads

**Tools to Learn:**
- **LangSmith** - LangChain's tracing platform (free tier)
- **Arize Phoenix** - Open source, self-hosted option
- **Pydantic Logfire** - If using PydanticAI

**Tasks:**
- [ ] Integrate LangSmith with your LangGraph agent
- [ ] Set up Arize Phoenix locally: `pip install arize-phoenix`
- [ ] Trace: prompt → LLM → tool calls → response
- [ ] Monitor: latency, token usage, error rates
- [ ] Build dashboard showing RAG pipeline health

**Deliverable:** Observable AI pipeline with traces and metrics

### Week 7: RAG Evaluation with Ragas

**Why Evaluation:**
- "Built a RAG" = junior
- "Built a RAG with 0.85 faithfulness score" = senior
- Ragas is the industry standard for RAG evaluation

**Tasks:**
- [ ] `pip install ragas`
- [ ] Create evaluation dataset (questions + ground truth)
- [ ] Measure: faithfulness, answer relevancy, context precision
- [ ] Implement automated eval in CI/CD
- [ ] Compare: naive RAG vs hybrid search vs re-ranking

**Deliverable:** Evaluation report showing RAG quality metrics

### Week 8: Vector DB + Hybrid Search (Production)

**Upgrade from basic pgvector:**
- [ ] Implement hybrid search (BM25 + vector) in pgvector
- [ ] Add re-ranking with Cohere or cross-encoder
- [ ] Deploy Qdrant for comparison (better filtering)
- [ ] Benchmark: latency, recall@k, MRR

**Deliverable:** Production vector search with hybrid retrieval and re-ranking

---

## Month 3: Multi-Agent Systems & Portfolio (Weeks 9-12)

**Theme:** Advanced patterns + interview-ready portfolio

### Week 9: CrewAI for Team-Based Agents

**Why CrewAI:**
- Role-based agent teams (researcher, analyst, writer)
- Popular for complex workflows
- Different paradigm from LangGraph (teams vs graphs)

**Tasks:**
- [ ] `pip install crewai`
- [ ] Build a crew: 3 agents with distinct roles
- [ ] Implement task delegation and handoff
- [ ] Add memory sharing between agents
- [ ] Compare: CrewAI vs LangGraph vs Google ADK

**Deliverable:** Multi-agent crew that researches and writes reports

### Week 10: DSPy for Prompt Optimization

**Why DSPy:**
- Stanford's framework - treats prompts as optimizable programs
- No more manual prompt engineering
- Define metrics, DSPy finds optimal prompts automatically

**Tasks:**
- [ ] `pip install dspy`
- [ ] Convert a manual prompt to DSPy signature
- [ ] Define evaluation metric
- [ ] Run optimization (BootstrapFewShot, MIPRO)
- [ ] Compare: hand-tuned prompt vs DSPy-optimized

**Deliverable:** DSPy-optimized RAG that outperforms manual prompts

### Week 11: Capstone - Enterprise AI Platform

**Build a complete system showcasing all skills:**

```
┌─────────────────────────────────────────────────────────┐
│                    Your Portfolio Project               │
├─────────────────────────────────────────────────────────┤
│  Data Layer:     LlamaIndex + pgvector + hybrid search  │
│  Agent Layer:    LangGraph agents with PydanticAI tools │
│  Integration:    MCP server for tool access             │
│  Observability:  Phoenix traces + Ragas evals           │
│  Cloud:          Bedrock + Lambda + API Gateway         │
│  IaC:            Terraform/CDK for everything           │
└─────────────────────────────────────────────────────────┘
```

**Deliverable:** GitHub repo with full documentation, architecture diagram, demo video

### Week 12: Resume & Interview Prep

**Resume Bullets (Before → After):**

| Before | After |
|--------|-------|
| Built RAG with Python | Engineered production RAG pipeline with LlamaIndex, achieving 0.85 faithfulness score via Ragas evaluation |
| Used LangChain | Designed multi-agent workflows using LangGraph with human-in-the-loop approval and checkpoint recovery |
| Called Bedrock API | Built type-safe AI agents with PydanticAI, integrated via MCP protocol for standardized tool access |
| Deployed to AWS | Implemented LLMOps observability with distributed tracing, reducing debugging time by 60% |

**Interview Topics to Master:**
- [ ] "Design a RAG system for 10K concurrent users" → LlamaIndex + Qdrant + caching + async
- [ ] "How would you evaluate RAG quality?" → Ragas metrics, A/B testing, human feedback loops
- [ ] "Compare agent frameworks" → LangGraph (graphs), CrewAI (teams), ADK (Google ecosystem)
- [ ] "What's MCP?" → Anthropic's standard for AI tool integration, adopted by OpenAI/Google

---

## Framework Comparison Cheat Sheet

| Framework | Best For | Key Concept |
|-----------|----------|-------------|
| **LlamaIndex** | RAG, data ingestion | Data connectors, query engines |
| **LangGraph** | Complex agents, workflows | Stateful graphs, checkpoints |
| **PydanticAI** | Type-safe agents | Validated I/O, dependency injection |
| **Google ADK** | Multi-agent systems | Sequential/parallel orchestration |
| **CrewAI** | Team-based agents | Roles, delegation, collaboration |
| **DSPy** | Prompt optimization | Signatures, optimizers, metrics |
| **MCP** | Tool integration | Standardized protocol, servers |
| **Ragas** | RAG evaluation | Faithfulness, relevancy, precision |
| **Phoenix** | Observability | Traces, spans, LLM metrics |

---

## What Makes This Path Different

1. **Framework Diversity** - You'll know LangGraph AND CrewAI AND ADK (not just one)
2. **Production Focus** - Evaluation, observability, type safety (not just "it works")
3. **Standards Awareness** - MCP shows you follow industry direction
4. **Measurable Outcomes** - Ragas scores, latency benchmarks, not just "built a thing"
5. **Cloud + Local** - Bedrock for production, Ollama for dev (cost-effective)

---

## Quick Wins for Resume (Do This Week)

If you want immediate resume impact:

1. **Add LlamaIndex to your RAG** - 2 hours, swap out your custom loaders
2. **Integrate Ragas** - 1 hour, get actual quality scores
3. **Set up Phoenix** - 30 min, instant observability
4. **Build one MCP server** - 2 hours, shows you know the standard

---

## Cost Estimate

| Item | Cost | Notes |
|------|------|-------|
| Bedrock API | ~$20-50/month | Claude + Titan Embeddings |
| LangSmith | Free tier | 5K traces/month |
| Phoenix | Free | Self-hosted |
| Ragas | Free | Open source |
| All frameworks | Free | Open source |
| **Total** | **~$30/month** | Much cheaper than courses |

---

## Next Steps

Ready to start? I recommend:

1. **This week:** Swap your custom RAG to LlamaIndex + add Ragas evaluation
2. **Next week:** Build a LangGraph agent with Bedrock
3. **Week 3:** Add PydanticAI for structured outputs
4. **Week 4:** Create your first MCP server

Want me to start with any of these?
