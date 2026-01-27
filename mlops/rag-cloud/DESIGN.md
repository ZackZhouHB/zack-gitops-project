# RAG Cloud - AWS Architecture Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              USERS                                       │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────────┐
│                           CloudFront                                     │
│                      (CDN + HTTPS + Caching)                            │
└──────────────┬──────────────────────────────────────┬───────────────────┘
               │                                      │
┌──────────────▼──────────────┐        ┌──────────────▼──────────────┐
│      S3 (Frontend)          │        │         ALB                 │
│   React Static Assets       │        │   Application Load Balancer │
└─────────────────────────────┘        └──────────────┬──────────────┘
                                                      │
┌─────────────────────────────────────────────────────▼───────────────────┐
│                              EKS Cluster                                 │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                         Namespace: rag                              │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │ │
│  │  │ Backend Pod     │  │ Worker Pod      │  │ Redis (Helm)    │    │ │
│  │  │ (FastAPI)       │  │ (SQS Consumer)  │  │ (Cache)         │    │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘    │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└──────┬──────────────────┬──────────────────┬────────────────────────────┘
       │                  │                  │
┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐    ┌─────────────┐
│ OpenSearch  │    │   Bedrock   │    │     S3      │    │     SQS     │
│ Serverless  │    │             │    │  Documents  │    │ Ingest Queue│
│ (1024-dim)  │    │• Titan v2   │    │             │    │             │
│             │    │• Claude 3   │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

---

## Service Mapping (Local → Cloud)

| Local (rag-v1) | AWS Cloud | Notes |
|----------------|-----------|-------|
| docker-compose | **EKS** | Managed Kubernetes |
| Weaviate | **OpenSearch Serverless** | Different client, 1024-dim vectors |
| In-memory queue | **SQS** | Managed queue |
| In-memory cache | **Redis on EKS** | Helm chart |
| File storage | **S3** | Document storage |
| Frontend (Nginx) | **S3 + CloudFront** | Static hosting (no container) |

---

## Key Technical Differences

### 1. Embedding Model
| Local | Cloud |
|-------|-------|
| `amazon.titan-embed-text-v1` | `amazon.titan-embed-text-v2:0` |
| 1536 dimensions | 1024 dimensions |

**Reason:** Titan v1 not available in ap-southeast-2, v2 uses 1024 dimensions.

### 2. OpenSearch Serverless Limitations
| Feature | Standard OpenSearch | Serverless |
|---------|---------------------|------------|
| Custom doc IDs | ✅ Supported | ❌ Not supported |
| Script scoring | ✅ Supported | ❌ Not supported |
| Index refresh | ✅ Manual control | ✅ Auto-managed |

**Code adaptations:**
- Removed custom document IDs in `index_document()`
- Replaced `script_score` with native kNN in hybrid search
- Use `knn` query with `bool.should` for hybrid search

### 3. Frontend Hosting
| Local | Cloud |
|-------|-------|
| Nginx container | S3 + CloudFront |
| Proxies `/api` to backend | Direct API calls to ALB |
| `docker-compose up` | `npm build` → S3 sync |

**Why S3 + CloudFront:**
- Static files don't need a container
- Cost: ~$1/month vs ~$30/month for container
- Global CDN, automatic HTTPS
- Standard pattern for SPAs on AWS

---

## Infrastructure Components

### VPC
- 2 AZs (ap-southeast-2a, 2b)
- Public subnets: ALB, NAT Gateway
- Private subnets: EKS nodes

### EKS
- Cluster: `rag-cloud-dev`
- Node: 1x t3.large (cost-saving)
- AWS Load Balancer Controller for Ingress
- IRSA for pod-level IAM

### OpenSearch Serverless
- Collection type: Vector search
- Index: `documents` with 1024-dim kNN field
- Auth: IAM SigV4 via IRSA

### Bedrock Models
- Embeddings: `amazon.titan-embed-text-v2:0`
- LLM: `anthropic.claude-3-haiku-20240307-v1:0`
- Smart routing: Haiku (fast) / Sonnet (complex)

---

## Current Deployment Values

| Resource | Value |
|----------|-------|
| Region | `ap-southeast-2` |
| Account | `381324498760` |
| EKS Cluster | `rag-cloud-dev` |
| VPC | `vpc-07f777246781deede` |
| OpenSearch | `https://0o0hrf8fm66k1ileok1e.ap-southeast-2.aoss.amazonaws.com` |
| S3 Documents | `rag-cloud-dev-documents-381324498760` |
| S3 Frontend | `rag-cloud-dev-frontend-381324498760` |
| SQS Queue | `https://sqs.ap-southeast-2.amazonaws.com/381324498760/rag-cloud-dev-ingestion` |
| ECR Backend | `381324498760.dkr.ecr.ap-southeast-2.amazonaws.com/rag-cloud-dev-backend` |
| ALB | `k8s-rag-backend-b82de7a322-1362292259.ap-southeast-2.elb.amazonaws.com` |
| CloudFront | `d20ioargdjagdk.cloudfront.net` |

---

## Cost Estimate (Dev Environment)

| Service | Spec | Monthly Cost |
|---------|------|--------------|
| EKS Control Plane | 1 cluster | $73 |
| EC2 (EKS node) | 1x t3.large | $60 |
| OpenSearch Serverless | 2 OCUs | $86 |
| NAT Gateway | 1 | $32 |
| ALB | 1 | $16 |
| S3 | <1GB | $1 |
| CloudFront | Low traffic | $1 |
| **Total** | | **~$270/month** |


---

## Feature Comparison: Local vs Cloud

| Feature | Local (rag-v1) | Cloud (rag-cloud) | Status |
|---------|----------------|-------------------|--------|
| **Core** |
| Health Check | ✅ | ✅ | Same |
| JWT Auth | ✅ | ✅ | Same |
| RBAC (group-based) | ✅ | ✅ | Same |
| **Ingestion** |
| Sync Upload | ✅ | ✅ | Same |
| Async Upload | ✅ | ✅ | SQS-backed |
| Multi-format | ✅ | ✅ | Same |
| **Search** |
| Vector Search | ✅ Weaviate | ✅ OpenSearch | Different backend |
| Keyword Search | ✅ | ✅ | Same |
| Hybrid Search | ✅ | ✅ | Adapted for Serverless |
| Reranking | ✅ | ✅ | Same |
| **RAG** |
| Query | ✅ | ✅ | Same |
| Streaming | ✅ | ✅ | Same |
| Model Routing | ✅ | ✅ | Same |
| Conversation Memory | ✅ | ✅ | Same |
| **Agent** |
| ReAct Agent | ✅ | ✅ | Same |
| **Observability** |
| Audit Logs | ✅ | ✅ | Same |
| Usage Tracking | ✅ | ✅ | Same |
| Cache Stats | ✅ | ✅ | Same |
| **Advanced** |
| Response Caching | ✅ Redis | ✅ Redis | Same |
| Rate Limiting | ✅ | ✅ | Same |
| RAG Evaluation | ✅ | ✅ | Same |
| **Connectors** |
| Web Connector | ✅ | ✅ | Same |
| Pipelines | ✅ | ✅ | Same |
| **Frontend** |
| React UI | ✅ Nginx | ✅ S3+CloudFront | Different hosting |


---

## Troubleshooting Reference

### OpenSearch Serverless Limitations
| Feature | Standard OpenSearch | Serverless |
|---------|---------------------|------------|
| Custom doc IDs | ✅ | ❌ |
| Script scoring | ✅ | ❌ |
| Manual refresh | ✅ | ❌ (auto) |

### Bedrock Model Availability (ap-southeast-2)
| Model | Available | Notes |
|-------|-----------|-------|
| Titan Embed v1 | ❌ | Use v2 instead |
| Titan Embed v2 | ✅ | 1024 dimensions |
| Claude 3 Haiku | ✅ | Fast model |
| Claude 3 Sonnet | ✅ | Smart model |

### Common Issues Quick Reference
| Issue | Solution |
|-------|----------|
| Embedding model invalid | Use `amazon.titan-embed-text-v2:0` |
| Script score error | Use native kNN query |
| Doc ID not supported | Remove `id` from index call |
| Mixed content (HTTPS/HTTP) | Route API through CloudFront |
| Source filter not working | Apply filter at search time |
| Chat history lost on logout | Store in `localStorage.allChats` |
| Document names truncated | Use `word-break: break-all` |
| Answer as single paragraph | Add markdown formatting function |

---

## Frontend Features

| Feature | Description |
|---------|-------------|
| Chat History | All conversations stored in localStorage, persist across sessions |
| Switch Chats | Click any previous chat to load it |
| Delete Chats | ✕ button on each chat in history |
| Delete Documents | ✕ button on each document |
| Markdown Rendering | Bold, code, lists, paragraphs formatted |
| Deduplicated Sources | Unique source URLs only |

---

## What We Skipped (Not Implemented)

### 1. Cognito Authentication (Skipped)

**What we did:** Simple JWT with hardcoded users
**Production approach:** Amazon Cognito

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────▶│  Cognito    │────▶│   Backend   │
│             │     │  User Pool  │     │  (Validate) │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │  Identity   │
                    │    Pool     │
                    │ (AWS Creds) │
                    └─────────────┘
```

**Cognito Features:**
| Feature | Description |
|---------|-------------|
| User Pool | User directory, sign-up/sign-in |
| Identity Pool | Federated identities, AWS credentials |
| MFA | Multi-factor authentication |
| Social Login | Google, Facebook, SAML, OIDC |
| Hosted UI | Pre-built login pages |
| JWT Tokens | ID token, access token, refresh token |

**Integration Pattern:**
```python
# Backend validates Cognito JWT
from jose import jwt
from jose.exceptions import JWTError

COGNITO_REGION = "ap-southeast-2"
COGNITO_USER_POOL_ID = "ap-southeast-2_xxxxx"
COGNITO_APP_CLIENT_ID = "xxxxxxxxx"

def verify_cognito_token(token: str):
    # Get Cognito public keys
    jwks_url = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    
    # Verify token signature and claims
    payload = jwt.decode(
        token,
        jwks_client.get_signing_key_from_jwt(token).key,
        algorithms=["RS256"],
        audience=COGNITO_APP_CLIENT_ID
    )
    return payload
```

**Why Skipped:** Adds complexity for demo, JWT pattern demonstrates the concept.

---

### 2. Automated Data Pipeline (Skipped)

**What we did:** Manual upload via API, simple web connector
**Production approach:** Event-driven ingestion pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PRODUCTION DATA PIPELINE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Data       │     │  S3         │     │ EventBridge │     │  Step       │
│  Sources    │────▶│  Landing    │────▶│  Rule       │────▶│  Functions  │
│             │     │  Bucket     │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └──────┬──────┘
                                                                   │
     ┌─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Lambda     │     │  SQS        │     │  Lambda     │     │ OpenSearch  │
│  Extract    │────▶│  Queue      │────▶│  Embed      │────▶│ Serverless  │
│  & Chunk    │     │  (Buffer)   │     │  & Index    │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────▼──────┐
                    │    DLQ      │
                    │ (Failures)  │
                    └─────────────┘
```

**Pipeline Components:**

| Component | Purpose | AWS Service |
|-----------|---------|-------------|
| Landing Zone | Raw document storage | S3 |
| Event Trigger | Detect new files | EventBridge |
| Orchestration | Coordinate steps | Step Functions |
| Extract | Parse documents | Lambda + Textract |
| Chunk | Split into pieces | Lambda |
| Buffer | Handle bursts | SQS |
| Embed | Generate vectors | Lambda + Bedrock |
| Index | Store vectors | OpenSearch |
| DLQ | Failed items | SQS Dead Letter |
| Monitoring | Track pipeline | CloudWatch |

**Step Functions Workflow:**
```json
{
  "StartAt": "ExtractText",
  "States": {
    "ExtractText": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:extract-text",
      "Next": "ChunkDocument"
    },
    "ChunkDocument": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:chunk-document",
      "Next": "GenerateEmbeddings"
    },
    "GenerateEmbeddings": {
      "Type": "Map",
      "Iterator": {
        "StartAt": "EmbedChunk",
        "States": {
          "EmbedChunk": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:...:embed-chunk",
            "End": true
          }
        }
      },
      "Next": "IndexToOpenSearch"
    },
    "IndexToOpenSearch": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:index-opensearch",
      "End": true
    }
  }
}
```

**Data Source Connectors (Enterprise):**

| Source | Integration Pattern |
|--------|---------------------|
| SharePoint | Graph API + OAuth |
| Confluence | REST API + API Token |
| Google Drive | Drive API + Service Account |
| Salesforce | REST API + OAuth |
| ServiceNow | REST API + OAuth |
| Slack | Events API + Bot Token |
| Email (O365) | Graph API + OAuth |
| Databases | CDC via DMS or Debezium |

**Connector Architecture:**
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Connector  │     │  Secrets    │     │  Lambda     │
│  Config     │────▶│  Manager    │────▶│  Connector  │
│  (DynamoDB) │     │  (Creds)    │     │             │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                        ┌──────▼──────┐
                                        │  External   │
                                        │  API        │
                                        └─────────────┘
```

**Change Detection:**
```python
# Track document versions to avoid re-ingestion
def should_process(doc_id: str, content_hash: str) -> bool:
    existing = dynamodb.get_item(
        TableName="document-versions",
        Key={"doc_id": doc_id}
    )
    if existing and existing["content_hash"] == content_hash:
        return False  # No change
    return True
```

**Why Skipped:** Requires multiple Lambda functions, Step Functions, external API credentials. Demo uses simple upload + web connector to show the pattern.

---

### 3. Production Security (Reference)

**What we did:** Basic JWT, simple RBAC
**Production approach:** Full security stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PRODUCTION SECURITY LAYERS                               │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   WAF       │────▶│  CloudFront │────▶│  ALB        │────▶│  EKS        │
│  (L7 FW)   │     │  (CDN)      │     │  (LB)       │     │  (App)      │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                                                   │
                                                            ┌──────▼──────┐
                                                            │  Bedrock    │
                                                            │  Guardrails │
                                                            └─────────────┘
```

| Layer | Service | Purpose |
|-------|---------|---------|
| Edge Protection | WAF | SQL injection, XSS, rate limiting |
| DDoS Protection | Shield | Volumetric attack mitigation |
| CDN | CloudFront | HTTPS termination, caching |
| Network | VPC | Private subnets, security groups |
| Identity | Cognito | User authentication |
| Authorization | IAM + RBAC | Fine-grained permissions |
| Secrets | Secrets Manager | API keys, credentials |
| Encryption | KMS | Data at rest encryption |
| Content Safety | Bedrock Guardrails | Block harmful content |
| Audit | CloudTrail | API activity logging |
| Compliance | Config | Resource compliance |

**Bedrock Guardrails:**
```python
# Apply guardrails to LLM calls
response = bedrock.invoke_model(
    modelId="anthropic.claude-3-haiku-20240307-v1:0",
    guardrailIdentifier="arn:aws:bedrock:...:guardrail/xxx",
    guardrailVersion="1",
    body=json.dumps({"prompt": user_input})
)
```

**WAF Rules:**
```yaml
# Common WAF rule set
Rules:
  - Name: AWSManagedRulesCommonRuleSet
    Priority: 1
    Statement:
      ManagedRuleGroupStatement:
        VendorName: AWS
        Name: AWSManagedRulesCommonRuleSet
  - Name: RateLimitRule
    Priority: 2
    Statement:
      RateBasedStatement:
        Limit: 2000
        AggregateKeyType: IP
```

---

### 4. Production Observability (Reference)

**What we did:** Basic logging, audit trail
**Production approach:** Full observability stack

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PRODUCTION OBSERVABILITY                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  App Logs   │────▶│ CloudWatch  │────▶│  Alarms     │
│  (stdout)   │     │  Logs       │     │             │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
┌─────────────┐     ┌─────────────┐     ┌──────▼──────┐
│  Metrics    │────▶│ CloudWatch  │────▶│    SNS      │
│  (Custom)   │     │  Metrics    │     │  (Alerts)   │
└─────────────┘     └─────────────┘     └─────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Traces     │────▶│  X-Ray      │────▶│  Service    │
│  (SDK)      │     │             │     │  Map        │
└─────────────┘     └─────────────┘     └─────────────┘
```

| Component | Service | Metrics |
|-----------|---------|---------|
| Logs | CloudWatch Logs | Error rates, latency |
| Metrics | CloudWatch Metrics | Custom business metrics |
| Traces | X-Ray | Request flow, bottlenecks |
| Dashboards | CloudWatch Dashboards | Unified view |
| Alerts | CloudWatch Alarms + SNS | Proactive notification |

**Key Metrics to Track:**
```python
# RAG-specific metrics
cloudwatch.put_metric_data(
    Namespace="RAG/Production",
    MetricData=[
        {"MetricName": "QueryLatency", "Value": latency_ms, "Unit": "Milliseconds"},
        {"MetricName": "RetrievalCount", "Value": num_docs, "Unit": "Count"},
        {"MetricName": "CacheHitRate", "Value": hit_rate, "Unit": "Percent"},
        {"MetricName": "TokensUsed", "Value": tokens, "Unit": "Count"},
        {"MetricName": "BedrockCost", "Value": cost, "Unit": "None"},
    ]
)
```

---

## Summary: Implemented vs Reference

| Category | Implemented | Reference Only |
|----------|-------------|----------------|
| **Auth** | JWT (simple) | Cognito, MFA, Social Login |
| **Pipeline** | Manual upload, Web connector | Step Functions, EventBridge, Connectors |
| **Security** | Basic RBAC, Rate limit | WAF, Shield, Guardrails, KMS |
| **Observability** | Audit logs | CloudWatch, X-Ray, Alarms |
| **Infrastructure** | Terraform + K8s | CI/CD, GitOps, Multi-env |

**Why this approach:**
- Demo focuses on RAG patterns, not AWS plumbing
- Reference sections show production path
- Same architecture, different implementation depth


---

## Agent Architecture

### Current Implementation

The `/agent` endpoint uses ReAct pattern with 5 tools:

| Tool | Description |
|------|-------------|
| `search_docs` | RAG search via OpenSearch |
| `list_sources` | List all documents |
| `calculate` | Math operations |
| `get_date` | Current date/time |
| `compare_docs` | Compare documents |

### AWS-Native Option: Bedrock Agents

```
┌─────────────────────────────────────────────────────────────┐
│                    BEDROCK AGENT                             │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Knowledge   │  │   Action    │  │   Action    │         │
│  │ Base        │  │  Group 1    │  │  Group 2    │         │
│  │ (OpenSearch)│  │  (Lambda)   │  │  (Lambda)   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
│  Guardrails: Content filtering, PII redaction               │
└─────────────────────────────────────────────────────────────┘
```

**Benefits:** Managed, built-in guardrails, automatic RAG integration

See `AGENT.md` for full documentation.
