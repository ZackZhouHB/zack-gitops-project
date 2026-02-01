# RAG Tooling Landscape: Our Approach vs Frameworks

> **Purpose:** Document the RAG tooling decisions and trade-offs  
> **Created:** 2026-02-01

---

## The RAG Implementation Spectrum

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RAG IMPLEMENTATION OPTIONS                           │
│                                                                              │
│  LEVEL 1: DIY (Our Approach)                                                │
│  ───────────────────────────                                                │
│  You write: Chunking → Embedding → Vector DB → Retrieval → LLM             │
│  Pros: Full control, understand everything, no abstraction leaks            │
│  Cons: More code, reinvent some wheels                                      │
│                                                                              │
│  LEVEL 2: Frameworks (LangChain / LlamaIndex)                               │
│  ────────────────────────────────────────────                               │
│  Pre-built components you compose together                                  │
│  Pros: Faster development, community patterns, integrations                 │
│  Cons: Abstraction overhead, harder to debug, version churn                 │
│                                                                              │
│  LEVEL 3: Managed Services (Bedrock KB, Azure AI Search)                    │
│  ───────────────────────────────────────────────────────                    │
│  Cloud provider handles everything                                          │
│  Pros: Zero code, managed scaling, enterprise support                       │
│  Cons: Expensive, less control, vendor lock-in                              │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tool Comparison

### LangChain

**What it is:** General-purpose LLM application framework with modular components.

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import BedrockEmbeddings
from langchain.vectorstores import Weaviate
from langchain.chains import RetrievalQA

# Compose pieces together
splitter = RecursiveCharacterTextSplitter(chunk_size=1000)
vectorstore = Weaviate(client, embeddings)
chain = RetrievalQA.from_chain_type(llm, retriever=vectorstore.as_retriever())
```

| Pros | Cons |
|------|------|
| Huge ecosystem | Frequent breaking changes |
| Many integrations | Abstraction hides details |
| Good chunking utilities | Chains can be hard to debug |
| Active community | Overkill for simple RAG |

**Best for:** Teams wanting pre-built patterns, rapid prototyping.

---

### LlamaIndex

**What it is:** RAG-focused framework with opinionated defaults.

```python
from llama_index import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("./data").load_data()
index = VectorStoreIndex.from_documents(documents)
query_engine = index.as_query_engine()
response = query_engine.query("What is X?")
```

| Pros | Cons |
|------|------|
| RAG-first design | Less flexible than LangChain |
| Quick to start | Opinionated defaults |
| Good for documents | Harder to customize deeply |
| Built-in evaluation | Smaller ecosystem |

**Best for:** Document Q&A use cases, quick demos.

---

### Agents

**What it is:** Pattern where LLM decides which tool to use.

```python
from langchain.agents import create_react_agent

tools = [
    search_documents,    # RAG retrieval
    search_web,          # Web search  
    run_sql,             # Database query
    calculate,           # Math
]

agent = create_react_agent(llm, tools)
agent.invoke("What were our Q3 sales?")  # Agent picks: run_sql
agent.invoke("What does our policy say?") # Agent picks: search_documents
```

| Pros | Cons |
|------|------|
| Dynamic routing | Unpredictable behavior |
| Multi-tool capability | Harder to test |
| Handles diverse queries | Higher latency (multiple LLM calls) |
| Impressive demos | Production reliability concerns |

**Best for:** Complex multi-source queries, chatbots with diverse capabilities.

---

### Managed Services (Bedrock KB, etc.)

**What it is:** Cloud provider handles chunking, embedding, storage, retrieval.

```python
# Bedrock Knowledge Base - just configure, no code
# 1. Point to S3 bucket with documents
# 2. Select embedding model
# 3. Query via API

response = bedrock_agent.retrieve_and_generate(
    input={"text": "What is our refund policy?"},
    retrieveAndGenerateConfiguration={
        "knowledgeBaseConfiguration": {
            "knowledgeBaseId": "KB123",
            "modelArn": "anthropic.claude-3-sonnet"
        }
    }
)
```

| Pros | Cons |
|------|------|
| Zero infrastructure | Expensive at scale |
| Managed scaling | Less control over chunking |
| Enterprise support | Vendor lock-in |
| Compliance ready | Black box behavior |

**Best for:** Enterprise with budget, compliance requirements, small doc sets.

---

## Where Tools Fit in RAG Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RAG PIPELINE                                    │
│                                                                              │
│   INGESTION                    RETRIEVAL                    GENERATION       │
│                                                                              │
│   ┌─────────┐                  ┌─────────┐                  ┌─────────┐     │
│   │ Chunking│                  │ Search  │                  │   LLM   │     │
│   └────┬────┘                  └────┬────┘                  └────┬────┘     │
│        │                            │                            │          │
│   ─────┴────────────────────────────┴────────────────────────────┴─────     │
│                                                                              │
│   LangChain:  TextSplitters ──── Retrievers ──── Chains/LCEL               │
│                                                                              │
│   LlamaIndex: Readers ────────── QueryEngine (all-in-one) ─────────        │
│                                                                              │
│   Agents:     RAG as one "tool" among many the LLM can choose              │
│                                                                              │
│   Managed:    ════════════════ Black Box ══════════════════════            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Our Hybrid Approach (Stage 4)

### Philosophy
> Use frameworks for what they're good at, DIY for what needs control.

### Component Decisions

| Component | Our Choice | Why |
|-----------|------------|-----|
| **Chunking** | LangChain splitters | Best-in-class, well-tested, no need to reinvent |
| **Embedding** | Direct API (Ollama) | Simple, no wrapper overhead |
| **Vector DB** | Weaviate direct client | Full control over hybrid queries |
| **Retrieval** | Custom code | LangChain retrievers too basic for hybrid+rerank |
| **Generation** | Direct API (vLLM) | No chain overhead, full control |
| **Evaluation** | Custom + RAGAS concepts | Need fine-grained metrics |

### What We Use from LangChain

```python
# ONLY these - not the full framework
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,  # General documents
    MarkdownTextSplitter,            # Markdown/technical docs
)
```

### What We Build Custom

```python
# These need more control than frameworks provide
class HybridRetriever:      # Vector + BM25 + tunable alpha
class LLMReranker:          # Relevance scoring with local vLLM
class RAGEvaluator:         # RAGAS-style metrics
```

### What We Skip (For Now)

| Skipped | Reason |
|---------|--------|
| LlamaIndex | Too opinionated, hides too much |
| LangChain chains | Abstraction overhead, hard to debug |
| LangChain retrievers | Too basic for hybrid search |
| Agents | Scope creep - save for future stage |

---

## When to Use What (Decision Guide)

| Scenario | Recommendation |
|----------|----------------|
| Quick prototype / demo | LlamaIndex |
| Production RAG with control | LangChain components + custom (our approach) |
| Multi-tool chatbot | Agents |
| Enterprise / compliance | Bedrock KB or Azure AI Search |
| Learning / interviews | DIY first, then frameworks |
| Cost-sensitive | Self-hosted (our approach) |

---

## The Chunking Dilemma

### Why Chunking is Hard

| Factor | Trade-off |
|--------|-----------|
| **Chunk Size** | Small = precise retrieval, loses context. Large = more context, noisy retrieval |
| **Overlap** | More = better continuity, but more storage/cost |
| **Strategy** | Fixed = simple/fast. Semantic = better quality, slow/complex |
| **Doc Types** | PDF, Markdown, HTML, Code all need different handling |

### Why Companies Choose Managed Services

| Benefit | Reality |
|---------|---------|
| "Zero config" | True, but you lose control |
| "It just works" | Until it doesn't, then you can't fix it |
| "Enterprise support" | Real value for compliance |
| **Hidden cost** | ~$0.10/1K tokens + storage = expensive at scale |

### Our Strategy

1. **Implement multiple strategies** (fixed, recursive, markdown-aware)
2. **Measure each with evaluation metrics**
3. **Choose based on data, not guesswork**

---

## Production-Grade RAG Checklist

| Aspect | Amateur RAG | Production RAG |
|--------|-------------|----------------|
| Chunking | Fixed size | Strategy per doc type |
| Retrieval | Vector only | Hybrid + rerank |
| Evaluation | "Looks good" | RAGAS metrics > 0.8 |
| Monitoring | None | Grafana dashboard |
| Testing | Manual | Automated test suite |
| Tuning | Guesswork | Data-driven |

---

## Interview Talking Points

### On Framework Choice:
> "I use LangChain's text splitters because they're well-tested, but I implement retrieval and evaluation custom because I need fine-grained control over hybrid search tuning and metrics."

### On Managed vs Self-Hosted:
> "Bedrock KB is great for quick enterprise deployments, but for production systems where you need to tune chunking and retrieval for your specific data, self-hosted gives you the control to optimize."

### On Evaluation:
> "You can't improve what you can't measure. I implement RAGAS-style metrics - faithfulness, relevance, context precision - and track them over time as I tune the system."

---

## Future Considerations

| Topic | When to Add |
|-------|-------------|
| **Agents** | When you need multi-tool routing (Stage 5+) |
| **LlamaIndex** | If you need their specific features (e.g., tree index) |
| **Full LangChain** | If team prefers framework consistency |
| **Managed services** | If compliance/support outweighs control needs |

---

## References

- [LangChain Docs](https://python.langchain.com/)
- [LlamaIndex Docs](https://docs.llamaindex.ai/)
- [RAGAS Evaluation](https://docs.ragas.io/)
- [Weaviate Hybrid Search](https://weaviate.io/developers/weaviate/search/hybrid)
