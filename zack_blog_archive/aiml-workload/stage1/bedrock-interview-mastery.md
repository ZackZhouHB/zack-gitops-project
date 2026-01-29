# Bedrock Mastery: Interview Readiness Checklist

> What you need to know to confidently answer scenario-based Bedrock questions

---

## What You've Covered Today ✅

| Topic | Depth | Confidence |
|-------|-------|------------|
| Foundation Model invocation | Deep | ✅ Can implement |
| Streaming responses | Deep | ✅ Can implement |
| Guardrails (PII, content) | Deep | ✅ Can implement |
| Cost tracking & optimization | Deep | ✅ Can implement |
| Model routing (Haiku vs Sonnet) | Deep | ✅ Can implement |
| Retry logic & rate limiting | Deep | ✅ Can implement |
| Knowledge Base architecture | Medium | ✅ Can explain |
| OpenSearch Serverless | Medium | ✅ Can explain costs/trade-offs |
| Managed vs Custom RAG | Deep | ✅ Can advise |

---

## What's Missing for Interview Mastery ⬜

### 1. Bedrock Agents (HIGH PRIORITY)

**Why it matters:** Agents are the "next level" of Bedrock - multi-step reasoning, tool use, autonomous actions. Interviewers WILL ask about this.

```
WHAT AGENTS DO:
User: "Book me a flight to Sydney under $500 next Tuesday"

Agent thinks:
├── Step 1: Search flights (calls Lambda)
├── Step 2: Check user's calendar (calls Lambda)
├── Step 3: Compare options (reasoning)
├── Step 4: Book best option (calls Lambda)
└── Returns: "Booked QF1 for $450, departing 9am"
```

**What you should know:**
- [ ] Agent architecture (orchestration, action groups, Lambda integration)
- [ ] When to use Agents vs simple RAG
- [ ] Session management (memory across turns)
- [ ] Guardrails integration with Agents
- [ ] Cost implications (multiple LLM calls per request)

**Interview question:** "When would you use Bedrock Agents vs Knowledge Base?"

**Your answer should include:**
- KB: Simple Q&A over documents
- Agents: Multi-step tasks, tool use, actions that change state
- Agents cost more (multiple LLM calls)
- Agents need careful error handling (what if a tool fails mid-flow?)

---

### 2. Prompt Engineering Best Practices (HIGH PRIORITY)

**Why it matters:** Every Bedrock implementation needs good prompts. This is foundational.

**What you should know:**
- [ ] System prompts vs user prompts
- [ ] Few-shot examples (when and how)
- [ ] Chain-of-thought prompting
- [ ] Output formatting (JSON mode, structured output)
- [ ] Prompt injection prevention
- [ ] Prompt versioning and A/B testing

**Interview question:** "How do you manage prompts in production?"

**Your answer should include:**
- Store prompts in S3 or Parameter Store (not hardcoded)
- Version prompts like code
- A/B test prompt variants
- Monitor prompt performance (latency, quality)
- Guardrails for prompt injection

---

### 3. Model Evaluation & Selection (MEDIUM PRIORITY)

**Why it matters:** Choosing the right model is a key decision. Interviewers want to see you can justify choices.

**What you should know:**
- [ ] Bedrock Model Evaluation feature
- [ ] Metrics: latency, cost, quality trade-offs
- [ ] When to use Claude vs Titan vs Llama vs Mistral
- [ ] Benchmarking methodology
- [ ] A/B testing models in production

**Interview question:** "How do you decide which model to use?"

**Your answer should include:**
- Start with task requirements (reasoning vs speed vs cost)
- Benchmark on YOUR data (not public benchmarks)
- Consider: latency, cost, context window, output quality
- Use Bedrock Model Evaluation for systematic comparison
- A/B test in production with real traffic

---

### 4. Security & Compliance (HIGH PRIORITY for Enterprise)

**Why it matters:** Enterprise customers care deeply about this. Shows you think beyond just "making it work."

**What you should know:**
- [ ] VPC endpoints for Bedrock (no public internet)
- [ ] IAM policies (least privilege for Bedrock access)
- [ ] KMS encryption (data at rest, in transit)
- [ ] CloudTrail logging (audit trail)
- [ ] Data residency (which regions, data sovereignty)
- [ ] Model invocation logging (what was sent/received)
- [ ] Guardrails for compliance (PII, PHI, financial data)

**Interview question:** "How do you secure a Bedrock deployment for a regulated industry?"

**Your answer should include:**
- VPC endpoints (traffic never leaves AWS network)
- IAM roles with least privilege
- Guardrails for PII/PHI filtering
- CloudTrail for audit logging
- Model invocation logging to S3 (for compliance review)
- Data residency considerations (keep data in-region)

---

### 5. Fine-tuning & Customization (LOW PRIORITY but good to know)

**Why it matters:** Shows you understand the full spectrum of customization options.

**What you should know:**
- [ ] When to fine-tune vs RAG vs prompt engineering
- [ ] Continued pre-training vs fine-tuning
- [ ] Cost of fine-tuning (expensive!)
- [ ] Data requirements for fine-tuning
- [ ] Model distillation (new feature)

**Interview question:** "When would you fine-tune vs use RAG?"

**Your answer should include:**
- RAG: Dynamic data, need citations, cost-sensitive
- Fine-tuning: Specific style/tone, domain terminology, no retrieval needed
- Fine-tuning is expensive ($$$) and needs lots of data
- Most use cases are better served by RAG + good prompts
- Fine-tuning doesn't add new knowledge (just style/behavior)

---

### 6. Observability & Monitoring (MEDIUM PRIORITY)

**Why it matters:** Production systems need monitoring. Shows operational maturity.

**What you should know:**
- [ ] CloudWatch metrics for Bedrock
- [ ] Custom metrics (tokens, cost, latency per request)
- [ ] Alerting on errors, latency spikes, cost anomalies
- [ ] Distributed tracing (X-Ray integration)
- [ ] Model performance monitoring (quality degradation)

**Interview question:** "How do you monitor a Bedrock application in production?"

**Your answer should include:**
- CloudWatch for operational metrics (latency, errors)
- Custom metrics for business metrics (cost per user, tokens per query)
- Alerts on: error rate > 1%, latency p99 > 5s, daily cost > threshold
- Log all invocations for debugging and audit
- Monitor for quality degradation (user feedback, automated evals)

---

### 7. Cost Optimization Strategies (HIGH PRIORITY)

**Why it matters:** LLM costs can explode. Showing cost awareness is impressive.

**What you should know:**
- [ ] Token-based pricing (input vs output costs)
- [ ] Model routing (cheap model for simple tasks)
- [ ] Caching strategies (semantic cache, exact match cache)
- [ ] Batch inference (50% cheaper for non-real-time)
- [ ] Provisioned throughput (when it makes sense)
- [ ] Prompt optimization (shorter prompts = lower cost)

**Interview question:** "How would you reduce Bedrock costs by 50%?"

**Your answer should include:**
- Model routing: Use Haiku for simple tasks (12x cheaper than Sonnet)
- Caching: Cache repeated queries (Redis/ElastiCache)
- Batch inference: For non-real-time workloads (50% cheaper)
- Prompt optimization: Shorter prompts, fewer examples
- Output limits: Set max_tokens appropriately
- Monitor and alert on cost anomalies

---

### 8. Multi-modal Capabilities (NICE TO KNOW)

**Why it matters:** Growing area, shows you're current.

**What you should know:**
- [ ] Claude Vision (image understanding)
- [ ] Titan Image Generator
- [ ] When to use multi-modal vs text-only
- [ ] Cost implications of image processing

---

## Scenario-Based Interview Questions

### Scenario 1: Design a Customer Support Bot

**Question:** "Design a customer support system using Bedrock for an e-commerce company."

**Strong answer includes:**
```
ARCHITECTURE:
├── Bedrock KB for product docs, FAQs, policies
├── Bedrock Agents for actions (check order, initiate return)
├── Guardrails for PII protection
├── Model routing: Haiku for FAQ, Sonnet for complex issues
├── Streaming for real-time chat UX
├── DynamoDB for conversation history
└── CloudWatch for monitoring

CONSIDERATIONS:
├── Cost: ~$X per 1000 conversations
├── Latency: Target < 3s for first response
├── Fallback: Escalate to human if confidence low
└── Security: VPC endpoints, no PII in logs
```

### Scenario 2: Reduce LLM Costs

**Question:** "Your team's Bedrock bill is $50K/month. How do you reduce it?"

**Strong answer includes:**
```
INVESTIGATION:
├── Analyze: Which models? Which features? Which users?
├── Find: 80% of calls are simple queries using Sonnet

SOLUTIONS:
├── Model routing: Route simple queries to Haiku (12x cheaper)
├── Caching: Implement semantic cache for repeated queries
├── Prompt optimization: Reduce prompt length by 30%
├── Batch inference: Move non-real-time to batch (50% cheaper)
├── Rate limiting: Prevent abuse/runaway scripts

EXPECTED SAVINGS:
├── Model routing: 40% reduction
├── Caching: 20% reduction
├── Combined: 50-60% reduction → $20-25K/month
```

### Scenario 3: Compliance Requirements

**Question:** "A healthcare company wants to use Bedrock. What do you recommend?"

**Strong answer includes:**
```
COMPLIANCE REQUIREMENTS:
├── HIPAA: PHI must be protected
├── Audit: All access must be logged
├── Data residency: May need to stay in specific region

ARCHITECTURE:
├── VPC endpoints: No public internet exposure
├── Guardrails: Block PHI in prompts and responses
├── CloudTrail: Audit all API calls
├── Model invocation logging: Log to S3 with encryption
├── IAM: Least privilege, role-based access
├── KMS: Encrypt all data at rest

ADDITIONAL:
├── BAA: Ensure AWS BAA covers Bedrock
├── Data handling: Don't use customer data for training
├── Review: Regular security audits
```

### Scenario 4: RAG Quality Issues

**Question:** "Users complain the RAG system gives wrong answers. How do you debug?"

**Strong answer includes:**
```
DEBUGGING STEPS:
├── 1. Check retrieval: Are the right chunks being retrieved?
│   └── Log retrieved chunks, check relevance scores
├── 2. Check chunking: Are chunks too small/large?
│   └── Review chunk boundaries, test different sizes
├── 3. Check embedding: Is semantic similarity working?
│   └── Test with known similar queries
├── 4. Check generation: Is the LLM using the context?
│   └── Review prompts, check for hallucination

SOLUTIONS:
├── Hybrid search: Add keyword search for exact matches
├── Re-ranking: Add cross-encoder for better precision
├── Evaluation: Build test set, measure retrieval metrics
├── Feedback loop: Collect user feedback, improve iteratively
```

---

## Study Plan: What to Do Next

### This Week (Before Interview)

| Priority | Topic | How to Learn |
|----------|-------|--------------|
| 🔴 High | Bedrock Agents | AWS docs + try in console |
| 🔴 High | Security best practices | AWS Well-Architected for GenAI |
| 🔴 High | Cost optimization | Review pricing, practice calculations |
| 🟡 Medium | Prompt engineering | Anthropic docs, practice |
| 🟡 Medium | Model evaluation | AWS docs |

### Resources

| Resource | URL | What You'll Learn |
|----------|-----|-------------------|
| AWS Bedrock User Guide | docs.aws.amazon.com/bedrock | Official documentation |
| AWS Well-Architected GenAI Lens | AWS docs | Best practices |
| Anthropic Prompt Engineering | docs.anthropic.com | Prompt techniques |
| AWS re:Invent Bedrock sessions | YouTube | Real-world patterns |

---

## Quick Reference: Bedrock Services Cheat Sheet

```
BEDROCK SERVICES:

INFERENCE:
├── InvokeModel: Sync call to FM
├── InvokeModelWithResponseStream: Streaming
├── Converse API: Multi-turn with tool use
└── Batch Inference: Async, 50% cheaper

KNOWLEDGE:
├── Knowledge Bases: Managed RAG
├── Data Sources: S3, Confluence, SharePoint, Web
└── Vector Stores: OpenSearch, Aurora, Pinecone, etc.

AGENTS:
├── Agents: Multi-step reasoning + actions
├── Action Groups: Lambda functions as tools
└── Knowledge Base integration: RAG within agents

CUSTOMIZATION:
├── Fine-tuning: Custom model training
├── Continued Pre-training: Domain adaptation
└── Model Distillation: Smaller custom models

SAFETY:
├── Guardrails: Content filtering, PII, topics
├── Model Invocation Logging: Audit trail
└── CloudTrail: API audit

EVALUATION:
├── Model Evaluation: Compare models
├── Human Evaluation: Manual review workflows
└── Automatic Evaluation: Metrics-based
```

---

## Your Interview Confidence Level

| Topic | Current | Target | Status |
|-------|---------|--------|--------|
| FM Invocation | ✅ High | High | ✅ Covered |
| Streaming | ✅ High | High | ✅ Covered |
| Guardrails | ✅ High | High | ✅ Covered |
| Cost Optimization | ✅ High | High | ✅ Covered |
| Knowledge Bases | ✅ Medium | High | ✅ Covered |
| **Agents** | ✅ High | High | ✅ Covered (bedrock-agents-deep-dive.md) |
| **Security** | ✅ High | High | ✅ Covered (bedrock-security-best-practices.md) |
| **Prompt Engineering** | ✅ High | High | ✅ Covered (prompt-engineering-guide.md) |
| Fine-tuning | ⚠️ Low | Medium | Read docs if time |
| Monitoring | ⚠️ Medium | High | Covered in security doc |

---

## Summary: Your Gaps - NOW FILLED ✅

**Completed today:**
1. ✅ **Bedrock Agents** - Architecture, ReAct pattern, when to use, cost implications
2. ✅ **Security best practices** - VPC, IAM, encryption, compliance, audit logging
3. ✅ **Prompt engineering** - Structure, few-shot, CoT, injection prevention, versioning

**Optional further reading:**
4. ⬜ Model evaluation methodology (AWS docs)
5. ⬜ Fine-tuning vs RAG decision framework (AWS docs)

---

## All Documents Created

```
stage1/
├── bedrock_client.py                      # Production Bedrock wrapper
├── bedrock_client_walkthrough.txt         # Code explanations
├── checklist.md                           # Learning path
├── production-patterns.md                 # 6 production features
├── bedrock-ecosystem.md                   # Full Bedrock map
├── case-study-cloud-engineer-rag.md       # Your project plan
├── your-data-vs-bedrock-kb-analysis.md    # Your data vs managed RAG
├── bedrock-interview-mastery.md           # This checklist
├── bedrock-agents-deep-dive.md            # ⭐ Agents architecture
├── bedrock-security-best-practices.md     # ⭐ Security guide
├── prompt-engineering-guide.md            # ⭐ Prompt techniques
├── bedrock-kb-demo/
│   └── opensearch-bedrock-deep-dive.md    # OpenSearch architecture
└── custom-rag/                            # Ready-to-run project
```

You are now interview-ready for Bedrock! 🎯
