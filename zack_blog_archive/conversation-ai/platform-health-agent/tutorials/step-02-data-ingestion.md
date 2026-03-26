# Tutorial Step 2: Data Ingestion — Loading Knowledge Into the Vector Database

> **Goal:** Build a pipeline that loads documents, chops them into chunks, converts them to vectors, and stores them in Weaviate so the AI agent can search by *meaning*  
> **Time:** ~20 minutes  
> **Prerequisites:** Step 1 complete (Docker, Weaviate & PostgreSQL running), AWS credentials configured  

---

## What We're Building in This Step

In Step 1, we set up Weaviate — an empty vector database. Now we need to **fill it with knowledge**. This step builds the data ingestion pipeline: a Python script that takes documents from three different sources and loads them into Weaviate so the agent can search them later.

Think of it like stocking a library. Step 1 built the library building. Step 2 fills the shelves with books — but instead of organising by author or title, we organise by *meaning*, so the agent can find relevant information even when the user's question doesn't use the exact same words as the documents.

```
┌──────────────────────────────────────────────────────────────────────┐
│                  The Data Ingestion Pipeline                         │
│                                                                      │
│   ┌───────────┐    ┌───────────┐    ┌───────────┐    ┌────────────┐ │
│   │  LOADERS  │───▶│  CHUNKER  │───▶│ EMBEDDER  │───▶│  WEAVIATE  │ │
│   │           │    │           │    │           │    │   STORE    │ │
│   │ Blog      │    │ Split     │    │ Text →    │    │ Chunks +  │ │
│   │ Confluence│    │ into      │    │ Vector    │    │ Vectors   │ │
│   │ Local PDF │    │ 2000-char │    │ (1024-dim)│    │ stored    │ │
│   │ & Markdown│    │ chunks    │    │ via AWS   │    │ for search│ │
│   └───────────┘    └───────────┘    └───────────┘    └────────────┘ │
│                                                                      │
│   12 blog posts   ─┐                                                 │
│    8 Confluence    ─┼─▶  24 documents  ─▶  198 chunks  ─▶  Weaviate │
│    4 local files   ─┘                                                │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Key Concepts (Explained for Beginners)

Before diving into the code, let's make sure we understand the core ideas.

### What Is Data Ingestion?

"Ingestion" just means "loading data into a system." In the context of AI agents, it's the process of taking your raw knowledge — blog posts, documents, PDFs — and preparing it so the AI can search through it quickly and accurately.

**Analogy:** Imagine you're studying for an exam. You don't read an entire textbook during the exam. Instead, you *prepare* beforehand: you highlight key passages, write summary cards, and organise them by topic. Data ingestion is the preparation step for an AI agent.

### What Is RAG and Why Does Ingestion Matter?

RAG stands for **Retrieval-Augmented Generation**. It's a pattern where an AI:

1. **Retrieves** relevant documents from a database (that's what we're building here)
2. **Augments** its prompt with those documents
3. **Generates** an answer based on the retrieved context

Without ingestion, the agent has no documents to retrieve — it's like a librarian with empty shelves.

### What Is an Embedding?

An embedding is a list of numbers that represents the *meaning* of a piece of text. The key insight: **texts with similar meanings produce similar numbers**.

```
"How does teacher accreditation work in NSW?"
  → [0.023, -0.041, 0.089, 0.112, ... 1024 numbers]

"What is the process for becoming an accredited teacher in New South Wales?"
  → [0.025, -0.039, 0.091, 0.108, ... very similar numbers!]

"Best pizza recipe"
  → [0.891, 0.334, -0.672, -0.441, ... completely different numbers]
```

This is what makes semantic search work. Instead of matching keywords, the database compares these number lists (vectors) and finds the closest matches.

### What Is a Chunk?

Documents can be very long — a blog post might be 10,000 characters. But embedding models work best on shorter, focused pieces of text. So we **chunk** (split) each document into smaller pieces, typically paragraph-sized.

**Why not embed the whole document?**
- Embedding models have input limits (~8,000 tokens for Titan)
- Shorter text = more precise meaning = better search results
- You only want to retrieve the *relevant part*, not the whole document

### What Is Chunk Overlap?

When we split a document, we overlap chunks by 200 characters. This means the last 200 characters of chunk 1 are also the first 200 characters of chunk 2.

```
Document:  [==========AAAAAAAAAA|BBBBBBBBBBB|CCCCCCCCCC==========]

Chunk 1:   [==========AAAAAAAAAA|BB]          ← includes start of B
Chunk 2:              [AAAA|BBBBBBBBBBB|CC]    ← includes end of A, start of C
Chunk 3:                        [BBBB|CCCCCCCCCC==========]  ← includes end of B
```

**Why overlap?** Without it, a sentence that falls exactly at a chunk boundary would be cut in half, and neither chunk would capture its full meaning. Overlap ensures every idea appears fully in at least one chunk.

---

## Project Structure

All ingestion code lives in `agent-backend/ingestion/`:

```
agent-backend/
└── ingestion/
    ├── __init__.py         ← Pipeline orchestrator (calls the 4 modules in order)
    ├── __main__.py         ← Entry point for `python -m ingestion`
    ├── loaders.py          ← Module 1: Load documents from 3 sources
    ├── chunker.py          ← Module 2: Split documents into chunks
    ├── embedder.py         ← Module 3: Convert text to vectors
    └── weaviate_store.py   ← Module 4: Store chunks + vectors in Weaviate
```

The `__main__.py` file is tiny — it just calls `main()`:

```python
"""Allow running: python -m ingestion"""
from ingestion import main
main()
```

This is a Python convention. When you run `python -m ingestion`, Python looks for `__main__.py` inside the `ingestion` package and executes it.

---

## Module 1: Loaders — Fetching Documents From 3 Sources

**File:** `ingestion/loaders.py`

The loaders module fetches raw content and returns it as a standard list of **Document dicts**. Every loader, regardless of source, returns the same shape:

```python
{
    "title": "How RAG Works With Bedrock",   # Human-readable name
    "content": "RAG stands for Retrieval...", # The actual text content
    "source": "blog/post/156",               # Where it came from (for deduplication)
    "url": "https://zackblog.work/post/156", # Link back to original
    "source_type": "blog"                    # Category: blog, confluence, or file
}
```

This consistent format is important — the chunker and embedder don't care *where* a document came from, they just process the `content` field.

### Helper: Stripping HTML

Both blog posts and Confluence pages come back as HTML. We need plain text, so the module includes a small HTML stripper:

```python
class HTMLStripper(HTMLParser):
    """Simple HTML tag stripper — converts HTML to plain text."""

    def __init__(self):
        super().__init__()
        self.result = []     # Collects text pieces
        self.skip = False    # Flag to ignore content inside <script>, <style>, etc.

    def handle_starttag(self, tag, attrs):
        # Skip non-content elements like navigation and scripts
        if tag in ("script", "style", "nav", "header", "footer"):
            self.skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "header", "footer"):
            self.skip = False
        # Add newlines after block-level elements (paragraphs, divs, etc.)
        if tag in ("p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr"):
            self.result.append("\n")

    def handle_data(self, data):
        # Only keep text that's NOT inside a skipped tag
        if not self.skip:
            self.result.append(data)
```

**What's happening:** Python's built-in `HTMLParser` reads HTML tag by tag. We override three methods to (a) skip non-content tags like `<script>`, (b) add newlines where paragraphs break, and (c) collect all visible text. The result is clean plain text.

### Loader 1: Blog Posts (Web Crawl)

```python
def load_blog_posts() -> list[dict]:
    blog_url = os.getenv("BLOG_URL", "https://zackblog.work/")
    documents = []

    # Step 1: Fetch the homepage to discover all post URLs
    resp = requests.get(blog_url, timeout=30)

    # Step 2: Find all post URLs using a regex pattern
    # Matches links like href="/post/156/"
    post_paths = list(set(re.findall(r'href="(/post/\d+/)"', resp.text)))
    post_paths.sort()

    # Step 3: Fetch each post and extract its content
    for path in post_paths:
        url = blog_url.rstrip("/") + path
        resp = requests.get(url, timeout=30)

        # Extract title from the first <h1> or <h2> tag
        title_match = re.search(r"<h[12][^>]*>(.*?)</h[12]>", resp.text, re.DOTALL)
        title = strip_html(title_match.group(1)) if title_match else f"Blog Post {path}"

        # Convert full page HTML to plain text
        content = strip_html(resp.text)

        if len(content) > 100:  # Skip empty/tiny pages
            documents.append({
                "title": title,
                "content": content,
                "source": f"blog{path}",
                "url": url,
                "source_type": "blog",
            })

    return documents
```

**How it works:**
1. Fetches the blog homepage
2. Uses a regular expression to find all links that look like `/post/156/`
3. Visits each post URL individually
4. Strips the HTML to get plain text
5. Skips pages with fewer than 100 characters (empty pages or error pages)

### Loader 2: Confluence Pages (REST API)

```python
def load_confluence_pages() -> list[dict]:
    # Read credentials from environment variables
    base_url = os.getenv("CONFLUENCE_URL", "")
    parent_id = os.getenv("CONFLUENCE_PARENT_PAGE_ID", "")
    username = os.getenv("CONFLUENCE_USERNAME", "")
    api_token = os.getenv("CONFLUENCE_API_TOKEN", "")

    if not all([base_url, parent_id, username, api_token]):
        print("   ⚠️  Confluence credentials not configured. Skipping.")
        return []

    auth = (username, api_token)  # HTTP Basic Auth (email + API token)

    # Fetch all child pages under a parent page
    resp = requests.get(
        f"{base_url}/wiki/rest/api/content/{parent_id}/child/page",
        auth=auth,
        params={"limit": 50, "expand": "body.storage"},  # Include HTML body
        timeout=30,
    )
    pages = resp.json().get("results", [])

    # Convert each page to a Document dict
    for page in pages:
        title = page.get("title", "Untitled")
        html_body = page.get("body", {}).get("storage", {}).get("value", "")
        content = strip_html(html_body)  # HTML → plain text

        if len(content) > 100:
            documents.append({
                "title": title,
                "content": content,
                "source": f"confluence/{page_id}",
                "url": f"{base_url}/wiki/spaces/ET/pages/{page_id}",
                "source_type": "confluence",
            })

    return documents
```

**Key terms explained:**
- **REST API:** A way to talk to web services over HTTP. We send a GET request, Confluence sends back JSON data.
- **Basic Auth:** The simplest authentication — send your username and password (here, email + API token) with every request.
- **`expand=body.storage`:** Tells the Confluence API to include the page's HTML body in the response, not just the title.

### Loader 3: Local Files (PDF & Markdown)

```python
def load_local_files() -> list[dict]:
    docs_dir = os.getenv("DOCUMENTS_DIR", "/app/documents")

    # Fallback for development outside Docker
    if not os.path.exists(docs_dir):
        docs_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "..", "documents"
        )

    documents = []

    for filename in sorted(os.listdir(docs_dir)):
        filepath = os.path.join(docs_dir, filename)

        if filename.endswith(".md") or filename.endswith(".txt"):
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()   # Plain text — no conversion needed

        elif filename.endswith(".pdf"):
            content = extract_pdf_text(filepath)  # Uses PyPDF2 library

        else:
            continue  # Skip unsupported file types

        if len(content) > 100:
            documents.append({
                "title": filename,
                "content": content,
                "source": f"file/{filename}",
                "url": f"local://{filename}",
                "source_type": "file",
            })

    return documents
```

**PDF extraction** uses the `PyPDF2` library. It reads each page and pulls out the text:

```python
def extract_pdf_text(filepath: str) -> str:
    from PyPDF2 import PdfReader
    reader = PdfReader(filepath)
    text_parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            text_parts.append(text)
    return "\n\n".join(text_parts)
```

---

## Module 2: Chunker — Splitting Documents Into Pieces

**File:** `ingestion/chunker.py`

### Configuration

```python
CHUNK_SIZE = 2000       # Target characters per chunk (~500 tokens)
CHUNK_OVERLAP = 200     # Characters of overlap between chunks
```

**Why 2,000 characters?** A rough rule of thumb is that 1 token ≈ 4 characters, so 2,000 characters ≈ 500 tokens. This is a sweet spot: long enough to contain a full idea, short enough for the embedding model to capture its meaning precisely.

**Why 200 characters of overlap?** About 1–2 sentences. Enough to preserve context at boundaries without creating too many duplicate chunks.

### The Main Function

```python
def chunk_documents(documents: list[dict]) -> list[dict]:
    all_chunks = []

    for doc in documents:
        text = doc["content"]
        chunks = split_text(text, CHUNK_SIZE, CHUNK_OVERLAP)

        for i, chunk_text in enumerate(chunks):
            all_chunks.append({
                "content": chunk_text,           # The chunk text itself
                "title": doc["title"],           # Keep track of parent document
                "source": doc["source"],         # Keep source for deduplication
                "url": doc["url"],               # Keep URL so we can link back
                "source_type": doc["source_type"],
                "chunk_index": i,                # 0, 1, 2, ... position within doc
            })

    return all_chunks
```

**What's happening:** For each document, we call `split_text()` to chop it up, then wrap each chunk with the parent document's metadata. The `chunk_index` lets us reconstruct the original order later.

### The Splitting Algorithm (Paragraph-Aware)

This is the most interesting part of the chunker. It doesn't just blindly cut every 2,000 characters — it tries to split at natural boundaries:

```python
def split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    # Short documents don't need chunking
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        if end >= len(text):
            # Last chunk — take everything remaining
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        # Look at the current window of text
        window = text[start:end]

        # PRIORITY 1: Split at paragraph break (double newline)
        para_break = window.rfind("\n\n")
        if para_break > chunk_size // 2:      # Only if in the second half
            end = start + para_break + 2

        else:
            # PRIORITY 2: Split at sentence end (period + space)
            sentence_break = window.rfind(". ")
            if sentence_break > chunk_size // 2:  # Only if in the second half
                end = start + sentence_break + 2

            # PRIORITY 3: Just cut at chunk_size (hard cut)

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # Move forward, but go BACK by overlap amount
        start = end - overlap

    return chunks
```

**The algorithm step by step:**

1. Start at the beginning of the text
2. Look ahead 2,000 characters (one chunk-sized window)
3. **First choice:** Find the last paragraph break (`\n\n`) in the second half of the window — this keeps paragraphs intact
4. **Second choice:** Find the last sentence end (`. `) in the second half — at least don't cut mid-sentence
5. **Last resort:** Cut at exactly 2,000 characters (this rarely happens with well-formatted text)
6. Move forward by `(end position - 200)` — the 200-character overlap
7. Repeat until we reach the end

**Why "second half only"?** If the nearest paragraph break is at position 100 (very early in the window), the chunk would be tiny — only 100 characters. By requiring the break to be past the halfway point, we ensure chunks are at least ~1,000 characters long.

---

## Module 3: Embedder — Text to Vectors via AWS Bedrock

**File:** `ingestion/embedder.py`

This module is the bridge between human-readable text and machine-searchable vectors.

### Configuration

```python
AWS_PROFILE = os.getenv("AWS_PROFILE", "sandboxtest")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")
EMBED_MODEL_ID = os.getenv("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")
EMBED_DIMENSIONS = int(os.getenv("EMBED_DIMENSIONS", "1024"))
```

**Key terms:**
- **AWS Bedrock:** Amazon's managed AI service. We use it to access embedding models without hosting them ourselves.
- **Titan Embed V2:** Amazon's text embedding model. It takes text in and returns a vector (list of numbers) out.
- **1024 dimensions:** Each vector has 1,024 numbers. More dimensions = more nuance in meaning, but more storage.

### Embedding a Single Chunk

```python
def embed_single(client, text: str) -> list[float]:
    # Titan Embed V2 has a max input of ~8,000 tokens — truncate if needed
    if len(text) > 20000:
        text = text[:20000]

    # Prepare the request body as JSON
    body = json.dumps({
        "inputText": text,              # The text to embed
        "dimensions": EMBED_DIMENSIONS, # 1024
    })

    # Call AWS Bedrock
    response = client.invoke_model(
        modelId=EMBED_MODEL_ID,          # "amazon.titan-embed-text-v2:0"
        contentType="application/json",
        accept="application/json",
        body=body,
    )

    # Parse the response — extract the embedding vector
    result = json.loads(response["body"].read())
    return result["embedding"]  # A list of 1024 floats
```

**What's happening:** We send a JSON request to AWS Bedrock containing our text. Bedrock runs it through the Titan embedding model and returns a JSON response containing `"embedding": [0.023, -0.041, ...]` — a list of 1,024 floating-point numbers.

### Embedding All Chunks (With Progress and Rate Limiting)

```python
def embed_chunks(chunks: list[dict], batch_size: int = 10) -> list[dict]:
    client = get_bedrock_client()
    embedded = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        try:
            embedding = embed_single(client, chunk["content"])
            chunk["embedding"] = embedding  # Add the vector to the chunk dict
            embedded.append(chunk)

            # Show progress every 10 chunks
            if (i + 1) % batch_size == 0 or i == total - 1:
                print(f"   Embedded {i + 1}/{total} chunks...")

        except Exception as e:
            print(f"   ⚠️  Failed to embed chunk {i} ({chunk['source']}): {e}")
            continue  # Skip broken chunks, don't crash the whole pipeline

        # Pause every 10 chunks to avoid hitting AWS rate limits
        if (i + 1) % batch_size == 0:
            time.sleep(0.5)

    return embedded
```

**Design decisions:**
- **One at a time, not in parallel:** Titan Embed V2's API takes a single text input per call, so we loop through chunks sequentially.
- **`batch_size=10` with `time.sleep(0.5)`:** AWS Bedrock has rate limits. Every 10 chunks, we pause half a second to avoid getting throttled.
- **`continue` on error:** If one chunk fails (network hiccup, text too long), we skip it rather than crashing the entire pipeline. Losing 1 chunk out of 198 is acceptable.

---

## Module 4: Weaviate Store — Saving to the Vector Database

**File:** `ingestion/weaviate_store.py`

### Connecting to Weaviate

```python
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
COLLECTION_NAME = "DocumentChunk"

def get_client() -> weaviate.WeaviateClient:
    """Connect to the local Weaviate instance."""
    url = WEAVIATE_URL
    host = url.replace("http://", "").replace("https://", "").split(":")[0]
    port = int(url.split(":")[-1]) if ":" in url.split("//")[-1] else 8080

    # Handle Docker hostname resolution
    if host in ("vectordb", "localhost", "127.0.0.1"):
        host = "localhost"

    client = weaviate.connect_to_local(host=host, port=port)
    return client
```

**Why the hostname juggling?** Inside Docker, the Weaviate container is called `vectordb` (its service name in docker-compose). Outside Docker (during development), we need `localhost`. This code handles both cases.

### Creating the Schema

Before storing anything, we need to tell Weaviate what shape our data has — like creating a table in SQL:

```python
def init_weaviate_schema():
    client = get_client()
    try:
        if client.collections.exists(COLLECTION_NAME):
            print(f"   Collection '{COLLECTION_NAME}' already exists")
            return

        client.collections.create(
            name=COLLECTION_NAME,

            # We bring our own vectors (from Bedrock), so no built-in vectorizer
            vectorizer_config=Configure.Vectorizer.none(),

            # Cosine distance — standard for text embeddings
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=VectorDistances.COSINE,
            ),

            # The fields stored alongside each vector
            properties=[
                Property(name="content", data_type=DataType.TEXT,
                         description="The text content of this chunk"),
                Property(name="title", data_type=DataType.TEXT,
                         description="Title of the source document"),
                Property(name="source", data_type=DataType.TEXT,
                         description="Source identifier (e.g., blog/post/156)"),
                Property(name="url", data_type=DataType.TEXT,
                         description="URL or path to the source document"),
                Property(name="source_type", data_type=DataType.TEXT,
                         description="Type: blog, confluence, or file"),
                Property(name="chunk_index", data_type=DataType.INT,
                         description="Position of this chunk within the document"),
            ],
        )
    finally:
        client.close()
```

**Key terms:**
- **Collection:** Weaviate's equivalent of a database table. Ours is called `DocumentChunk`.
- **`Vectorizer.none()`:** We compute embeddings ourselves (via Bedrock Titan), so we tell Weaviate not to try to compute them.
- **HNSW index:** A fast algorithm for searching through millions of vectors. HNSW stands for "Hierarchical Navigable Small World" — it builds a graph structure that makes nearest-neighbour search very fast.
- **Cosine distance:** The method used to compare two vectors. Cosine measures the *angle* between vectors — vectors pointing in the same direction (similar meaning) have a small cosine distance.

### Storing Chunks (Batch Insert)

```python
def store_chunks(chunks: list[dict]):
    client = get_client()
    try:
        collection = client.collections.get(COLLECTION_NAME)

        # Batch insert for efficiency (much faster than inserting one at a time)
        with collection.batch.dynamic() as batch:
            for chunk in chunks:
                batch.add_object(
                    properties={
                        "content": chunk["content"],
                        "title": chunk["title"],
                        "source": chunk["source"],
                        "url": chunk["url"],
                        "source_type": chunk["source_type"],
                        "chunk_index": chunk["chunk_index"],
                    },
                    vector=chunk["embedding"],  # The 1024-dim vector from Bedrock
                )

        print(f"   ✅ Stored {len(chunks)} chunks in Weaviate")
    finally:
        client.close()
```

**Why batch insert?** Inserting 198 chunks one at a time would mean 198 separate network calls. Batch insert groups them into a few larger requests — much faster and more reliable. The `dynamic()` batch mode automatically sizes batches based on performance.

### Counting Chunks

```python
def get_chunk_count() -> int:
    client = get_client()
    try:
        if not client.collections.exists(COLLECTION_NAME):
            return 0
        collection = client.collections.get(COLLECTION_NAME)
        result = collection.aggregate.over_all(total_count=True)
        return result.total_count
    finally:
        client.close()
```

This is used before and after ingestion to show how many chunks are stored — a simple sanity check.

---

## The Pipeline Orchestrator — Tying It All Together

**File:** `ingestion/__init__.py`

This is the main script that calls the four modules in order. Here's the flow:

```python
def main():
    source_filter = sys.argv[1] if len(sys.argv) > 1 else "all"

    # Step 0: Ensure Weaviate schema exists
    init_weaviate_schema()

    # Step 1: Load documents from sources
    documents = []
    if source_filter in ("all", "blog"):
        blog_docs = load_blog_posts()
        documents.extend(blog_docs)

    if source_filter in ("all", "confluence"):
        confluence_docs = load_confluence_pages()
        documents.extend(confluence_docs)

    if source_filter in ("all", "files"):
        file_docs = load_local_files()
        documents.extend(file_docs)

    # Step 2: Chunk documents
    chunks = chunk_documents(documents)

    # Step 3: Embed chunks using Bedrock Titan
    embedded_chunks = embed_chunks(chunks)

    # Step 4: Store in Weaviate
    store_chunks(embedded_chunks)
    total = get_chunk_count()
    print(f"   Total chunks in Weaviate: {total}")
```

**Notice the `source_filter`:** You can ingest everything at once, or just one source type. This is useful during development — re-ingesting only blog posts is much faster than re-running the entire pipeline.

---

## How to Run It

### Prerequisites

1. Weaviate running (from Step 1): `docker compose up -d vectordb`
2. AWS credentials configured (profile `sandboxtest` with Bedrock access)
3. Python dependencies installed: `pip install requests boto3 weaviate-client python-dotenv PyPDF2`
4. Environment variables set in `.env` file

### Run the full pipeline

```bash
cd ~/zz/Documents/conversation-ai/teacher-accreditation-agent/agent-backend
python -m ingestion
```

### Run only one source

```bash
python -m ingestion blog         # Only blog posts
python -m ingestion confluence   # Only Confluence pages
python -m ingestion files        # Only local PDF/MD files
```

### Expected output

```
============================================================
  Teacher Accreditation Agent — Document Ingestion
============================================================

📦 Step 0: Initialising Weaviate schema...
   Collection 'DocumentChunk' already exists
   Current chunk count: 0

🌐 Step 1a: Loading blog posts...
   Found 12 blog posts
   ✅ Building a RAG-Powered Agent with AWS Bedrock...
   ✅ Teacher Accreditation in NSW: A Complete Guide...
   ...
   Loaded 12 blog posts

📄 Step 1b: Loading Confluence pages...
   Found 8 Confluence pages
   ✅ Accreditation Process Overview...
   ...
   Loaded 8 Confluence pages

📁 Step 1c: Loading local files...
   ✅ teacher-standards.pdf (15432 chars)
   ...
   Loaded 4 local files

📊 Total documents loaded: 24

✂️  Step 2: Chunking documents...
   Created 198 chunks from 24 documents

🧠 Step 3: Embedding chunks via AWS Bedrock Titan...
   Embedded 10/198 chunks...
   Embedded 20/198 chunks...
   ...
   Embedded 198/198 chunks...
   Embedded 198 chunks (1024 dimensions each)

💾 Step 4: Storing in Weaviate...
   ✅ Stored 198 chunks in Weaviate
   Total chunks in Weaviate: 198

============================================================
  ✅ Ingestion complete!
============================================================
```

---

## How to Verify Results

After ingestion, you can query Weaviate to verify everything worked.

### Check total chunk count

```bash
curl http://localhost:8080/v1/objects?class=DocumentChunk&limit=1 | python3 -m json.tool
```

### Run a semantic search (via Python)

```python
import weaviate
import json
import boto3

# Connect to Weaviate
client = weaviate.connect_to_local()

# First, embed the search query using the same model
session = boto3.Session(profile_name="sandboxtest", region_name="ap-southeast-2")
bedrock = session.client("bedrock-runtime")

query_text = "How does RAG work with Bedrock?"
body = json.dumps({"inputText": query_text, "dimensions": 1024})
response = bedrock.invoke_model(
    modelId="amazon.titan-embed-text-v2:0",
    contentType="application/json",
    accept="application/json",
    body=body,
)
query_vector = json.loads(response["body"].read())["embedding"]

# Search Weaviate for the nearest chunks
collection = client.collections.get("DocumentChunk")
results = collection.query.near_vector(
    near_vector=query_vector,
    limit=3,
    return_metadata=["distance"],
)

for obj in results.objects:
    print(f"📄 {obj.properties['title']} (chunk {obj.properties['chunk_index']})")
    print(f"   Source: {obj.properties['source_type']}")
    print(f"   Distance: {obj.metadata.distance:.4f}")
    print(f"   Preview: {obj.properties['content'][:150]}...")
    print()

client.close()
```

**Expected result:** The query "How does RAG work with Bedrock?" should return chunks from blog posts and Confluence pages that discuss RAG and Bedrock — even though those documents might never use that exact phrase.

---

## What Happens Under the Hood (Step-by-Step Flow)

Here's the complete journey of a single blog post through the pipeline:

```
1. LOAD
   Input:  URL "https://zackblog.work/post/156/"
   Action: HTTP GET → receive HTML page
   Output: {"title": "Building RAG with Bedrock",
            "content": "<html>RAG stands for Retrieval...",
            "source": "blog/post/156", ...}

2. STRIP HTML
   Input:  "<html><body><h1>Building RAG...</h1><p>RAG stands for..."
   Action: HTMLStripper removes tags, keeps text
   Output: "Building RAG with Bedrock\nRAG stands for Retrieval..."

3. CHUNK
   Input:  8,500 characters of plain text
   Action: split_text(text, 2000, 200)
   Output: 5 chunks (each ~1800–2000 chars, with 200-char overlap)
           chunk_index: 0, 1, 2, 3, 4

4. EMBED
   Input:  "RAG stands for Retrieval Augmented Generation..."  (chunk 0)
   Action: Send to AWS Bedrock Titan → receive vector
   Output: [0.023, -0.041, 0.089, ... 1024 floats]

5. STORE
   Input:  {content, title, source, url, chunk_index, embedding}
   Action: Batch insert into Weaviate "DocumentChunk" collection
   Output: Stored with HNSW vector index for fast cosine search
```

Multiply this by 24 documents → 198 chunks → 198 embedding API calls → 198 stored objects.

---

## Key Design Decisions

| Decision | Value | Why |
|---|---|---|
| Chunk size | 2,000 chars (~500 tokens) | Sweet spot: big enough for a full paragraph, small enough for precise search |
| Chunk overlap | 200 chars (~50 tokens) | 1–2 sentences — prevents information loss at boundaries |
| Paragraph-aware splitting | Yes | Preserves logical structure. Chunks start/end at paragraph or sentence breaks |
| Embedding model | Titan Embed V2 (1024-dim) | Same model as original PoC. Good quality, runs on AWS (no external API keys needed) |
| Vector distance | Cosine | Industry standard for text embeddings. Measures directional similarity |
| Batch insert | Yes (dynamic) | 198 objects in a few network calls vs 198 individual calls |
| Error handling | Skip and continue | One failed chunk shouldn't kill the entire pipeline |
| Rate limiting | 0.5s pause every 10 chunks | Respects AWS Bedrock API rate limits |

---

## Common Issues and Troubleshooting

| Problem | Cause | Solution |
|---|---|---|
| `Weaviate connection refused` | Weaviate not running | Run `docker compose up -d vectordb` and wait for healthy status |
| `NoCredentialsError` from boto3 | AWS profile not configured | Run `aws configure --profile sandboxtest` and set access key, secret, region |
| `ThrottlingException` from Bedrock | Too many API calls too fast | Increase `time.sleep()` in `embed_chunks()` from 0.5 to 1.0 seconds |
| `ModuleNotFoundError: PyPDF2` | PDF library not installed | Run `pip install PyPDF2` |
| `Confluence credentials not configured` | Missing env vars | Set `CONFLUENCE_URL`, `CONFLUENCE_PARENT_PAGE_ID`, `CONFLUENCE_USERNAME`, `CONFLUENCE_API_TOKEN` in `.env` |
| 0 documents loaded | All sources failed silently | Check the ⚠️ warning messages — they indicate which source failed and why |
| Duplicate chunks after re-run | Schema wasn't reset | Delete the collection first: use Weaviate API or delete `./data/weaviate/` and restart |
| Chunks are too small/large | Chunk size doesn't fit your content | Adjust `CHUNK_SIZE` and `CHUNK_OVERLAP` in `chunker.py` |
| `embed_single` timeout | Large text or slow network | The 20,000-char truncation should prevent this; check your internet connection |

---

## What We Have Now

```
BEFORE this step:              AFTER this step:
──────────────────             ─────────────────
Empty Weaviate                 198 chunks loaded and indexed
No searchable knowledge        Semantic search working
No document pipeline           Repeatable ingestion script
Raw HTML/PDF/MD files          Clean, chunked, embedded text
```

---

## Next Step

**Step 3: RAG Search Tool** — we'll build the tool that the agent uses to search Weaviate. When a user asks "What are the requirements for teacher accreditation?", the agent will embed the question, search Weaviate for the nearest chunks, and use those chunks as context for its answer.
