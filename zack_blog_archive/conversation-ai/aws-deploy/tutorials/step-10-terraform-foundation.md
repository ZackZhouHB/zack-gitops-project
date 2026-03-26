# Step 10: Terraform Foundation Infrastructure

> **Time estimate:** 30–45 minutes  
> **Prerequisites:** AWS CLI configured (`aws sts get-caller-identity` works), Terraform ≥ 1.5 installed  
> **What you'll build:** ECR repos, S3 bucket, EFS file system, DynamoDB tables, Secrets Manager — everything the AI agent needs before we wire up the "brain" (Bedrock + OpenSearch)

---

## 10.1 What is Terraform? (For Beginners)

If you've ever created an S3 bucket by clicking through the AWS Console, you know the problem: it's hard to remember exactly what you clicked, impossible to reproduce perfectly, and if someone accidentally deletes it, you start from scratch.

**Terraform solves this by letting you define your infrastructure in text files.** Instead of clicking buttons, you write code. This is called **Infrastructure as Code (IaC)**.

### Why Terraform?

| Concept | What it means | Analogy |
|---------|--------------|---------|
| **Infrastructure as Code** | Define AWS resources in `.tf` text files instead of clicking in the Console | A recipe vs. cooking from memory |
| **Declarative** | You describe *what* you want ("I want an S3 bucket with encryption"). Terraform figures out *how* to create it. | Ordering food at a restaurant — you say "pizza", you don't explain how to use the oven |
| **State file** | Terraform keeps a file called `terraform.tfstate` that remembers every resource it created: IDs, ARNs, settings | A checklist — Terraform checks off what exists so it knows what's new vs. already created |
| **Plan → Apply** | You always *preview* changes before making them. `terraform plan` is a dry run; `terraform apply` actually creates/changes things | Pressing "Print Preview" before printing a document |
| **Idempotent** | Running `terraform apply` twice with no code changes does *nothing* the second time — it only creates what's missing | Turning on a light that's already on — nothing happens |

### HCL Language Basics (30-second crash course)

Terraform uses a language called **HCL (HashiCorp Configuration Language)**. Here are the building blocks you'll see in our files:

```hcl
# --- RESOURCE BLOCK ---
# Creates something new in AWS
resource "aws_s3_bucket" "my_bucket" {
  bucket = "my-unique-bucket-name"
}
#         ↑ type             ↑ local name (your label for it)

# --- DATA SOURCE ---
# Reads something that ALREADY EXISTS in AWS (doesn't create anything)
data "aws_vpc" "default" {
  default = true
}

# --- VARIABLE ---
# An input parameter (like a function argument)
variable "aws_region" {
  default = "ap-southeast-2"
}

# --- REFERENCE ---
# Use other resources/variables with interpolation
bucket = "${var.project_name}-documents"
#          ↑ references the variable named project_name
```

> 💡 **Key insight:** Every resource block has the form `resource "TYPE" "NAME" { ... }`. The TYPE tells Terraform which AWS service to talk to. The NAME is your internal label — Terraform uses it, AWS never sees it.

---

## 10.2 Project Setup (main.tf + variables.tf)

These two files are the "skeleton" of every Terraform project. `main.tf` sets up the connection to AWS. `variables.tf` defines all the configurable values.

### main.tf — The Foundation

```hcl
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

# Default VPC and subnets (data sources, not created)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}

data "aws_caller_identity" "current" {}
```

Let's break down **every block**:

#### `terraform { required_version }` — Pin your Terraform version

```hcl
terraform {
  required_version = ">= 1.5.0"
```

This says: "Don't let anyone run this code with Terraform older than 1.5.0." Why? Because different versions of Terraform can behave differently. If your teammate has v1.3 and you wrote code for v1.5, things might break. Pinning the version prevents this.

The `~> 5.0` for the AWS provider means "any 5.x version" (5.0, 5.12, 5.78, etc.) but NOT 6.0. This gives you bug fixes without surprise breaking changes.

#### `provider "aws"` — Connect Terraform to AWS

```hcl
provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}
```

A **provider** is a plugin that knows how to talk to a specific cloud. The AWS provider knows every AWS API call. Here we tell it:
- **region:** Which AWS data center region to create resources in (Sydney: `ap-southeast-2`)
- **profile:** Which AWS CLI profile to use for credentials (the one you set up with `aws configure --profile sandboxtest`)

> ⚠️ **Gotcha:** If you named your AWS CLI profile something different, you'll need to change the `aws_profile` variable to match. Run `aws configure list-profiles` to see your profiles.

#### `data "aws_vpc" "default"` — Look Up the Default VPC

```hcl
data "aws_vpc" "default" {
  default = true
}
```

This is a **data source** — it reads something that already exists; it does NOT create anything. Every AWS account comes with a "default VPC" (Virtual Private Cloud — think of it as your private network inside AWS). We look it up here so we can reference its ID later.

**Why don't we create a new VPC?** For a dev/learning project, the default VPC is perfectly fine. Creating a custom VPC adds significant complexity (CIDR blocks, route tables, internet gateways). We're keeping it simple.

#### `data "aws_subnets" "default"` — Find All Subnets

```hcl
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }
}
```

**Subnets** are subdivisions of a VPC. AWS creates default subnets in each Availability Zone (AZ). Sydney (`ap-southeast-2`) has 3 AZs, so you'll have 3 subnets. We look them all up because later we need to place resources (like EFS mount targets) in each subnet.

The two filters say: "Give me subnets that (1) belong to our default VPC and (2) are the default subnet for their AZ."

#### `data "aws_caller_identity"` — Who Am I?

```hcl
data "aws_caller_identity" "current" {}
```

This retrieves your **AWS account ID** (a 12-digit number like `615299759525`). We use this later to construct unique resource names — for example, S3 bucket names must be globally unique across ALL AWS accounts, so we append the account ID.

### variables.tf — Configurable Inputs

```hcl
variable "aws_region" {
  default = "ap-southeast-2"
}

variable "aws_profile" {
  default = "sandboxtest"
}

variable "project_name" {
  default = "platform-health"
}

variable "bedrock_model_id" {
  default = "apac.anthropic.claude-sonnet-4-20250514-v1:0"
}

variable "bedrock_embed_model_id" {
  default = "amazon.titan-embed-text-v2:0"
}

variable "confluence_token" {
  description = "Confluence API token (set via TF_VAR_confluence_token or -var)"
  type        = string
  sensitive   = true
}

variable "confluence_email" {
  default = "Hongbo.Zhou@nesa.nsw.edu.au"
}

variable "confluence_host" {
  default = "https://educationstandards.atlassian.net"
}

variable "blog_url" {
  default = "https://zackblog.work/"
}

variable "opensearch_collection_arn" {
  description = "ARN of the pre-created OpenSearch Serverless collection"
  default     = "arn:aws:aoss:ap-southeast-2:615299759525:collection/0s43wsj0nu6nsj4bdlxf"
}
```

Here's what each variable controls:

| Variable | Purpose | Why this default? |
|----------|---------|-------------------|
| `aws_region` | Which AWS region to deploy in | `ap-southeast-2` = Sydney, closest to our users |
| `aws_profile` | AWS CLI credential profile | Matches the profile you created during setup |
| `project_name` | Prefix for all resource names | Keeps everything organized — every resource starts with `platform-health-` |
| `bedrock_model_id` | Which LLM to use for the AI agent | Claude Sonnet 4 via the APAC endpoint |
| `bedrock_embed_model_id` | Which model converts text → vectors for search | Titan Embed v2 — Amazon's own embedding model |
| `confluence_token` | Your Confluence API token | **No default!** Marked `sensitive` so it won't appear in logs. You must provide this at apply time |
| `confluence_email` | Email tied to the Confluence token | Used for API authentication |
| `confluence_host` | Your Confluence instance URL | Points to the Atlassian cloud instance |
| `blog_url` | Blog URL to crawl for knowledge base | An additional data source for the AI |
| `opensearch_collection_arn` | ARN of a pre-existing OpenSearch collection | Referenced by the Bedrock Knowledge Base (created separately) |

> 💡 **How to override a variable:** You have three options:
> 1. `terraform apply -var="aws_profile=myprofile"` — on the command line
> 2. `export TF_VAR_aws_profile=myprofile` — environment variable (prefix `TF_VAR_`)
> 3. Create a `terraform.tfvars` file with `aws_profile = "myprofile"` — auto-loaded

> ⚠️ **Security note:** The `confluence_token` variable is marked `sensitive = true`. Terraform will hide its value in all output. **Never** put the actual token value in `variables.tf` — pass it via `TF_VAR_confluence_token` or a `.tfvars` file that's in your `.gitignore`.

### Running Your First Terraform Commands

Now that you understand the code, let's run it:

```bash
cd aws-deploy/terraform

# Step 1: Initialize — downloads the AWS provider plugin (~200 MB first time)
terraform init

# Step 2: Validate — checks for syntax errors (doesn't connect to AWS)
terraform validate

# Step 3: Plan — connects to AWS and shows what will be created (DRY RUN)
#   Pass your Confluence token here
terraform plan -var="confluence_token=YOUR_TOKEN_HERE"

# Step 4: Apply — actually creates resources (you'll type 'yes' to confirm)
terraform apply -var="confluence_token=YOUR_TOKEN_HERE"
```

**What happens during `terraform init`?**
- Creates a `.terraform/` directory (like `node_modules/` for JavaScript)
- Downloads the AWS provider plugin
- Creates `.terraform.lock.hcl` (like `package-lock.json` — pins exact provider versions)

**What does `terraform plan` output look like?**
You'll see something like:
```
Plan: 14 to add, 0 to change, 0 to destroy.
```
Each resource shows a `+` (create), `~` (modify), or `-` (destroy). Review this carefully before applying!

> ⚠️ **Gotcha:** If you see `Error: No valid credential sources found`, your AWS CLI profile isn't set up correctly. Go back and run `aws configure --profile sandboxtest`.

---

## 10.3 ECR — Docker Image Registry (ecr.tf)

### What is ECR?

**Amazon Elastic Container Registry (ECR)** is AWS's version of Docker Hub. It's a private place to store your Docker images. When you build your backend or frontend Docker image, you push it to ECR. Later, when ECS runs your containers, it pulls the image from ECR.

Think of it like this: ECR is the "parking garage" for your Docker images. ECS is the "highway" where they actually run.

### The Code

```hcl
resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}/agent-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = false
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project_name}/frontend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = false
  }
}
```

### Line-by-Line Explanation

**Why two repositories?** We have two separate Docker images:
1. `platform-health/agent-backend` — the Python FastAPI backend that talks to Bedrock
2. `platform-health/frontend` — the Next.js web interface users interact with

Each image needs its own repository, just like each project on Docker Hub has its own page.

**`image_tag_mutability = "MUTABLE"`** — Docker images have tags like `:latest`, `:v1.0`, `:abc123`. "MUTABLE" means you can push a *new* image with the same tag (e.g., push a new `:latest` that overwrites the old one). This is convenient during development. In production, you might set this to `"IMMUTABLE"` to prevent accidental overwrites.

**`force_delete = true`** — Normally, ECR won't let you delete a repository that still contains images. This setting overrides that protection. Perfect for a dev environment where you might want to `terraform destroy` everything cleanly. **In production, you'd set this to `false`.**

**`scan_on_push = false`** — ECR can scan images for security vulnerabilities when you push them. We've turned this off to keep things simple and avoid scan costs. For a production workload, you'd enable this.

> 💡 **Why we don't have a lifecycle policy here:** Our ECR repos are simple — we mainly use the `:latest` tag during development. If you were pushing hundreds of tagged images (e.g., one per commit), you'd add a `lifecycle_policy` to auto-delete old ones and save storage costs.

---

## 10.4 S3 — Document Storage (s3.tf)

### What is S3?

**Amazon S3 (Simple Storage Service)** is AWS's object storage — think of it as an infinite hard drive in the cloud. You store files (called "objects") in "buckets." S3 is where we'll store documents that the AI Knowledge Base will index and search through.

### The Code

```hcl
resource "aws_s3_bucket" "kb_documents" {
  bucket        = "${var.project_name}-kb-documents-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "kb_documents" {
  bucket = aws_s3_bucket.kb_documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

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

### Line-by-Line Explanation

**Bucket naming: `"${var.project_name}-kb-documents-${data.aws_caller_identity.current.account_id}"`**

S3 bucket names must be **globally unique across all AWS accounts worldwide**. If someone in Tokyo already has a bucket called `my-bucket`, you can't use that name. By appending your AWS account ID (e.g., `platform-health-kb-documents-615299759525`), we guarantee uniqueness.

**`force_destroy = true`** — Normally, S3 won't let you delete a bucket that contains objects. With `force_destroy`, Terraform will empty the bucket first, then delete it. Essential for dev environments where you `terraform destroy` frequently. **In production, remove this to prevent accidental data loss.**

**Versioning:**

```hcl
resource "aws_s3_bucket_versioning" "kb_documents" {
  bucket = aws_s3_bucket.kb_documents.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

With versioning enabled, S3 keeps **every version** of every file. If you upload `report.pdf`, then upload a new `report.pdf`, both versions are preserved. You can always go back to the old one. This is important for a Knowledge Base — if someone accidentally uploads a bad document, you can revert.

> 💡 **Note about encryption and public access:** You might notice we don't explicitly configure `server_side_encryption` or `block_public_access` in this file. As of 2023, **AWS enables S3 bucket encryption (SSE-S3 with AES-256) by default** for all new buckets, and **blocks public access by default**. So our documents are encrypted at rest and private without extra configuration!

**S3 Notifications — The Magic Trigger:**

```hcl
resource "aws_s3_bucket_notification" "kb_sync" {
  ...
  lambda_function {
    lambda_function_arn = aws_lambda_function.kb_sync_trigger.arn
    events              = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
    filter_prefix       = "documents/"
  }
  depends_on = [aws_lambda_permission.s3_invoke]
}
```

This is where the **automation magic** happens. This notification rule says:

1. **Watch** the `documents/` folder inside the bucket
2. **When** any file is created (`s3:ObjectCreated:*`) or deleted (`s3:ObjectRemoved:*`)...
3. **Trigger** a Lambda function (`kb_sync_trigger`) that tells Bedrock to re-sync its Knowledge Base

This means: **upload a PDF → the AI automatically learns from it.** No manual steps needed.

The `depends_on` tells Terraform: "Don't create this notification until the Lambda permission is ready." Otherwise, S3 would try to call a Lambda it doesn't have permission to invoke.

> ⚠️ **Gotcha:** The `filter_prefix = "documents/"` means only files in the `documents/` folder trigger the Lambda. If you upload to the bucket root or a different folder, nothing happens. Make sure you upload to `s3://your-bucket/documents/your-file.pdf`.

---

## 10.5 EFS — Persistent File System (efs.tf)

### What is EFS?

**Amazon Elastic File System (EFS)** is a shared network drive in the cloud. Multiple containers can mount the same EFS file system simultaneously, and data persists even if containers are restarted or destroyed.

**Why do we need this?** Our AI agent stores chat history as local files. If we used the container's built-in storage, chat history would vanish every time the container restarts (containers are ephemeral!). EFS gives us persistent, shared storage.

Think of it like a shared Google Drive that all your containers can access.

### The Code

```hcl
resource "aws_efs_file_system" "chat_history" {
  creation_token = "${var.project_name}-efs"
  encrypted      = true

  tags = {
    Name = "${var.project_name}-chat-history"
  }
}

resource "aws_efs_mount_target" "chat_history" {
  for_each = toset(data.aws_subnets.default.ids)

  file_system_id  = aws_efs_file_system.chat_history.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}

resource "aws_security_group" "efs" {
  name_prefix = "${var.project_name}-efs-"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-efs"
  }
}
```

### Line-by-Line Explanation

**The file system itself:**

```hcl
resource "aws_efs_file_system" "chat_history" {
  creation_token = "${var.project_name}-efs"
  encrypted      = true
}
```

- **`creation_token`** — A unique identifier to prevent accidentally creating duplicate file systems. If you run `terraform apply` twice, Terraform uses this token to know it's the same one.
- **`encrypted = true`** — All data stored on EFS is encrypted at rest using AWS-managed keys. This means if someone physically stole the hard drive from an AWS data center (extremely unlikely), they couldn't read your data.

**Mount targets — one per subnet:**

```hcl
resource "aws_efs_mount_target" "chat_history" {
  for_each = toset(data.aws_subnets.default.ids)

  file_system_id  = aws_efs_file_system.chat_history.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}
```

A **mount target** is an access point in a specific subnet. Your containers need a mount target in their subnet to access EFS. Since our default VPC has subnets in 3 Availability Zones (AZs), we create 3 mount targets — one in each.

`for_each = toset(data.aws_subnets.default.ids)` is Terraform's loop syntax. It says: "For each subnet ID we found earlier, create a mount target." The `toset()` converts the list to a set (required by `for_each`).

**Security group — the firewall:**

```hcl
resource "aws_security_group" "efs" {
  ...
  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }
}
```

A **security group** is a virtual firewall. This one says:

- **Ingress (incoming traffic):** Allow TCP on port **2049** (the NFS protocol port) **only from** containers running in our ECS tasks security group. Nobody else can connect.
- **Egress (outgoing traffic):** Allow all outbound traffic (`protocol = "-1"` means "all protocols", `0.0.0.0/0` means "anywhere").

> 💡 **Why port 2049?** EFS uses the NFS (Network File System) protocol, which has used port 2049 since the 1980s. This isn't something you choose — it's a standard.

> 💡 **Security best practice:** Notice we don't allow access from `0.0.0.0/0` (the whole internet) on the ingress rule. Only our ECS tasks can reach the file system. This is the principle of **least privilege** — only grant the minimum access needed.

---

## 10.6 DynamoDB — NoSQL Tables (dynamodb.tf)

### What is DynamoDB?

**Amazon DynamoDB** is a fully managed NoSQL database. "Fully managed" means you don't have to worry about servers, patches, or scaling — AWS handles everything. "NoSQL" means it stores data as key-value pairs / JSON documents, not in traditional rows and columns like PostgreSQL.

**Why DynamoDB for this project?** We need to store two types of structured data:
1. **Checklists** — health check items the agent generates
2. **Escalations** — issues that need human attention

DynamoDB is perfect because it's serverless (no idle costs), scales automatically, and has single-digit millisecond response times.

### The Code

```hcl
resource "aws_dynamodb_table" "checklists" {
  name         = "${var.project_name}-checklists"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "checklist_id"

  attribute {
    name = "checklist_id"
    type = "S"
  }

  tags = {
    Project = var.project_name
  }
}

resource "aws_dynamodb_table" "escalations" {
  name         = "${var.project_name}-escalations"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "escalation_id"

  attribute {
    name = "escalation_id"
    type = "S"
  }

  tags = {
    Project = var.project_name
  }
}
```

### Line-by-Line Explanation

**`billing_mode = "PAY_PER_REQUEST"`** — This is the "on-demand" pricing mode. You pay per read/write operation with no minimum. If you make 0 requests, you pay $0. The alternative is `PROVISIONED`, where you pre-allocate capacity (cheaper at high scale, but you pay even when idle). For development, `PAY_PER_REQUEST` is the way to go.

**`hash_key` — The Primary Key:**

```hcl
hash_key = "checklist_id"

attribute {
  name = "checklist_id"
  type = "S"    # S = String
}
```

Every DynamoDB table needs a primary key. The simplest form is a **hash key** (also called a partition key). Think of it as the unique ID for each item.

### Understanding Hash Keys (Simply)

Imagine a filing cabinet:
- The **hash key** is which drawer to look in. Each item's `checklist_id` (or `escalation_id`) determines its drawer.
- DynamoDB uses the hash key to distribute data across servers for performance.

For our tables, each checklist and escalation gets a unique ID as its hash key. Since we only have a hash key (no range/sort key), each `checklist_id` must be unique.

> 💡 **What about range keys?** Some DynamoDB tables use a **composite key**: hash key + range key. The range key lets you store multiple items with the same hash key, sorted by the range key. Example: hash=`user_id`, range=`created_at` would let you store multiple items per user, sorted by creation time. Our tables are simpler — just a hash key for direct lookups.

**`type = "S"`** — The attribute type. DynamoDB supports three attribute types:
- `S` = String (what we use)
- `N` = Number
- `B` = Binary

> ⚠️ **Gotcha:** You only define `attribute` blocks for keys and indexes in Terraform. You do NOT define every column upfront — DynamoDB is schemaless! Your application can store any JSON structure it wants. The attributes block just tells DynamoDB about the key fields it needs to index.

---

## 10.7 Secrets Manager + KMS (secrets.tf)

### What is Secrets Manager?

**AWS Secrets Manager** is a secure vault for sensitive data: API keys, database passwords, tokens. Instead of hardcoding secrets in your code (terrible idea!) or environment variables (better but still risky), you store them in Secrets Manager and retrieve them at runtime.

### What is KMS?

**AWS Key Management Service (KMS)** manages encryption keys. Think of KMS as a locksmith — it creates and manages the master keys that encrypt your data. Secrets Manager uses a KMS key to encrypt your secrets at rest.

### Why Do We Need This?

Our AI agent connects to **Confluence** to read documentation. This requires an API token (like a password). We need to store this token securely so that:
1. It's not in our source code (security risk!)
2. It's encrypted at rest (compliance requirement)
3. Bedrock Knowledge Base can read it when connecting to Confluence

### The Code

```hcl
resource "aws_kms_key" "secrets" {
  description             = "${var.project_name} secrets encryption key"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${var.project_name}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

resource "aws_secretsmanager_secret" "confluence_token" {
  name       = "${var.project_name}/confluence-credentials"
  kms_key_id = aws_kms_key.secrets.arn
}

resource "aws_secretsmanager_secret_version" "confluence_token" {
  secret_id = aws_secretsmanager_secret.confluence_token.id
  secret_string = jsonencode({
    confluenceUrl    = var.confluence_host
    username         = var.confluence_email
    password         = var.confluence_token
  })
}
```

### Line-by-Line Explanation

**The KMS Key:**

```hcl
resource "aws_kms_key" "secrets" {
  description             = "${var.project_name} secrets encryption key"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}
```

- **`deletion_window_in_days = 7`** — When you delete a KMS key, AWS waits this many days before actually destroying it. This is a safety net — if you accidentally delete the key, you have 7 days to recover it. (The minimum is 7 days, maximum is 30 days.)
- **`enable_key_rotation = true`** — AWS automatically rotates the key material every year. The old key material is kept for decrypting old data, but new data uses the new key. This is a security best practice — even if a key is compromised, it's only valid for a year.

**The KMS Alias:**

```hcl
resource "aws_kms_alias" "secrets" {
  name          = "alias/${var.project_name}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}
```

KMS keys have ugly, random IDs like `a1b2c3d4-5678-90ab-cdef-EXAMPLE11111`. An alias gives it a human-readable name: `alias/platform-health-secrets`. Think of it like a DNS name for the key.

**The Secret:**

```hcl
resource "aws_secretsmanager_secret" "confluence_token" {
  name       = "${var.project_name}/confluence-credentials"
  kms_key_id = aws_kms_key.secrets.arn
}
```

This creates the secret *container* (like creating an empty safe). The `kms_key_id` tells Secrets Manager to use our custom KMS key for encryption instead of the default AWS-managed key.

**The Secret Value:**

```hcl
resource "aws_secretsmanager_secret_version" "confluence_token" {
  secret_id = aws_secretsmanager_secret.confluence_token.id
  secret_string = jsonencode({
    confluenceUrl    = var.confluence_host
    username         = var.confluence_email
    password         = var.confluence_token
  })
}
```

This puts the actual secret value inside the container. The value is a JSON object containing:
- **`confluenceUrl`** — The Confluence instance URL
- **`username`** — The email address for API authentication
- **`password`** — The actual Confluence API token (from the `confluence_token` variable you pass at apply time)

`jsonencode()` converts the HCL map to a JSON string. Bedrock Knowledge Base expects the credentials in this specific JSON format when connecting to a Confluence data source.

> 💡 **How does Bedrock use this?** When we set up the Bedrock Knowledge Base (next step), we'll point it at this secret's ARN. Bedrock will call Secrets Manager, decrypt the value using KMS, and use the credentials to crawl Confluence pages. The token never touches your application code.

> ⚠️ **Remember:** The `confluence_token` variable is `sensitive = true`, so Terraform hides it in plan/apply output. But the value *is* stored in `terraform.tfstate`. If you're using a remote backend (S3 + DynamoDB for state locking), make sure the state bucket is encrypted. For local development, just don't commit `terraform.tfstate` to git (it should already be in `.gitignore`).

---

## 10.8 Verification

After `terraform apply` completes successfully, verify each resource was created:

```bash
# ECR — Should show platform-health/agent-backend and platform-health/frontend
aws ecr describe-repositories \
  --query 'repositories[].repositoryName' \
  --output table

# S3 — Should show your kb-documents bucket
aws s3 ls | grep platform-health

# EFS — Should show one file system tagged "platform-health-chat-history"
aws efs describe-file-systems \
  --query 'FileSystems[].{Name:Name,Id:FileSystemId,State:LifeCycleState}' \
  --output table

# DynamoDB — Should show platform-health-checklists and platform-health-escalations
aws dynamodb list-tables \
  --query 'TableNames[?contains(@, `platform-health`)]' \
  --output table

# Secrets Manager — Should show platform-health/confluence-credentials
aws secretsmanager list-secrets \
  --query 'SecretList[?contains(Name, `platform-health`)].Name' \
  --output table

# KMS — Should show alias/platform-health-secrets
aws kms list-aliases \
  --query 'Aliases[?contains(AliasName, `platform-health`)].AliasName' \
  --output table
```

> ✅ **All resources should show as active/available.** If anything is missing, check the `terraform apply` output for errors.

### Common Issues and Fixes

| Problem | Cause | Fix |
|---------|-------|-----|
| "bucket already exists" | S3 name collision (extremely rare with account ID) | Change `project_name` variable |
| "no valid credential sources" | AWS CLI not configured | Run `aws configure --profile sandboxtest` |
| "error creating EFS mount target" | Subnet or security group issue | Check that default VPC exists: `aws ec2 describe-vpcs --filters Name=isDefault,Values=true` |
| "InvalidSignatureException" | Clock skew on your machine | Sync your system clock |

---

## 10.9 What's Next

Congratulations! You've created the **foundation layer** of the platform:

```
┌─────────────────────────────────────────────────────────┐
│                  What You Just Built                     │
├─────────────────────────────────────────────────────────┤
│  📦 ECR Repos        → Where Docker images live          │
│  📂 S3 Bucket        → Where documents are stored        │
│  💾 EFS File System   → Persistent chat history storage  │
│  🗄️ DynamoDB Tables  → Checklists + Escalations data    │
│  🔐 Secrets + KMS    → Secure Confluence credentials     │
└─────────────────────────────────────────────────────────┘
```

These are the "storage and registry" resources — they hold data and images but don't *do* anything intelligent on their own.

**In the next step**, we'll create the AI brain:
- **Amazon Bedrock Knowledge Base** — connects to Confluence and S3 documents
- **OpenSearch Serverless** — vector database for semantic search
- **Lambda function** — auto-syncs the Knowledge Base when documents change

That's where your documents get turned into searchable AI knowledge. The foundation you just built is what makes it all possible.

> 💡 **Tip:** Run `terraform state list` to see all resources Terraform is managing. Run `terraform show` for a detailed view of each resource's current state. These commands are invaluable for debugging.

---

*Next: [Step 11 — Bedrock Knowledge Base + OpenSearch Serverless →](step-11-bedrock-knowledge-base.md)*
