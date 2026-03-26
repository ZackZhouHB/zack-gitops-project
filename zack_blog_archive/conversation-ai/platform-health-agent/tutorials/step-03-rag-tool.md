# Tutorial Step 3: The RAG Search Tool — Giving Your Agent Knowledge

> **Goal:** Understand how the agent searches its knowledge base and retrieves relevant documents  
> **Time:** ~15 minutes  
> **Prerequisites:** Step 1 (infrastructure running), Step 2 (documents ingested into Weaviate)  

---

## What We're Building in This Step

In Steps 1–2 we set up databases and loaded documents. But our agent still can't *find* anything — it needs a **search tool**. That's what `rag_tool.py` is: a function the agent calls to search the knowledge base by meaning, not keywords.

```
┌──────────────────────────────────────────────────┐
│              What We Build Here                   │
│                                                   │
│   rag_search()                                    │
│   ├── Converts a question into numbers (embed)    │
│   ├── Finds closest documents (vector search)     │
│   └── Returns ranked results with sources         │
│                                                   │
│   format_context_for_llm()                        │
│   └── Turns results into text Claude can read     │
└──────────────────────────────────────────────────┘
```

---

## Key Concepts (Explained for Beginners)

### What Is RAG?

**RAG** stands for **Retrieval-Augmented Generation**. Let's break that down:

- **Generation** — an LLM (like Claude) generates a response
- **Retrieval** — we first *retrieve* relevant documents from our knowledge base
- **Augmented** — we *augment* (boost) the LLM's answer with those documents

**Without RAG:**
```
User:  "What are the requirements for Proficient Teacher?"
Claude: "I don't have specific NESA policy information."  ← knows nothing about your docs
```

**With RAG:**
```
User:  "What are the requirements for Proficient Teacher?"
Tool:  [searches knowledge base, finds 5 relevant chunks]
Claude: "Based on NESA documentation, Proficient Teacher requires..."  ← accurate answer!
```

Think of it like an open-book exam. Without RAG, the LLM is doing a closed-book test and can only use what it memorised during training. With RAG, the LLM gets to flip through the textbook first and *then* answer.

### Why Do Agents Need RAG?

LLMs have a knowledge cutoff — they don't know about your private documents, internal policies, or anything published after training. RAG solves this by:

1. **Grounding** — the LLM answers from *your* actual documents, not hallucinated memories
2. **Attribution** — you can show exactly which source the answer came from
3. **Freshness** — update documents anytime, no retraining needed
4. **Cost** — way cheaper than fine-tuning a model on your data

---

## The 3-Step Search Flow

Every RAG search follows the same pattern. Here it is as a picture:

```
         User's Question
              │
              ▼
  ┌───────────────────────┐
  │  Step 1: EMBED QUERY  │    "What are the requirements for Proficient Teacher?"
  │                        │              │
  │  Send question to      │              ▼
  │  AWS Bedrock Titan     │    [0.023, -0.041, 0.089, ... 1024 numbers]
  └───────────┬────────────┘
              │
              ▼
  ┌───────────────────────┐
  │  Step 2: VECTOR SEARCH│    Find the 5 closest document chunks
  │                        │    in Weaviate by comparing numbers
  │  Query Weaviate with   │              │
  │  near_vector()         │              ▼
  └───────────┬────────────┘    Chunk 1 (score 0.92): "Proficient Teacher requires..."
              │                 Chunk 2 (score 0.87): "The Australian Professional..."
              │                 Chunk 3 (score 0.81): "Evidence must demonstrate..."
              ▼
  ┌───────────────────────┐
  │  Step 3: FORMAT       │    Turn raw results into something Claude
  │  RESULTS              │    can read and cite in its answer
  │                        │              │
  │  format_context_for_  │              ▼
  │  llm()                │    "[Source 1: NESA Guide (pdf) — relevance: 0.92]
  └───────────────────────┘     Proficient Teacher requires the completion of..."
```

Now let's see how the actual code implements each step.

---

## Code Walkthrough

### File: `agent-backend/tools/rag_tool.py`

#### The SearchResult Data Model

```python
from pydantic import BaseModel

class SearchResult(BaseModel):
    """Structured output from RAG search."""
    query: str                # The original search query
    results: list[dict]       # List of matching document chunks
    sources: list[str]        # Unique source titles (for attribution)
    success: bool             # Did the search work?
    latency_ms: int           # How long it took (milliseconds)
    message: str = ""         # Human-readable status message
```

**What is Pydantic?** Pydantic is a Python library that validates data. When you say `success: bool`, Pydantic guarantees that `success` will always be `True` or `False` — never `"maybe"` or `42`. If someone passes bad data, it throws an error immediately instead of silently breaking later.

**Why a data model instead of a plain dict?**

| Approach | Problem |
|---|---|
| Return a `dict` | No one knows what keys exist. Was it `result` or `results`? `time` or `latency_ms`? Typos everywhere. |
| Return a `SearchResult` | IDE autocomplete works. Type checking catches errors. Every consumer knows exactly what they'll get. |

Think of it like a shipping label. A `dict` is a mystery box — could contain anything. A `SearchResult` has a label that says exactly what's inside.

#### Step 1: Embed the Query

```python
def _embed_query(text: str) -> list[float]:
    """Embed a query string using Bedrock Titan Embed V2."""

    # Connect to AWS using your local credentials
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    bedrock = session.client("bedrock-runtime")

    # Tell Titan: "Convert this text into a 1024-number vector"
    body = json.dumps({
        "inputText": text,             # The question to embed
        "dimensions": EMBED_DIMENSIONS, # 1024 numbers (configured in config.py)
        "normalize": True,              # Scale to unit length (makes comparison easier)
    })

    # Call the embedding model and extract the result
    response = bedrock.invoke_model(modelId=BEDROCK_EMBED_MODEL_ID, body=body)
    return json.loads(response["body"].read())["embedding"]
```

**What does `normalize: True` do?** Imagine two arrows (vectors) pointing in similar directions but one is really long and one is short. Normalizing makes them the same length so we only compare *direction* (meaning), not *magnitude* (how emphatic the text is). This makes cosine similarity work correctly.

**Why the leading underscore in `_embed_query`?** In Python, a leading underscore is a convention meaning "this is private — don't call it directly from outside this module." It's a helper used by `rag_search()`, not something other code should import.

#### Step 2: Vector Search in Weaviate

```python
async def rag_search(query: str, top_k: int = 5) -> SearchResult:
    """Search the knowledge base for relevant documents."""
    start = time.time()  # Start the stopwatch (for latency tracking)

    try:
        # Step 1: Convert question to numbers
        query_vector = _embed_query(query)

        # Step 2: Connect to Weaviate and search
        client = _get_weaviate_client()
        try:
            collection = client.collections.get("DocumentChunk")  # Our collection from Step 2
            wv_results = collection.query.near_vector(
                near_vector=query_vector,     # "Find chunks close to this vector"
                limit=top_k,                  # Return at most 5 results
                return_properties=[           # Which fields we want back
                    "content", "title", "source_type", "source", "url", "chunk_index"
                ],
                return_metadata=weaviate.classes.query.MetadataQuery(
                    distance=True  # Also tell us HOW close each result is
                ),
            )
        finally:
            client.close()  # Always close the connection (even if search fails)
```

**What is `near_vector`?** This is Weaviate's way of saying "find the objects whose stored vectors are closest to this query vector." Under the hood, it's comparing 1024-dimensional arrows and finding the ones pointing in the most similar direction.

**What is `top_k`?** This means "give me the top K results." If `top_k=5`, Weaviate returns the 5 most similar chunks. More results = more context for Claude, but also more tokens used (and more cost). 5 is a good default.

**Why `async def`?** The `async` keyword means this function can pause while waiting for slow things (like network calls to Weaviate or Bedrock) without blocking the entire server. Other users can be served while one request waits for a response.

#### Processing Results — Score Conversion

```python
        results = []
        sources = set()              # A set automatically removes duplicates
        for obj in wv_results.objects:
            props = obj.properties   # The actual document chunk data

            # Convert distance to score (higher = better)
            score = round(1.0 - (obj.metadata.distance or 0.0), 4)

            results.append({
                "content": props.get("content", ""),
                "title": props.get("title", ""),
                "source_type": props.get("source_type", ""),
                "source": props.get("source", ""),
                "url": props.get("url", ""),
                "chunk_index": props.get("chunk_index", 0),
                "score": score,        # 0.0 to 1.0, higher = more relevant
            })
            sources.add(props.get("title", "unknown"))  # Track unique sources
```

### How Vector Similarity Works

This deserves its own section because it's the core of RAG.

**Cosine Distance vs Cosine Similarity:**

```
Cosine Similarity:  How similar two vectors are (1.0 = identical, 0.0 = unrelated)
Cosine Distance:    How far apart they are       (0.0 = identical, 1.0 = unrelated)

They're just inverses:
    similarity = 1.0 - distance
```

Weaviate returns **distance** (lower = better). But humans think in terms of **scores** (higher = better). So the code converts:

```python
score = 1.0 - distance
```

**Visual example:**

```
Query: "Proficient Teacher requirements"

Result 1:  distance = 0.08  →  score = 0.92  ✅ Very relevant
Result 2:  distance = 0.13  →  score = 0.87  ✅ Relevant
Result 3:  distance = 0.19  →  score = 0.81  ✅ Somewhat relevant
Result 4:  distance = 0.45  →  score = 0.55  ⚠️ Weakly relevant
Result 5:  distance = 0.72  →  score = 0.28  ❌ Probably not relevant
```

**Analogy:** Imagine you're standing in a library. You shout your question, and books on nearby shelves "hear" you clearly (low distance, high score). Books on the other side of the library barely hear you (high distance, low score). Vector search is like sound — closer books are more relevant.

#### The `finally` Block and Error Handling

Notice the nested `try/finally`:

```python
client = _get_weaviate_client()
try:
    # ... do the search ...
finally:
    client.close()  # This runs NO MATTER WHAT — even if search crashes
```

**Why?** Database connections are limited resources. If we opened connections without closing them, we'd eventually run out (called a "connection leak"). The `finally` block guarantees cleanup even if an exception is thrown.

The outer `try/except` catches any error and returns a graceful failure:

```python
    except Exception as e:
        return SearchResult(
            query=query,
            results=[],
            sources=[],
            success=False,             # The caller can check this flag
            latency_ms=latency_ms,
            message=f"RAG search failed: {str(e)}",  # What went wrong
        )
```

**Why return a SearchResult instead of raising an exception?** Because the agent needs to keep running. If the search fails, Claude should say "I couldn't find relevant documents" — not crash the entire conversation. This pattern is called **graceful degradation**.

#### Step 3: Format Results for Claude

```python
def format_context_for_llm(search_result: SearchResult) -> str:
    """Format RAG results into a context string for the LLM prompt."""

    # If nothing was found, say so plainly
    if not search_result.results:
        return "No relevant documents found in the knowledge base."

    # Build a numbered list of sources with content
    parts = []
    for i, r in enumerate(search_result.results, 1):  # Start counting from 1
        parts.append(
            f"[Source {i}: {r['title']} ({r['source_type']}) — relevance: {r['score']}]\n"
            f"{r['content']}\n"
        )
    return "\n---\n".join(parts)  # Separate sources with divider lines
```

**What does this output look like?**

```
[Source 1: NESA Accreditation Guide (pdf) — relevance: 0.9234]
Proficient Teacher accreditation requires demonstration of all 37 standard
descriptors across the four domains of teaching...

---
[Source 2: Policy Handbook (confluence) — relevance: 0.8712]
To achieve Proficient Teacher, candidates must submit evidence of at least
100 hours of professional development...

---
[Source 3: FAQ Document (blog) — relevance: 0.8105]
Common questions about the Proficient Teacher pathway include...
```

**Why format it this way?** Claude needs to:
1. **Know which source said what** — the `[Source N: ...]` header provides attribution
2. **Judge relevance** — the score tells Claude which sources to trust more
3. **Distinguish between sources** — the `---` dividers prevent source text from blending together

This formatted string gets injected into the conversation as a `ToolMessage`, so Claude sees it as "the tool returned this information" and can cite it naturally.

---

## The Complete Flow (Putting It All Together)

```
User asks: "What evidence do I need for Proficient Teacher?"
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  rag_search("evidence requirements Proficient Teacher")     │
│                                                              │
│  1. _embed_query() → [0.023, -0.041, 0.089, ...]           │
│                         │                                    │
│  2. Weaviate.near_vector(query_vector, limit=5)             │
│     Returns 5 closest document chunks with distances         │
│                         │                                    │
│  3. Convert distance → score, build SearchResult             │
│     SearchResult(success=True, results=[...], latency=142ms) │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  format_context_for_llm(search_result)                       │
│                                                              │
│  "[Source 1: NESA Guide (pdf) — relevance: 0.9234]          │
│   Proficient Teacher requires...                             │
│   ---                                                        │
│   [Source 2: Policy Handbook (confluence) — relevance: 0.87] │
│   Evidence must demonstrate..."                              │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
            Claude reads this context and
            generates an accurate, sourced answer
```

---

## How to Test It Standalone

You can test `rag_search()` independently without running the full agent. Create a small test script:

```python
# test_rag.py — run from agent-backend/ directory
import asyncio
from tools.rag_tool import rag_search, format_context_for_llm

async def main():
    # Search for something you know is in the knowledge base
    result = await rag_search("What are the requirements for Proficient Teacher?")

    # Check if it worked
    print(f"Success: {result.success}")
    print(f"Latency: {result.latency_ms}ms")
    print(f"Found: {len(result.results)} results")
    print(f"Sources: {result.sources}")
    print()

    # Look at individual results
    for r in result.results:
        print(f"  [{r['score']:.4f}] {r['title']} ({r['source_type']})")
        print(f"         {r['content'][:100]}...")  # First 100 chars
        print()

    # See what Claude would see
    print("=== Context for LLM ===")
    print(format_context_for_llm(result))

asyncio.run(main())
```

**Run it:**
```bash
cd ~/zz/Documents/conversation-ai/teacher-accreditation-agent/agent-backend
python test_rag.py
```

**Expected output (if documents are ingested):**
```
Success: True
Latency: 342ms
Found: 5 results
Sources: ['FAQ Document', 'NESA Accreditation Guide', 'Policy Handbook']

  [0.9234] NESA Accreditation Guide (pdf)
         Proficient Teacher accreditation requires demonstration of all 37 standard...

  [0.8712] Policy Handbook (confluence)
         To achieve Proficient Teacher, candidates must submit evidence of at least...
  ...
```

**If you get an error:**

| Error | Cause | Fix |
|---|---|---|
| `ConnectionRefusedError` | Weaviate not running | `docker compose up -d vectordb` |
| `botocore.exceptions.NoCredentialsError` | AWS not configured | Check `AWS_PROFILE` in `.env` |
| `Found: 0 results` | No documents ingested | Run Step 2 (data ingestion) first |
| `Collection 'DocumentChunk' not found` | Schema not created | Run the ingestion script from Step 2 |

---

## Summary

```
BEFORE this step:        AFTER this step:
──────────────────       ─────────────────
Documents in Weaviate    Agent can SEARCH those documents
No search capability     rag_search() converts questions to vectors
No result formatting     format_context_for_llm() prepares context
No error handling        Graceful failures with SearchResult model
```

**Key takeaways:**
- RAG = retrieve documents first, then let the LLM generate an answer using them
- The 3-step flow: **embed** → **vector search** → **format**
- Scores are `1.0 - distance` (higher = more relevant)
- Pydantic models (`SearchResult`) make your tool outputs predictable and debuggable
- Always close database connections (use `try/finally`)
- Return graceful errors, don't crash the agent

---

## Next Step

**Step 4: The Basic Agent** — we'll build the LangGraph agent that *uses* this RAG tool in a reasoning loop, deciding when to search and when to answer directly.
