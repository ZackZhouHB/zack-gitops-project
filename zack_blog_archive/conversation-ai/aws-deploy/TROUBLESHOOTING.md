# Troubleshooting Guide — Platform Health Insight Assistant (AWS ECS)

Real issues encountered during AWS ECS deployment and their resolutions.

---

## Issue #1: OpenSearch Serverless Vector Index Creation

**Symptoms**
`terraform apply` fails on Bedrock Knowledge Base creation with error: "vector index does not exist"

**Root Cause**
Bedrock KB requires the OpenSearch vector index to exist BEFORE KB creation. The `null_resource` provisioner using `curl` with `aws-sigv4` did not create the index successfully.

**How Found**
Terraform apply error message explicitly stated the vector index was missing.

**Fix**
Created the index manually using the Python `opensearch-py` client:

```python
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

credentials = boto3.Session(profile_name='sandboxtest').get_credentials()
auth = AWS4Auth(
    credentials.access_key,
    credentials.secret_key,
    'ap-southeast-2',
    'aoss',
    session_token=credentials.token,
)

client = OpenSearch(
    hosts=[{'host': '0s43wsj0nu6nsj4bdlxf.ap-southeast-2.aoss.amazonaws.com', 'port': 443}],
    http_auth=auth,
    use_ssl=True,
    connection_class=RequestsHttpConnection,
)

client.indices.create('bedrock-knowledge-base-default-index', body={
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 512,
        }
    },
    "mappings": {
        "properties": {
            "bedrock-knowledge-base-default-vector": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "engine": "faiss",
                    "parameters": {"ef_construction": 512, "m": 16},
                    "space_type": "l2",
                },
            },
            "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text"},
            "AMAZON_BEDROCK_METADATA": {"type": "text"},
        }
    },
})
```

**Verification**
`terraform apply` succeeds on retry after the index exists.

**Prevention**
Always pre-create the OpenSearch collection and vector index before running Terraform.

---

## Issue #2: ECS Cluster Name Mismatch

**Symptoms**
`aws ecs update-service --cluster platform-health --service agent-backend` returns `ClusterNotFoundException`.

**Root Cause**
Terraform created the cluster as `platform-health-cluster`, not `platform-health`.

**How Found**
```bash
aws ecs list-clusters
```
Output showed the actual name was `platform-health-cluster`.

**Fix**
Use the correct cluster name:
```bash
aws ecs update-service --cluster platform-health-cluster --service <service-name>
```

**Verification**
`aws ecs update-service` succeeds with the corrected cluster name.

**Prevention**
Always verify resource names with `list-*` commands before scripting against them.

---

## Issue #3: ECS Service Name Mismatch

**Symptoms**
`aws ecs update-service --service agent-backend` returns `ServiceNotFoundException`.

**Root Cause**
Terraform created services with a project prefix: `platform-health-backend` and `platform-health-frontend`, not `agent-backend`.

**How Found**
```bash
aws ecs list-services --cluster platform-health-cluster
```

**Fix**
Use the full prefixed service names:
```bash
aws ecs update-service --cluster platform-health-cluster --service platform-health-backend
aws ecs update-service --cluster platform-health-cluster --service platform-health-frontend
```

**Verification**
Service update commands succeed and new deployments roll out.

**Prevention**
Reference Terraform outputs for exact resource names, or add outputs to `outputs.tf` for service names.

---

## Issue #4: OpenSearch Serverless Collection Takes 10–15 Minutes

**Symptoms**
Collection status shows `CREATING` for an extended period during Terraform apply or manual creation.

**Root Cause**
OpenSearch Serverless provisioning is inherently slow — it provisions dedicated compute resources behind the scenes.

**How Found**
Repeated status checks via:
```bash
aws opensearchserverless batch-get-collection --ids <collection-id>
```

**Fix**
Pre-create the collection before running `terraform apply` using the AWS CLI, then poll until the status is `ACTIVE`:
```bash
aws opensearchserverless create-collection --name platform-health-kb --type VECTORSEARCH

# Poll until ACTIVE
aws opensearchserverless batch-get-collection --names platform-health-kb
```

**Verification**
Collection status returns `ACTIVE` before proceeding.

**Prevention**
Factor in a 10–15 minute wait for collection creation in any deployment pipeline or runbook.

---

## Issue #5: KB Concurrent Ingestion Limit

**Symptoms**
`start-ingestion-job` returns:
```
ConflictException: maximum number of concurrent ingestion jobs per knowledge base: 1
```

**Root Cause**
Uploading documents to S3 triggered the Lambda auto-sync function, which started an ingestion job. A manual `start-ingestion-job` call then conflicted with the already-running job.

**How Found**
Error message from the `start-ingestion-job` CLI call.

**Fix**
Wait for the current job to complete before triggering the next one:
```bash
aws bedrock-agent list-ingestion-jobs \
    --knowledge-base-id II5KAPFHJP \
    --data-source-id <data-source-id>
```

**Verification**
Subsequent `start-ingestion-job` succeeds after the previous job reaches `COMPLETE` status.

**Prevention**
Sync data sources sequentially, not in parallel. If Lambda auto-sync is enabled, avoid manual sync immediately after S3 uploads.

---

## Issue #6: Docker Build Platform for Fargate

**Symptoms**
ECS task fails to start or crashes immediately after launch.

**Root Cause**
Docker image was built on an Apple Silicon Mac (arm64), but Fargate defaults to `linux/amd64`.

**How Found**
ECS task stopped reason visible in:
```bash
aws ecs describe-tasks --cluster platform-health-cluster --tasks <task-id>
```

**Fix**
Build with the correct platform flag:
```bash
docker build --platform linux/amd64 -t platform-health-backend .
```

**Verification**
ECS tasks start successfully and containers pass health checks.

**Prevention**
Always specify `--platform linux/amd64` when building images for Fargate on Apple Silicon Macs. Add it to build scripts and CI/CD pipelines.

---

## Issue #7: ALB Health Check Fails Before Image Push

**Symptoms**
ECS service events show:
```
service platform-health-backend has no running tasks — target group has no healthy targets
```

**Root Cause**
ECS tasks were referencing placeholder or empty ECR images before the real application images were pushed.

**How Found**
ECS service events and ALB target group health check status.

**Fix**
Push images to ECR and force a new deployment:
```bash
# Push images
docker push <account>.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health-backend:latest

# Force new deployment
aws ecs update-service --cluster platform-health-cluster \
    --service platform-health-backend --force-new-deployment
```

**Verification**
ALB target group shows healthy targets after deployment stabilises.

**Prevention**
This is expected during initial infrastructure setup. Push images immediately after ECR repository creation, before or right after the first `terraform apply`.

---

## Issue #8: AWS_PROFILE Not Available in ECS

**Symptoms**
`boto3.exceptions.NoCredentialsError` in container logs.

**Root Cause**
Application code contained `boto3.Session(profile_name='sandboxtest')`, which only works on local machines with `~/.aws/credentials`. ECS tasks use IAM task roles, not AWS profiles.

**How Found**
Container logs in CloudWatch showing credential errors:
```bash
aws logs tail /ecs/platform-health-backend --follow
```

**Fix**
Remove all `profile_name='sandboxtest'` references from application code. Use the default boto3 credential chain:
```python
# Before (broken in ECS)
session = boto3.Session(profile_name='sandboxtest')

# After (works everywhere)
session = boto3.Session()
```

Boto3 automatically discovers credentials from the ECS task role via the container credential provider.

**Verification**
Container starts without credential errors and can successfully call AWS services.

**Prevention**
Never hardcode AWS profile names. Use environment-variable-based configuration or rely on the default credential chain, which works in both local and ECS environments.

---

## Issue #9: Confluence API Token Truncated

**Symptoms**
Confluence data source sync fails with "Failed to connect to the URL of your data source"

**Root Cause**
API token in Secrets Manager was missing the `=ABA7B279` suffix. The full token from local `.env` file was `ATATT3x...JGc=ABA7B279` but only `ATATT3x...JGc` was stored.

**How Found**
Compared Secrets Manager value with local `.env` file. Tested both tokens with `curl -u` against Confluence API — truncated token returned 403, full token returned 200.

**Fix**
`aws secretsmanager put-secret-value` with the complete token

**Verification**
Confluence sync succeeded — 58 scanned, 40 indexed

**Prevention**
Always copy the full token including any trailing `=` and suffix characters

---

## Issue #10: Confluence Filter Pattern Too Broad

**Symptoms**
Confluence sync indexed 40 pages instead of the expected 8 target pages

**Root Cause**
Initial filter `.*ET.*` matched the space key in many page paths. Even after updating to specific title patterns like `.*Platform Health.*`, other pages in ET space with similar keywords matched.

**How Found**
Compared indexed count (40) vs expected (8). Checked ET space has 100+ pages total.

**Fix**
The 8 target pages ARE indexed and retrievable — the extra pages don't hurt search quality. For strict filtering, could use more specific regex patterns or page ID-based filtering.

**Verification**
KB retrieve queries return correct Confluence page URLs for targeted questions

**Prevention**
Test inclusionFilters against actual page titles before syncing. Note: Bedrock scans ALL accessible pages and filters during indexing, not crawling.

---

## Issue #11: Confluence Secret Format

**Symptoms**
Same "Failed to connect" error even with correct token

**Root Cause**
Initial secret had extra fields: `{"confluenceUrl":"...","password":"...","username":"..."}`. Bedrock BASIC auth expects exactly: `{"username":"...","password":"..."}`

**How Found**
Checked AWS docs for Bedrock Confluence data source BASIC auth secret format

**Fix**
Updated secret to contain only `username` and `password` keys

**Verification**
Sync connected successfully after format fix + token fix

---

## Issue #12: Router Misclassified "Can You Check" as Incident

**Symptoms**
User asks "ok, lets see how you know about the health analyzer solution and how it used the 2 staged pipeline" or "there is a story about a letter to matilda, can you check" — system returns empty response or wrong answer.

**Root Cause**
The router LLM classified "can you check" as incident_triage instead of general_qa. The incident_triage workflow then failed because:
1. Import names were wrong: `db_tool` (local) vs `dynamodb_tool` (AWS), `rag_tool` vs `kb_tool`
2. Attribute names differed: `checklist.id` vs `checklist.checklist_id`, `checklist.total` vs `len(checklist.items)`

**How Found**
Frontend showed "complete" with no content. Backend logs showed HTTP 500 with `ModuleNotFoundError: No module named 'tools.db_tool'`.

**Fix (Phase 1 — Patch)**
Fixed imports: `db_tool` → `dynamodb_tool`, `rag_tool` → `kb_tool`. Fixed attributes: `.id` → `.checklist_id`, `.total` → `len(.items)`. Rewrote ROUTER_PROMPT to make general_qa the explicit default.

**Fix (Phase 2 — Root Cause)**
Removed the router entirely. Simplified to single ReAct loop where the LLM decides tools directly. This eliminates the misclassification problem permanently.

**Verification**
After graph simplification, all queries route through the same ReAct loop — no more misrouting.

**Prevention**
Prefer single ReAct loop over router + workflow patterns. Tool descriptions ARE the routing logic. Two LLMs fighting (router + tool-caller) is an anti-pattern.

---

## Issue #13: Two-Brain Problem — Router vs Tool-Calling LLM

**Symptoms**
Inconsistent routing behavior. Some queries work, others don't, with no clear pattern. The router and the tool-calling LLM make conflicting decisions.

**Root Cause**
Architecture had two separate LLM decision points:
1. Router LLM: sees ONLY user message text, classifies intent
2. Tool-calling LLM: sees system prompt + message + tool descriptions, picks tools

The router had no context about what content exists in the KB. It made snap judgments based on keywords ("check" → incident, "story" → unclear). The tool-calling LLM, with richer context, would have made better decisions.

**How Found**
Analysis of the routing patterns in step-17 debugging tutorial. Realized the router was a worse version of what the ReAct loop already does.

**Fix**
Removed router_node from graph.py. Removed ROUTER_PROMPT from prompts.py. Simplified AgentState (removed current_workflow, workflow_step, workflow_status, workflow_data, incident_result). Made `llm` the entry point with single ReAct loop: START → llm → tools → llm → ... → END.

**Verification**
Health endpoint passing. All queries now go through the same decision path.

**Prevention**
Design principle: one decision-maker per turn. If you need routing, encode it in tool descriptions, not in a separate LLM call. Vector search handles content-type routing naturally for single-KB systems.

---

## Issue #14: Frontend Shows "Complete" But No Content (HTTP 500)

**Symptoms**
User submits a question. Frontend progress bar completes normally. But no answer text or citations appear.

**Root Cause**
Backend returned HTTP 500 error. The frontend's SSE handler received the error but displayed it as "complete" without showing the error to the user.

**How Found**
1. Noticed empty response in frontend
2. Checked backend logs: `aws logs tail /ecs/platform-health/agent-backend --follow`
3. Found `ModuleNotFoundError` and `AttributeError` stack traces

**Fix**
Fixed the underlying backend errors (see Issue #12). The frontend error handling could also be improved to show error messages.

**Verification**
Backend returns 200 with actual content after fixes.

**Prevention**
Always check backend logs when frontend shows unexpected empty results. The SSE streaming pattern can mask backend errors. Add error event types to SSE stream for better frontend error display.

---

## General AWS Debugging Commands

```bash
# Check ECS service status
aws ecs describe-services \
    --cluster platform-health-cluster \
    --services platform-health-backend platform-health-frontend

# Check task logs (CloudWatch)
aws logs tail /ecs/platform-health-backend --follow

# Check ALB target health
aws elbv2 describe-target-health --target-group-arn <arn>

# Check KB ingestion status
aws bedrock-agent list-ingestion-jobs \
    --knowledge-base-id II5KAPFHJP \
    --data-source-id <data-source-id>

# Test KB retrieve directly
aws bedrock-agent-runtime retrieve \
    --knowledge-base-id II5KAPFHJP \
    --retrieval-query '{"text": "test query"}'

# Check ECS task stopped reason
aws ecs describe-tasks --cluster platform-health-cluster --tasks <task-id>

# Check Lambda invocations
aws logs tail /aws/lambda/platform-health-kb-sync

# List S3 objects
aws s3 ls s3://platform-health-kb-documents-615299759525/documents/
```

---

## Testing Each Component

Use these steps to verify each service is working correctly after deployment.

### 1. ECS Cluster & Services

```bash
# Confirm cluster exists and is ACTIVE
aws ecs describe-clusters --clusters platform-health-cluster \
    --query 'clusters[0].status'

# Confirm services are ACTIVE with desired count > 0
aws ecs describe-services --cluster platform-health-cluster \
    --services platform-health-backend platform-health-frontend \
    --query 'services[].{name:serviceName, status:status, desired:desiredCount, running:runningCount}'

# Confirm tasks are RUNNING
aws ecs list-tasks --cluster platform-health-cluster --service-name platform-health-backend
aws ecs list-tasks --cluster platform-health-cluster --service-name platform-health-frontend
```

### 2. ALB & Networking

```bash
# Get ALB DNS name
aws elbv2 describe-load-balancers --names platform-health-alb \
    --query 'LoadBalancers[0].DNSName' --output text

# Check target group health (all targets should be "healthy")
aws elbv2 describe-target-health --target-group-arn <backend-tg-arn>
aws elbv2 describe-target-health --target-group-arn <frontend-tg-arn>

# Test backend health endpoint
curl -s http://<alb-dns>/api/health | jq .

# Test frontend is serving
curl -s -o /dev/null -w "%{http_code}" http://<alb-dns>/
```

### 3. ECR Repositories

```bash
# Verify images exist
aws ecr describe-images --repository-name platform-health-backend \
    --query 'imageDetails[].imageTags'
aws ecr describe-images --repository-name platform-health-frontend \
    --query 'imageDetails[].imageTags'
```

### 4. OpenSearch Serverless

```bash
# Confirm collection is ACTIVE
aws opensearchserverless batch-get-collection --names platform-health-kb \
    --query 'collectionDetails[0].status'

# Verify the vector index exists (use the Python client or dashboard)
```

### 5. Bedrock Knowledge Base

```bash
# Confirm KB exists
aws bedrock-agent get-knowledge-base --knowledge-base-id II5KAPFHJP

# Confirm data source exists
aws bedrock-agent list-data-sources --knowledge-base-id II5KAPFHJP

# Test retrieval
aws bedrock-agent-runtime retrieve \
    --knowledge-base-id II5KAPFHJP \
    --retrieval-query '{"text": "What is the platform health status?"}' \
    --retrieval-configuration '{"vectorSearchConfiguration":{"numberOfResults":3}}'
```

### 6. S3 Knowledge Base Documents

```bash
# Verify documents are uploaded
aws s3 ls s3://platform-health-kb-documents-615299759525/documents/ --recursive

# Check bucket policy allows Bedrock access
aws s3api get-bucket-policy --bucket platform-health-kb-documents-615299759525
```

### 7. Lambda Auto-Sync

```bash
# Check function exists
aws lambda get-function --function-name platform-health-kb-sync

# Check recent invocations
aws logs tail /aws/lambda/platform-health-kb-sync --since 1h

# Test manually
aws lambda invoke --function-name platform-health-kb-sync \
    --payload '{"test": true}' response.json && cat response.json && rm response.json
```

### 8. IAM & Permissions

```bash
# Verify ECS task role has required permissions
aws iam list-attached-role-policies --role-name platform-health-task-role

# Verify task execution role
aws iam list-attached-role-policies --role-name platform-health-execution-role
```

### 9. CloudWatch Logs

```bash
# Verify log groups exist
aws logs describe-log-groups --log-group-name-prefix /ecs/platform-health

# Tail backend logs for errors
aws logs tail /ecs/platform-health-backend --follow --format short

# Tail frontend logs
aws logs tail /ecs/platform-health-frontend --follow --format short
```

### 10. End-to-End Test

```bash
# Send a query through the full stack
curl -s -X POST http://<alb-dns>/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "What platform health issues are there?"}' | jq .
```

If any component fails, cross-reference with the issues above and the debugging commands section.

---

## Architecture Evolution

The agent graph was simplified in M5 from a router-based design to a single ReAct loop:

**Before (M1–M4):**
```
START → router → [general_qa]: llm → tools → llm → END
                → [incident_triage]: gather → search → fix/investigate/escalate → END
```

**After (M5):**
```
START → llm → [should_continue] → tools → llm → ... → END
```

Key files changed:
- `agent-backend/agent/graph.py` — router_node removed, entry point is now `llm`
- `agent-backend/agent/prompts.py` — ROUTER_PROMPT removed
- `agent-backend/agent/state.py` — simplified to 3 fields
- `agent-backend/main.py` — removed workflow state references

See `tutorials/step-17-agent-routing-and-tool-debugging.md` and `tutorials/step-18-routing-design-for-mixed-content.md` for the full analysis.
