# Step 16: Build, Deploy & End-to-End Testing

> **Audience:** Complete beginners to Docker, ECR, and ECS deployments.
> **Time to complete:** ~45–60 minutes (first time), ~10 minutes once familiar.

You've written your code, set up your infrastructure with Terraform, and everything is ready locally. Now it's time for the most exciting part — getting your application running **in the cloud** so anyone with the URL can use it.

This guide walks you through every single step, explains *why* each command exists, and gives you the tools to troubleshoot when things go wrong (because they will, and that's completely normal).

---

## 16.1 The Deployment Pipeline (Overview)

Before we dive into commands, let's understand the big picture. Every time you change your code and want users to see the update, you follow this pipeline:

```
Code Change → Docker Build → ECR Push → ECS Redeploy → ALB Routes Traffic → Test
```

Here's what each stage does:

| Stage | What Happens | Tool |
|-------|-------------|------|
| **Code Change** | You edit Python/Streamlit files locally | Your editor |
| **Docker Build** | Package your code + dependencies into a portable image | `docker build` |
| **ECR Push** | Upload that image to AWS's private container registry | `docker push` |
| **ECS Redeploy** | Tell AWS to pull the new image and restart your service | `aws ecs update-service` |
| **ALB Routes Traffic** | The load balancer shifts users to the new version (zero downtime) | Automatic |
| **Test** | Verify everything works end-to-end | `curl`, browser |

Think of it like shipping a product:
1. You **build** the product in your workshop (Docker Build)
2. You **ship** it to the warehouse (ECR Push)
3. The warehouse **delivers** it to the store shelves (ECS Redeploy)
4. Customers **buy** it through the storefront (ALB Routes Traffic)

Let's go through each stage in detail.

---

## 16.2 Docker Build (Step by Step)

### Docker Basics — What You Need to Know

If you've never used Docker before, here are the only three concepts you need:

**What is a Docker image?**
A Docker image is a **snapshot** of your application plus *everything* it needs to run — the Python interpreter, all your pip packages, your source code, and even a minimal Linux operating system. It's like a zip file that contains an entire computer, frozen in time.

**What is a container?**
A container is a **running instance** of an image. If the image is the recipe, the container is the cooked meal. You can run multiple containers from the same image, just like you can cook the same recipe multiple times.

**What is a Dockerfile?**
A Dockerfile is a **text file with instructions** that tells Docker how to build your image, step by step. Think of it as the recipe itself.

### The Build Command

When you run `docker build`, Docker reads your Dockerfile and executes each instruction to create an image. Each instruction creates a **layer**, and Docker caches these layers. This means if you only changed your application code but not your dependencies, Docker skips the dependency installation step — making rebuilds fast.

### ⚠️ CRITICAL: The `--platform` Flag on Apple Silicon Macs

If you're on an **Apple Silicon Mac** (M1, M2, M3, or M4), pay close attention. Your Mac uses ARM architecture (`arm64`), but **AWS Fargate runs on x86_64 architecture** (`amd64`). If you build an image without specifying the platform, Docker will build for your Mac's architecture, and the container will **crash on AWS** with a cryptic error like:

```
exec format error
```

The fix is simple — always include `--platform linux/amd64`:

```bash
docker build --platform linux/amd64 -t my-image .
```

This tells Docker: "Build this image as if we're on a Linux x86_64 machine." It will be slightly slower because Docker uses emulation, but the image will run correctly on Fargate.

> **Tip:** If you're on an Intel Mac or a Linux machine, `--platform linux/amd64` is technically redundant but harmless. Include it anyway for consistency and portability.

---

### Building the Backend Image

Navigate to the backend directory and build:

```bash
cd aws-deploy/agent-backend

# Build for Fargate's architecture (x86_64)
docker build --platform linux/amd64 -t platform-health-backend .
```

The `-t platform-health-backend` flag **tags** (names) the image so you can refer to it later. The `.` at the end tells Docker: "The Dockerfile is in the current directory."

#### What Happens at Each Dockerfile Step

Let's walk through each line of the Dockerfile and what it does:

**Step 1: `FROM python:3.12-slim`**
```dockerfile
FROM python:3.12-slim
```
This downloads a **base image** from Docker Hub — a minimal Linux system with Python 3.12 pre-installed. The `slim` variant is a smaller version (~150MB vs ~900MB for the full image) that strips out things you don't need in production (compilers, documentation, etc.). Think of this as choosing your starting ingredients.

**Step 2: `WORKDIR /app`**
```dockerfile
WORKDIR /app
```
This creates a directory called `/app` inside the container and sets it as the working directory. Every command after this runs from `/app`. It's like running `mkdir /app && cd /app`.

**Step 3: `COPY requirements.txt .`**
```dockerfile
COPY requirements.txt .
```
This copies **only** the `requirements.txt` file from your local machine into the container. Why copy this first, before the rest of your code? Because of Docker's **layer caching**. If `requirements.txt` hasn't changed since the last build, Docker skips the next step entirely. This saves minutes on each rebuild.

**Step 4: `RUN pip install --no-cache-dir -r requirements.txt`**
```dockerfile
RUN pip install --no-cache-dir -r requirements.txt
```
This installs all your Python dependencies inside the container. `--no-cache-dir` tells pip not to cache downloaded packages (saves space in the image). This step can take 1–3 minutes the first time, but is skipped on subsequent builds if requirements haven't changed.

**Step 5: `COPY . .`**
```dockerfile
COPY . .
```
This copies your **entire application code** into the container. This is done last so that code changes don't invalidate the dependency cache from Step 4. This is the most important Docker optimization to understand.

**Step 6: `EXPOSE 8001`**
```dockerfile
EXPOSE 8001
```
This is **documentation only** — it tells anyone reading the Dockerfile that the app listens on port 8001. It doesn't actually open the port; that's done by ECS task definitions and security groups. Think of it as a comment that tooling can read.

**Step 7: `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]`**
```dockerfile
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```
This is the **startup command** — what runs when the container starts. It launches your FastAPI application using Uvicorn. `--host 0.0.0.0` means "accept connections from any IP address" (required in containers, since `localhost` won't work from outside).

You should see output like:
```
 => [1/5] FROM python:3.12-slim@sha256:...
 => [2/5] WORKDIR /app
 => [3/5] COPY requirements.txt .
 => [4/5] RUN pip install --no-cache-dir -r requirements.txt
 => [5/5] COPY . .
 => exporting to image
```

---

### Building the Frontend Image

Same process, different directory and port:

```bash
cd aws-deploy/agent-frontend

# Build for Fargate's architecture
docker build --platform linux/amd64 -t platform-health-frontend .
```

The frontend Dockerfile follows the same pattern but runs Streamlit on port 8501 instead of Uvicorn on port 8001. The startup command will look something like:

```dockerfile
CMD ["streamlit", "run", "app/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

> **Quick sanity check:** You can test images locally before pushing:
> ```bash
> docker run -p 8001:8001 platform-health-backend
> # In another terminal:
> curl http://localhost:8001/health
> ```
> If you get a healthy response, the image is good.

---

## 16.3 ECR Push (Getting Images to AWS)

Your images exist on your laptop now. AWS can't see them. **Amazon ECR** (Elastic Container Registry) is AWS's private Docker registry — think of it as a private Docker Hub that only your AWS account can access.

Getting an image to ECR is a three-step process: **authenticate**, **tag**, **push**.

### Step 1: Authenticate Docker with ECR

```bash
AWS_PROFILE=sandboxtest aws ecr get-login-password --region ap-southeast-2 | \
  docker login --username AWS --password-stdin \
  615299759525.dkr.ecr.ap-southeast-2.amazonaws.com
```

**What this does, piece by piece:**

1. `aws ecr get-login-password` — Asks AWS for a **temporary authentication token** (valid for 12 hours). This is like getting a visitor badge to enter a secure building.
2. The `|` (pipe) sends that token directly to the next command.
3. `docker login --username AWS --password-stdin` — Gives that token to Docker so it's authorized to push images to your private registry.

The `--password-stdin` flag means "read the password from the pipe" instead of typing it interactively. The username is always `AWS` for ECR — this never changes.

You should see:
```
Login Succeeded
```

> **Note:** This token expires after 12 hours. If you get "authorization token has expired" errors later, just run this command again.

### Step 2: Tag the Image

```bash
docker tag platform-health-backend:latest \
  615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-backend:latest
```

**Why do we need to tag?**

Docker needs to know **where** to push. When you built the image, you tagged it as `platform-health-backend:latest` — a local-only name. Now you need to re-tag it with the full ECR URL so Docker knows the destination.

**The tag format is:**
```
<aws-account-id>.dkr.ecr.<region>.amazonaws.com/<repository-name>:<tag>
```

Breaking down our tag:
- `615299759525` — Your AWS account ID
- `dkr.ecr.ap-southeast-2.amazonaws.com` — ECR's domain in Sydney region
- `platform-health/agent-backend` — The repository name (created by Terraform)
- `latest` — The image tag (you could also use version numbers like `v1.0.0`)

> **Tip:** Tagging doesn't copy the image — it just creates an additional name pointing to the same image. It's instant and uses zero extra disk space.

### Step 3: Push to ECR

```bash
docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-backend:latest
```

This **uploads** your image to AWS. You'll see output like:

```
The push refers to repository [615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-backend]
a1b2c3d4e5f6: Pushed
b2c3d4e5f6g7: Pushed
c3d4e5f6g7h8: Layer already exists
latest: digest: sha256:abc123... size: 1234
```

Notice **"Layer already exists"** — Docker is smart about uploads. If a layer hasn't changed (like the Python base image), it skips uploading it. Only modified layers are transferred. This makes subsequent pushes much faster (seconds instead of minutes).

### Repeat for Frontend

```bash
docker tag platform-health-frontend:latest \
  615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-frontend:latest

docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-frontend:latest
```

---

## 16.4 ECS Deployment

Your images are now sitting in ECR. But ECS is still running the **old** version. You need to tell ECS: "Hey, there's a new image — go get it."

### Force New Deployment

```bash
AWS_PROFILE=sandboxtest aws ecs update-service \
  --cluster platform-health-cluster \
  --service platform-health-backend \
  --force-new-deployment
```

**What each flag means:**
- `--cluster platform-health-cluster` — Which ECS cluster to target (you might have multiple clusters for different projects)
- `--service platform-health-backend` — Which service within that cluster to update
- `--force-new-deployment` — The key flag. It tells ECS: "Even though the task definition hasn't changed, pull the `latest` image again and replace running tasks."

**How the rolling deployment works:**

ECS doesn't just kill the old container and start a new one — that would cause downtime. Instead, it does a **rolling deployment**:

1. 🟢 **Old task** is running and serving traffic
2. 🔵 **New task** starts up alongside the old one
3. 🔵 New task pulls the latest image from ECR
4. 🔵 New task starts the application
5. 🔵 ALB runs **health checks** against the new task (`/health` endpoint)
6. 🔵 Once health checks pass, ALB **shifts traffic** to the new task
7. 🔴 Old task is **drained** (finishes in-flight requests) and then stopped

The whole process takes about 2–5 minutes. During this time, **users experience zero downtime**.

Do the same for the frontend:

```bash
AWS_PROFILE=sandboxtest aws ecs update-service \
  --cluster platform-health-cluster \
  --service platform-health-frontend \
  --force-new-deployment
```

### Monitoring the Deployment

Don't just fire and forget — watch the deployment to make sure it succeeds:

```bash
# Watch service events (most recent first)
AWS_PROFILE=sandboxtest aws ecs describe-services \
  --cluster platform-health-cluster \
  --services platform-health-backend \
  --query 'services[0].events[:5].message' \
  --output table
```

You'll see messages like:
```
(service platform-health-backend) has started 1 tasks: (task abc123).
(service platform-health-backend) registered 1 targets in (target-group arn:...)
(service platform-health-backend) has reached a steady state.
```

**"has reached a steady state"** is the magic message — it means the deployment is complete and the new version is running.

If you want to watch it in real-time, you can poll:

```bash
# Quick one-liner to watch until steady state
watch -n 10 "AWS_PROFILE=sandboxtest aws ecs describe-services \
  --cluster platform-health-cluster \
  --services platform-health-backend \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Latest:events[0].message}' \
  --output table"
```

Press `Ctrl+C` to stop watching once you see the steady state message.

### Common Deployment Issues

| Problem | What You See | Root Cause | Fix |
|---------|-------------|------------|-----|
| **Image not found** | `CannotPullContainerError` | ECR repo name doesn't match task definition | Verify image URI in task definition matches your ECR push target |
| **Task keeps crashing** | Task starts then immediately stops, over and over | Application error (crash on startup) | Check CloudWatch logs (see below) |
| **Health check failing** | Task runs but ALB never sends traffic | `/health` endpoint broken or wrong port | Test health endpoint locally first |
| **Wrong platform** | `exec format error` in logs | Built for ARM on Apple Silicon without `--platform` flag | Rebuild with `--platform linux/amd64` |
| **Out of memory** | `OutOfMemoryError: Container killed` | Container exceeds memory limit in task definition | Increase memory in task definition or optimize code |

**Checking CloudWatch logs (your best debugging tool):**

```bash
AWS_PROFILE=sandboxtest aws logs tail /ecs/platform-health-backend --follow
```

This streams logs from your container in real-time. Press `Ctrl+C` to stop. You'll see your application's stdout/stderr output here — Python tracebacks, startup messages, request logs, everything.

To see recent logs without following:

```bash
AWS_PROFILE=sandboxtest aws logs tail /ecs/platform-health-backend --since 30m
```

---

## 16.5 Data Source Sync

Your application is running, but the **Knowledge Base** needs data to search. There are three data sources, and they need to be synced in order.

### Upload Documents to S3

```bash
AWS_PROFILE=sandboxtest aws s3 sync documents/ \
  s3://platform-health-kb-documents-615299759525/documents/
```

This uploads any new or modified files from your local `documents/` folder to the S3 bucket. The `sync` command is smart — it only uploads files that have changed (based on size and modification time).

After the upload, a **Lambda function automatically triggers** a Knowledge Base ingestion job for the S3 data source. You don't need to do anything manually for this one.

Check the sync status:

```bash
AWS_PROFILE=sandboxtest aws bedrock-agent list-ingestion-jobs \
  --knowledge-base-id II5KAPFHJP \
  --data-source-id THEYKFVVTX
```

Wait until the status shows `COMPLETE` before proceeding.

### Manual Trigger for Web & Confluence

The web crawler and Confluence data sources don't auto-trigger — you need to start them manually. **Important: Only one ingestion job can run per Knowledge Base at a time!** Running them concurrently will cause failures.

```bash
# Web crawler (start AFTER S3 sync completes!)
AWS_PROFILE=sandboxtest aws bedrock-agent start-ingestion-job \
  --knowledge-base-id II5KAPFHJP \
  --data-source-id G0QLXXLD5B
```

Wait for this to complete (check with `list-ingestion-jobs`), then:

```bash
# Confluence (start AFTER web crawler completes!)
AWS_PROFILE=sandboxtest aws bedrock-agent start-ingestion-job \
  --knowledge-base-id II5KAPFHJP \
  --data-source-id FCAVAELI9A
```

> **⚠️ Remember:** Max 1 concurrent ingestion job per Knowledge Base. Always wait for one to finish before starting the next. Running them in parallel will result in a `ConflictException`.

---

## 16.6 End-to-End Testing

Everything should be deployed now. Let's verify it all works. Run these tests in order — each one builds confidence that the previous layer is working.

### Test 1: Health Check

The simplest test. If this fails, nothing else will work.

```bash
curl http://platform-health-alb-1623429612.ap-southeast-2.elb.amazonaws.com/health
```

**Expected response:**
```json
{"status": "healthy", "agent": true}
```

- `"status": "healthy"` — The backend is running
- `"agent": true` — The Bedrock agent is connected and responsive

If you get a **502 Bad Gateway**, the ECS task hasn't started yet or is crashing. Wait a few minutes or check CloudWatch logs.

### Test 2: Synchronous Chat

Tests the core RAG (Retrieval-Augmented Generation) pipeline:

```bash
curl -X POST http://platform-health-alb-1623429612.ap-southeast-2.elb.amazonaws.com/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is terraform redo about?", "session_id": "test-001"}'
```

**What to verify in the response:**
- ✅ An `answer` field with a coherent, relevant response
- ✅ A `sources` array listing the documents that were used
- ✅ `confidence` scores for each source (higher = more relevant)
- ✅ Response time under ~10 seconds

If you get an answer but no sources, the Knowledge Base may not have finished syncing.

### Test 3: Streaming Chat

Tests Server-Sent Events (SSE) streaming — the key feature for a good chat UX:

```bash
curl -N -X POST http://platform-health-alb-1623429612.ap-southeast-2.elb.amazonaws.com/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "What is lakehouse?", "session_id": "test-002"}'
```

The `-N` flag disables curl's output buffering so you see tokens stream in real-time.

**What to verify:**
- ✅ Data arrives in chunks (you can see text appearing word by word)
- ✅ Each chunk is an SSE event formatted as `data: {...}`
- ✅ Stream ends with a final event containing the complete response
- ✅ No long pauses or timeouts mid-stream

> **If streaming hangs after ~60 seconds:** The ALB idle timeout is probably too low. It needs to be ≥120 seconds to support long-running LLM responses. Check the ALB's `idle_timeout.timeout_seconds` attribute in Terraform.

### Test 4: Session Management

Tests that conversations are being persisted (to EFS):

```bash
curl http://platform-health-alb-1623429612.ap-southeast-2.elb.amazonaws.com/sessions
```

**What to verify:**
- ✅ Response is a JSON array
- ✅ You see `test-001` and `test-002` sessions (from Tests 2 and 3)
- ✅ Each session shows a `message_count` or similar field
- ✅ Sessions have timestamps

If sessions are empty or missing, check that EFS is properly mounted in the ECS task definition and that the security group allows NFS traffic (port 2049).

### Test 5: Browser Test

Open your browser and navigate to:

```
http://platform-health-alb-1623429612.ap-southeast-2.elb.amazonaws.com
```

Run through this checklist:

1. **Ask a question** → Type something like "What is terraform redo?" and press Enter
   - ✅ You should see the response **streaming** in, word by word
   - ❌ If the entire response appears at once, streaming isn't working

2. **Check source citations** → Look below the response
   - ✅ Document names should appear with relevance scores
   - ✅ Clicking a source should show more details

3. **Test sidebar sessions** → Look at the session history in the sidebar
   - ✅ Previous conversations should be listed
   - ✅ Clicking one should load that conversation's history

4. **Start a new chat** → Click "New Chat" or the equivalent button
   - ✅ Chat area should clear
   - ✅ A new session should begin
   - ✅ Old session should still be visible in the sidebar

### Test 6: KB Retrieve Direct

Tests the Knowledge Base independently (bypasses your application):

```bash
AWS_PROFILE=sandboxtest aws bedrock-agent-runtime retrieve \
  --knowledge-base-id II5KAPFHJP \
  --retrieval-query '{"text": "terraform"}'
```

**What to verify:**
- ✅ Returns a `retrievalResults` array
- ✅ Each result has a `content` field with text chunks
- ✅ Each result has a `score` (relevance, 0 to 1)
- ✅ Each result has a `location` with an S3 URI pointing to the source document

If this returns empty results but your S3 sync completed, the OpenSearch Serverless index might need time to propagate. Wait a few minutes and try again.

---

## 16.7 Troubleshooting Quick Reference

When something goes wrong, start from the bottom of the stack and work up:

| Symptom | What to Check | How to Fix |
|---------|--------------|------------|
| **502 Bad Gateway** | ECS task health — is the task running? | Check CloudWatch logs: `aws logs tail /ecs/platform-health-backend --since 30m`. Fix the error, rebuild, push, redeploy. |
| **504 Gateway Timeout** | ALB timeout settings | Increase ALB `idle_timeout` to ≥120s in Terraform. |
| **No streaming** | ALB idle timeout too low | Set `idle_timeout.timeout_seconds = 120` (or higher) on the ALB. Streaming connections stay open for the full response duration. |
| **No search results** | KB sync status | Run `list-ingestion-jobs` to check. If stuck, trigger a new sync. Ensure documents were uploaded to S3 first. |
| **Container crashes on start** | CloudWatch logs | Usually a Python import error or missing environment variable. Check logs, fix locally, rebuild, push. |
| **`exec format error`** | Image architecture | Rebuilt with `--platform linux/amd64`. This is almost always caused by building on an Apple Silicon Mac without the platform flag. |
| **Session not saved** | EFS mount in task definition | Verify the EFS mount target exists in the same subnets as your tasks. Check security group allows port 2049 (NFS). |
| **Slow responses** | Bedrock throttling or cold start | Check Bedrock service quotas. First request after deployment may be slower (cold start). |
| **`CannotPullContainerError`** | ECR permissions / image URI | Ensure task execution role has `ecr:GetDownloadUrlForLayer` permission. Verify image URI in task definition exactly matches what you pushed. |

### The Debug Loop

When you're stuck, follow this systematic approach:

```
1. Check ECS service events:  aws ecs describe-services ...
2. Check task status:         aws ecs describe-tasks ...
3. Check container logs:      aws logs tail /ecs/<service-name> --since 30m
4. Fix the issue locally
5. Rebuild → Push → Redeploy
6. Repeat until steady state
```

---

## 16.8 Cleanup / Teardown

When you're done with the environment (or want to avoid ongoing AWS charges):

```bash
cd aws-deploy/terraform

# Preview what will be destroyed
AWS_PROFILE=sandboxtest terraform plan -destroy

# Destroy all Terraform-managed resources
AWS_PROFILE=sandboxtest terraform destroy
```

Terraform will show you everything it plans to delete and ask for confirmation. Type `yes` to proceed.

**⚠️ Manual cleanup required** — some resources aren't managed by Terraform or have deletion protection:

1. **ECR images** — Delete images from ECR repositories before or after Terraform destroy:
   ```bash
   AWS_PROFILE=sandboxtest aws ecr batch-delete-image \
     --repository-name platform-health/agent-backend \
     --image-ids imageTag=latest

   AWS_PROFILE=sandboxtest aws ecr batch-delete-image \
     --repository-name platform-health/agent-frontend \
     --image-ids imageTag=latest
   ```

2. **OpenSearch Serverless collection** — If Terraform can't delete it (due to deletion protection), remove it manually via the AWS Console under Amazon OpenSearch Service → Serverless → Collections.

3. **S3 bucket contents** — Terraform can't delete non-empty buckets. Empty them first:
   ```bash
   AWS_PROFILE=sandboxtest aws s3 rm s3://platform-health-kb-documents-615299759525 --recursive
   ```

4. **CloudWatch log groups** — These persist after Terraform destroy. Delete them manually if you want a clean slate:
   ```bash
   AWS_PROFILE=sandboxtest aws logs delete-log-group --log-group-name /ecs/platform-health-backend
   AWS_PROFILE=sandboxtest aws logs delete-log-group --log-group-name /ecs/platform-health-frontend
   ```

---

## Deployment Checklist

Use this as a quick reference for every deployment. Print it, bookmark it, stick it on your wall.

### Pre-Deploy
- [ ] Code changes tested locally
- [ ] `requirements.txt` updated (if dependencies changed)
- [ ] Environment variables set correctly in task definition

### Build
- [ ] `docker build --platform linux/amd64 -t platform-health-backend .` (from `agent-backend/`)
- [ ] `docker build --platform linux/amd64 -t platform-health-frontend .` (from `agent-frontend/`)
- [ ] Quick local test: `docker run -p 8001:8001 platform-health-backend` → `curl localhost:8001/health`

### Push
- [ ] ECR login: `aws ecr get-login-password ... | docker login ...`
- [ ] Tag backend: `docker tag platform-health-backend:latest 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-backend:latest`
- [ ] Push backend: `docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-backend:latest`
- [ ] Tag frontend: `docker tag platform-health-frontend:latest 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-frontend:latest`
- [ ] Push frontend: `docker push 615299759525.dkr.ecr.ap-southeast-2.amazonaws.com/platform-health/agent-frontend:latest`

### Deploy
- [ ] Force new deployment (backend): `aws ecs update-service --cluster platform-health-cluster --service platform-health-backend --force-new-deployment`
- [ ] Force new deployment (frontend): `aws ecs update-service --cluster platform-health-cluster --service platform-health-frontend --force-new-deployment`
- [ ] Watch for "steady state" in service events

### Data Sync (if documents changed)
- [ ] Upload to S3: `aws s3 sync documents/ s3://platform-health-kb-documents-615299759525/documents/`
- [ ] Wait for S3 ingestion to complete
- [ ] Trigger web crawler sync (wait for completion)
- [ ] Trigger Confluence sync (wait for completion)

### Verify
- [ ] Health check returns `{"status": "healthy", "agent": true}`
- [ ] Synchronous chat returns answer + sources
- [ ] Streaming chat delivers tokens in real-time
- [ ] Sessions endpoint lists conversations
- [ ] Browser UI works end-to-end
- [ ] KB retrieve returns relevant results

---

> **🎉 Congratulations!** You've successfully deployed a production-grade conversational AI application to AWS. Every time you need to update, just follow the Build → Push → Deploy cycle. It gets faster with practice — your 10th deployment will take under 5 minutes.
