---
title: "Boost EKS RAG with LangChain"
date: 2025-10-11T05:21:03Z
slug: boost-eks-rag-with-langchain
categories: ["Machine Learning"]
aliases: ["/post/156/"]
legacy_id: 156
---
After building a [custom RAG system on Amazon EKS](/posts/bedrock-powered-rag-on-eks/), my son asked why the application could only handle one question at a time, while ChatGPT allows users to continue conversations through follow-up questions with contextual memory. That made me realize there was an opportunity to leverage the power of the LangChain framework for better abstractions, conversational memory, and access to the broader LangChain ecosystem.

This post documents the journey of migrating to a LangChain-powered solution — the challenges faced, and the new capabilities and benefits gained.

**Why LangChain?**

**LangChain** is an industry-standard framework offering standardized abstractions for RAG, chains, and memory; built-in conversational memory for context retention; advanced ConversationalRetrievalChain for multi-turn dialogue; seamless ecosystem integration with agents and tools; strong community support with active development and documentation; and continuous future-proofing through regular updates and new features.

```bash
# Architecture Comparison
┌─────────────────────────────────────────────────────────────────────┐
│                    ORIGINAL CUSTOM IMPLEMENTATION                   │
├─────────────────────────────────────────────────────────────────────┤
│  User Query → Manual Vector Search → Context Assembly              │
│              → Manual Prompt Construction → Bedrock API Call        │
│              → Manual Response Parsing → Return Answer              │
│                                                                     │
│  Pros: Full control, lightweight, no framework overhead            │
│  Cons: Manual memory management, limited conversational context     │
└─────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│                    LANGCHAIN-POWERED IMPLEMENTATION                 │
├─────────────────────────────────────────────────────────────────────┤
│  User Query → ConversationalRetrievalChain                         │
│              → Automatic Context Retrieval + Memory Integration    │
│              → Optimized Prompt Templates → Custom DirectBedrockLLM│
│              → Structured Response with Sources → Return Answer     │
│                                                                     │
│  Pros: Built-in memory, contextual conversation, extensible chains │
│  Cons: Framework dependency, requires custom LLM for profiles      │
└─────────────────────────────────────────────────────────────────────┘
# Performance Comparison
┌──────────────────────┬─────────────────┬─────────────────────┐
│ Metric               │ Original        │ LangChain           │
├──────────────────────┼─────────────────┼─────────────────────┤
│ Query Time           │ 6–8 seconds     │ 6–8 seconds         │
│ Embedding Dimensions │ 384 (V1)        │ 1024 (V2)           │
│ Chunk Size           │ 1000 chars      │ 1000 chars          │
│ Chunk Overlap        │ 200 chars       │ 200 chars           │
│ Source Attribution   │ ✓ (manual)      │ ✓ (automatic)       │
│ Confidence Scores    │ ✓               │ ✓                   │
│ Conversation Memory  │ ✗ (manual)      │ ✓ (built-in)        │
│ Context Awareness    │ Limited         │ Full multi-turn     │
│ Code Maintainability │ Custom logic    │ Framework patterns  │
│ Extensibility        │ Manual work     │ Plugin ecosystem    │
└──────────────────────┴─────────────────┴─────────────────────┘
```

**Technology Stack Evolution**

```bash
# Core Technologies (Maintained)
- **Orchestration:** Amazon EKS (Elastic Kubernetes Service)
- **Vector Database:** Weaviate (deployed as a StatefulSet)
- **LLM:** Amazon Bedrock (Claude 4.0 Sonnet via Inference Profile)
- **Embeddings:** Amazon Titan Text Embeddings V2 (1024 dimensions)
- **Frontend:** React SPA (served via Nginx)
- **Storage:** AWS S3 for documents, AWS EFS for chat history
- **Infrastructure as Code:** Terraform

# New Additions (LangChain Integration)
- **Framework:** LangChain (Python)
- **Backend:** FastAPI + LangChain RAG Components
- **Chains:** ConversationalRetrievalChain with Memory
- **Custom Components:** DirectBedrockLLM for inference profile support
- **Document Processing:** RecursiveCharacterTextSplitter
- **Memory Management:** ConversationBufferMemory

# The deployment architecture remains cloud-native and fully scalable
┌─────────────────────────────────────────────────────────────────────┐
│                          EKS Cluster (langchain namespace)          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │   Frontend      │  │   Backend       │  │   Weaviate Vector   │ │
│  │   - Nginx       │  │   - FastAPI     │  │   - StatefulSet     │ │
│  │   - React SPA   │  │   - LangChain   │  │   - 1024-dim        │ │
│  │   - LoadBalancer│  │   - Custom LLM  │  │   - Persistence     │ │
│  │                 │  │   - Chains      │  │   - HNSW Index      │ │
│  └─────────────────┘  │   - Memory      │  └─────────────────────┘ │
│                       └─────────────────┘                           │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
        ┌─────────────────┐ ┌─────────────┐ ┌─────────────┐
        │       S3        │ │   Bedrock   │ │     EFS     │
        │ Document Store  │ │ Inference   │ │ Chat History│
        │ (LangChain)     │ │ Profile     │ │ (Memory)    │
        └─────────────────┘ └─────────────┘ └─────────────┘
```

**The Migration Journey: Key Improvements**

- **Direct Bedrock Integration with LangChain**
  Developed a custom `DirectBedrockLLM` class to directly invoke Bedrock inference profile models, achieving full compatibility with Anthropic Claude inference profiles and smoother LangChain integration. Also adopted Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`) for 1024-dimensional embeddings and improved performance.
- **Backend Updated for LangChain Framework Alignment**
  Updated backend code, imports, and implemented the `_call` method to align with the latest LangChain architecture, ensuring compatibility across document upload, chat, and memory functions.

  [![[Conversation UI Update]](/images/rag20.png)](/images/rag20.png)
- **Improved Conversation Experience**
  Added a `NEW CHAT` button to let users start new conversations while preserving previous threads in Shared Conversation History. The conversation interface was moved to the top of the QUERY tab for better accessibility.

  [![[Conversation UI Update]](/images/rag22.png)](/images/rag22.png)
- **Ensure Vector Database with LangChain**
  Updated the UI to display detailed vector statistics after document processing, including document counts, embedding dimensions, and chunk totals for improved observability after LangChain update.

  [![[Vector Database Insights]](/images/rag21.png)](/images/rag21.png)

**Workflow: LangChain Edition**

The LangChain-powered system maintains the same user experience while adding sophisticated conversation management under the hood:

```text
┌─────────────────────────────────────────────────────────────────────┐
│                      DOCUMENT INGESTION FLOW                        │
├─────────────────────────────────────────────────────────────────────┤
│  User Upload → FastAPI → S3 Storage                                │
│              → LangChain Document Creation (with metadata)          │
│              → RecursiveCharacterTextSplitter (1000/200)            │
│              → BedrockEmbeddings (Titan V2)                         │
│              → Weaviate.add_documents() → Index Complete            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    CONVERSATIONAL QUERY FLOW                        │
├─────────────────────────────────────────────────────────────────────┤
│  User Query → ConversationalRetrievalChain                         │
│              ├─ Memory: Load conversation history                  │
│              ├─ Retriever: Vector search in Weaviate               │
│              ├─ Context: Combine history + retrieved docs          │
│              └─ LLM: DirectBedrockLLM generates answer             │
│              → Memory: Store Q&A pair                               │
│              → Response: Answer + Sources + Confidence + Time       │
└─────────────────────────────────────────────────────────────────────┘
```

**Final Look**

The frontend now supports context-aware conversations and follow-up questions while still displaying source attribution, confidence scores, and execution time.

[![[Conversation Result Screenshot]](/images/rag23.png)](/images/rag23.png)

[![[Conversation Example Screenshot]](/images/rag24.png)](/images/rag24.png)

**Conclusion**

Migrating from a custom RAG implementation to LangChain was a journey of discovery, problem-solving, and learning. It preserved all original features while adding sophisticated conversation management and future-proofing for advanced AI capabilities using LangChain as the framework.

**LangChain** also unlocks powerful future capabilities such as multi-agent systems for specialized tasks, seamless tool integration with APIs and databases, advanced memory using entity tracking and knowledge graphs, hybrid search combining vector and keyword retrieval, streaming responses for real-time UX, multi-modal RAG for text and images, built-in evaluation frameworks for testing, and smart cost optimization through caching and token control.

The complete LangChain implementation — including all custom components, deployment manifests, and comprehensive documentation — is available at [my GitHub repository](https://github.com/ZackZhouHB/zack-gitops-project/tree/editing/mlops/eks-rag/langchain-memory). Special thanks to Amazon Q and Claude for their assistance in debugging, problem-solving, and providing architectural guidance throughout this migration journey.
