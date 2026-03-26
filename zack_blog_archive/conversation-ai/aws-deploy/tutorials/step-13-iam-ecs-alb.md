# Step 13: IAM Roles, ECS Fargate & Application Load Balancer

> **Estimated reading time:** 25 minutes
> **Prerequisites:** Steps 1–12 completed (ECR images pushed, DynamoDB tables created, EFS mounted, Bedrock KB configured)
> **Files covered:** `terraform/iam.tf`, `terraform/ecs.tf`, `terraform/alb.tf`

This is the step where everything comes together. Up until now we've built individual pieces — Docker images, databases, a Knowledge Base, an EFS file system. In this step, we wire them all up: we tell AWS **who is allowed to do what** (IAM), we **run our containers** in the cloud (ECS Fargate), and we put a **load balancer** in front of them so users can reach our app through a single URL.

If the previous steps were about buying ingredients and prepping them on the counter, this step is about actually cooking the meal.

---

## 13.1 IAM — Who Can Do What? (`iam.tf`)

### What Is IAM?

**IAM** stands for **Identity and Access Management**. It is AWS's permission system — the bouncer at the door of every AWS service.

Think of it this way: in a company, not everyone has access to every room. The receptionist can open the front door, the accountant can open the safe, and the CEO can open everything. IAM works the same way for AWS services and code.

Every IAM policy answers three questions:

| Question | IAM Concept | Example |
|----------|-------------|---------|
| **WHO** wants to do something? | **Principal** | The ECS service, your Python code, a Lambda function |
| **WHAT** do they want to do? | **Action** | `s3:GetObject`, `bedrock:InvokeModel`, `dynamodb:PutItem` |
| **ON WHAT** resource? | **Resource** | A specific S3 bucket, a specific DynamoDB table, or `"*"` (all) |

There's a fourth critical concept: the **Trust Policy** (also called the "assume role policy"). This answers: **"Which AWS service is even allowed to PUT ON this role?"** It's like a name tag that says "Only ECS tasks can wear this badge."

> **Why does this matter?**
> Without IAM roles, your containers would have zero permissions. They couldn't call Bedrock, read DynamoDB, or even write logs. Every AWS API call checks IAM first — no permission, no access.

### The Four Roles in Our Project

Our project defines **four IAM roles**, each for a different component:

```
┌─────────────────────────┐
│   ECS Execution Role    │  ← Used by ECS itself (pull images, write logs)
├─────────────────────────┤
│   ECS Task Role         │  ← Used by YOUR Python code (Bedrock, DynamoDB)
├─────────────────────────┤
│   Bedrock KB Role       │  ← Used by Bedrock KB service (S3, OpenSearch)
├─────────────────────────┤
│   Lambda Execution Role │  ← Used by the Lambda function (KB sync)
└─────────────────────────┘
```

Let's walk through each one.

---

### Role 1: ECS Execution Role

**Who uses this?** The ECS service itself — not your code.

When ECS starts a container, it needs to do a few things before your code even begins running:
1. **Pull the Docker image** from ECR (your private container registry)
2. **Create a CloudWatch log group** (where your container's stdout/stderr goes)
3. **Read secrets** from Secrets Manager (if you inject them as environment variables)

Your Python code doesn't do any of this — ECS does it on your behalf. This role gives ECS permission to do so.

```hcl
# -----------------------------------------------------------------------------
# 1. ECS Task Execution Role (pulling images, logging, secrets)
# -----------------------------------------------------------------------------
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-ecs-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
```

**Line-by-line breakdown:**

- `assume_role_policy` — This is the **trust policy**. It says: "Only the `ecs-tasks.amazonaws.com` service can assume (wear) this role." If some random Lambda tried to use this role, AWS would say "nope."
- `sts:AssumeRole` — STS (Security Token Service) is how services "put on" a role. Think of it as swiping a badge to enter a secure area.
- `AmazonECSTaskExecutionRolePolicy` — Instead of writing out every permission by hand, we attach AWS's **pre-built managed policy**. This policy includes `ecr:GetDownloadUrlForLayer`, `ecr:BatchGetImage`, `logs:CreateLogStream`, `logs:PutLogEvents`, and more.

> **💡 Tip:** AWS maintains hundreds of managed policies for common use cases. When one exists for your needs, use it instead of writing custom policies — fewer mistakes, and AWS updates them when new permissions are needed.

---

### Role 2: ECS Task Role (CRITICAL — This Is What Your Backend Code Uses)

**Who uses this?** Your Python application running inside the container.

This is the role that matters most for your application. When your FastAPI backend calls `boto3.client('bedrock-runtime').invoke_model(...)`, boto3 needs credentials. But wait — there's no `AWS_ACCESS_KEY_ID` environment variable, no `~/.aws/credentials` file, no `AWS_PROFILE`. How does it work?

**The magic of task role credentials:** When you assign a `task_role_arn` to an ECS task definition, AWS injects temporary credentials into the container's metadata endpoint. The boto3 SDK automatically discovers these credentials — you don't write a single line of credential code. It just works.

```hcl
# -----------------------------------------------------------------------------
# 2. ECS Task Role (backend service → AWS APIs)
# -----------------------------------------------------------------------------
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_bedrock" {
  name = "bedrock-access"
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:Retrieve",
          "bedrock:RetrieveAndGenerate"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem"
        ]
        Resource = [
          aws_dynamodb_table.checklists.arn,
          aws_dynamodb_table.escalations.arn
        ]
      }
    ]
  })
}
```

This policy has **three Statement blocks** — let's break each one down:

**Statement 1 — Bedrock Model Invocation:**
- `bedrock:InvokeModel` — Call Claude Sonnet 4 to generate answers (non-streaming)
- `bedrock:InvokeModelWithResponseStream` — Call Claude with **streaming** (SSE). This is what gives the "typing effect" where tokens appear one by one
- `Resource = "*"` — Allow calling any Bedrock model. You could lock this down to a specific model ARN, but `"*"` keeps it flexible during development

**Statement 2 — Bedrock Knowledge Base:**
- `bedrock:Retrieve` — Search the Knowledge Base for relevant document chunks (RAG retrieval)
- `bedrock:RetrieveAndGenerate` — Search AND generate an answer in one API call
- These are `bedrock:` actions (not `bedrock-agent:`), allowing our backend to query the KB directly

**Statement 3 — DynamoDB:**
- `PutItem`, `GetItem`, `Query`, `Scan`, `UpdateItem`, `DeleteItem` — Full CRUD operations
- `Resource` is **locked down** to exactly two tables: `checklists` and `escalations`. This is **least privilege** — even if your code had a bug that tried to delete another table, IAM would block it

> **⚠️ Common Mistake:** Beginners often put AWS access keys in environment variables or Docker images. **Never do this in production.** Task roles are the correct way — credentials are temporary (rotated automatically), never stored on disk, and automatically available to boto3.

> **🔑 Key Insight:** The difference between "execution role" and "task role" confuses everyone at first:
> - **Execution role** = what ECS needs to START your container (pull image, create logs)
> - **Task role** = what your CODE needs WHILE RUNNING (call Bedrock, read DynamoDB)

---

### Role 3: Bedrock Knowledge Base Role

**Who uses this?** The Bedrock Knowledge Base **service** — not your code, not ECS.

When you created the Knowledge Base in earlier steps, you told Bedrock: "Here's an S3 bucket with documents. Index them into OpenSearch using Titan Embeddings V2." The Bedrock service needs permission to do all of that.

```hcl
# -----------------------------------------------------------------------------
# 3. Bedrock Knowledge Base Role (S3, OpenSearch, Bedrock embedding)
# -----------------------------------------------------------------------------
resource "aws_iam_role" "bedrock_kb" {
  name = "${var.project_name}-bedrock-kb"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "bedrock.amazonaws.com" }
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.account_id
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "bedrock_kb" {
  name = "kb-access"
  role = aws_iam_role.bedrock_kb.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.kb_documents.arn,
          "${aws_s3_bucket.kb_documents.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["aoss:APIAccessAll"]
        Resource = [var.opensearch_collection_arn]
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [aws_secretsmanager_secret.confluence_token.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [aws_kms_key.secrets.arn]
      }
    ]
  })
}
```

**Key differences from the task role:**

- **Trust policy says `bedrock.amazonaws.com`** — only the Bedrock service can assume this role (not ECS tasks)
- **Condition block** — Extra security: only Bedrock requests from YOUR AWS account can use this role. This prevents a "confused deputy" attack where someone else's Bedrock service tricks yours into acting on their behalf
- **S3 access:** `s3:GetObject` reads individual documents; `s3:ListBucket` lists what's in the bucket. Note two resource entries — one for the bucket itself, one for `/*` (objects inside it)
- **`aoss:APIAccessAll`** — OpenSearch Serverless access for storing/querying vector embeddings
- **`secretsmanager:GetSecretValue`** — Read the Confluence API token (if using Confluence as a data source)
- **`kms:Decrypt`** — Decrypt the secret (it's encrypted with a KMS key)

---

### Role 4: Lambda Execution Role

**Who uses this?** The Lambda function that triggers Knowledge Base re-syncs when new documents arrive in S3.

```hcl
# -----------------------------------------------------------------------------
# 4. Lambda Role (S3 → KB sync trigger)
# -----------------------------------------------------------------------------
resource "aws_iam_role" "lambda_kb_sync" {
  name = "${var.project_name}-lambda-kb-sync"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_kb_sync.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_bedrock" {
  name = "bedrock-kb-sync"
  role = aws_iam_role.lambda_kb_sync.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["bedrock:StartIngestionJob"]
      Resource = "*"
    }]
  })
}
```

This role is simple:

- **Trust policy:** `lambda.amazonaws.com` — only Lambda can assume it
- **`AWSLambdaBasicExecutionRole`** — AWS managed policy for CloudWatch Logs (`logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`). Every Lambda needs this to write its execution logs
- **`bedrock:StartIngestionJob`** — The one custom permission: kick off a Knowledge Base sync job. When a new PDF lands in S3, the Lambda fires and calls this API to re-index the documents

> **💡 Pattern to notice:** Every role follows the same structure: (1) Create the role with a trust policy, (2) Attach managed policies for common needs, (3) Add inline policies for custom permissions.

---

## 13.2 ECS Fargate — Running Containers (`ecs.tf`)

### What Is ECS Fargate?

If Docker is about building containers, **ECS** (Elastic Container Service) is about **running** them in the cloud. And **Fargate** is ECS's **serverless mode** — you don't provision or manage any EC2 instances. You just say "run this container with this much CPU and memory" and AWS handles the rest.

Here's the hierarchy, explained with an analogy:

```
┌─────────────────────────────────────────────────────┐
│  ECS Cluster    = The office building               │
│  ├── ECS Service  = A department (keeps headcount)  │
│  │   ├── Task     = An employee (a running unit)    │
│  │   │   └── Container = Their desk (the process)   │
│  │   └── Task     = Another employee                │
│  └── ECS Service  = Another department              │
└─────────────────────────────────────────────────────┘
```

- **Cluster:** A logical grouping. Just a name that ties everything together.
- **Service:** Ensures a certain number of tasks are always running. If a task crashes, the service automatically starts a new one. Think of it as a manager who always keeps the team at full headcount.
- **Task:** A running instance of a task definition. Like a running process based on a blueprint.
- **Container:** The actual Docker container running inside the task.

### ECS Cluster

The simplest resource in our entire project:

```hcl
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
```

That's it — one resource, one setting. The cluster is just a name (`platform-health-cluster`). The `containerInsights` setting enables detailed CPU/memory/network metrics in CloudWatch, which is invaluable for debugging performance issues.

### CloudWatch Log Groups

Before defining tasks, we create log groups where container output will go:

```hcl
resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.project_name}/agent-backend"
  retention_in_days = 14
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.project_name}/frontend"
  retention_in_days = 14
}
```

Logs are retained for 14 days — long enough to debug issues, short enough to avoid ballooning costs. Everything your container prints to stdout/stderr shows up here.

### Task Definition: Backend

This is the **blueprint** for the backend container. It doesn't run anything — it describes WHAT to run:

```hcl
resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project_name}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  volume {
    name = "efs-chat-history"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.chat_history.id
      root_directory     = "/"
      transit_encryption = "ENABLED"
    }
  }

  container_definitions = jsonencode([{
    name  = "agent-backend"
    image = "${aws_ecr_repository.backend.repository_url}:latest"
    portMappings = [{
      containerPort = 8001
      protocol      = "tcp"
    }]
    mountPoints = [{
      sourceVolume  = "efs-chat-history"
      containerPath = "/mnt/efs"
      readOnly      = false
    }]
    environment = [
      { name = "AWS_REGION", value = var.aws_region },
      { name = "BEDROCK_MODEL_ID", value = var.bedrock_model_id },
      { name = "KNOWLEDGE_BASE_ID", value = aws_bedrockagent_knowledge_base.main.id },
      { name = "DYNAMODB_CHECKLISTS_TABLE", value = aws_dynamodb_table.checklists.name },
      { name = "DYNAMODB_ESCALATIONS_TABLE", value = aws_dynamodb_table.escalations.name },
      { name = "EFS_MOUNT_PATH", value = "/mnt/efs" },
    ]
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8001/health')\" || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 10
    }
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.backend.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}
```

**Let's unpack this piece by piece:**

| Setting | Value | Why |
|---------|-------|-----|
| `cpu` | `512` | 0.5 vCPU — enough for a FastAPI server that mostly waits on Bedrock API calls |
| `memory` | `1024` | 1 GB RAM — plenty for Python + FastAPI |
| `network_mode` | `awsvpc` | Each task gets its own private IP (required for Fargate) |
| `execution_role_arn` | Execution role | So ECS can pull the image from ECR and write logs |
| `task_role_arn` | Task role | So your Python code can call Bedrock and DynamoDB |

**EFS Volume Mount:**
The `volume` block attaches the EFS file system (created in Step 10) for persistent chat history. The `mountPoints` section maps it into the container at `/mnt/efs`. `transit_encryption = "ENABLED"` encrypts data moving between the container and EFS.

**Environment Variables:**
These are how your Python code knows which Bedrock model to call, which Knowledge Base to query, and which DynamoDB tables to use. Terraform resolves the references (like `aws_bedrockagent_knowledge_base.main.id`) at deploy time and injects the actual values.

**Health Check:**
ECS periodically runs this command inside the container. If it fails 3 times in a row, ECS kills the task and starts a new one. The check hits `http://localhost:8001/health` — the same endpoint your FastAPI app exposes.

- `startPeriod = 10` — Give the container 10 seconds to start up before checking health
- `interval = 30` — Check every 30 seconds
- `retries = 3` — Allow 3 failures before considering it unhealthy

### Task Definition: Frontend

```hcl
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "frontend"
    image = "${aws_ecr_repository.frontend.repository_url}:latest"
    portMappings = [{
      containerPort = 8501
      protocol      = "tcp"
    }]
    environment = [
      { name = "AGENT_BACKEND_URL", value = "http://agent-backend.${var.project_name}.local:8001" },
    ]
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')\" || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 15
    }
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.frontend.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }])
}
```

The frontend is lighter weight:
- **256 CPU / 512 MiB** — Streamlit is a simple Python web server; it needs less resources
- **Port 8501** — Streamlit's default port
- **No EFS mount** — The frontend doesn't store anything; it's a pure UI
- **`AGENT_BACKEND_URL`** — This is the **Cloud Map DNS address** (explained below). The frontend calls `http://agent-backend.platform-health.local:8001` to reach the backend. This replaces Docker Compose's automatic `http://agent-backend:8001` service name
- **Health check path:** `/_stcore/health` is Streamlit's built-in health endpoint

### Security Groups for ECS Tasks

Security groups are virtual firewalls. They control which network traffic can reach your containers:

```hcl
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${var.project_name}-ecs-"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 8001
    to_port         = 8001
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    from_port       = 8501
    to_port         = 8501
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Allow ECS tasks to talk to each other via service discovery
  ingress {
    from_port = 0
    to_port   = 0
    protocol  = "-1"
    self      = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ecs-tasks"
  }
}
```

**Ingress rules (incoming traffic):**
- **Port 8001 from ALB** — The load balancer can reach the backend
- **Port 8501 from ALB** — The load balancer can reach the frontend
- **`self = true`** — Tasks in this security group can talk to EACH OTHER on any port. This is how the frontend reaches the backend via Cloud Map DNS

**Egress rules (outgoing traffic):**
- **`0.0.0.0/0` on all ports** — Tasks can reach the internet (needed to call AWS APIs like Bedrock, DynamoDB, ECR, etc.)

> **⚠️ Common Mistake:** Forgetting the `self = true` ingress rule. Without it, the frontend can't reach the backend via Cloud Map, even though they're in the same security group.

### Cloud Map — Service Discovery

In Docker Compose, you can call another container by its service name (e.g., `http://agent-backend:8001`). In ECS, containers get random private IPs that change on every restart. **Cloud Map** solves this by providing a stable DNS name.

```hcl
resource "aws_service_discovery_private_dns_namespace" "main" {
  name = "${var.project_name}.local"
  vpc  = data.aws_vpc.default.id
}

resource "aws_service_discovery_service" "backend" {
  name = "agent-backend"
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id
    dns_records {
      ttl  = 10
      type = "A"
    }
    routing_policy = "MULTIVALUE"
  }
  health_check_custom_config {
    failure_threshold = 1
  }
}
```

**How it works:**

1. We create a **private DNS namespace**: `platform-health.local` — this is a private DNS zone that only exists inside our VPC
2. We register a **service** called `agent-backend` in that namespace
3. When the backend ECS service starts, it automatically registers its task's IP in Cloud Map
4. **Result:** `agent-backend.platform-health.local` resolves to the backend container's current IP address
5. `ttl = 10` — DNS records update every 10 seconds, so if a task restarts with a new IP, the frontend picks it up quickly

> **💡 Think of Cloud Map as a phone book.** When the backend moves to a new IP (like changing phone numbers), Cloud Map updates the directory automatically. The frontend just looks up the name.

### ECS Services

Services are the **managers** that ensure your tasks keep running:

```hcl
resource "aws_ecs_service" "backend" {
  name            = "${var.project_name}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "agent-backend"
    container_port   = 8001
  }

  service_registries {
    registry_arn = aws_service_discovery_service.backend.arn
  }

  depends_on = [aws_lb_listener.http]
}

resource "aws_ecs_service" "frontend" {
  name            = "${var.project_name}-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.ecs_tasks.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 8501
  }

  depends_on = [aws_lb_listener.http]
}
```

**Key settings explained:**

- **`desired_count = 1`** — Keep exactly 1 task running at all times. If it crashes, ECS will start a new one automatically. You could scale to 2, 3, or more for high availability
- **`assign_public_ip = true`** — Fargate tasks in the default VPC need a public IP to reach the internet (for AWS API calls). In a production setup with private subnets + NAT gateway, you'd set this to `false`
- **`load_balancer` block** — Registers the task with the ALB target group so the load balancer knows where to send traffic
- **`service_registries`** — Registers the backend with Cloud Map (the frontend service doesn't need this since nothing discovers the frontend by DNS)
- **`depends_on = [aws_lb_listener.http]`** — Wait for the ALB listener to exist before creating the service. Without this, Terraform might try to register with a target group that isn't connected to a listener yet, causing an error

---

## 13.3 Application Load Balancer (`alb.tf`)

### What Is an ALB?

An **Application Load Balancer** sits between the internet and your containers. It serves three critical purposes:

1. **Single entry point** — Users hit one URL instead of needing to know individual container IPs
2. **Health checks** — If a container is unhealthy, the ALB stops sending it traffic
3. **Path-based routing** — Different URL paths go to different services (`/chat` → backend, `/` → frontend)

```
Users on the Internet
         │
         ▼
   ┌─────────────┐
   │     ALB      │  ← Single URL (e.g., platform-health-alb-xxx.elb.amazonaws.com)
   │  (port 80)   │
   └──────┬───────┘
          │
    ┌─────┴──────┐
    │            │
    ▼            ▼
 Backend     Frontend
 (:8001)     (:8501)
```

### ALB Security Group

```hcl
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-alb-"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb"
  }
}
```

- **Ingress: port 80 from `0.0.0.0/0`** — Anyone on the internet can reach the ALB on port 80 (HTTP)
- **Egress: everything** — The ALB needs to forward traffic to the ECS tasks on ports 8001 and 8501

> **⚠️ Production note:** For a real production app, you'd add HTTPS (port 443) with an SSL certificate. HTTP-only is fine for development and internal tools.

### The ALB Resource

```hcl
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = data.aws_subnets.default.ids
  idle_timeout       = 120

  tags = {
    Project = var.project_name
  }
}
```

| Setting | Value | Why |
|---------|-------|-----|
| `internal = false` | Internet-facing | Users need to reach it from outside the VPC |
| `load_balancer_type = "application"` | Layer 7 (HTTP) | Understands URL paths, enabling path-based routing |
| `idle_timeout = 120` | 120 seconds | **Critical for SSE streaming** (explained below) |

#### Why `idle_timeout = 120`?

This is one of the most important settings in the entire file. Our app uses **Server-Sent Events (SSE)** to stream tokens from Claude. Here's what happens during a chat:

1. User sends a message
2. Backend opens a connection to the ALB
3. Backend starts receiving tokens from Bedrock one by one
4. Each token is sent to the frontend as an SSE event
5. The connection stays open until the entire response is complete

Long LLM responses can take 30–90 seconds. The ALB's default `idle_timeout` is 60 seconds — if no data flows for 60 seconds, the ALB **drops the connection**. This would cut off the response mid-sentence!

Setting it to `120` gives us a comfortable buffer. Even if there's a pause between tokens (which can happen with complex reasoning), the connection survives.

### Target Groups

Target groups tell the ALB WHERE to send traffic and HOW to check if the destination is healthy:

```hcl
resource "aws_lb_target_group" "frontend" {
  name        = "${var.project_name}-frontend"
  port        = 8501
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"

  health_check {
    path                = "/_stcore/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }
}

resource "aws_lb_target_group" "backend" {
  name        = "${var.project_name}-backend"
  port        = 8001
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }

  stickiness {
    type    = "lb_cookie"
    enabled = false
  }
}
```

**Key settings:**

- **`target_type = "ip"`** — Required for Fargate (since Fargate tasks get individual IPs, not EC2 instance IDs)
- **Health check paths:** `/health` for the backend FastAPI app, `/_stcore/health` for Streamlit's built-in endpoint
- **`healthy_threshold = 2`** — Need 2 consecutive successes to be considered healthy
- **`unhealthy_threshold = 3`** — Need 3 consecutive failures to be considered unhealthy
- **`interval = 30`** — Check every 30 seconds
- **`stickiness: enabled = false`** — No sticky sessions needed. Each request is independent (we use EFS for shared state)

### Listener & Path-Based Routing Rules

The listener is the "ear" of the ALB — it listens on a port and decides where to forward traffic:

```hcl
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# Route API paths to backend
resource "aws_lb_listener_rule" "backend_chat" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/chat", "/chat/*", "/health", "/sessions", "/sessions/*"]
    }
  }
}
```

**How path-based routing works:**

1. A request arrives at the ALB on port 80
2. The ALB checks the URL path against listener rules, **starting with the lowest priority number** (most specific first)
3. **Priority 100** — If the path matches `/chat`, `/chat/*`, `/health`, `/sessions`, or `/sessions/*`, forward to the **backend** target group (port 8001)
4. **Default action** — If no rules match (everything else: `/`, `/static/*`, etc.), forward to the **frontend** target group (port 8501)

```
Request: GET /chat/stream     → matches /chat/*    → Backend (:8001)
Request: GET /health          → matches /health    → Backend (:8001)
Request: GET /sessions/abc123 → matches /sessions/* → Backend (:8001)
Request: GET /                → no rule match      → Frontend (:8501) [default]
Request: GET /static/app.js   → no rule match      → Frontend (:8501) [default]
```

> **💡 Priority matters!** Lower numbers = higher priority = checked first. If you had a rule at priority 200 for `/*`, it would catch everything and the frontend would never receive traffic. The default action is effectively priority ∞ (last resort).

---

## 13.4 Verification

After running `terraform apply`, verify everything is working:

```bash
# Check ECS cluster exists
aws ecs list-clusters

# Check ECS services are running and healthy
aws ecs describe-services \
  --cluster platform-health-cluster \
  --services platform-health-backend platform-health-frontend \
  --query 'services[].{name:serviceName,status:status,running:runningCount,desired:desiredCount}'

# Check the ALB health endpoint (replace with your actual ALB DNS)
curl http://platform-health-alb-1623429612.ap-southeast-2.elb.amazonaws.com/health

# Check target group health (are containers registered and healthy?)
# Get target group ARNs first:
aws elbv2 describe-target-groups --names platform-health-backend platform-health-frontend \
  --query 'TargetGroups[].{name:TargetGroupName,arn:TargetGroupArn}'

# Then check health for each:
aws elbv2 describe-target-health --target-group-arn <backend-target-group-arn>
aws elbv2 describe-target-health --target-group-arn <frontend-target-group-arn>

# Check Cloud Map service discovery
aws servicediscovery list-services
aws servicediscovery list-instances --service-id <service-id>

# Check CloudWatch logs for errors
aws logs tail /ecs/platform-health/agent-backend --since 5m
aws logs tail /ecs/platform-health/frontend --since 5m
```

**What "healthy" looks like:**
- ECS services show `runningCount: 1` and `desiredCount: 1`
- Target health shows `"State": "healthy"` for both target groups
- `curl /health` returns a 200 response
- CloudWatch logs show your application startup messages without errors

**Common issues:**
- **Target showing "unhealthy"** — Check CloudWatch logs. The container might be crashing on startup (missing env var, wrong image tag)
- **Task keeps restarting** — Health check failing. Verify the health check path and `startPeriod` is long enough for your app to boot
- **Frontend can't reach backend** — Check the `self = true` security group rule and Cloud Map DNS registration

---

## 13.5 How It All Connects

Here's the complete picture of how a user request flows through the system:

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  ALB (port 80)          idle_timeout = 120s                     │
│  Security Group: allow 80 from 0.0.0.0/0                       │
│                                                                 │
│  Listener Rules:                                                │
│  ├─ /chat, /chat/*, /health,        ──→  Backend TG (:8001)    │
│  │  /sessions, /sessions/*                                      │
│  └─ /* (default)                     ──→  Frontend TG (:8501)   │
└───────────────────┬──────────────────┬──────────────────────────┘
                    │                  │
                    ▼                  ▼
        ┌───────────────────┐  ┌───────────────────┐
        │  Backend Task     │  │  Frontend Task     │
        │  512 CPU / 1GB    │  │  256 CPU / 512MB   │
        │  Port 8001        │  │  Port 8501         │
        │                   │  │                    │
        │  Task Role:       │  │  Env:              │
        │  - Bedrock        │  │  AGENT_BACKEND_URL │
        │  - DynamoDB       │  │  = http://agent-   │
        │  - EFS            │  │    backend          │
        │                   │  │    .platform-health │
        │  EFS: /mnt/efs    │  │    .local:8001     │
        └────────┬──────────┘  └───────────────────┘
                 │                       │
                 │         Cloud Map DNS  │
                 │◄────────────────────── │
                 │  agent-backend.platform-health.local:8001
                 │
        ┌────────┴──────────┐
        │  AWS Services     │
        │  - Bedrock (LLM)  │
        │  - DynamoDB       │
        │  - EFS            │
        │  - S3             │
        └───────────────────┘
```

**The complete request flow for a chat message:**

1. User opens browser → hits ALB URL
2. ALB sees path `/` → routes to Frontend (Streamlit)
3. User types a message → Streamlit calls `AGENT_BACKEND_URL/chat/stream`
4. But wait — that's a private Cloud Map DNS! The frontend container resolves `agent-backend.platform-health.local` → gets the backend's private IP
5. Frontend sends HTTP request to backend container on port 8001
6. Backend receives the request → assumes its **Task Role** via instance metadata
7. Backend calls **Bedrock** (with streaming) → gets tokens one by one
8. Backend also queries **DynamoDB** (checklists/escalations) and **Bedrock KB** (document search)
9. Backend streams SSE tokens back to the frontend
10. Frontend renders them in the Streamlit chat UI
11. Chat history is saved to **EFS** at `/mnt/efs`

**Meanwhile, in the background:**
- The **Execution Role** pulled the Docker images and set up logging
- The **Bedrock KB Role** indexed documents from S3 into OpenSearch
- The **Lambda Role** triggers re-indexing when new documents arrive

---

## Summary

| Component | File | What It Does |
|-----------|------|--------------|
| IAM Execution Role | `iam.tf` | Lets ECS pull images and write logs |
| IAM Task Role | `iam.tf` | Lets your Python code call Bedrock + DynamoDB |
| IAM Bedrock KB Role | `iam.tf` | Lets Bedrock KB access S3, OpenSearch, Secrets |
| IAM Lambda Role | `iam.tf` | Lets Lambda trigger KB re-sync |
| ECS Cluster | `ecs.tf` | Logical grouping for services |
| Task Definitions | `ecs.tf` | Blueprints: what image, how much CPU/RAM, what env vars |
| ECS Services | `ecs.tf` | Managers: keep desired_count tasks running |
| Cloud Map | `ecs.tf` | DNS phone book: `agent-backend.platform-health.local` |
| Security Groups | `ecs.tf` | Firewalls: who can talk to whom |
| ALB | `alb.tf` | Internet gateway: routes paths to services |
| Target Groups | `alb.tf` | Health-checked pools of container IPs |
| Listener Rules | `alb.tf` | URL path → target group routing |

> **Next step:** In Step 14, we'll deploy everything with `terraform apply` and watch the magic happen! 🚀
