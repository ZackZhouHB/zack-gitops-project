---
title: "Bedrock-Powered RAG on EKS"
date: 2025-10-06T03:30:40Z
slug: bedrock-powered-rag-on-eks
categories: ["Kubernetes"]
aliases: ["/post/154/"]
legacy_id: 154
---
**The Idea**

I've previously built [Local RAG](/posts/mlops-build-a-knowledge-base-with-deepseek-r1/)  and [ChatBot applications](/posts/aws-bedrock-with-open-webui/)  using OpenWebUI, and after exploring AWS Bedrock by creating a knowledge base with an S3 data source, I saw a bigger opportunity. My existing OpenWebUI chatbot was running on AWS Fargate, and I decided it was time to level up the architecture.

The goal was to migrate the solution to an Amazon EKS cluster and build a custom, self-developed RAG pipeline that leverages core AWS services. This would allow me to host two distinct AI applications on a single, scalable platform:

- **A General Chatbot:** An OpenWebUI instance for general-purpose conversation, powered directly by a serverless LLM from Amazon Bedrock.
- **A Custom RAG System:** A new pipeline where internal documents are embedded, stored in a vector database (Weaviate), and retrieved at query time to provide accurate, document-grounded answers.

**System Design**

My objective was to deploy a robust Retrieval-Augmented Generation (RAG) system with a decoupled, microservices-based architecture on a scalable, cloud-managed infrastructure. The platform supports document uploads, automated text extraction, vectorization, and a conversational interface where users can ask questions about their own documents. To achieve scalability, reliability, and operational efficiency, I adopted a containerized architecture centered around AWS managed services, fully defined using Infrastructure as Code (IaC).

**Technology Stack**

```bash
# Core Technologies
- **Orchestration:** Amazon EKS (Elastic Kubernetes Service)
- **Vector Database:** Weaviate (deployed as a StatefulSet)
- **LLM:** Amazon Bedrock (Anthropic Claude Sonnet 4.0)
- **Backend:** FastAPI (Python)
- **Frontend:** React SPA (served via Nginx)
- **Storage:** AWS S3 for documents, AWS EFS for chat history
- **Container Registry:** AWS ECR
- **Infrastructure as Code:** Terraform
```

**Vector Database: Weaviate on EKS**

Weaviate was chosen over AWS Kendra for its open-source flexibility, cost efficiency, and Kubernetes-native deployment. Running directly inside the EKS cluster minimizes latency between the backend and the database. Weaviate provides native vector search using the HNSW algorithm, supports multi-modal data (text, images, etc.), and exposes a powerful GraphQL API for flexible queries. Its modular architecture allows pluggable vectorizers such as `text2vec-transformers`, making it ideal for scalable, cloud-native applications.

```text
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Frontend      │    │   EKS Cluster    │    │   AWS Services      │
│   (React SPA)   │──▶│   Backend API    │──▶│   Bedrock Claude    │
│   LoadBalancer  │    │   Weaviate DB    │    │   S3 / EFS Storage  │
└─────────────────┘    └──────────────────┘    └─────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                             EKS Cluster                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │   Frontend      │  │   Backend       │  │   Weaviate Vector   │ │
│  │   - Nginx       │  │   - FastAPI     │  │   - Vector Store    │ │
│  │   - Static SPA  │  │   - Doc Service │  │   - Transformer     │ │
│  │   - LoadBalancer│  │   - Chat API    │  │   - Text2Vec        │ │
│  └─────────────────┘  │   - Weaviate    │  │   - HNSW Index      │ │
│                       │     Client      │  │   - Persistence     │ │
│                       └─────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
        ┌─────────────────┐ ┌─────────────┐ ┌─────────────┐
        │       S3        │ │   Bedrock   │ │     EFS     │
        │ Document Store  │ │ Claude 4.0  │ │ Chat History│
        │ File Uploads    │ │ Sonnet Model│ │ Persistence │
        └─────────────────┘ └─────────────┘ └─────────────┘
```

**System Workflow**

The RAG system delivers a seamless flow from document ingestion to conversational querying. The React single-page frontend is served through Nginx and communicates with the backend via proxied `/api/*` calls, eliminating CORS issues. External access and health checks are managed through an AWS Application Load Balancer (ALB). To maintain lightweight security for internal users, I implemented a session-based authentication system that displays an access modal when the app first loads. The access code is validated and stored in the browser’s `sessionStorage`, enforcing per-session protection without complex user management.

[![[Frontend UI Screenshot]](/images/rag7.png)](/images/rag7.png)

The backend, built with FastAPI, handles concurrent requests efficiently through async I/O. It connects to Weaviate for vector operations via the Python SDK, integrates with AWS Bedrock and S3 through Boto3, and supports document ingestion in formats such as PDF, DOCX, and XLSX. When users upload a document, the pipeline stores the file in S3, extracts text content, embeds it into vector representations, and indexes it in Weaviate. Progress tracking and UI updates are managed in real time through the FastAPI backend.

```text
User Upload → FastAPI → S3 Storage → Text Extraction → Vector Embedding → Weaviate Index
     │              │                    │                    │              │
     │              └─ Metadata ─────────┘                    │              │
     └─ Progress Tracking ──────────────────────────────────────┘              │
     └─ Frontend Update ←─────────────────────────────────────────────────────┘
```

[![[Document Processing Flow]](/images/rag1.png)](/images/rag1.png)

[![[System Overview]](/images/rag2.png)](/images/rag2.png)

For question answering, user queries go through a vector search pipeline that retrieves the most relevant document chunks from Weaviate using HNSW similarity search. These context snippets are passed to Claude Sonnet on Amazon Bedrock, which generates the final answer enriched with referenced sources. Each query and response pair is persisted in AWS EFS to maintain per-session chat history.

```text
User Query → Vector Search → Context Retrieval → LLM Generation → Response + Sources
     │              │              │                    │              │
     │              │              └─ Top-K Documents ──┘              │
     │              └─ Similarity Search (HNSW) ────────────────────────┘
     └─ Chat History Update ←─────────────────────────────────────────────┘
```

[![[Image Placeholder 02: Frontend UI Screenshot]](/images/rag3.png)](/images/rag3.png)

[![[Image Placeholder 02: Frontend UI Screenshot]](/images/rag4.png)](/images/rag4.png)

[![[Image Placeholder 02: Frontend UI Screenshot]](/images/rag5.png)](/images/rag5.png)

**Enable Tracing, Monitoring, and Dashboards**

Even with only two namespaces deployed for the Chatbot and RAG systems, it’s essential to have foundational Kubernetes observability stacks in place. Proper tracing, monitoring, and dashboard visualization ensure visibility into system performance, simplify debugging, and support proactive maintenance as the deployment scales.

Kiali Dashboard:

[![[Image Placeholder 02: Frontend UI Screenshot]](/images/rag9.png)](/images/rag9.png)

Grafana Dashboard:

[![[Image Placeholder 02: Frontend UI Screenshot]](/images/rag0.png)](/images/rag0.png)

Jaeger Tracing:

[![[Image Placeholder 02: Frontend UI Screenshot]](/images/rag10.png)](/images/rag10.png)

**Challenges and Debugging**

With great support using ClaudeCode and AmazonQ, I was able to fix the following issues:

- Fixing inference parameter mismatches for the selected Bedrock model.
- Resolving a client initiation failure in the backend's connection to Weaviate.
- Solving a port conflict (8080) between the two containers in the Weaviate StatefulSet.
- Implementing frontend optimizations to fix document DELETE button pop-up.
- Designing functions to properly manage, retrieve, and display document lists, indexed and chunk status, and chat histories.
- Enabling secure document downloads from the web interface.
- Tuning Weaviate's resource request and limits to resolve OOM (Out of Memory) kills.
- Optimized resource request to have a single t3.large (2C8G) ec2 can handle: Chatbot, RAG System, Add-on (CoreDNS, EFS driver, AWS Loadbalancer Controller), Istio, Monitoring Stack (Prometheus, Grafana, Kiali and Jaeger).

[![[Image Placeholder 02: Frontend UI Screenshot]](/images/rag6.png)](/images/rag6.png)

**Conclusion**

I think this is a well-structured, powerful, scalable, and cost-effective AI application for intelligent document processing that can grow with organizational needs. Using EKS, with its native support for scalability and namespaces, this solution can be easily replicated to serve different teams, ensuring complete security and data isolation for documents and chat histories.

The full application, Terraform and EKS manifests are now available at [my GitHub repo](https://github.com/ZackZhouHB/zack-gitops-project/tree/editing/mlops/eks-rag).
