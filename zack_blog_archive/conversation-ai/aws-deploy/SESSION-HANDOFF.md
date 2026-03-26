# SESSION-HANDOFF.md — AWS Deployment

## Project Overview
Platform Health Insight Assistant — AWS ECS Fargate deployment with Bedrock KB + OpenSearch Serverless.
- **Repository**: /Users/zz/zz/Documents/conversation-ai/aws-deploy/
- **AWS Account**: 615299759525 (sandboxtest), ap-southeast-2
- **Local Profile**: sandboxtest
- **Current Status**: ⛔ **DESTROYED** (2026-03-26) — all resources torn down to save costs (~$1,034/month)
- **Re-spin Guide**: See `CLEANUP-AND-RESPIN.md` (30-45 min to rebuild)
- **ALB URL** (when running): http://platform-health-alb-1623429612.ap-southeast-2.elb.amazonaws.com

## Architecture
```
Internet → ALB (idle_timeout=120s for SSE) → ECS Fargate (default VPC)
├── platform-health-frontend (Streamlit :8501, 256 CPU / 512 MiB)
│    └── Cloud Map: agent-backend.platform-health.local:8001
└── platform-health-backend (FastAPI+LangGraph :8001, 512 CPU / 1024 MiB)
     │
     │  Single ReAct loop (no router):
     │  START → llm → [should_continue] → tools → llm → ... → END
     │
     ├── Tool: rag_search → Bedrock KB Retrieve API (KB: II5KAPFHJP) — "ALWAYS use first"
     ├── Tool: assess_incident → KB + pattern matching — "ONLY for active outages"
     ├── Tool: create_checklist → DynamoDB
     ├── Tool: escalate → DynamoDB
     └── Chat history → EFS (fs-0932b5da25a24f024, /mnt/efs/sessions/)

Data Sources (auto-sync):
├── S3 (platform-health-kb-documents-615299759525/documents/) → Lambda trigger → KB Sync
├── Web Crawler (https://zackblog.work/) → Daily sync
└── Confluence (educationstandards.atlassian.net, ET space) → Daily sync

Managed Services:
├── Bedrock Knowledge Base (auto-chunk, auto-embed with Titan V2 1024d)
├── OpenSearch Serverless (collection: platform-health-kb, 0s43wsj0nu6nsj4bdlxf)
├── DynamoDB (platform-health-checklists, platform-health-escalations)
├── EFS (chat history + session state)
├── Secrets Manager (platform-health/confluence-credentials, KMS encrypted)
└── Bedrock LLM: apac.anthropic.claude-sonnet-4-20250514-v1:0
```

## Milestones

### M1: AWS Infrastructure (Terraform) ✅
- 49 resources created via `terraform apply`
- OpenSearch Serverless collection pre-created (10-15 min activation)
- Vector index created via Python opensearch-py (curl+sigv4 didn't work)
- Commit: 6fd20f8

### M2: Docker Build & Deploy ✅
- Images built (linux/amd64 for Fargate) and pushed to ECR
- ECS services at steady state, ALB health checks passing
- Backend: /health → {"status":"healthy","agent":true}
- Frontend: HTTP 200

### M3: Data Sync & E2E Test ✅
- S3: 4 docs uploaded, Lambda auto-triggered sync, 4 indexed
- KB retrieve working: terraform redo query returns results with relevance scores
- Chat endpoint working: full answers with source citations
- Streaming SSE working through ALB
- Sessions endpoint working: chat history persisted on EFS

### M4: Data Source Sync ✅
- S3: 4 docs indexed (auto-trigger via Lambda works)
- Web Crawler: 64 blog pages indexed (178 image files skipped — expected)
- Confluence: 40 pages indexed from ET space (18 image attachments skipped)
- All 3 sources returning correct citations in KB retrieve queries

### M5: Graph Simplification — Single ReAct Loop ✅
- Removed router_node — LLM decides tools directly via ReAct pattern
- Removed incident_triage workflow path — assess_incident is now just a tool
- Removed ROUTER_PROMPT — tool descriptions serve as routing logic
- Simplified AgentState: only messages, tool_calls_log, iteration_count
- Updated SYSTEM_PROMPT: "ALWAYS search KB first" with numbered steps
- Redeployed to ECS, health check passing

### M6: E2E Validation + Cost Analysis + Teardown ✅
- 15-test E2E validation: 100% pass rate, avg 59.9% relevance, 0% error rate
- Concurrency test: 5 simultaneous requests all succeeded
- Cost analysis: ~$1,034/month (94% = OpenSearch Serverless)
- AWS Managed vs Local RAG comparison doc created
- **All 49 Terraform + 3 manual resources destroyed** — verified clean
- Cleanup & re-spin guide created (30-45 min rebuild)

## Resource IDs
> ⚠️ These IDs are from the destroyed deployment. New IDs will be generated on re-spin.

| Resource | Last Known ID |
|----------|---------------|
| ECS Cluster | platform-health-cluster |
| Backend Service | platform-health-backend |
| Frontend Service | platform-health-frontend |
| ALB | platform-health-alb-1623429612.ap-southeast-2.elb.amazonaws.com |
| Bedrock KB | II5KAPFHJP |
| S3 Bucket | platform-health-kb-documents-615299759525 |
| OpenSearch Collection | 0s43wsj0nu6nsj4bdlxf |
| EFS | fs-0932b5da25a24f024 |
| KB Data Source (S3) | THEYKFVVTX |
| KB Data Source (Web) | G0QLXXLD5B |
| KB Data Source (Confluence) | FCAVAELI9A |

## Key Files
```
aws-deploy/
├── terraform/                    # 13 files, 49 resources
├── agent-backend/                # FastAPI + LangGraph + Bedrock KB tools
├── frontend/                     # Streamlit + session management
├── lambda/                       # S3 event → KB sync trigger
├── documents/                    # S3 upload source (4 docs)
├── tutorials/                    # Steps 09-18 (full tutorial series)
│   ├── step-09 to step-16        # Infrastructure & code walkthroughs
│   ├── step-17                   # Agent routing & tool debugging (real story)
│   └── step-18                   # Routing design patterns + implementation
├── SESSION-HANDOFF.md            # This file
├── TROUBLESHOOTING.md            # 14 real issues with fixes
├── OPERATIONS-GUIDE.md           # Container logs, KB inspection, debugging
├── REBUILD-PLAYBOOK.md           # 9-phase destroy+recreate sequence
├── AWS-MANAGED-RAG-VS-LOCAL-RAG.md  # Managed vs local RAG comparison
├── E2E-VALIDATION-REPORT.md      # 15-test validation results
└── CLEANUP-AND-RESPIN.md         # Destroy & rebuild guide (current)
```

## Deployment Commands
```bash
# Terraform
cd terraform && terraform init && terraform apply

# Docker build + push
AWS_PROFILE=sandboxtest aws ecr get-login-password --region ap-southeast-2 | docker login --username AWS --password-stdin 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com
cd agent-backend && docker build --platform linux/amd64 -t platform-health-backend . && docker tag platform-health-backend:latest 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-backend:latest && docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-backend:latest
cd ../frontend && docker build --platform linux/amd64 -t platform-health-frontend . && docker tag platform-health-frontend:latest 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/frontend:latest && docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/frontend:latest

# Force ECS redeploy
AWS_PROFILE=sandboxtest aws ecs update-service --cluster platform-health-cluster --service platform-health-backend --force-new-deployment
AWS_PROFILE=sandboxtest aws ecs update-service --cluster platform-health-cluster --service platform-health-frontend --force-new-deployment

# Data sync
aws s3 sync documents/ s3://platform-health-kb-documents-615299759525/documents/
aws bedrock-agent start-ingestion-job --knowledge-base-id II5KAPFHJP --data-source-id THEYKFVVTX  # S3
aws bedrock-agent start-ingestion-job --knowledge-base-id II5KAPFHJP --data-source-id G0QLXXLD5B  # Web
aws bedrock-agent start-ingestion-job --knowledge-base-id II5KAPFHJP --data-source-id FCAVAELI9A  # Confluence
```

## Teardown
See `CLEANUP-AND-RESPIN.md` for the full destroy + rebuild guide.

**Quick destroy** (4 steps):
```bash
aws s3 rm s3://platform-health-kb-documents-615299759525/ --recursive
# Delete ECR images (see CLEANUP-AND-RESPIN.md for batch command)
cd terraform && TF_VAR_confluence_token="dummy" terraform destroy -auto-approve
# Delete OpenSearch collection + policies manually (see CLEANUP-AND-RESPIN.md)
```

## Known Issues & Gotchas
1. OpenSearch Serverless takes 10-15 min to activate — pre-create before terraform
2. Vector index must exist before Bedrock KB creation — use Python opensearch-py
3. Max 1 concurrent ingestion job per KB — sync sequentially
4. Build Docker with `--platform linux/amd64` on Apple Silicon
5. ECS service names have `platform-health-` prefix (not bare names)
6. ECS cluster name is `platform-health-cluster` (not `platform-health`)
7. No AWS_PROFILE in containers — uses IAM task roles automatically
8. ALB idle_timeout=120s required for SSE streaming
9. Confluence API token was truncated in Secrets Manager — the full token from local .env has `=ABA7B279` suffix
10. Confluence filter `.*ET.*` was wrong — updated to match specific page title patterns (8 target pages under parent 4346576951)
11. Web crawler "failures" are image files (.png) — expected, not real errors
12. Confluence scans 58 pages in ET space but filters to index ~40 matching pages (including our 8 target pages)
13. Router misclassified "can you check" as incident_triage — fixed by removing router entirely (M5)
14. Two-brain problem: router LLM + tool-calling LLM fight — resolved with single ReAct loop
15. OpenSearch Serverless costs $975/month IDLE (4 OCU minimum) — biggest cost driver, destroy when not in use
16. S3 bucket must be emptied before `terraform destroy` — or destroy hangs
17. ECR repos must have images deleted before `terraform destroy` — or destroy fails
18. OpenSearch collection + policies created manually — must be deleted separately from terraform

## Cost Summary (When Running)
| Component | Monthly | % of Total |
|-----------|---------|-----------|
| OpenSearch Serverless (4 OCU min) | $975 | 94% |
| ALB | $24 | 2% |
| ECS Fargate (2 tasks) | $31 | 3% |
| Everything else | $4 | 1% |
| **Total** | **~$1,034** | |

## Next Steps (Future Enhancements)
- CI/CD pipeline (GitHub Actions)
- Custom domain + HTTPS
- CloudWatch monitoring + alerting
- Switch to Semantic Chunking (1-line Terraform change, +10-15% retrieval quality)
- Add sitemap.xml to blog (fixes JS crawling gap for older posts)
- Re-ranking Lambda for precision improvement
- Consider replacing OpenSearch Serverless with cheaper vector DB for cost reduction
