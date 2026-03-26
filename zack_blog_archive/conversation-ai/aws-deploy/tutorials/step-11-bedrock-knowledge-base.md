# Step 11: Bedrock Knowledge Base & OpenSearch Serverless

> **What you'll learn:** How AWS Bedrock Knowledge Base automates the entire RAG pipeline — from chunking documents to searching them with vector embeddings — and how OpenSearch Serverless acts as the vector database behind it all.

---

## 11.1 What is a Knowledge Base? (RAG Explained Simply)

### The Problem: LLMs Don't Know YOUR Documents

Large Language Models like Claude are trained on massive internet datasets, but they have **no idea** what's in your company's internal documents, your Confluence wiki, or your PDF reports. If you ask Claude "What did our Q3 report say about revenue?", it will either hallucinate an answer or say "I don't have that information."

### The Solution: RAG (Retrieval-Augmented Generation)

**RAG** stands for **Retrieval-Augmented Generation**. Think of it like giving the LLM an open-book exam instead of a closed-book exam:

1. **Closed-book (no RAG):** "Answer this question from memory" → often wrong
2. **Open-book (with RAG):** "Here are the relevant pages — now answer" → much better!

The idea is simple:
- **Before** asking the LLM your question, **search** your documents for relevant chunks
- **Then** paste those chunks into the LLM's prompt as context
- The LLM reads the context and gives an **accurate, grounded** answer

### The RAG Pipeline (6 Steps)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        THE RAG PIPELINE                             │
│                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│  │ 1.UPLOAD │──▶│ 2. CHUNK │──▶│ 3.EMBED  │──▶│ 4.INDEX  │        │
│  │          │   │          │   │          │   │          │        │
│  │ PDF,HTML │   │ Split to │   │ Convert  │   │ Store in │        │
│  │ Docs     │   │ 300-token│   │ to 1024- │   │ vector   │        │
│  │          │   │ pieces   │   │ dim      │   │ database │        │
│  │          │   │          │   │ vectors  │   │          │        │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘        │
│       ▲                                             │               │
│       │              INGESTION PHASE                │               │
│       │          (happens once per sync)            │               │
│  ─────┼─────────────────────────────────────────────┼───────────── │
│       │              QUERY PHASE                    ▼               │
│       │          (happens per question)                             │
│  ┌──────────┐   ┌──────────┐                 ┌──────────┐          │
│  │ 6.ANSWER │◀──│ 5.SEARCH │◀────────────────│ Question │          │
│  │          │   │          │                 │ embedded │          │
│  │ LLM reads│   │ Find     │                 │ as vector│          │
│  │ chunks + │   │ nearest  │                 │          │          │
│  │ answers  │   │ vectors  │                 │          │          │
│  └──────────┘   └──────────┘                 └──────────┘          │
└─────────────────────────────────────────────────────────────────────┘
```

Let's walk through each step:

| Step | What Happens | Analogy |
|------|-------------|---------|
| **1. Upload** | Your documents (PDFs, web pages, Confluence) are collected | Bringing books to the library |
| **2. Chunk** | Documents are split into small pieces (~300 tokens each) | Cutting a book into index cards |
| **3. Embed** | Each chunk is converted to a 1024-number vector by Titan V2 | Giving each card a GPS coordinate in "meaning space" |
| **4. Index** | Vectors are stored in OpenSearch Serverless | Filing the cards in a specially organized cabinet |
| **5. Search** | Your question is also embedded → find nearest chunk vectors | Looking up the closest GPS coordinates to your question |
| **6. Generate** | The matching chunks are given to Claude as context → answer | Handing the relevant cards to a human expert to answer |

### In Our Local Solution vs. AWS

In the local Python implementation (`platform-health-agent/`), we did **every step manually**:

```
LOCAL (manual):                    AWS (automated):
─────────────────                  ──────────────────
Load PDF with PyPDF2               ✅ Bedrock KB handles it
Split text with RecursiveCharSplitter  ✅ Bedrock KB handles it
Call Titan V2 embedding API        ✅ Bedrock KB handles it
Store in ChromaDB/FAISS            ✅ OpenSearch Serverless
Query with similarity_search()     ✅ Bedrock KB retrieve API
Format prompt with context         ✅ Bedrock KB handles it
```

**The entire RAG pipeline that took us ~200 lines of Python is replaced by a single Terraform resource.** That's the magic of Bedrock Knowledge Base.

---

## 11.2 What is OpenSearch Serverless?

### Vector Databases: The Key Concept

A **vector database** is a database optimized for storing and searching **embeddings** — arrays of numbers that represent the "meaning" of text.

```
Traditional Database:              Vector Database:
┌─────────────────────┐           ┌──────────────────────────────┐
│ id │ name  │ age    │           │ id │ text_chunk  │ vector     │
├────┼───────┼────────┤           ├────┼─────────────┼────────────┤
│ 1  │ Alice │ 30     │           │ 1  │ "Terraform  │ [0.12,     │
│ 2  │ Bob   │ 25     │           │    │  is an IaC  │  0.85,     │
│                     │           │    │  tool..."   │  0.33, ... │
│ Query: age > 28     │           │    │             │  1024 dims]│
│ → Exact match       │           │                              │
│                     │           │ Query: "infrastructure tool"  │
│                     │           │ → Nearest neighbor search     │
└─────────────────────┘           └──────────────────────────────┘
```

Think of it like this: a traditional database finds rows where a column **exactly equals** something. A vector database finds rows whose vector is **closest in meaning** to your query vector.

### What Makes It "Serverless"?

| Aspect | Regular OpenSearch | OpenSearch Serverless |
|--------|-------------------|----------------------|
| Servers | You manage EC2 instances | AWS manages everything |
| Scaling | Manual cluster resizing | Auto-scales up/down |
| Patching | Your responsibility | AWS handles it |
| Pricing | Pay for instances 24/7 | Pay per usage (OCU-hours) |
| Setup | Complex cluster config | Create a collection, done |

**"Serverless" = no servers to manage.** You just create a "collection" and start using it.

### Key Terminology

```
OpenSearch Serverless
├── Collection  ← Like a "database" (our: platform-health-kb)
│   ├── Index   ← Like a "table"   (our: bedrock-knowledge-base-default-index)
│   │   ├── Document 1  (a chunk + its vector)
│   │   ├── Document 2
│   │   └── ...
│   └── (can have multiple indexes)
└── (can have multiple collections)
```

### How Vector Search Works

When you ask "What is Terraform?", here's what happens under the hood:

```
Step 1: Your question → Titan V2 embedding model
        "What is Terraform?" → [0.14, 0.82, 0.41, ..., 0.67]  (1024 numbers)

Step 2: OpenSearch finds the K nearest vectors

        Your question vector: ★

        Vector space (imagine 1024 dimensions, shown in 2D):

                    •chunk_47 (terraform modules)
               •chunk_12
          ★ question
               •chunk_91 (terraform providers)
                         •chunk_3 (S3 buckets)

        Nearest neighbors: chunk_47, chunk_91, chunk_12

Step 3: Return the TEXT associated with those vectors
        → "Terraform is an infrastructure as code tool..."
        → "Terraform providers connect to cloud APIs..."
```

### Why 1024 Dimensions?

Each embedding model produces vectors of a specific size. **Amazon Titan Text Embedding V2** outputs **1024-dimensional vectors**. That's 1024 numbers per chunk. This is fixed by the model — you can't change it. Our OpenSearch index must be configured to expect exactly 1024 dimensions, and it must match.

### FAISS HNSW Algorithm

Searching through millions of vectors by computing the distance to every single one would be way too slow. Instead, OpenSearch uses the **HNSW** (Hierarchical Navigable Small World) algorithm from the **FAISS** (Facebook AI Similarity Search) engine.

Think of HNSW like a highway system:

```
Layer 3 (express):     A ─────────────────── B
                       │                     │
Layer 2 (highway):     A ──── C ──── D ──── B
                       │      │      │      │
Layer 1 (local):       A ─ E ─ C ─ F ─ D ─ G ─ B
                       │   │   │   │   │   │   │
Layer 0 (all nodes):   A E H C I F J D K G L B M
```

Instead of checking every node, HNSW starts at the top layer and "zooms in" — jumping from highway to local roads to quickly find the nearest neighbors. This makes search **~100x faster** than brute force, with only a tiny accuracy tradeoff.

---

## 11.3 OpenSearch Serverless Policies (Three Required!)

OpenSearch Serverless is **secure by default** — nothing can access your data until you explicitly create three types of policies. Think of it like a building with three security checkpoints:

```
┌─────────────────────────────────────────────────────┐
│                   YOUR DATA                          │
│                                                      │
│   ┌─────────────────────────────────────────────┐   │
│   │  Checkpoint 3: DATA ACCESS POLICY            │   │
│   │  "Can you read/write the actual data?"       │   │
│   │                                              │   │
│   │   ┌─────────────────────────────────────┐   │   │
│   │   │  Checkpoint 2: NETWORK POLICY        │   │   │
│   │   │  "Can you reach this over the        │   │   │
│   │   │   network?"                          │   │   │
│   │   │                                      │   │   │
│   │   │   ┌─────────────────────────────┐   │   │   │
│   │   │   │  Checkpoint 1: ENCRYPTION   │   │   │   │
│   │   │   │  POLICY                     │   │   │   │
│   │   │   │  "Is data encrypted at      │   │   │   │
│   │   │   │   rest?"                    │   │   │   │
│   │   │   └─────────────────────────────┘   │   │   │
│   │   └─────────────────────────────────────┘   │   │
│   └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Policy 1: Encryption Policy

**What:** Data at rest must be encrypted. AWS requires this — you can't skip it.

**Why:** Even if someone gains physical access to the underlying storage, they can't read your data without the encryption key.

> **Note:** Our OpenSearch collection was created via CLI (`aws opensearchserverless create-collection`), so the encryption policy was set at creation time. You can use either an AWS-managed key (default) or your own KMS key.

### Policy 2: Network Policy

**What:** Controls whether the collection endpoint is reachable from the public internet or only from specific VPCs.

**Why:** Even with authentication, you might want to restrict network-level access. For our development setup, we allow public access for simplicity.

> **Tip:** In production, you'd restrict this to specific VPC endpoints so only your internal services can reach the collection.

### Policy 3: Data Access Policy

**What:** Controls which IAM principals can perform which operations on which collections/indexes.

**Why:** Even if someone can reach the collection over the network AND the data is encrypted, they still need explicit permission to read or write.

Here's our data access policy from `bedrock-kb.tf`:

```hcl
resource "aws_opensearchserverless_access_policy" "bedrock_kb" {
  name = "${var.project_name}-kb-access"
  type = "data"
  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "index"
          Resource     = ["index/platform-health-kb/*"]
          Permission = [
            "aoss:CreateIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
        },
        {
          ResourceType = "collection"
          Resource     = ["collection/platform-health-kb"]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
        }
      ]
      Principal = [
        aws_iam_role.bedrock_kb.arn,
        data.aws_caller_identity.current.arn
      ]
    }
  ])
}
```

**Breaking it down:**

| Field | Value | Meaning |
|-------|-------|---------|
| `type = "data"` | — | This is a data access policy (not encryption or network) |
| `ResourceType = "index"` | `index/platform-health-kb/*` | Applies to all indexes in our collection |
| `Permission` (index) | CreateIndex, ReadDocument, WriteDocument, etc. | Can create indexes and read/write documents |
| `ResourceType = "collection"` | `collection/platform-health-kb` | Applies to the collection itself |
| `Permission` (collection) | CreateCollectionItems, UpdateCollectionItems, etc. | Can manage collection items |
| `Principal` | KB role ARN + our deployer ARN | Both the Bedrock KB service role AND our admin can access |

**Why two principals?** The Bedrock KB role needs access to ingest and search. Our deployer identity (`data.aws_caller_identity.current.arn`) needs access to create the vector index via the Python script.

---

## 11.4 Creating the Vector Index (The Gotcha!)

This was a **real issue** we hit during deployment. Here's the problem:

```
What Terraform creates:             What Bedrock KB needs:
┌───────────────────────┐           ┌───────────────────────┐
│ OpenSearch Collection  │           │ OpenSearch Collection  │
│ (the container)        │           │ ├── Vector Index       │
│ ├── (empty!)           │           │ │   ├── vector field   │
│                        │           │ │   ├── text field     │
└───────────────────────┘           │ │   └── metadata field │
       ↑                            └───────────────────────┘
  Terraform creates                         ↑
  the collection but                   Bedrock KB REQUIRES
  NOT the index inside it!             this to exist FIRST!
```

**The gap:** Terraform can create an OpenSearch Serverless *collection*, but there's no native Terraform resource for creating an *index* inside it. The index must be created via the OpenSearch REST API.

### Attempt 1: null_resource with curl (didn't work)

Our first attempt in `bedrock-kb.tf` used a `null_resource` with `curl --aws-sigv4`:

```hcl
resource "null_resource" "opensearch_vector_index" {
  triggers = {
    collection_id = "0s43wsj0nu6nsj4bdlxf"
    index_name    = "bedrock-knowledge-base-default-index"
  }

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    command     = <<-EOT
      set -e

      COLLECTION_ENDPOINT=$(aws opensearchserverless batch-get-collection \
        --ids "${self.triggers.collection_id}" \
        --query 'collectionDetails[0].collectionEndpoint' \
        --output text \
        --region ${var.aws_region} \
        --profile ${var.aws_profile})

      # Check if index already exists (ignore errors – 404 means not found)
      STATUS=$(curl -s -o /dev/null -w "%%{http_code}" \
        --aws-sigv4 "aws:amz:${var.aws_region}:aoss" \
        --user "" \
        "$COLLECTION_ENDPOINT/${self.triggers.index_name}" 2>/dev/null || true)

      if [ "$STATUS" = "200" ]; then
        echo "Index ${self.triggers.index_name} already exists – skipping creation."
        exit 0
      fi

      echo "Creating vector index ${self.triggers.index_name} ..."
      curl -s -X PUT \
        --aws-sigv4 "aws:amz:${var.aws_region}:aoss" \
        --user "" \
        -H "Content-Type: application/json" \
        "$COLLECTION_ENDPOINT/${self.triggers.index_name}" \
        -d '{
          "settings": {
            "index": {
              "knn": true,
              "knn.algo_param.ef_search": 512
            }
          },
          "mappings": {
            "properties": {
              "bedrock-knowledge-base-default-vector": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                  "engine": "faiss",
                  "name": "hnsw",
                  "parameters": {
                    "m": 16,
                    "ef_construction": 512
                  },
                  "space_type": "l2"
                }
              },
              "AMAZON_BEDROCK_METADATA": {
                "type": "text",
                "index": false
              },
              "AMAZON_BEDROCK_TEXT_CHUNK": {
                "type": "text"
              }
            }
          }
        }'

      echo ""
      echo "Vector index created successfully."
    EOT
  }

  depends_on = [aws_opensearchserverless_access_policy.bedrock_kb]
}
```

**Why it didn't work:** The `curl --aws-sigv4` approach had authentication issues with OpenSearch Serverless. The SigV4 signing for the `aoss` service requires proper session token handling that `curl` doesn't handle reliably in all environments.

### Solution: Python Script with opensearch-py + AWS4Auth

We ended up running a Python script manually to create the index:

```python
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

# Get AWS credentials from our named profile
credentials = boto3.Session(profile_name='sandboxtest').get_credentials()
auth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    'ap-southeast-2',    # region
    'aoss',              # service (OpenSearch Serverless)
    session_token=credentials.token
)

# Connect to our OpenSearch Serverless collection
client = OpenSearch(
    hosts=[{
        'host': '0s43wsj0nu6nsj4bdlxf.ap-southeast-2.aoss.amazonaws.com',
        'port': 443
    }],
    http_auth=auth,
    use_ssl=True,
    connection_class=RequestsHttpConnection
)

# Define the vector index schema
index_body = {
    "settings": {
        "index": {
            "knn": True,                      # Enable k-nearest-neighbors
            "knn.algo_param.ef_search": 512   # Search quality parameter
        }
    },
    "mappings": {
        "properties": {
            "bedrock-knowledge-base-default-vector": {
                "type": "knn_vector",
                "dimension": 1024,            # Must match Titan V2 output
                "method": {
                    "name": "hnsw",           # Algorithm
                    "engine": "faiss",        # Search engine
                    "parameters": {
                        "ef_construction": 512,  # Build quality
                        "m": 16                  # Connectivity
                    },
                    "space_type": "l2"        # Distance metric
                }
            },
            "AMAZON_BEDROCK_TEXT_CHUNK": {
                "type": "text"                # The actual text content
            },
            "AMAZON_BEDROCK_METADATA": {
                "type": "text"                # Source URL, page number, etc.
            }
        }
    }
}

# Create the index
client.indices.create('bedrock-knowledge-base-default-index', body=index_body)
print("✅ Vector index created successfully!")
```

### Parameter Deep Dive

| Parameter | Value | What It Means |
|-----------|-------|--------------|
| `knn: true` | — | Enables k-nearest-neighbors search on this index |
| `knn.algo_param.ef_search: 512` | — | How many candidates to consider during search (higher = more accurate, slower) |
| `dimension: 1024` | — | Vector size — **must** match Titan V2's output (1024 floats per embedding) |
| `hnsw` | — | **H**ierarchical **N**avigable **S**mall **W**orld — the graph algorithm for fast approximate search |
| `faiss` | — | **F**acebook **AI** **S**imilarity **S**earch — the engine that implements HNSW |
| `ef_construction: 512` | — | Quality during index building. Higher = better graph quality, slower indexing. 512 is a good balance. |
| `m: 16` | — | Number of connections per node in the HNSW graph. 16 is the recommended default. Higher = more memory, better recall. |
| `l2` | — | **L2 (Euclidean) distance** — measures straight-line distance between vectors. Alternatives: `cosinesimil`, `innerproduct`. |

### The Three Required Fields

These field names are **not arbitrary** — they are what Bedrock Knowledge Base expects:

```
bedrock-knowledge-base-default-vector  → Where the 1024-dim embedding is stored
AMAZON_BEDROCK_TEXT_CHUNK              → The actual text of the chunk
AMAZON_BEDROCK_METADATA               → JSON metadata (source file, page, etc.)
```

> ⚠️ **Critical:** If you name these fields differently, you must update the `field_mapping` block in the KB resource to match. Mismatched names = KB creation will fail silently.

---

## 11.5 Bedrock Knowledge Base Resource

This is the heart of our setup — the Knowledge Base itself. From `bedrock-kb.tf`:

```hcl
resource "aws_bedrockagent_knowledge_base" "main" {
  name     = "${var.project_name}-kb"
  role_arn = aws_iam_role.bedrock_kb.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${var.aws_region}::foundation-model/${var.bedrock_embed_model_id}"
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = var.opensearch_collection_arn
      vector_index_name = "bedrock-knowledge-base-default-index"
      field_mapping {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
  }

  depends_on = [
    aws_opensearchserverless_access_policy.bedrock_kb,
    null_resource.opensearch_vector_index,
  ]
}
```

**Line-by-line breakdown:**

| Block | What It Does |
|-------|-------------|
| `name` | Human-readable name: `platform-health-kb` |
| `role_arn` | The IAM role KB uses to access S3, OpenSearch, Titan V2, etc. |
| `type = "VECTOR"` | This is a vector-based KB (the only type currently) |
| `embedding_model_arn` | Points to **Amazon Titan Text Embedding V2** (`amazon.titan-embed-text-v2:0`) — the model that converts text → 1024-dim vectors |
| `type = "OPENSEARCH_SERVERLESS"` | We're using OpenSearch Serverless as our vector store (other options: Pinecone, Redis, Aurora) |
| `collection_arn` | ARN of our pre-created collection: `arn:aws:aoss:ap-southeast-2:615299759525:collection/0s43wsj0nu6nsj4bdlxf` |
| `vector_index_name` | The index name inside the collection (must already exist!) |
| `field_mapping` | Maps KB concepts to our index fields — vector, text, and metadata |
| `depends_on` | Ensures the access policy AND vector index exist before KB creation |

```
┌──────────────────────────────────────────────────────────┐
│              Bedrock Knowledge Base                        │
│              (platform-health-kb)                          │
│                                                            │
│  Embedding Model: Titan V2 (text → 1024-dim vectors)      │
│                        │                                   │
│                        ▼                                   │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  OpenSearch Serverless Collection                    │  │
│  │  (platform-health-kb / 0s43wsj0nu6nsj4bdlxf)       │  │
│  │                                                      │  │
│  │  Index: bedrock-knowledge-base-default-index         │  │
│  │  ┌──────────────────────────────────────────────┐   │  │
│  │  │  vector_field  → 1024-dim float array        │   │  │
│  │  │  text_field    → "The quick brown fox..."    │   │  │
│  │  │  metadata_field → {"source": "s3://..."}     │   │  │
│  │  └──────────────────────────────────────────────┘   │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 11.6 Three Data Sources

A Knowledge Base by itself is just a container. **Data sources** tell it _where_ to find your documents. We have three:

### Data Source 1: S3 (PDF Documents)

```hcl
resource "aws_bedrockagent_data_source" "s3" {
  name                 = "s3-documents"
  knowledge_base_id    = aws_bedrockagent_knowledge_base.main.id
  data_deletion_policy = "RETAIN"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn         = aws_s3_bucket.kb_documents.arn
      inclusion_prefixes = ["documents/"]
    }
  }
}
```

**How it works:**

```
S3 Bucket: platform-health-kb-documents
├── documents/              ← ✅ KB will sync these
│   ├── q3-report.pdf
│   ├── onboarding-guide.pdf
│   └── architecture.docx
├── images/                 ← ❌ Ignored (not in "documents/" prefix)
└── temp/                   ← ❌ Ignored
```

| Field | Value | Meaning |
|-------|-------|---------|
| `data_deletion_policy = "RETAIN"` | — | If you delete the data source, keep the indexed chunks in OpenSearch (don't wipe them) |
| `inclusion_prefixes = ["documents/"]` | — | Only sync files under the `documents/` folder — ignore everything else in the bucket |

> **Think of it like:** "Hey KB, watch this specific folder in S3. When I sync, read everything in there, chunk it up, embed it, and store it in OpenSearch."

### Data Source 2: Web Crawler (Blog)

```hcl
resource "aws_bedrockagent_data_source" "web_crawler" {
  name                 = "blog-crawler"
  knowledge_base_id    = aws_bedrockagent_knowledge_base.main.id
  data_deletion_policy = "RETAIN"

  data_source_configuration {
    type = "WEB"
    web_configuration {
      source_configuration {
        url_configuration {
          seed_urls {
            url = var.blog_url
          }
        }
      }
      crawler_configuration {
        crawler_limits {
          rate_limit = 10
        }
        scope = "HOST_ONLY"
      }
    }
  }
}
```

**How it works:**

```
Seed URL: https://zackblog.work/
                │
                ▼
        ┌───────────────┐
        │  Web Crawler   │
        │  (Bedrock)     │
        │                │
        │  Follows links │──→ https://zackblog.work/post-1  ✅ Same host
        │  on the page   │──→ https://zackblog.work/post-2  ✅ Same host
        │                │──→ https://example.com/other     ❌ Different host
        └───────────────┘
                │
                ▼
        Chunks → Embeds → Stores in OpenSearch
```

| Field | Value | Meaning |
|-------|-------|---------|
| `seed_urls` | `https://zackblog.work/` | Starting URL — the crawler begins here and follows links |
| `scope = "HOST_ONLY"` | — | Only crawl pages on the same domain. Won't follow external links. |
| `rate_limit = 10` | — | Max 10 pages per minute — respects the website's capacity and `robots.txt` |

### Data Source 3: Confluence

```hcl
resource "aws_bedrockagent_data_source" "confluence" {
  name                 = "confluence-pages"
  knowledge_base_id    = aws_bedrockagent_knowledge_base.main.id
  data_deletion_policy = "RETAIN"

  data_source_configuration {
    type = "CONFLUENCE"
    confluence_configuration {
      source_configuration {
        host_url               = var.confluence_host
        host_type              = "SAAS"
        auth_type              = "BASIC"
        credentials_secret_arn = aws_secretsmanager_secret.confluence_token.arn
      }
      crawler_configuration {
        filter_configuration {
          type = "PATTERN"
          pattern_object_filter {
            filters {
              object_type       = "Page"
              inclusion_filters = [".*ET.*"]
            }
          }
        }
      }
    }
  }
}
```

**How it works:**

```
Confluence: https://educationstandards.atlassian.net
                │
                ▼
        ┌──────────────────────┐
        │  Confluence Connector │
        │                      │
        │  Auth: BASIC          │──→ Secrets Manager (API token)
        │  Host: SAAS           │
        │                      │
        │  Filter: .*ET.*       │──→ "Project ET overview"  ✅ Matches
        │  (page titles)        │──→ "Budget Report 2024"   ❌ No match
        │                      │──→ "ET Requirements"       ✅ Matches
        └──────────────────────┘
                │
                ▼
        Chunks → Embeds → Stores in OpenSearch
```

| Field | Value | Meaning |
|-------|-------|---------|
| `host_url` | `https://educationstandards.atlassian.net` | Your Confluence instance URL |
| `host_type = "SAAS"` | — | Cloud-hosted Confluence (not self-hosted/Data Center) |
| `auth_type = "BASIC"` | — | Username + API token authentication |
| `credentials_secret_arn` | — | The API token is stored encrypted in AWS Secrets Manager (not hardcoded!) |
| `inclusion_filters = [".*ET.*"]` | — | Regex pattern — only sync pages whose title contains "ET" |

> **Security note:** The Confluence API token is stored in AWS Secrets Manager, encrypted with our KMS key. The KB role has `secretsmanager:GetSecretValue` and `kms:Decrypt` permissions to read it at sync time. Credentials are never stored in Terraform state or code.

---

## 11.7 IAM Role for Knowledge Base

The Knowledge Base needs permissions to do its job. Here's the IAM role from `iam.tf`:

### Trust Policy (Who Can Assume This Role)

```hcl
resource "aws_iam_role" "bedrock_kb" {
  name = "${var.project_name}-bedrock-kb"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
        }
      }
    }]
  })
}
```

**Translation:** "Only the Bedrock service, and only from OUR AWS account, can use this role."

The `Condition` block prevents **confused deputy attacks** — where another AWS account could trick Bedrock into using our role. The `aws:SourceAccount` condition ensures only requests from our account ID are accepted.

### Permissions Policy (What The Role Can Do)

```hcl
resource "aws_iam_role_policy" "bedrock_kb" {
  name = "kb-access"
  role = aws_iam_role.bedrock_kb.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.kb_documents.arn,
          "${aws_s3_bucket.kb_documents.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["aoss:APIAccessAll"]
        Resource = [var.opensearch_collection_arn]
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.confluence_token.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [aws_kms_key.secrets.arn]
      }
    ]
  })
}
```

**Each permission mapped to its purpose:**

```
┌───────────────────────┬──────────────────────────┬────────────────────────────┐
│ Permission            │ Resource                  │ Why KB Needs It            │
├───────────────────────┼──────────────────────────┼────────────────────────────┤
│ s3:GetObject          │ KB documents bucket       │ Read PDF/doc files during  │
│ s3:ListBucket         │ + all objects inside      │ ingestion/sync             │
├───────────────────────┼──────────────────────────┼────────────────────────────┤
│ bedrock:InvokeModel   │ * (all models)            │ Call Titan V2 to generate  │
│                       │                           │ embeddings for each chunk  │
├───────────────────────┼──────────────────────────┼────────────────────────────┤
│ aoss:APIAccessAll     │ Our OpenSearch collection │ Read/write vectors and     │
│                       │                           │ documents in the index     │
├───────────────────────┼──────────────────────────┼────────────────────────────┤
│ secretsmanager:       │ Confluence token secret   │ Retrieve Confluence API    │
│ GetSecretValue        │                           │ credentials at sync time   │
├───────────────────────┼──────────────────────────┼────────────────────────────┤
│ kms:Decrypt           │ Our KMS encryption key    │ Decrypt the secret (it's   │
│                       │                           │ encrypted with our KMS key)│
└───────────────────────┴──────────────────────────┴────────────────────────────┘
```

> **Principle of least privilege:** This role can ONLY do what the KB needs — read S3 documents, call embedding models, write to OpenSearch, and read the Confluence secret. It cannot, for example, delete S3 objects, create new collections, or access other secrets.

---

## 11.8 Verification

After deploying, verify everything is working:

```bash
# 1. Check the Knowledge Base exists and is ACTIVE
aws bedrock-agent get-knowledge-base \
  --knowledge-base-id II5KAPFHJP \
  --region ap-southeast-2 \
  --profile sandboxtest

# Expected: "status": "ACTIVE"

# 2. Check OpenSearch collection is ACTIVE
aws opensearchserverless batch-get-collection \
  --ids 0s43wsj0nu6nsj4bdlxf \
  --region ap-southeast-2 \
  --profile sandboxtest

# Expected: "status": "ACTIVE", "collectionEndpoint": "https://..."

# 3. List all data sources attached to the KB
aws bedrock-agent list-data-sources \
  --knowledge-base-id II5KAPFHJP \
  --region ap-southeast-2 \
  --profile sandboxtest

# Expected: 3 data sources (s3-documents, blog-crawler, confluence-pages)

# 4. Test a retrieve query (the most important test!)
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id II5KAPFHJP \
  --retrieval-query '{"text": "terraform"}' \
  --region ap-southeast-2 \
  --profile sandboxtest

# Expected: retrievalResults with matching text chunks and scores
```

**What the retrieve test does:**

```
"terraform" → Titan V2 → [0.14, 0.82, ...] → OpenSearch nearest-neighbor search
                                                        │
                                                        ▼
                                              Returns top K chunks
                                              with relevance scores
```

If you get results back, the entire pipeline is working: embedding model → vector search → chunk retrieval. 🎉

---

## 11.9 Common Issues & Troubleshooting

### ❌ Issue 1: "Collection is not ACTIVE"

```
Error: Collection 0s43wsj0nu6nsj4bdlxf is in CREATING state
```

**Fix:** OpenSearch Serverless collections take **10–15 minutes** to activate after creation. Wait and retry.

```bash
# Check status
aws opensearchserverless batch-get-collection \
  --ids 0s43wsj0nu6nsj4bdlxf --query 'collectionDetails[0].status'
```

### ❌ Issue 2: "Vector index does not exist"

```
Error: Knowledge base creation failed - index not found
```

**Fix:** The vector index must be created BEFORE the KB resource. If using our Python script, run it after the collection is ACTIVE but before `terraform apply` creates the KB.

```
Timeline:
1. Collection created (CLI)    ──→ Wait 10-15 min
2. Collection becomes ACTIVE   ──→ Run Python script
3. Vector index created        ──→ terraform apply
4. KB resource created         ──→ ✅ Success
```

### ❌ Issue 3: "Field mapping mismatch"

```
Error: Field 'vector' not found in index
```

**Fix:** The field names in your index MUST exactly match the `field_mapping` block in the KB resource:

```
Index field name                         KB field_mapping
─────────────────────────────────────    ──────────────────
bedrock-knowledge-base-default-vector  = vector_field
AMAZON_BEDROCK_TEXT_CHUNK              = text_field
AMAZON_BEDROCK_METADATA                = metadata_field
```

If these don't match, the KB can't find where to store/retrieve data.

### ❌ Issue 4: "Max concurrent ingestion jobs exceeded"

```
Error: ConflictException - An ingestion job is already in progress
```

**Fix:** Bedrock KB allows only **1 concurrent ingestion job per Knowledge Base**. Wait for the current sync to finish before starting another. You can check status:

```bash
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id II5KAPFHJP \
  --data-source-id <DATA_SOURCE_ID> \
  --region ap-southeast-2 \
  --profile sandboxtest
```

### ❌ Issue 5: "Access denied on OpenSearch"

```
Error: 403 Forbidden when accessing collection endpoint
```

**Fix:** Check all three policies:
1. **Encryption policy** — must exist for the collection
2. **Network policy** — must allow access from your network
3. **Data access policy** — must include your IAM principal with correct permissions

> 💡 **Pro tip:** When debugging OpenSearch Serverless access issues, check the data access policy first — it's the most common cause.

---

## Summary

Here's everything we built in this step:

```
┌──────────────────────────────────────────────────────────────────┐
│                    COMPLETE ARCHITECTURE                          │
│                                                                  │
│  Data Sources              Bedrock KB            OpenSearch       │
│  ┌──────────┐            ┌───────────┐        ┌──────────────┐  │
│  │ S3 Bucket│──────┐     │           │        │  Collection   │  │
│  │ (PDFs)   │      │     │ Knowledge │ embed  │  ┌─────────┐ │  │
│  └──────────┘      ├────▶│ Base      │───────▶│  │  Vector  │ │  │
│  ┌──────────┐      │     │           │ store  │  │  Index   │ │  │
│  │ Web      │──────┤     │ Titan V2  │        │  │         │ │  │
│  │ Crawler  │      │     │ Embeddings│        │  │ 1024-dim│ │  │
│  └──────────┘      │     │           │        │  │ vectors │ │  │
│  ┌──────────┐      │     │           │        │  └─────────┘ │  │
│  │Confluence│──────┘     └───────────┘        └──────────────┘  │
│  │ (Wiki)   │                  │                     ▲           │
│  └──────────┘                  │                     │           │
│                                ▼                     │           │
│                         ┌───────────┐                │           │
│                         │  IAM Role  │───────────────┘           │
│                         │ (least     │  aoss:APIAccessAll        │
│                         │  privilege)│                            │
│                         └───────────┘                            │
│                                                                  │
│  Security: 3 OpenSearch policies (encryption + network + data)   │
│  Auth: Secrets Manager for Confluence API token (KMS encrypted)  │
└──────────────────────────────────────────────────────────────────┘
```

**Key takeaways:**
1. **RAG** = search your docs first, then give context to the LLM
2. **Bedrock KB** automates the entire RAG pipeline (chunk → embed → index → search)
3. **OpenSearch Serverless** is the vector database — stores embeddings for fast similarity search
4. **Three policies required** — encryption, network, data access (secure by default)
5. **Vector index must exist before KB creation** — this is the biggest gotcha
6. **Three data sources** feed the KB: S3 documents, web crawler, and Confluence
7. **IAM role** follows least privilege — only the permissions KB actually needs
