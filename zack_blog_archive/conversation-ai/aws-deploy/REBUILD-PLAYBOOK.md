# Rebuild Playbook — Destroy & Recreate from Scratch

## ⚠️ Why This Guide Exists

During our first deployment, `terraform apply` did NOT succeed in one shot. Several resources required manual intervention, and some steps are intentionally outside Terraform. This guide captures the EXACT sequence needed to rebuild the entire solution.

## What Terraform Handles vs What's Manual

### ✅ Terraform Handles Automatically (no issues)
- ECR repositories (2)
- S3 bucket with notification config
- EFS + mount targets
- DynamoDB tables (2)
- Secrets Manager + KMS key (creates the secret, but NOT the value)
- IAM roles (4) with policies
- ECS cluster + task definitions + services
- ALB + target groups + listener rules
- Cloud Map namespace + service
- Lambda function + S3 trigger
- CloudWatch log groups

### ❌ Terraform Did NOT Handle (required manual steps)
1. **OpenSearch Serverless Collection** — Terraform CAN create it, but it takes 10-15 minutes to activate. Our approach was to pre-create it via CLI so Terraform wouldn't timeout waiting.
2. **OpenSearch Vector Index** — The Terraform `null_resource` with `curl + aws-sigv4` FAILED to create the index. Had to use Python `opensearch-py` client. The index MUST exist BEFORE Bedrock KB creation.
3. **Bedrock KB** — Failed on first `terraform apply` because vector index didn't exist. Succeeded on second run after index was manually created.
4. **Confluence Secret Value** — Terraform creates the Secrets Manager secret but with a placeholder value. The real Confluence API token must be set manually.
5. **Docker Images** — Terraform creates ECR repos but doesn't build/push images. This is by design.
6. **Document Upload** — S3 bucket is created empty. Documents must be uploaded manually.
7. **KB Data Source Sync** — S3 sync auto-triggers via Lambda on upload. Web crawler and Confluence sync must be triggered manually.

## Complete Rebuild Sequence (Tested Order)

### Phase 0: Destroy Everything (if rebuilding)
```bash
cd aws-deploy/terraform

# First, delete the OpenSearch collection manually (Terraform may timeout)
AWS_PROFILE=sandboxtest aws opensearchserverless delete-collection \
  --id <old-collection-id> --no-cli-pager

# Then destroy everything else
AWS_PROFILE=sandboxtest terraform destroy

# Clean ECR images if needed
AWS_PROFILE=sandboxtest aws ecr delete-repository --repository-name platform-health/agent-backend --force
AWS_PROFILE=sandboxtest aws ecr delete-repository --repository-name platform-health/frontend --force
```

### Phase 1: Pre-Create OpenSearch Serverless (10-15 min wait)
DO THIS FIRST because it takes the longest.

```bash
# Step 1a: Create encryption policy (REQUIRED before collection)
AWS_PROFILE=sandboxtest aws opensearchserverless create-security-policy \
  --name platform-health-enc --type encryption \
  --policy '{"Rules":[{"ResourceType":"collection","Resource":["collection/platform-health-kb"]}],"AWSOwnedKey":true}' \
  --no-cli-pager

# Step 1b: Create network policy
AWS_PROFILE=sandboxtest aws opensearchserverless create-security-policy \
  --name platform-health-net --type network \
  --policy '[{"Rules":[{"ResourceType":"collection","Resource":["collection/platform-health-kb"]},{"ResourceType":"dashboard","Resource":["collection/platform-health-kb"]}],"AllowFromPublic":true}]' \
  --no-cli-pager

# Step 1c: Create data access policy (use YOUR account ID and role)
AWS_PROFILE=sandboxtest aws opensearchserverless create-access-policy \
  --name platform-health-access --type data \
  --policy '[{"Rules":[{"ResourceType":"index","Resource":["index/platform-health-kb/*"],"Permission":["aoss:*"]},{"ResourceType":"collection","Resource":["collection/platform-health-kb"],"Permission":["aoss:*"]}],"Principal":["arn:aws:iam::615299759525:role/aws-reserved/sso.amazonaws.com/ap-southeast-2/AWSReservedSSO_AdministratorAccess_f7ca6219276682e0","arn:aws:sts::615299759525:assumed-role/AWSReservedSSO_AdministratorAccess_f7ca6219276682e0/*"]}]' \
  --no-cli-pager

# Step 1d: Create the collection
AWS_PROFILE=sandboxtest aws opensearchserverless create-collection \
  --name platform-health-kb --type VECTORSEARCH \
  --no-cli-pager

# Step 1e: WAIT for ACTIVE status (poll every 30 seconds)
watch -n 30 "AWS_PROFILE=sandboxtest aws opensearchserverless batch-get-collection \
  --names platform-health-kb --query 'collectionDetails[0].{status:status,id:id,endpoint:collectionEndpoint}' --output table"
# WAIT until status = ACTIVE (10-15 minutes)
# NOTE the collection ID (e.g., 0s43wsj0nu6nsj4bdlxf) — needed for next step
```

### Phase 2: Create Vector Index (Python Script)
MUST be done AFTER collection is ACTIVE, BEFORE terraform apply.

```bash
# Install dependencies if needed
pip install opensearch-py requests-aws4auth boto3

# Run the index creation script
python3 << 'EOF'
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3

session = boto3.Session(profile_name='sandboxtest')
credentials = session.get_credentials().get_frozen_credentials()
auth = AWS4Auth(credentials.access_key, credentials.secret_key,
                'ap-southeast-2', 'aoss', session_token=credentials.token)

# ⚠️ REPLACE with your NEW collection endpoint (from Phase 1 output)
COLLECTION_ENDPOINT = '<your-collection-id>.ap-southeast-2.aoss.amazonaws.com'

client = OpenSearch(
    hosts=[{'host': COLLECTION_ENDPOINT, 'port': 443}],
    http_auth=auth, use_ssl=True, connection_class=RequestsHttpConnection
)

index_body = {
    "settings": {"index": {"knn": True, "knn.algo_param.ef_search": 512}},
    "mappings": {"properties": {
        "bedrock-knowledge-base-default-vector": {
            "type": "knn_vector", "dimension": 1024,
            "method": {"name": "hnsw", "engine": "faiss",
                      "parameters": {"ef_construction": 512, "m": 16},
                      "space_type": "l2"}
        },
        "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text"},
        "AMAZON_BEDROCK_METADATA": {"type": "text"}
    }}
}

response = client.indices.create('bedrock-knowledge-base-default-index', body=index_body)
print(f"Index created: {response}")

# Verify
print(f"Index exists: {client.indices.exists('bedrock-knowledge-base-default-index')}")
EOF
```

### Phase 3: Update Terraform Variables
Before running terraform apply, update `variables.tf` or create a `terraform.tfvars`:
```bash
cat > aws-deploy/terraform/terraform.tfvars << 'EOF'
# ⚠️ UPDATE these with your NEW values from Phase 1
opensearch_collection_arn = "arn:aws:aoss:ap-southeast-2:615299759525:collection/<NEW-ID>"
opensearch_endpoint       = "https://<NEW-ID>.ap-southeast-2.aoss.amazonaws.com"
EOF
```

ALSO: Check `bedrock-kb.tf` — the OpenSearch collection ARN and endpoint are referenced there. They may be hardcoded or use data sources. Ensure they point to the NEW collection.

### Phase 4: Terraform Apply
```bash
cd aws-deploy/terraform
terraform init
terraform validate
terraform plan   # Review — should show ~49 resources
terraform apply  # Type 'yes'
```

**Expected outcome**: ALL resources created in one shot (because vector index already exists).

**If it fails on Bedrock KB**:
- Check vector index exists (Phase 2)
- Check OpenSearch data access policy includes the Bedrock KB role ARN
- The KB role ARN won't exist until Terraform creates it — this is a chicken-and-egg problem!

### Phase 4b: Fix Data Access Policy (if KB creation fails)
After terraform creates the IAM roles but before KB can be created:
```bash
# Get the Bedrock KB role ARN from terraform output
KB_ROLE_ARN=$(cd aws-deploy/terraform && terraform output -raw bedrock_kb_role_arn)

# Update the data access policy to include the KB role
# You need to add the KB_ROLE_ARN to the Principal list in the data access policy
AWS_PROFILE=sandboxtest aws opensearchserverless update-access-policy \
  --name platform-health-access --type data --policy-version "...(current version)..." \
  --policy '[...include KB_ROLE_ARN in Principal list...]'

# Then re-run terraform apply
terraform apply
```

### Phase 5: Set Confluence Secret

⚠️ **IMPORTANT**: Use the FULL API token — check for trailing `=` and suffix characters (e.g., `=ABA7B279`). Truncated tokens will cause "Failed to connect" errors.

⚠️ **Secret format** MUST be exactly `{"username":"email","password":"full_token"}` — no extra fields like `confluenceUrl`. Bedrock BASIC auth rejects secrets with unexpected keys.

```bash
# Step 5a: Test token locally FIRST
curl -s -u "Hongbo.Zhou@nesa.nsw.edu.au:<YOUR_FULL_CONFLUENCE_API_TOKEN>" \
  "https://educationstandards.atlassian.net/wiki/rest/api/user/current"
# If you get 403, the token is wrong or expired. Do NOT proceed until you get 200.

# Step 5b: Set the secret (BASIC auth format — username + password only)
AWS_PROFILE=sandboxtest aws secretsmanager put-secret-value \
  --secret-id platform-health/confluence-credentials \
  --secret-string '{"username":"Hongbo.Zhou@nesa.nsw.edu.au","password":"<YOUR_FULL_CONFLUENCE_API_TOKEN>"}' \
  --no-cli-pager
```

### Phase 6: Build & Push Docker Images
```bash
# Login to ECR
AWS_PROFILE=sandboxtest aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com

# Backend
cd aws-deploy/agent-backend
docker build --platform linux/amd64 -t platform-health-backend .
docker tag platform-health-backend:latest 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-backend:latest
docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-backend:latest

# Frontend
cd ../frontend
docker build --platform linux/amd64 -t platform-health-frontend .
docker tag platform-health-frontend:latest 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/frontend:latest
docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/frontend:latest
```

### Phase 7: Force ECS Redeployment
```bash
AWS_PROFILE=sandboxtest aws ecs update-service --cluster platform-health-cluster \
  --service platform-health-backend --force-new-deployment --no-cli-pager
AWS_PROFILE=sandboxtest aws ecs update-service --cluster platform-health-cluster \
  --service platform-health-frontend --force-new-deployment --no-cli-pager

# Wait for steady state
watch -n 10 "AWS_PROFILE=sandboxtest aws ecs describe-services --cluster platform-health-cluster \
  --services platform-health-backend platform-health-frontend \
  --query 'services[].{name:serviceName,running:runningCount,events:events[0].message}' --output table"
```

### Phase 8: Upload Documents & Sync
```bash
# Upload docs (Lambda auto-triggers S3 sync)
AWS_PROFILE=sandboxtest aws s3 sync documents/ s3://platform-health-kb-documents-615299759525/documents/

# Wait for S3 sync to complete
watch -n 15 "AWS_PROFILE=sandboxtest aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id <NEW-KB-ID> --data-source-id <NEW-S3-DS-ID> \
  --query 'ingestionJobSummaries[0].{status:status,docs:statistics.numberOfDocumentsScanned}' --output table"

# Then trigger web crawler (AFTER S3 completes)
AWS_PROFILE=sandboxtest aws bedrock-agent start-ingestion-job \
  --knowledge-base-id <NEW-KB-ID> --data-source-id <NEW-WEB-DS-ID> --no-cli-pager

# Then trigger Confluence (AFTER web crawler completes)
AWS_PROFILE=sandboxtest aws bedrock-agent start-ingestion-job \
  --knowledge-base-id <NEW-KB-ID> --data-source-id <NEW-CONFLUENCE-DS-ID> --no-cli-pager
```
⚠️ All resource IDs will be NEW — get them from `terraform output`

> **Note on Confluence sync counts**: The Confluence connector scans ALL pages in accessible spaces and filters during indexing — the "scanned" count will be higher than the "indexed" count. For example, scanning 58 pages but indexing ~40 is normal when using inclusionFilters. Image attachments are also skipped (expected).

### Phase 9: Verify
```bash
# Health check
curl http://<NEW-ALB-URL>/health

# Test chat
curl -X POST http://<NEW-ALB-URL>/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is terraform?", "session_id": "rebuild-test"}'

# Open browser
open http://<NEW-ALB-URL>/
```

## Timeline Estimate
| Phase | Duration | Notes |
|-------|----------|-------|
| 0: Destroy | 5-10 min | OpenSearch collection deletion can be slow |
| 1: OpenSearch collection | 10-15 min | Mostly waiting |
| 2: Vector index | 1 min | Python script |
| 3: Update variables | 2 min | Manual edit |
| 4: Terraform apply | 5-10 min | Should succeed first try now |
| 5: Confluence secret | 1 min | |
| 6: Docker build+push | 5 min | Depends on internet speed |
| 7: ECS redeploy | 3-5 min | Rolling deployment |
| 8: Doc upload + sync | 5-15 min | S3 fast, web crawler slow |
| 9: Verify | 2 min | |
| **Total** | **~40-60 min** | |

## Chicken-and-Egg Problems

### Problem 1: OpenSearch Data Access Policy ↔ Bedrock KB Role
- The data access policy needs the KB role ARN
- The KB role is created by Terraform
- But Terraform also creates the KB which needs the data access policy
- **Solution**: Terraform creates its own data access policy (`platform-health-kb-access`) that includes the KB role ARN. The manual policy (`platform-health-access`) is for admin access.

### Problem 2: Vector Index ↔ Bedrock KB
- Bedrock KB requires vector index to exist
- Vector index lives in OpenSearch collection
- Collection takes 10-15 min to activate
- **Solution**: Pre-create collection + index BEFORE terraform apply

### Problem 3: Docker Images ↔ ECS Services
- ECS services need images in ECR
- ECR repos are created by Terraform
- But images aren't pushed until after Terraform
- **Solution**: ECS services will fail health checks initially. Push images, then force redeploy.

## What Could Be Improved (Future Work)
1. **Script the entire rebuild**: A single `./deploy.sh` that handles all phases in order
2. **Use Terraform's `time_sleep` resource** for OpenSearch collection activation
3. **Use a proper CI/CD pipeline** to auto-build and push Docker images
4. **EventBridge rules** for scheduled web crawler + Confluence sync
5. **Move vector index creation into a Lambda** called by Terraform custom resource

## Quick Reference: New Resource IDs After Rebuild
After `terraform apply`, run:
```bash
cd aws-deploy/terraform
terraform output
```
This shows ALL new resource IDs. Update your commands accordingly.

⚠️ NOTHING from the old deployment carries over. All IDs, ARNs, and URLs will be NEW.
