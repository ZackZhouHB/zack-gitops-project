# Step 12: Lambda Auto-Sync — Event-Driven Document Ingestion

> **Goal:** Make document ingestion fully automatic — upload a PDF to S3 and it
> gets chunked, embedded, and indexed in your Knowledge Base without any human
> intervention.

---

## 12.1 The Problem

Think about how document ingestion works in a **local** development setup:

1. You place a PDF on your machine.
2. You run an ingestion script by hand (`python ingest.py`).
3. You wait for the script to chunk the document, generate embeddings, and push
   them into your vector store.
4. You manually verify that the new content is searchable.

Every single step requires **you** to be at the keyboard. If a teammate drops a
new file in the shared folder at 2 a.m., nothing happens until someone
remembers to run the script the next morning.

### What we want in AWS

The ideal workflow is:

```
Upload a PDF to S3 → it automatically gets chunked, embedded, and indexed
```

No scripts to run. No cron jobs to babysit. The system **reacts** to the upload
event and does the right thing on its own.

This pattern is called **event-driven architecture**. Instead of code that
constantly *polls* ("Are there new files? Are there new files? Are there new
files?"), we register an interest in an event ("Hey S3, let me know when someone
uploads a file") and the cloud platform delivers a notification the instant it
happens.

### Why this matters

| Manual approach | Event-driven approach |
|---|---|
| Human must remember to run ingestion | Ingestion starts automatically |
| Delay between upload and availability | Near-real-time availability |
| Error-prone (forgot to run the script) | Consistent and reliable |
| Doesn't scale — one human, many files | Scales to thousands of files |

---

## 12.2 How S3 Events Work

Here is the full flow from upload to a searchable document:

```
User uploads PDF ──────► S3 bucket  (documents/ prefix)
                            │
                            ▼  S3 Event Notification
                     Lambda function triggered
                            │
                            ▼  Calls Bedrock KB StartIngestionJob API
                     Knowledge Base receives job
                            │
                            ▼  KB reads new file from S3
                     Processing pipeline
                            │
                  ┌─────────┼─────────┐
                  ▼         ▼         ▼
               Chunks    Embeds    Indexes
              the doc   via Titan  in OpenSearch
                  │         │         │
                  └─────────┼─────────┘
                            ▼
                  Document is now searchable!
```

Let's walk through each hop:

1. **User uploads PDF** — could be `aws s3 cp`, the S3 console, or any
   application that writes to S3.
2. **S3 Event Notification** — S3 has a built-in feature that can fire a
   notification when objects are created (or deleted). We configure it to send
   the notification to a Lambda function.
3. **Lambda function triggered** — AWS automatically runs our small Python
   function. It receives an *event* object containing the bucket name, object
   key (file path), and event type.
4. **StartIngestionJob API** — our Lambda calls Bedrock's API to tell the
   Knowledge Base "there is new data — please re-process the data source."
5. **KB reads from S3** — Bedrock knows which S3 bucket/prefix belongs to the
   data source. It reads the file(s).
6. **Chunks → Embeds → Indexes** — Bedrock splits the document into chunks,
   generates vector embeddings with Amazon Titan, and stores them in our
   OpenSearch Serverless collection.
7. **Searchable!** — the document is now available for retrieval-augmented
   generation (RAG) queries.

> **Key insight:** Each component only knows about its immediate neighbour. S3
> doesn't know what a Knowledge Base is. Lambda doesn't care how embedding
> works. This is **loose coupling** — and it makes the system easy to change
> and debug.

---

## 12.3 The Lambda Function (`kb_sync_trigger.py`)

Here is the complete Lambda function. Read through it first, then we'll break
it down line by line.

```python
"""Lambda function: S3 upload → Bedrock KB sync trigger.

When a file is uploaded to the KB data source S3 bucket,
this Lambda automatically starts an ingestion job to re-index.

Environment variables:
    KNOWLEDGE_BASE_ID: Bedrock Knowledge Base ID
    DATA_SOURCE_ID: S3 data source ID within the KB
"""
import os
import json
import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock_agent = boto3.client("bedrock-agent")

KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
DATA_SOURCE_ID = os.environ["DATA_SOURCE_ID"]


def handler(event, context):
    """Handle S3 event notification → start KB ingestion job."""
    logger.info(f"S3 event received: {json.dumps(event)}")

    # Extract S3 details for logging
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        logger.info(f"File uploaded: s3://{bucket}/{key}")

    # Start ingestion job
    try:
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID,
        )
        job_id = response["ingestionJob"]["ingestionJobId"]
        status = response["ingestionJob"]["status"]
        logger.info(f"Ingestion job started: {job_id} (status: {status})")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Ingestion job started",
                "jobId": job_id,
                "status": status,
            }),
        }

    except Exception as e:
        logger.error(f"Failed to start ingestion job: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
```

### Line-by-line explanation

#### The imports

```python
import os
import json
import logging

import boto3
```

| Module | Purpose |
|---|---|
| `os` | Read **environment variables** that Terraform injects at deploy time. |
| `json` | Serialize / deserialize JSON — needed to log the event and build the response body. |
| `logging` | Write structured logs to **CloudWatch Logs** so we can debug later. |
| `boto3` | The **AWS SDK for Python**. Every AWS service has a corresponding *client* in boto3. |

#### Logger setup

```python
logger = logging.getLogger()
logger.setLevel(logging.INFO)
```

By default Lambda's root logger is set to `WARNING`. We lower it to `INFO` so
our `logger.info(...)` calls actually appear in CloudWatch.

#### Creating the Bedrock Agent client

```python
bedrock_agent = boto3.client("bedrock-agent")
```

This line creates a client for the **Bedrock Agent** API. It is placed at the
*module level* (outside the handler function) intentionally — Lambda may reuse
the same execution environment across multiple invocations ("warm starts"), so
the client gets created once and reused, saving time on subsequent calls.

#### Reading environment variables

```python
KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
DATA_SOURCE_ID = os.environ["DATA_SOURCE_ID"]
```

These are injected by Terraform's `environment { variables { ... } }` block
(see section 12.4). Using `os.environ["KEY"]` (with square brackets) will raise
a `KeyError` if the variable is missing — this is on purpose. We *want* the
function to fail loudly if it was deployed without the required configuration.

#### The handler function

```python
def handler(event, context):
```

This is the **entry point** that AWS Lambda calls. Every Lambda function must
export a handler with exactly two parameters:

- **`event`** — a Python dict containing the trigger payload. For an S3
  notification it looks like this (simplified):

  ```json
  {
    "Records": [
      {
        "eventSource": "aws:s3",
        "eventName": "ObjectCreated:Put",
        "s3": {
          "bucket": { "name": "platform-health-kb-documents-615299759525" },
          "object": { "key": "documents/my-doc.pdf" }
        }
      }
    ]
  }
  ```

- **`context`** — a Lambda runtime object with metadata like the function name,
  remaining execution time, log group, etc. We don't use it here, but it's
  always available.

#### Logging S3 details

```python
for record in event.get("Records", []):
    bucket = record["s3"]["bucket"]["name"]
    key = record["s3"]["object"]["key"]
    logger.info(f"File uploaded: s3://{bucket}/{key}")
```

The `Records` list can contain multiple events (S3 batches them). We loop
through each one and log the bucket/key. This is invaluable for debugging —
you'll see exactly which file triggered the function when you check CloudWatch.

#### Starting the ingestion job

```python
response = bedrock_agent.start_ingestion_job(
    knowledgeBaseId=KNOWLEDGE_BASE_ID,
    dataSourceId=DATA_SOURCE_ID,
)
job_id = response["ingestionJob"]["ingestionJobId"]
status = response["ingestionJob"]["status"]
```

`start_ingestion_job()` tells the Knowledge Base: *"Re-scan the S3 data source
and process any new, modified, or deleted files."* It does **not** process just
the uploaded file — it re-syncs the entire data source. This is by design; the
KB handles deduplication internally.

The response contains a `jobId` (a UUID) and an initial `status` (usually
`STARTING`).

#### Error handling

```python
except Exception as e:
    logger.error(f"Failed to start ingestion job: {e}")
    return {
        "statusCode": 500,
        "body": json.dumps({"error": str(e)}),
    }
```

If the API call fails (permissions issue, service outage, concurrent job already
running, etc.), we catch the exception, log the error, and return a 500
response. Lambda retries on failure automatically (twice, by default for
asynchronous invocations), so a transient error will often resolve itself.

#### Return value

```python
return {
    "statusCode": 200,
    "body": json.dumps({
        "message": "Ingestion job started",
        "jobId": job_id,
        "status": status,
    }),
}
```

The return value isn't strictly required for an event-driven Lambda (S3 doesn't
read the response), but it's good practice — it shows up in CloudWatch logs and
helps when testing manually from the Lambda console.

---

## 12.4 Terraform: Lambda Resource (`lambda.tf`)

Here is the complete Terraform configuration that deploys the Lambda function:

```hcl
###############################################################################
# Lambda – KB Sync Trigger
# Invoked by S3 events to start a Bedrock KB data-source ingestion job.
###############################################################################

# --- Package the Lambda function ---------------------------------------------

data "archive_file" "kb_sync" {
  type        = "zip"
  source_file = "${path.module}/../lambda/kb_sync_trigger.py"
  output_path = "${path.module}/../lambda/kb_sync_trigger.zip"
}

# --- Lambda function ---------------------------------------------------------

resource "aws_lambda_function" "kb_sync_trigger" {
  function_name    = "${var.project_name}-kb-sync-trigger"
  runtime          = "python3.12"
  handler          = "kb_sync_trigger.handler"
  role             = aws_iam_role.lambda_kb_sync.arn
  filename         = data.archive_file.kb_sync.output_path
  source_code_hash = data.archive_file.kb_sync.output_base64sha256
  timeout          = 30

  environment {
    variables = {
      KNOWLEDGE_BASE_ID = aws_bedrockagent_knowledge_base.main.id
      DATA_SOURCE_ID    = aws_bedrockagent_data_source.s3.data_source_id
    }
  }
}

# --- Allow S3 to invoke the Lambda ------------------------------------------

resource "aws_lambda_permission" "s3_invoke" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.kb_sync_trigger.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.kb_documents.arn
}
```

### Block-by-block breakdown

#### `data "archive_file" "kb_sync"`

```hcl
data "archive_file" "kb_sync" {
  type        = "zip"
  source_file = "${path.module}/../lambda/kb_sync_trigger.py"
  output_path = "${path.module}/../lambda/kb_sync_trigger.zip"
}
```

Lambda expects your code as a **ZIP file**. Instead of zipping manually, we use
Terraform's built-in `archive_file` data source. Every time you run
`terraform apply`, it:

1. Reads `kb_sync_trigger.py`.
2. Produces `kb_sync_trigger.zip` in the same directory.
3. Computes a SHA-256 hash so Terraform knows when the code has changed.

> **Why a data source and not a resource?** Data sources are read-only — they
> compute values but don't create cloud resources. The ZIP file is a local
> artefact used as input to the `aws_lambda_function` resource.

#### `aws_lambda_function "kb_sync_trigger"`

Let's look at each argument:

| Argument | Value | Explanation |
|---|---|---|
| `function_name` | `"${var.project_name}-kb-sync-trigger"` | Human-readable name. Terraform interpolates the project name variable (e.g. `platform-health-kb-sync-trigger`). |
| `runtime` | `"python3.12"` | The language runtime Lambda uses. Python 3.12 is the latest supported Python runtime at the time of writing. |
| `handler` | `"kb_sync_trigger.handler"` | Tells Lambda: *"In the file `kb_sync_trigger.py`, call the function named `handler`."* The format is always `<filename_without_extension>.<function_name>`. |
| `role` | `aws_iam_role.lambda_kb_sync.arn` | The IAM role the function assumes at runtime. This role must have permissions to call `bedrock-agent:StartIngestionJob` and write to CloudWatch Logs. |
| `filename` | `data.archive_file.kb_sync.output_path` | Path to the ZIP file produced by the `archive_file` block above. |
| `source_code_hash` | `data.archive_file.kb_sync.output_base64sha256` | A hash of the ZIP contents. When the hash changes, Terraform knows it needs to upload a new version. Without this, Terraform might skip updating the function even if you changed the code. |
| `timeout` | `30` | Maximum execution time in **seconds**. Our function just makes a single API call, so 30 seconds is more than enough. If the function exceeds this, Lambda kills it. The default is 3 seconds — too short for an API call. |

##### The `environment` block

```hcl
environment {
  variables = {
    KNOWLEDGE_BASE_ID = aws_bedrockagent_knowledge_base.main.id
    DATA_SOURCE_ID    = aws_bedrockagent_data_source.s3.data_source_id
  }
}
```

This is how we pass **configuration** from Terraform to the Python code. The
values come from other Terraform resources (the KB and the S3 data source), so
we never hard-code IDs. When `os.environ["KNOWLEDGE_BASE_ID"]` runs inside the
Lambda, it gets the real ID that Terraform discovered at deploy time.

#### `aws_lambda_permission "s3_invoke"`

```hcl
resource "aws_lambda_permission" "s3_invoke" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.kb_sync_trigger.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.kb_documents.arn
}
```

By default, **no AWS service** can invoke your Lambda — you have to grant
explicit permission. This resource-based policy says:

> *"The S3 service (`s3.amazonaws.com`), specifically the bucket
> `kb_documents`, is allowed to call `lambda:InvokeFunction` on this
> Lambda."*

Without this permission, S3 would try to invoke the Lambda and receive an
`Access Denied` error, and your files would sit un-indexed.

#### Lambda IAM Role (referenced as `aws_iam_role.lambda_kb_sync`)

The Lambda's execution role (defined elsewhere in the Terraform code) needs
these permissions:

| Permission | Why |
|---|---|
| `bedrock-agent:StartIngestionJob` | To tell the Knowledge Base to start syncing. |
| `logs:CreateLogGroup` | To create the CloudWatch log group on first run. |
| `logs:CreateLogStream` | To create a new log stream for each invocation. |
| `logs:PutLogEvents` | To write the actual log lines (our `logger.info` calls). |

The role also has a **trust policy** that allows the Lambda service
(`lambda.amazonaws.com`) to assume it. Without the trust policy, Lambda can't
"become" this role.

---

## 12.5 S3 Notification Configuration (from `s3.tf`)

Here is the relevant portion of `s3.tf` that wires S3 to Lambda:

```hcl
resource "aws_s3_bucket_notification" "kb_sync" {
  bucket = aws_s3_bucket.kb_documents.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.kb_sync_trigger.arn
    events              = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
    filter_prefix       = "documents/"
  }

  depends_on = [aws_lambda_permission.s3_invoke]
}
```

### What each line does

| Line | Explanation |
|---|---|
| `bucket = aws_s3_bucket.kb_documents.id` | Which S3 bucket to attach the notification to. |
| `lambda_function_arn` | The ARN (Amazon Resource Name) of the Lambda function to invoke. |
| `events = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]` | **Which events trigger the notification.** `ObjectCreated:*` covers uploads via PUT, POST, COPY, and multipart upload. `ObjectRemoved:*` covers deletions — so deleting a document also triggers a re-sync to remove it from the index. |
| `filter_prefix = "documents/"` | **Only** objects whose key starts with `documents/` will trigger the Lambda. |
| `depends_on = [aws_lambda_permission.s3_invoke]` | Terraform must create the Lambda permission **before** the S3 notification. Otherwise S3 would try to validate the Lambda target and fail. |

### Why `filter_prefix`?

The S3 bucket might contain other objects — Terraform state, temporary files,
logs, etc. Without a prefix filter, *any* write to the bucket would trigger the
Lambda. That means:

- Uploading a Terraform state file → unnecessary ingestion job.
- An ingestion job output file → recursive trigger loop (worst case).

By restricting to `documents/`, we ensure the Lambda only fires when someone
uploads an actual document intended for the Knowledge Base.

### Why `depends_on`?

Terraform usually figures out the creation order automatically by following
resource references. But the S3 notification resource doesn't directly reference
the permission — they both reference the Lambda. We add an explicit
`depends_on` to guarantee the permission exists before S3 tries to validate the
Lambda target.

---

## 12.6 Testing the Auto-Sync

Time to see it in action! Run these commands after `terraform apply` has
completed successfully.

### 1. Upload a test document

```bash
aws s3 cp my-doc.pdf s3://platform-health-kb-documents-615299759525/documents/
```

As soon as the upload completes, S3 fires the event notification.

### 2. Check Lambda was invoked (CloudWatch Logs)

```bash
aws logs tail /aws/lambda/platform-health-kb-sync-trigger --since 5m
```

You should see output similar to:

```
S3 event received: {"Records": [{"eventSource": "aws:s3", ...}]}
File uploaded: s3://platform-health-kb-documents-615299759525/documents/my-doc.pdf
Ingestion job started: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX (status: STARTING)
```

If you see `Failed to start ingestion job`, check:
- Is another ingestion job already running? (max 1 concurrent per KB)
- Does the Lambda role have `bedrock-agent:StartIngestionJob` permission?

### 3. Check the ingestion job status

```bash
aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id II5KAPFHJP \
  --data-source-id THEYKFVVTX \
  --query 'ingestionJobSummaries[0]'
```

The status will progress through: `STARTING` → `IN_PROGRESS` → `COMPLETE`.

### 4. Verify the document is searchable

Once the job shows `COMPLETE`, test a retrieval query:

```bash
aws bedrock-agent-runtime retrieve \
  --knowledge-base-id II5KAPFHJP \
  --retrieval-query '{"text": "content from my doc"}'
```

Replace `"content from my doc"` with something you know is in your uploaded
file. If the retrieval returns relevant chunks — congratulations, the full
pipeline is working end to end!

### Troubleshooting checklist

| Symptom | Likely cause | Fix |
|---|---|---|
| No CloudWatch logs at all | S3 notification or Lambda permission missing | Check `terraform apply` output; redeploy |
| `AccessDeniedException` in logs | IAM role missing `bedrock-agent:StartIngestionJob` | Update the IAM policy and redeploy |
| `ConflictException` in logs | Another ingestion job is already running | Wait for it to finish; Lambda retries will handle it |
| Ingestion completes but retrieval returns nothing | File not in `documents/` prefix, or KB chunking config issue | Verify the S3 key starts with `documents/` |

---

## 12.7 Scheduled Syncs (Web Crawler & Confluence)

Our S3 data source has a beautiful auto-trigger via Lambda. But what about the
other data sources?

| Data Source | Trigger Mechanism |
|---|---|
| **S3 documents** | Automatic — S3 event → Lambda → `StartIngestionJob` |
| **Web crawler** | Manual or scheduled — no upload event to trigger on |
| **Confluence** | Manual or scheduled — changes happen in Confluence, not S3 |

The web crawler and Confluence data sources don't live in S3, so there is no
"upload event" to hook into. Instead, we have two options:

### Option A: Manual sync (what we do today)

```bash
# Sync the web crawler data source
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id II5KAPFHJP \
  --data-source-id G0QLXXLD5B

# Sync the Confluence data source
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id II5KAPFHJP \
  --data-source-id FCAVAELI9A
```

> ⚠️ **IMPORTANT: Max 1 concurrent ingestion job per Knowledge Base!**
> If you try to start a second job while one is running, you'll get a
> `ConflictException`. Always wait for the previous job to complete before
> starting the next one. Run them **sequentially**, not in parallel.

### Option B: Scheduled sync with EventBridge (future improvement)

Amazon EventBridge (formerly CloudWatch Events) can run a Lambda on a schedule
(like cron). The architecture would be:

```
EventBridge rule (daily at 2 AM)
        │
        ▼
  Lambda function
        │
        ├──► start_ingestion_job(web_crawler)
        │         wait for completion...
        └──► start_ingestion_job(confluence)
```

This ensures your non-S3 data sources stay in sync without anyone remembering
to run a command. We'll cover EventBridge scheduled rules in a future step.

---

## 12.8 Key Concepts Learned

Let's step back and name the architectural patterns we just used:

### Event-driven architecture

Resources **react** to events rather than polling for changes. S3 fires an
event → Lambda reacts → KB syncs. No component sits in a loop asking "anything
new?" This is more efficient, faster, and cheaper than polling.

### Serverless

We didn't provision any servers. We didn't install Python on an EC2 instance.
We didn't configure auto-scaling. AWS Lambda:

- Runs our code **on demand** — only when S3 fires an event.
- Scales automatically — if 100 files are uploaded simultaneously, Lambda can
  handle all 100 events (though our KB can only run one job at a time).
- Charges per invocation — if no files are uploaded in a month, we pay $0 for
  Lambda.

### Loose coupling

Each component is independent:

- **S3** doesn't know Lambda exists — it just fires events.
- **Lambda** doesn't know how the Knowledge Base works — it just calls an API.
- **Bedrock KB** doesn't know why it was asked to sync — it just processes
  files.

If we wanted to replace the Lambda with a different function, S3 wouldn't care.
If we wanted to add a second Lambda that sends a Slack notification on upload,
we could — without touching the existing Lambda. Loose coupling makes systems
**easy to extend, debug, and replace piece by piece**.

### Infrastructure as Code

The entire pipeline — S3 bucket, Lambda function, IAM role, event notification
— is defined in Terraform. To recreate it in a different AWS account, we run
`terraform apply`. Nothing was clicked in the console. Nothing is undocumented.

---

**Next step:** [Step 13](./step-13-agent-action-groups.md) — Adding Agent Action Groups to give your conversational AI the ability to *do things* (not just answer questions).
