# Bedrock Security Best Practices

> Enterprise security, compliance, and governance for Bedrock deployments

---

## Security Layers Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        BEDROCK SECURITY LAYERS                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   LAYER 1: NETWORK                                                              │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  VPC Endpoints ──▶ Traffic never leaves AWS network                     │   │
│   │  Security Groups ──▶ Control inbound/outbound                           │   │
│   │  NACLs ──▶ Subnet-level filtering                                       │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│   LAYER 2: IDENTITY & ACCESS                                                    │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  IAM Policies ──▶ Who can call which Bedrock APIs                       │   │
│   │  IAM Roles ──▶ Service-to-service access                                │   │
│   │  Resource Policies ──▶ Cross-account access control                     │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│   LAYER 3: DATA PROTECTION                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  KMS Encryption ──▶ Data at rest                                        │   │
│   │  TLS ──▶ Data in transit                                                │   │
│   │  Guardrails ──▶ PII/PHI filtering                                       │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│   LAYER 4: AUDIT & MONITORING                                                   │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │  CloudTrail ──▶ API call logging                                        │   │
│   │  Model Invocation Logging ──▶ Prompt/response logging                   │   │
│   │  CloudWatch ──▶ Metrics and alarms                                      │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Layer 1: Network Security

### VPC Endpoints (Critical for Enterprise)

**Why VPC Endpoints?**
```
WITHOUT VPC ENDPOINT:
┌─────────┐     Internet      ┌─────────────┐
│ Your    │ ───────────────▶  │   Bedrock   │
│ VPC     │   (public)        │   Service   │
└─────────┘                   └─────────────┘
❌ Traffic goes over public internet
❌ Potential exposure
❌ Compliance risk

WITH VPC ENDPOINT:
┌─────────┐     AWS Network   ┌─────────────┐
│ Your    │ ───────────────▶  │   Bedrock   │
│ VPC     │   (private)       │   Service   │
└─────────┘                   └─────────────┘
✅ Traffic stays within AWS
✅ No internet exposure
✅ Compliance friendly
```

**Setting Up VPC Endpoint:**
```bash
# Create VPC endpoint for Bedrock Runtime
aws ec2 create-vpc-endpoint \
    --vpc-id vpc-xxx \
    --service-name com.amazonaws.ap-southeast-2.bedrock-runtime \
    --vpc-endpoint-type Interface \
    --subnet-ids subnet-xxx subnet-yyy \
    --security-group-ids sg-xxx \
    --private-dns-enabled
```

**Required Endpoints for Full Bedrock:**
| Endpoint | Service | When Needed |
|----------|---------|-------------|
| `bedrock-runtime` | Model invocation | Always |
| `bedrock` | Management APIs | Creating KB, Agents |
| `bedrock-agent-runtime` | Agent invocation | Using Agents |
| `s3` | Data access | KB with S3 source |

### Security Group Configuration

```
INBOUND RULES (for VPC endpoint):
┌──────────┬──────────┬─────────────────────────────┐
│ Protocol │ Port     │ Source                      │
├──────────┼──────────┼─────────────────────────────┤
│ HTTPS    │ 443      │ Application security group  │
└──────────┴──────────┴─────────────────────────────┘

OUTBOUND RULES (for application):
┌──────────┬──────────┬─────────────────────────────┐
│ Protocol │ Port     │ Destination                 │
├──────────┼──────────┼─────────────────────────────┤
│ HTTPS    │ 443      │ VPC endpoint security group │
└──────────┴──────────┴─────────────────────────────┘
```

---

## Layer 2: Identity & Access Management

### IAM Policy: Least Privilege

**❌ BAD: Overly Permissive**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "bedrock:*",
            "Resource": "*"
        }
    ]
}
```

**✅ GOOD: Least Privilege**
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowSpecificModelInvocation",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:ap-southeast-2::foundation-model/anthropic.claude-3-haiku*",
                "arn:aws:bedrock:ap-southeast-2::foundation-model/anthropic.claude-3-5-sonnet*"
            ]
        },
        {
            "Sid": "AllowGuardrailUse",
            "Effect": "Allow",
            "Action": [
                "bedrock:ApplyGuardrail"
            ],
            "Resource": [
                "arn:aws:bedrock:ap-southeast-2:ACCOUNT_ID:guardrail/GUARDRAIL_ID"
            ]
        }
    ]
}
```

### IAM Policies by Use Case

| Use Case | Required Permissions |
|----------|---------------------|
| **Invoke models only** | `bedrock:InvokeModel`, `bedrock:InvokeModelWithResponseStream` |
| **Use Knowledge Base** | Above + `bedrock:Retrieve`, `bedrock:RetrieveAndGenerate` |
| **Use Agents** | Above + `bedrock:InvokeAgent` |
| **Create/manage KB** | `bedrock:CreateKnowledgeBase`, `bedrock:UpdateKnowledgeBase`, etc. |
| **Create guardrails** | `bedrock:CreateGuardrail`, `bedrock:UpdateGuardrail`, etc. |

### Service-Linked Roles

```
BEDROCK KNOWLEDGE BASE ROLE:
├── Trust: bedrock.amazonaws.com
├── Permissions:
│   ├── s3:GetObject (for data source)
│   ├── bedrock:InvokeModel (for embeddings)
│   └── aoss:* or rds:* (for vector store)
└── Condition: Restrict to specific KB ARN

BEDROCK AGENT ROLE:
├── Trust: bedrock.amazonaws.com
├── Permissions:
│   ├── bedrock:InvokeModel
│   ├── lambda:InvokeFunction (for action groups)
│   └── bedrock:Retrieve (if using KB)
└── Condition: Restrict to specific Agent ARN
```

---

## Layer 3: Data Protection

### Encryption at Rest

```
WHAT'S ENCRYPTED:
├── Knowledge Base data (in vector store)
├── Fine-tuned model artifacts
├── Agent configurations
└── Guardrail configurations

HOW:
├── Default: AWS managed keys
├── Recommended: Customer managed KMS keys (CMK)
└── Benefit: You control key rotation, access policies
```

**Using Customer Managed Key:**
```bash
# Create KMS key for Bedrock
aws kms create-key \
    --description "Bedrock encryption key" \
    --key-usage ENCRYPT_DECRYPT

# Create Knowledge Base with CMK
aws bedrock-agent create-knowledge-base \
    --name "secure-kb" \
    --role-arn "arn:aws:iam::xxx:role/BedrockKBRole" \
    --knowledge-base-configuration '...' \
    --storage-configuration '...' \
    --server-side-encryption-configuration '{
        "kmsKeyArn": "arn:aws:kms:ap-southeast-2:xxx:key/xxx"
    }'
```

### Encryption in Transit

```
AUTOMATIC:
├── All Bedrock API calls use TLS 1.2+
├── VPC endpoint traffic is encrypted
└── No configuration needed

VERIFY:
├── Ensure clients don't disable TLS verification
├── Use latest AWS SDK versions
└── Monitor for TLS errors in logs
```

### Guardrails for Data Protection

**PII Filtering Configuration:**
```json
{
    "name": "enterprise-guardrail",
    "sensitiveInformationPolicyConfig": {
        "piiEntitiesConfig": [
            {"type": "EMAIL", "action": "ANONYMIZE"},
            {"type": "PHONE", "action": "ANONYMIZE"},
            {"type": "NAME", "action": "ANONYMIZE"},
            {"type": "SSN", "action": "BLOCK"},
            {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "BLOCK"},
            {"type": "AWS_ACCESS_KEY", "action": "BLOCK"},
            {"type": "AWS_SECRET_KEY", "action": "BLOCK"}
        ],
        "regexesConfig": [
            {
                "name": "InternalProjectCode",
                "pattern": "PROJ-[A-Z]{3}-[0-9]{4}",
                "action": "ANONYMIZE"
            }
        ]
    },
    "contentPolicyConfig": {
        "filtersConfig": [
            {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
            {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
            {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
            {"type": "INSULTS", "inputStrength": "MEDIUM", "outputStrength": "MEDIUM"}
        ]
    },
    "topicPolicyConfig": {
        "topicsConfig": [
            {
                "name": "CompetitorDiscussion",
                "definition": "Discussion about competitor products or strategies",
                "examples": ["What does competitor X offer?", "Compare us to competitor Y"],
                "type": "DENY"
            }
        ]
    }
}
```

---

## Layer 4: Audit & Monitoring

### CloudTrail (API Logging)

**What CloudTrail Captures:**
```
LOGGED EVENTS:
├── InvokeModel calls (who, when, which model)
├── CreateKnowledgeBase
├── CreateGuardrail
├── InvokeAgent
└── All management API calls

NOT LOGGED BY DEFAULT:
├── Actual prompt content
├── Model responses
└── Retrieved documents
```

**Enable CloudTrail for Bedrock:**
```bash
# CloudTrail is usually already enabled
# Verify Bedrock events are captured
aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventSource,AttributeValue=bedrock.amazonaws.com \
    --max-results 10
```

### Model Invocation Logging (Critical for Compliance)

**What It Captures:**
```
WITH INVOCATION LOGGING:
├── Full prompt text
├── Full response text
├── Model ID
├── Token counts
├── Timestamp
└── Request ID

STORAGE:
├── S3 bucket (you control)
├── CloudWatch Logs (optional)
└── Encrypted with KMS
```

**Enable Model Invocation Logging:**
```bash
aws bedrock put-model-invocation-logging-configuration \
    --logging-config '{
        "cloudWatchConfig": {
            "logGroupName": "/aws/bedrock/invocations",
            "roleArn": "arn:aws:iam::xxx:role/BedrockLoggingRole",
            "largeDataDeliveryS3Config": {
                "bucketName": "bedrock-logs-xxx",
                "keyPrefix": "large-payloads/"
            }
        },
        "s3Config": {
            "bucketName": "bedrock-logs-xxx",
            "keyPrefix": "invocations/"
        },
        "textDataDeliveryEnabled": true,
        "imageDataDeliveryEnabled": true,
        "embeddingDataDeliveryEnabled": false
    }'
```

**Log Format Example:**
```json
{
    "schemaType": "ModelInvocationLog",
    "schemaVersion": "1.0",
    "timestamp": "2024-01-15T10:30:00Z",
    "accountId": "123456789012",
    "identity": {
        "arn": "arn:aws:iam::123456789012:role/AppRole"
    },
    "region": "ap-southeast-2",
    "requestId": "abc-123",
    "operation": "InvokeModel",
    "modelId": "anthropic.claude-3-haiku-20240307-v1:0",
    "input": {
        "inputContentType": "application/json",
        "inputBodyJson": {
            "messages": [{"role": "user", "content": "What is AWS?"}]
        },
        "inputTokenCount": 10
    },
    "output": {
        "outputContentType": "application/json",
        "outputBodyJson": {
            "content": [{"text": "AWS is..."}]
        },
        "outputTokenCount": 50
    }
}
```

### CloudWatch Metrics & Alarms

**Key Metrics to Monitor:**
| Metric | Alarm Threshold | Why |
|--------|-----------------|-----|
| `InvocationLatency` | p99 > 10s | Performance degradation |
| `InvocationClientErrors` | > 10/min | Bad requests, auth issues |
| `InvocationServerErrors` | > 1/min | Service issues |
| `InvocationThrottles` | > 5/min | Hitting rate limits |

**Create Alarm:**
```bash
aws cloudwatch put-metric-alarm \
    --alarm-name "Bedrock-HighLatency" \
    --metric-name "InvocationLatency" \
    --namespace "AWS/Bedrock" \
    --statistic "p99" \
    --period 300 \
    --threshold 10000 \
    --comparison-operator "GreaterThanThreshold" \
    --evaluation-periods 2 \
    --alarm-actions "arn:aws:sns:ap-southeast-2:xxx:alerts"
```

---

## Compliance Frameworks

### HIPAA (Healthcare)

```
REQUIREMENTS:
├── BAA: AWS BAA must cover Bedrock
├── PHI Protection: Use Guardrails to filter PHI
├── Audit: Enable model invocation logging
├── Encryption: Use CMK for all data
├── Access: Strict IAM, MFA required
└── Network: VPC endpoints only

IMPLEMENTATION:
├── ✅ Guardrails with PHI entity types
├── ✅ Model invocation logging to encrypted S3
├── ✅ VPC endpoints (no public internet)
├── ✅ IAM policies with MFA condition
└── ✅ CloudTrail for API audit
```

### SOC 2

```
REQUIREMENTS:
├── Access Control: IAM least privilege
├── Audit Logging: CloudTrail + invocation logs
├── Encryption: At rest and in transit
├── Monitoring: CloudWatch alarms
└── Incident Response: Documented procedures

IMPLEMENTATION:
├── ✅ IAM policies per service/user
├── ✅ CloudTrail enabled, logs to S3
├── ✅ KMS encryption for all data
├── ✅ CloudWatch dashboards and alarms
└── ✅ Runbooks for security incidents
```

### GDPR (Data Privacy)

```
REQUIREMENTS:
├── Data Residency: Keep data in EU if required
├── Right to Erasure: Ability to delete user data
├── Consent: User consent for AI processing
├── Transparency: Explain AI decision-making
└── Data Minimization: Don't store more than needed

IMPLEMENTATION:
├── ✅ Use EU region (eu-west-1, etc.)
├── ✅ Don't persist prompts/responses (or have deletion process)
├── ✅ Guardrails to prevent PII in responses
├── ✅ Document AI usage in privacy policy
└── ✅ Minimal logging (or anonymize logs)
```

---

## Security Architecture Patterns

### Pattern 1: Basic Secure Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                         YOUR VPC                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────┐         ┌─────────────┐                       │
│   │ Application │────────▶│ VPC Endpoint│──────▶ Bedrock        │
│   │   (Lambda)  │         │  (bedrock)  │                       │
│   └─────────────┘         └─────────────┘                       │
│         │                                                       │
│         │ IAM Role                                              │
│         │ (least privilege)                                     │
│         │                                                       │
│         ▼                                                       │
│   ┌─────────────┐                                               │
│   │ CloudWatch  │                                               │
│   │   Logs      │                                               │
│   └─────────────┘                                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Pattern 2: Enterprise Secure Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                      ENTERPRISE VPC                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    PRIVATE SUBNET                       │   │
│   │                                                         │   │
│   │   ┌─────────────┐         ┌─────────────┐               │   │
│   │   │ Application │────────▶│ VPC Endpoint│               │   │
│   │   │   (ECS)     │         │  (bedrock)  │               │   │
│   │   └──────┬──────┘         └─────────────┘               │   │
│   │          │                       │                      │   │
│   │          │                       │                      │   │
│   │   ┌──────▼──────┐         ┌──────▼──────┐               │   │
│   │   │  Guardrail  │         │   Bedrock   │               │   │
│   │   │  (applied)  │         │   Service   │               │   │
│   │   └─────────────┘         └─────────────┘               │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐   │
│   │                    LOGGING SUBNET                       │   │
│   │                                                         │   │
│   │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │   │
│   │   │ CloudTrail  │    │ Invocation  │    │ CloudWatch  │ │   │
│   │   │   Logs      │    │   Logs      │    │   Metrics   │ │   │
│   │   └──────┬──────┘    └──────┬──────┘    └──────┬──────┘ │   │
│   │          │                  │                  │        │   │
│   │          └──────────────────┼──────────────────┘        │   │
│   │                             │                           │   │
│   │                      ┌──────▼──────┐                    │   │
│   │                      │  S3 Bucket  │                    │   │
│   │                      │ (encrypted) │                    │   │
│   │                      └─────────────┘                    │   │
│   │                                                         │   │
│   └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Security Checklist

### Pre-Production Checklist

| Category | Item | Status |
|----------|------|--------|
| **Network** | VPC endpoints configured | ⬜ |
| **Network** | Security groups restrict access | ⬜ |
| **Network** | No public internet access to Bedrock | ⬜ |
| **IAM** | Least privilege policies | ⬜ |
| **IAM** | Service roles properly scoped | ⬜ |
| **IAM** | MFA required for console access | ⬜ |
| **Encryption** | KMS CMK for sensitive data | ⬜ |
| **Encryption** | TLS 1.2+ enforced | ⬜ |
| **Guardrails** | PII filtering enabled | ⬜ |
| **Guardrails** | Content filtering configured | ⬜ |
| **Logging** | CloudTrail enabled | ⬜ |
| **Logging** | Model invocation logging enabled | ⬜ |
| **Logging** | Logs encrypted and retained | ⬜ |
| **Monitoring** | CloudWatch alarms configured | ⬜ |
| **Monitoring** | Error rate alerts | ⬜ |
| **Monitoring** | Cost alerts | ⬜ |

---

## Interview Questions & Answers

### Q1: "How do you secure a Bedrock deployment?"

**Answer:**
> "I approach Bedrock security in four layers:
>
> 1. **Network**: VPC endpoints so traffic never goes over public internet. Security groups to restrict access to only authorized services.
>
> 2. **Identity**: IAM policies with least privilege - only allow specific models and actions needed. Use IAM roles for services, not access keys.
>
> 3. **Data**: Guardrails to filter PII and sensitive content. KMS encryption for data at rest. TLS for data in transit.
>
> 4. **Audit**: CloudTrail for API logging, model invocation logging for prompt/response audit trail. CloudWatch alarms for anomaly detection.
>
> For regulated industries, I'd also ensure compliance requirements are met - like HIPAA BAA coverage, data residency, and retention policies."

### Q2: "How do you prevent sensitive data from being sent to or returned from Bedrock?"

**Answer:**
> "Multiple layers of protection:
>
> 1. **Guardrails**: Configure PII entity detection to BLOCK or ANONYMIZE sensitive data types like SSN, credit cards, and PHI.
>
> 2. **Input validation**: Application layer validates and sanitizes input before sending to Bedrock.
>
> 3. **Custom regex**: Add regex patterns in Guardrails for company-specific sensitive data patterns.
>
> 4. **Output filtering**: Guardrails also filter responses, so even if the model generates sensitive content, it's blocked.
>
> 5. **Logging controls**: If logging prompts/responses, ensure logs are encrypted and access is restricted."

### Q3: "How do you audit Bedrock usage for compliance?"

**Answer:**
> "Three levels of auditing:
>
> 1. **CloudTrail**: Captures all API calls - who called what, when, from where. Good for access auditing.
>
> 2. **Model Invocation Logging**: Captures actual prompts and responses. Essential for content auditing and compliance review. Logs go to S3 with encryption.
>
> 3. **Application logging**: Our application logs business context - which user, which feature, what purpose. Links to Bedrock request IDs.
>
> For compliance, we retain logs according to policy, restrict access to auditors, and have automated alerts for suspicious patterns."

---

## Summary

```
BEDROCK SECURITY ESSENTIALS:

NETWORK:
├── VPC endpoints (no public internet)
├── Security groups (least privilege)
└── Private subnets for applications

IDENTITY:
├── IAM least privilege
├── Specific model ARNs in policies
├── Service roles for automation
└── MFA for human access

DATA PROTECTION:
├── Guardrails (PII, content filtering)
├── KMS encryption (CMK recommended)
├── TLS in transit (automatic)
└── Input/output validation

AUDIT:
├── CloudTrail (API logging)
├── Model invocation logging (content)
├── CloudWatch (metrics/alarms)
└── Retention policies

COMPLIANCE:
├── HIPAA: BAA, PHI filtering, audit logs
├── SOC 2: Access control, encryption, monitoring
├── GDPR: Data residency, erasure, consent
└── Document everything
```
