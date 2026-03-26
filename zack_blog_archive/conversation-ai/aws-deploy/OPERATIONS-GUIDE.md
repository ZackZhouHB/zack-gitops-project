# Operations & Debugging Guide

**AWS Account:** 615299759525 | **Region:** ap-southeast-2 | **Profile:** sandboxtest

---

## 1. Container Logs

### View Live Backend Logs
```bash
# Tail live logs (last 5 min)
AWS_PROFILE=sandboxtest aws logs tail /ecs/platform-health-backend --follow --since 5m

# Search for errors only (last hour)
AWS_PROFILE=sandboxtest aws logs filter-log-events \
  --log-group-name /ecs/platform-health-backend \
  --filter-pattern "ERROR" \
  --start-time $(date -v-1H +%s000) \
  --query 'events[].message' --output text

# Search for a specific session ID
AWS_PROFILE=sandboxtest aws logs filter-log-events \
  --log-group-name /ecs/platform-health-backend \
  --filter-pattern "session_id_here"

# Frontend logs
AWS_PROFILE=sandboxtest aws logs tail /ecs/platform-health-frontend --follow --since 5m

# Lambda logs (S3 sync trigger)
AWS_PROFILE=sandboxtest aws logs tail /aws/lambda/platform-health-kb-sync --follow --since 30m
```

> **macOS note:** Uses `-v-1H` for date math. On Linux, use `date -d '1 hour ago' +%s000` instead.

### ECS Exec — Shell Into Running Container
```bash
# Get the running task ID
TASK_ID=$(AWS_PROFILE=sandboxtest aws ecs list-tasks \
  --cluster platform-health-cluster \
  --service-name platform-health-backend \
  --query 'taskArns[0]' --output text | awk -F'/' '{print $NF}')

# Shell in
AWS_PROFILE=sandboxtest aws ecs execute-command \
  --cluster platform-health-cluster \
  --task $TASK_ID \
  --container agent-backend \
  --interactive \
  --command "/bin/bash"
```

**If ECS Exec is not enabled:**
```bash
AWS_PROFILE=sandboxtest aws ecs update-service \
  --cluster platform-health-cluster \
  --service platform-health-backend \
  --enable-execute-command --no-cli-pager

# Force new deployment to pick up the change
AWS_PROFILE=sandboxtest aws ecs update-service \
  --cluster platform-health-cluster \
  --service platform-health-backend \
  --force-new-deployment --no-cli-pager
```

---

## 2. Examining Chat History (EFS)

### From Inside the Container (via ECS Exec)
```bash
# List all sessions
ls -la /mnt/efs/sessions/

# View session metadata
cat /mnt/efs/sessions/<session_id>/metadata.json | python3 -m json.tool

# View chat messages
cat /mnt/efs/sessions/<session_id>/messages.json | python3 -m json.tool

# Count messages per session
for d in /mnt/efs/sessions/*/; do
  sid=$(basename $d)
  count=$(python3 -c "import json; print(len(json.load(open('${d}messages.json'))))" 2>/dev/null || echo 0)
  echo "$sid: $count messages"
done

# Search for a specific question across all sessions
grep -r "terraform" /mnt/efs/sessions/*/messages.json

# Check disk usage
du -sh /mnt/efs/sessions/
```

### From API (without shell access)
```bash
# List all sessions
curl -s http://platform-health-alb-1623429612.ap-southeast-2.elb.amazonaws.com/sessions | python3 -m json.tool

# Get specific session history
curl -s http://platform-health-alb-1623429612.ap-southeast-2.elb.amazonaws.com/sessions/<session_id>/history | python3 -m json.tool
```

---

## 3. Examining Knowledge Base Chunks

### Query KB to See What Chunks Exist for a Topic
```bash
# Retrieve chunks matching a query (shows what the agent "sees")
AWS_PROFILE=sandboxtest aws bedrock-agent-runtime retrieve \
  --knowledge-base-id II5KAPFHJP \
  --retrieval-query '{"text": "terraform modules"}' \
  --retrieval-configuration '{"vectorSearchConfiguration": {"numberOfResults": 10}}' \
  --no-cli-pager --output json | python3 -m json.tool

# Compact view — just sources and scores
AWS_PROFILE=sandboxtest aws bedrock-agent-runtime retrieve \
  --knowledge-base-id II5KAPFHJP \
  --retrieval-query '{"text": "terraform modules"}' \
  --retrieval-configuration '{"vectorSearchConfiguration": {"numberOfResults": 10}}' \
  --no-cli-pager \
  --query 'retrievalResults[].{score:score, source:location.s3Location.uri, type:location.type, text:content.text}' \
  --output table
```

### Check Ingestion Job History (per data source)
```bash
# S3 data source (THEYKFVVTX)
AWS_PROFILE=sandboxtest aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id II5KAPFHJP --data-source-id THEYKFVVTX --no-cli-pager \
  --query 'ingestionJobSummaries[].{id:ingestionJobId,status:status,started:startedAt,scanned:statistics.numberOfDocumentsScanned,indexed:statistics.numberOfNewDocumentsIndexed,failed:statistics.numberOfDocumentsFailed}' \
  --output table

# Web crawler (G0QLXXLD5B)
AWS_PROFILE=sandboxtest aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id II5KAPFHJP --data-source-id G0QLXXLD5B --no-cli-pager \
  --query 'ingestionJobSummaries[].{id:ingestionJobId,status:status,started:startedAt,scanned:statistics.numberOfDocumentsScanned,indexed:statistics.numberOfNewDocumentsIndexed,failed:statistics.numberOfDocumentsFailed}' \
  --output table

# Confluence (FCAVAELI9A)
AWS_PROFILE=sandboxtest aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id II5KAPFHJP --data-source-id FCAVAELI9A --no-cli-pager \
  --query 'ingestionJobSummaries[].{id:ingestionJobId,status:status,started:startedAt,scanned:statistics.numberOfDocumentsScanned,indexed:statistics.numberOfNewDocumentsIndexed,failed:statistics.numberOfDocumentsFailed}' \
  --output table
```

### Check What's in S3
```bash
# List all documents
AWS_PROFILE=sandboxtest aws s3 ls s3://platform-health-kb-documents-615299759525/documents/ --recursive --human-readable

# Check a specific document exists
AWS_PROFILE=sandboxtest aws s3api head-object \
  --bucket platform-health-kb-documents-615299759525 \
  --key documents/20Terraformredo.pdf
```

### Query OpenSearch Directly (Advanced)

```python
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

session = boto3.Session(profile_name='sandboxtest')
credentials = session.get_credentials().get_frozen_credentials()
auth = AWS4Auth(
    credentials.access_key, credentials.secret_key,
    'ap-southeast-2', 'aoss',
    session_token=credentials.token
)

client = OpenSearch(
    hosts=[{'host': '0s43wsj0nu6nsj4bdlxf.ap-southeast-2.aoss.amazonaws.com', 'port': 443}],
    http_auth=auth, use_ssl=True, connection_class=RequestsHttpConnection
)

# Count total chunks indexed
print(client.count(index='bedrock-knowledge-base-default-index'))

# Search by text content
results = client.search(index='bedrock-knowledge-base-default-index', body={
    "query": {"match": {"AMAZON_BEDROCK_TEXT_CHUNK": "terraform"}},
    "size": 5
})
for hit in results['hits']['hits']:
    print(f"Score: {hit['_score']}")
    print(f"Text: {hit['_source']['AMAZON_BEDROCK_TEXT_CHUNK'][:200]}...")
    print(f"Metadata: {hit['_source'].get('AMAZON_BEDROCK_METADATA', 'N/A')}")
    print("---")

# Get index stats (total docs, size)
print(client.indices.stats(index='bedrock-knowledge-base-default-index'))
```

> **Requires:** `pip install opensearch-py requests-aws4auth boto3`

---

## 4. Validating Citation Accuracy

### Method 1: Compare KB Retrieve vs Chat Response

1. Send a question via `/chat`, note the sources and scores returned
2. Run the same query directly against KB retrieve API
3. Compare: do the chunks actually contain the information the LLM cited?
4. Check for hallucination: does the response claim things NOT in the chunks?

```bash
# Step 1: Ask via chat (save full response)
RESPONSE=$(curl -s -X POST \
  http://platform-health-alb-1623429612.ap-southeast-2.elb.amazonaws.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is terraform redo?", "session_id": "validate-001"}')

# Step 2: Extract what sources the agent cited
echo "$RESPONSE" | python3 -c "
import json, sys
resp = json.load(sys.stdin)
print('=== ANSWER ===')
print(resp['response'][:500])
print('\n=== TOOL CALLS ===')
for tc in resp.get('tool_calls', []):
    print(f'Tool: {tc[\"name\"]}, Latency: {tc.get(\"latency_ms\")}ms')
    for r in tc.get('rag_results', []):
        print(f'  Source: {r[\"title\"]}, Score: {r[\"score\"]:.2%}, Type: {r[\"source_type\"]}')
"

# Step 3: Direct KB retrieve with same query
AWS_PROFILE=sandboxtest aws bedrock-agent-runtime retrieve \
  --knowledge-base-id II5KAPFHJP \
  --retrieval-query '{"text": "terraform redo"}' \
  --no-cli-pager --output json | python3 -c "
import json, sys
kb = json.load(sys.stdin)
for i, r in enumerate(kb['retrievalResults'][:5]):
    print(f'=== Chunk {i+1} (score: {r[\"score\"]:.4f}) ===')
    text = r['content']['text'] if isinstance(r['content']['text'], str) else str(r['content']['text'])
    print(text[:300])
    print(f'Source: {r[\"location\"]}')
    print()
"
```

### Method 2: Confidence Score Thresholds

| Score Range | Reliability | Action |
|-------------|-------------|--------|
| > 0.5       | Strong match | Reliable — trust the chunk |
| 0.3 – 0.5   | Moderate     | Verify chunk content manually |
| < 0.3       | Weak match   | Likely padding — high hallucination risk |

### Method 3: Trace a Question Through the System

1. Check backend logs for the session: grep `session_id` in CloudWatch
2. Check which tools were called (from `tool_calls` in response)
3. Check what KB returned (from `rag_results`)
4. Check what the LLM was given as context (from logs if verbose logging enabled)
5. Check if the answer is grounded in the chunks

---

## 5. ECS Service Health

### Service Status
```bash
AWS_PROFILE=sandboxtest aws ecs describe-services \
  --cluster platform-health-cluster \
  --services platform-health-backend platform-health-frontend \
  --no-cli-pager \
  --query 'services[].{name:serviceName,status:status,desired:desiredCount,running:runningCount,pending:pendingCount,lastEvent:events[0].message}' \
  --output table
```

### Task Details (CPU, Memory, Status)
```bash
AWS_PROFILE=sandboxtest aws ecs describe-tasks \
  --cluster platform-health-cluster \
  --tasks $(AWS_PROFILE=sandboxtest aws ecs list-tasks \
    --cluster platform-health-cluster \
    --service-name platform-health-backend \
    --query 'taskArns[0]' --output text) \
  --no-cli-pager \
  --query 'tasks[0].{status:lastStatus,health:healthStatus,cpu:cpu,memory:memory,startedAt:startedAt,stoppedReason:stoppedReason}'
```

### Task Stopped Reason (Why Did It Crash?)
```bash
# List stopped tasks
AWS_PROFILE=sandboxtest aws ecs list-tasks \
  --cluster platform-health-cluster \
  --service-name platform-health-backend \
  --desired-status STOPPED \
  --no-cli-pager --query 'taskArns' --output text

# Describe a stopped task
AWS_PROFILE=sandboxtest aws ecs describe-tasks \
  --cluster platform-health-cluster \
  --tasks <task-arn> \
  --no-cli-pager \
  --query 'tasks[0].{status:lastStatus,stoppedReason:stoppedReason,stopCode:stopCode,exitCode:containers[0].exitCode}'
```

### ALB Target Health
```bash
# Backend targets
AWS_PROFILE=sandboxtest aws elbv2 describe-target-health \
  --target-group-arn $(AWS_PROFILE=sandboxtest aws elbv2 describe-target-groups \
    --names platform-health-backend \
    --query 'TargetGroups[0].TargetGroupArn' --output text) \
  --no-cli-pager --output table

# Frontend targets
AWS_PROFILE=sandboxtest aws elbv2 describe-target-health \
  --target-group-arn $(AWS_PROFILE=sandboxtest aws elbv2 describe-target-groups \
    --names platform-health-frontend \
    --query 'TargetGroups[0].TargetGroupArn' --output text) \
  --no-cli-pager --output table
```

---

## 6. Data Source Management

### Trigger Manual Sync

> **Max 1 concurrent ingestion job.** Check status before triggering next.

```bash
# S3 (usually auto-triggered by Lambda, but manual when needed)
AWS_PROFILE=sandboxtest aws bedrock-agent start-ingestion-job \
  --knowledge-base-id II5KAPFHJP --data-source-id THEYKFVVTX --no-cli-pager

# Web crawler
AWS_PROFILE=sandboxtest aws bedrock-agent start-ingestion-job \
  --knowledge-base-id II5KAPFHJP --data-source-id G0QLXXLD5B --no-cli-pager

# Confluence
AWS_PROFILE=sandboxtest aws bedrock-agent start-ingestion-job \
  --knowledge-base-id II5KAPFHJP --data-source-id FCAVAELI9A --no-cli-pager
```

### Upload New Document
```bash
AWS_PROFILE=sandboxtest aws s3 cp new-document.pdf \
  s3://platform-health-kb-documents-615299759525/documents/

# Lambda auto-triggers sync. Verify:
AWS_PROFILE=sandboxtest aws logs tail /aws/lambda/platform-health-kb-sync --since 2m
```

### Delete a Document
```bash
AWS_PROFILE=sandboxtest aws s3 rm \
  s3://platform-health-kb-documents-615299759525/documents/old-document.pdf

# Must re-sync to remove from index:
AWS_PROFILE=sandboxtest aws bedrock-agent start-ingestion-job \
  --knowledge-base-id II5KAPFHJP --data-source-id THEYKFVVTX --no-cli-pager
```

---

## 7. DynamoDB Inspection

### View Checklists
```bash
# Scan all checklists
AWS_PROFILE=sandboxtest aws dynamodb scan \
  --table-name platform-health-checklists \
  --no-cli-pager --output json | python3 -m json.tool

# Query specific checklist by key
AWS_PROFILE=sandboxtest aws dynamodb query \
  --table-name platform-health-checklists \
  --key-condition-expression "checklist_id = :id" \
  --expression-attribute-values '{":id": {"S": "some-id"}}' \
  --no-cli-pager
```

### View Escalations
```bash
AWS_PROFILE=sandboxtest aws dynamodb scan \
  --table-name platform-health-escalations \
  --no-cli-pager --output json | python3 -m json.tool
```

---

## 8. Redeployment (Code Change Cycle)

```bash
# 1. Build (cross-compile for ECS linux/amd64)
docker build --platform linux/amd64 -t platform-health-backend ./agent-backend

# 2. Authenticate with ECR
AWS_PROFILE=sandboxtest aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com

# 3. Tag
docker tag platform-health-backend:latest \
  615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-backend:latest

# 4. Push
docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-backend:latest

# 5. Force new deployment
AWS_PROFILE=sandboxtest aws ecs update-service \
  --cluster platform-health-cluster \
  --service platform-health-backend \
  --force-new-deployment --no-cli-pager

# 6. Watch logs for the new task coming up
AWS_PROFILE=sandboxtest aws logs tail /ecs/platform-health-backend --follow --since 1m

# 7. Verify health
curl -s http://platform-health-alb-1623429612.ap-southeast-2.elb.amazonaws.com/health
```

Same flow for frontend — substitute `agent-backend` → `agent-frontend`, `platform-health-backend` → `platform-health-frontend`.

---

## 9. Cost Monitoring

```bash
# What's running (and costing money)
AWS_PROFILE=sandboxtest aws ecs describe-services \
  --cluster platform-health-cluster \
  --services platform-health-backend platform-health-frontend \
  --query 'services[].{name:serviceName,running:runningCount}' --output table

# OpenSearch Serverless collection (~$0.24/hr even idle!)
AWS_PROFILE=sandboxtest aws opensearchserverless list-collections --no-cli-pager

# Quick teardown if not using
cd aws-deploy/terraform && terraform destroy
```

**Cost hotspots to watch:**
- OpenSearch Serverless: ~$700/month baseline (2 OCU minimum)
- ECS Fargate: per-task, per-hour (check task CPU/memory sizing)
- Bedrock: per-invocation (LLM calls + embedding calls during ingestion)
- NAT Gateway: ~$32/month + data transfer

---

## 10. Common Debug Scenarios

### Answer doesn't cite the right document
1. Run KB retrieve with the same query → check if correct chunks appear
2. If chunks are wrong → check if the document was ingested (Section 3: ingestion jobs)
3. If chunks are right but answer is wrong → LLM hallucination, check score thresholds
4. If document is missing from chunks → check S3, check ingestion job status for failures

### Streaming drops mid-response
1. Check ALB idle timeout — must be ≥120s for long LLM responses
2. Check backend logs for timeout/connection reset errors
3. Check task memory — OOM kills show in stopped task reason
4. Check if the task was replaced during a deployment

### New document uploaded but not searchable
1. Check Lambda invocation: `aws logs tail /aws/lambda/platform-health-kb-sync --since 5m`
2. Check ingestion job status for S3 data source (Section 3)
3. Verify file is in the correct S3 prefix: `documents/`
4. Check for ingestion failures (docs_failed > 0 in job status)

### Session history missing
1. ECS exec into container, check `/mnt/efs/sessions/` for the session directory
2. If directory missing → session was never created or different task handled it
3. Check EFS mount: `df -h /mnt/efs` (should show the EFS filesystem)
4. Check file permissions: `ls -la /mnt/efs/`

### High latency responses
1. Check `tool_calls[].latency_ms` in the chat response JSON
2. KB retrieve typically 1-3s — if higher, check OpenSearch collection health
3. Bedrock LLM call typically 5-15s — if higher, check for throttling in logs
4. Check ECS task CPU: sustained high CPU = undersized task
5. Check if multiple concurrent requests are queuing

---

## Quick Reference

| Resource | ID |
|---|---|
| ECS Cluster | `platform-health-cluster` |
| Backend Service | `platform-health-backend` |
| Frontend Service | `platform-health-frontend` |
| ALB | `platform-health-alb-1623429612.ap-southeast-2.elb.amazonaws.com` |
| Knowledge Base | `II5KAPFHJP` |
| S3 Data Source | `THEYKFVVTX` |
| Web Data Source | `G0QLXXLD5B` |
| Confluence Data Source | `FCAVAELI9A` |
| S3 Bucket | `platform-health-kb-documents-615299759525` |
| EFS | `fs-0932b5da25a24f024` (mount: `/mnt/efs`) |
| DynamoDB Tables | `platform-health-checklists`, `platform-health-escalations` |
| Lambda | `platform-health-kb-sync` |
| OpenSearch | `0s43wsj0nu6nsj4bdlxf` |
| LLM | `apac.anthropic.claude-sonnet-4-20250514-v1:0` |
| Embeddings | `amazon.titan-embed-text-v2:0` (1024d) |
