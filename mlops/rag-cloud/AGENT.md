# RAG Cloud Agent Patterns

## Current Implementation

The cloud RAG has the same agent as local (`/agent` endpoint) with 5 tools:
- `search_docs` - RAG search via OpenSearch Serverless
- `list_sources` - List all documents
- `calculate` - Math operations
- `get_date` - Current date/time
- `compare_docs` - Compare documents

---

## AWS-Native Agent Options

### Option 1: Amazon Bedrock Agents (Recommended)

Fully managed agent service with built-in RAG integration:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BEDROCK AGENT                                    │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │  Knowledge Base  │  │  Action Group 1  │  │  Action Group 2  │      │
│  │  (OpenSearch)    │  │  (Lambda)        │  │  (Lambda)        │      │
│  │                  │  │                  │  │                  │      │
│  │  • Your docs     │  │  • Create ticket │  │  • Send email    │      │
│  │  • Auto-sync     │  │  • Query DB      │  │  • Call API      │      │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘      │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │                      GUARDRAILS                               │      │
│  │  • Content filtering  • PII redaction  • Topic blocking      │      │
│  └──────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
```

**Benefits:**
- No agent code to maintain
- Built-in guardrails
- Automatic RAG integration
- Tracing and versioning
- Pay per invocation

**Implementation:**
```python
# Invoke Bedrock Agent
response = bedrock_agent_runtime.invoke_agent(
    agentId="AGENT_ID",
    agentAliasId="ALIAS_ID",
    sessionId=session_id,
    inputText=user_query
)
```

### Option 2: Custom Agent on EKS (Current)

Self-managed agent with full control:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              EKS                                         │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      Backend Pod                                    │ │
│  │                                                                     │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │ │
│  │  │ RAG Service │  │   Agent     │  │   Tools     │                │ │
│  │  │             │  │  (ReAct)    │  │             │                │ │
│  │  │ • Search    │  │             │  │ • search    │                │ │
│  │  │ • Embed     │  │ • Plan      │  │ • calculate │                │ │
│  │  │ • Rerank    │  │ • Execute   │  │ • date      │                │ │
│  │  │             │  │ • Answer    │  │ • list      │                │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└──────┬──────────────────────────────────────────────────────────────────┘
       │
┌──────▼──────┐    ┌─────────────┐    ┌─────────────┐
│ OpenSearch  │    │   Bedrock   │    │   Lambda    │
│ Serverless  │    │   (LLM)     │    │  (Actions)  │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## Adding Action Groups (Lambda)

For enterprise use cases, add Lambda-based tools:

### Architecture

```
Agent → Invoke Lambda → External System → Response
```

### Example: Ticket Creation Tool

```python
# Lambda function: create_ticket
def handler(event, context):
    params = event['parameters']
    
    # Call ServiceNow/Jira API
    ticket = servicenow.create_incident(
        short_description=params['title'],
        description=params['description'],
        urgency=params.get('urgency', '3')
    )
    
    return {
        'ticket_id': ticket['sys_id'],
        'ticket_number': ticket['number']
    }
```

### Agent Tool Definition

```python
# In rag_agent.py
async def _create_ticket(self, title: str, description: str) -> str:
    """Create support ticket via Lambda"""
    response = lambda_client.invoke(
        FunctionName='rag-cloud-create-ticket',
        Payload=json.dumps({
            'parameters': {'title': title, 'description': description}
        })
    )
    result = json.loads(response['Payload'].read())
    return f"Created ticket: {result['ticket_number']}"
```

---

## Bedrock Agent Setup (Reference)

### 1. Create Knowledge Base

```bash
# Create OpenSearch Serverless collection (already have this)
# Create Knowledge Base pointing to it
aws bedrock-agent create-knowledge-base \
  --name "rag-cloud-kb" \
  --role-arn "arn:aws:iam::ACCOUNT:role/BedrockKBRole" \
  --knowledge-base-configuration '{
    "type": "VECTOR",
    "vectorKnowledgeBaseConfiguration": {
      "embeddingModelArn": "arn:aws:bedrock:ap-southeast-2::foundation-model/amazon.titan-embed-text-v2:0"
    }
  }' \
  --storage-configuration '{
    "type": "OPENSEARCH_SERVERLESS",
    "opensearchServerlessConfiguration": {
      "collectionArn": "arn:aws:aoss:ap-southeast-2:ACCOUNT:collection/xxx",
      "vectorIndexName": "documents",
      "fieldMapping": {
        "vectorField": "vector",
        "textField": "content",
        "metadataField": "metadata"
      }
    }
  }'
```

### 2. Create Agent

```bash
aws bedrock-agent create-agent \
  --agent-name "rag-cloud-agent" \
  --foundation-model "anthropic.claude-3-haiku-20240307-v1:0" \
  --instruction "You are a helpful assistant that answers questions using the knowledge base." \
  --agent-resource-role-arn "arn:aws:iam::ACCOUNT:role/BedrockAgentRole"
```

### 3. Associate Knowledge Base

```bash
aws bedrock-agent associate-agent-knowledge-base \
  --agent-id "AGENT_ID" \
  --knowledge-base-id "KB_ID" \
  --description "RAG Cloud documents"
```

### 4. Create Action Group (Optional)

```bash
aws bedrock-agent create-agent-action-group \
  --agent-id "AGENT_ID" \
  --action-group-name "TicketActions" \
  --action-group-executor '{
    "lambda": "arn:aws:lambda:ap-southeast-2:ACCOUNT:function:create-ticket"
  }' \
  --api-schema '{
    "s3": {
      "s3BucketName": "rag-cloud-schemas",
      "s3ObjectKey": "ticket-api.json"
    }
  }'
```

---

## Cost Comparison

| Approach | Monthly Cost | Pros | Cons |
|----------|--------------|------|------|
| **Custom (EKS)** | ~$0 extra | Full control, no limits | Maintain code |
| **Bedrock Agent** | ~$5-50 | Managed, guardrails | Less flexibility |
| **Bedrock + Actions** | ~$10-100 | Full features | Lambda costs |

---

## Testing (Current Implementation)

```bash
# Get ALB URL
ALB_URL="http://$(kubectl get ingress -n rag backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"
TOKEN=$(curl -s -X POST "$ALB_URL/auth/login" -H "Content-Type: application/json" -d '{"username":"admin"}' | jq -r '.token')

# Test agent
curl -s -X POST "$ALB_URL/agent" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is todays date?"}' | jq .

curl -s -X POST "$ALB_URL/agent" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Calculate 100 * 5"}' | jq .

curl -s -X POST "$ALB_URL/agent" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "List all documents"}' | jq .
```

---

## Summary

| Feature | Current | Bedrock Agent |
|---------|---------|---------------|
| RAG Search | ✅ OpenSearch | ✅ Knowledge Base |
| Custom Tools | ✅ 5 tools | ✅ Action Groups |
| Guardrails | ❌ Manual | ✅ Built-in |
| Multi-step | ✅ ReAct | ✅ Native |
| Managed | ❌ Self | ✅ AWS |
| Cost | EKS only | Per invocation |
