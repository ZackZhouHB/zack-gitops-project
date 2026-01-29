# Bedrock Agents: Deep Dive

> Multi-step reasoning, tool use, and autonomous actions

---

## What Are Bedrock Agents?

### The Problem Agents Solve

```
KNOWLEDGE BASE (what we covered):
├── User asks question
├── Retrieve relevant docs
├── Generate answer
└── Done (single step)

AGENTS (what we're covering now):
├── User asks complex request
├── Agent THINKS about what to do
├── Agent CALLS tools (Lambda, APIs)
├── Agent REASONS about results
├── Agent may CALL MORE tools
├── Agent synthesizes final answer
└── Done (multi-step, autonomous)
```

### Real-World Example

```
USER: "Check if we have the blue widget in stock, and if so, 
       create an order for 10 units for customer ACME Corp"

AGENT EXECUTION:
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: THINK                                                   │
│ "I need to check inventory first, then create order if in stock"│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: ACTION - Call inventory_check tool                      │
│ Input: {"product": "blue widget"}                               │
│ Output: {"in_stock": true, "quantity": 150}                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: THINK                                                   │
│ "In stock with 150 units. Can fulfill order for 10. Proceeding."│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 4: ACTION - Call create_order tool                         │
│ Input: {"customer": "ACME Corp", "product": "blue widget",      │
│         "quantity": 10}                                         │
│ Output: {"order_id": "ORD-12345", "status": "created"}          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ Step 5: RESPOND                                                 │
│ "I've checked inventory and confirmed 150 blue widgets are      │
│  available. I've created order ORD-12345 for 10 units for       │
│  ACME Corp. The order status is 'created'."                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           BEDROCK AGENT ARCHITECTURE                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                              AGENT                                      │   │
│   │                                                                         │   │
│   │   ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐     │   │
│   │   │ INSTRUCTION │    │    LLM      │    │     ACTION GROUPS       │     │   │
│   │   │   (system   │    │  (Claude/   │    │                         │     │   │
│   │   │   prompt)   │    │   Titan)    │    │  ┌─────────────────┐    │     │   │
│   │   │             │    │             │    │  │ Action Group 1  │    │     │   │
│   │   │ "You are a  │───▶│  Reasoning  │───▶│  │ - Lambda func   │    │     │   │
│   │   │  helpful    │    │  & Planning │    │  │ - API schema    │    │     │   │
│   │   │  assistant" │    │             │    │  └─────────────────┘    │     │   │
│   │   │             │    │             │    │  ┌─────────────────┐    │     │   │
│   │   └─────────────┘    └─────────────┘    │  │ Action Group 2  │    │     │   │
│   │                                         │  │ - Lambda func   │    │     │   │
│   │                                         │  │ - API schema    │    │     │   │
│   │                                         │  └─────────────────┘    │     │   │
│   │                                         └─────────────────────────┘     │   │
│   │                                                                         │   │
│   │   ┌─────────────────────────────────────────────────────────────────┐   │   │
│   │   │                    KNOWLEDGE BASES (optional)                   │   │   │
│   │   │                                                                 │   │   │
│   │   │   Agent can query KB for information during reasoning          │   │   │
│   │   │                                                                 │   │   │
│   │   └─────────────────────────────────────────────────────────────────┘   │   │
│   │                                                                         │   │
│   │   ┌─────────────────────────────────────────────────────────────────┐   │   │
│   │   │                      GUARDRAILS (optional)                      │   │   │
│   │   │                                                                 │   │   │
│   │   │   Filter inputs/outputs for safety and compliance              │   │   │
│   │   │                                                                 │   │   │
│   │   └─────────────────────────────────────────────────────────────────┘   │   │
│   │                                                                         │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Components

### 1. Agent Instructions (System Prompt)

```
PURPOSE: Define the agent's persona, capabilities, and constraints

EXAMPLE:
"You are a helpful IT support assistant for Acme Corp. You can:
- Check the status of support tickets
- Create new tickets
- Reset user passwords
- Check system status

Always verify the user's identity before performing sensitive actions.
Never share information about other users' tickets.
If you're unsure, ask for clarification."
```

### 2. Action Groups (Tools)

```
PURPOSE: Define what actions the agent can take

COMPONENTS:
├── Name: "TicketManagement"
├── Description: "Actions for managing support tickets"
├── Lambda Function: arn:aws:lambda:...:ticket-actions
└── API Schema: OpenAPI spec defining available operations

EXAMPLE API SCHEMA:
{
  "openapi": "3.0.0",
  "paths": {
    "/tickets/{ticketId}": {
      "get": {
        "operationId": "getTicket",
        "description": "Get details of a support ticket",
        "parameters": [
          {
            "name": "ticketId",
            "in": "path",
            "required": true,
            "schema": {"type": "string"}
          }
        ]
      }
    },
    "/tickets": {
      "post": {
        "operationId": "createTicket",
        "description": "Create a new support ticket",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "title": {"type": "string"},
                  "description": {"type": "string"},
                  "priority": {"type": "string", "enum": ["low", "medium", "high"]}
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### 3. Knowledge Base Integration

```
PURPOSE: Give agent access to documents for RAG within reasoning

USE CASE:
├── User: "What's the process for requesting a new laptop?"
├── Agent: Queries KB for "laptop request process"
├── Agent: Gets policy document
└── Agent: Answers based on policy + can create ticket if needed
```

---

## Agent Execution Flow (ReAct Pattern)

```
ReAct = Reasoning + Acting

┌─────────────────────────────────────────────────────────────────┐
│                        ReAct LOOP                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   USER INPUT                                                    │
│       │                                                         │
│       ▼                                                         │
│   ┌───────────────────────────────────────────────────────┐     │
│   │ THOUGHT: What do I need to do?                        │     │
│   │ "User wants to check order status. I need order ID."  │     │
│   └───────────────────────────────────────────────────────┘     │
│       │                                                         │
│       ▼                                                         │
│   ┌───────────────────────────────────────────────────────┐     │
│   │ ACTION: Call a tool                                   │     │
│   │ Tool: get_order_status                                │     │
│   │ Input: {"order_id": "ORD-123"}                        │     │
│   └───────────────────────────────────────────────────────┘     │
│       │                                                         │
│       ▼                                                         │
│   ┌───────────────────────────────────────────────────────┐     │
│   │ OBSERVATION: Tool result                              │     │
│   │ {"status": "shipped", "tracking": "1Z999..."}         │     │
│   └───────────────────────────────────────────────────────┘     │
│       │                                                         │
│       ▼                                                         │
│   ┌───────────────────────────────────────────────────────┐     │
│   │ THOUGHT: Do I have enough info to answer?             │     │
│   │ "Yes, I have the status and tracking number."         │     │
│   └───────────────────────────────────────────────────────┘     │
│       │                                                         │
│       ▼                                                         │
│   FINAL RESPONSE                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## When to Use Agents vs Knowledge Base

| Scenario | Use KB | Use Agent | Why |
|----------|--------|-----------|-----|
| "What's our refund policy?" | ✅ | | Simple doc lookup |
| "Process a refund for order 123" | | ✅ | Needs action |
| "How do I reset my password?" | ✅ | | Doc lookup |
| "Reset my password" | | ✅ | Needs action |
| "What were our Q3 sales?" | ✅ | | Doc lookup |
| "Compare Q3 sales to Q2 and create a report" | | ✅ | Multi-step + action |
| "Find documents about Project X" | ✅ | | Search |
| "Find docs about Project X and schedule a meeting with the team" | | ✅ | Search + action |

### Decision Framework

```
START
  │
  ▼
Does the request require CHANGING state?
(create, update, delete, send, book, etc.)
  │
  ├── YES ──▶ Use AGENT
  │
  └── NO ───▶ Does it require MULTIPLE steps?
                │
                ├── YES ──▶ Use AGENT
                │
                └── NO ───▶ Use KNOWLEDGE BASE
```

---

## Cost Implications

### Agent Costs More Than KB

```
KNOWLEDGE BASE QUERY:
├── 1 embedding call (query)
├── 1 LLM call (generate answer)
└── Total: ~$0.005 per query

AGENT QUERY (simple):
├── 1 LLM call (initial reasoning)
├── 1 Lambda invocation
├── 1 LLM call (process result)
└── Total: ~$0.01-0.02 per query

AGENT QUERY (complex, 5 steps):
├── 5 LLM calls (reasoning at each step)
├── 3 Lambda invocations
├── 1 KB query (if integrated)
└── Total: ~$0.05-0.10 per query
```

### Cost Control Strategies

| Strategy | How |
|----------|-----|
| **Limit iterations** | Set max steps (e.g., 5) |
| **Use cheaper model** | Haiku for simple agents |
| **Cache common paths** | If same request pattern, cache result |
| **Validate before action** | Confirm with user before expensive operations |

---

## Session Management

### Stateless vs Stateful

```
STATELESS (default):
├── Each request is independent
├── No memory of previous turns
└── User must provide all context each time

STATEFUL (with session):
├── Agent remembers conversation history
├── Can reference previous turns
└── Better for multi-turn interactions

EXAMPLE:
Turn 1: "Check my order status" → "Order ORD-123 is shipped"
Turn 2: "When will it arrive?" → Agent remembers we're talking about ORD-123
```

### Session Implementation

```python
# Invoke agent with session
response = bedrock_agent_runtime.invoke_agent(
    agentId="AGENT_ID",
    agentAliasId="ALIAS_ID",
    sessionId="user-123-session",  # Same session ID = same conversation
    inputText="When will it arrive?"
)
```

---

## Error Handling

### What Can Go Wrong

| Error | Cause | Handling |
|-------|-------|----------|
| **Lambda timeout** | Tool takes too long | Set appropriate timeout, add retry |
| **Lambda error** | Tool fails | Agent should gracefully handle, inform user |
| **Max iterations** | Agent stuck in loop | Set limit, return partial result |
| **Guardrail block** | Content filtered | Return safe message |
| **Model error** | LLM issue | Retry with backoff |

### Best Practice: Defensive Tool Design

```python
# Lambda function for agent action
def lambda_handler(event, context):
    try:
        # Parse agent request
        action = event.get('actionGroup')
        function = event.get('function')
        parameters = event.get('parameters', [])
        
        # Execute action
        result = execute_action(function, parameters)
        
        # Return success
        return {
            'response': {
                'actionGroup': action,
                'function': function,
                'functionResponse': {
                    'responseBody': {
                        'TEXT': {'body': json.dumps(result)}
                    }
                }
            }
        }
    except Exception as e:
        # Return error gracefully (agent will see this)
        return {
            'response': {
                'actionGroup': action,
                'function': function,
                'functionResponse': {
                    'responseBody': {
                        'TEXT': {'body': json.dumps({
                            'error': str(e),
                            'message': 'Action failed, please try again'
                        })}
                    }
                }
            }
        }
```

---

## Real-World Use Cases

### 1. IT Helpdesk Agent

```
CAPABILITIES:
├── Check ticket status
├── Create new tickets
├── Reset passwords (with verification)
├── Check system status
├── Query KB for troubleshooting guides
└── Escalate to human

EXAMPLE FLOW:
User: "My laptop won't connect to VPN"
Agent: Queries KB for VPN troubleshooting
Agent: "Have you tried restarting the VPN client?"
User: "Yes, still not working"
Agent: Creates ticket, returns ticket number
Agent: "I've created ticket INC-456. IT will contact you within 2 hours."
```

### 2. Order Management Agent

```
CAPABILITIES:
├── Check order status
├── Modify orders (before shipping)
├── Process returns
├── Apply discounts (with limits)
├── Query KB for policies
└── Escalate complex issues

GUARDRAILS:
├── Can only access user's own orders
├── Discount limit: 20% max
├── Cannot cancel shipped orders
└── Must verify identity for refunds
```

### 3. Data Analysis Agent

```
CAPABILITIES:
├── Query databases (Athena)
├── Generate reports
├── Create visualizations
├── Schedule recurring reports
├── Query KB for metric definitions
└── Send reports via email

EXAMPLE:
User: "Show me sales by region for Q3, compare to Q2"
Agent: Queries Athena for Q3 data
Agent: Queries Athena for Q2 data
Agent: Calculates comparison
Agent: Generates summary with insights
```

---

## Interview Questions & Answers

### Q1: "When would you use Bedrock Agents vs Knowledge Base?"

**Answer:**
> "Knowledge Base is for information retrieval - answering questions from documents. Agents are for tasks that require actions or multi-step reasoning.
>
> Use KB when: user asks 'what is X?' or 'how do I do Y?' - pure information lookup.
>
> Use Agents when: user asks 'do X for me' or the task requires multiple steps, calling APIs, or changing state in systems.
>
> Agents cost more because they make multiple LLM calls per request, so I'd only use them when the task genuinely requires action or complex reasoning."

### Q2: "How do you handle errors in Agent workflows?"

**Answer:**
> "Three levels of error handling:
>
> 1. **Tool level**: Lambda functions return graceful error messages that the agent can understand and communicate to users.
>
> 2. **Agent level**: Set max iterations to prevent infinite loops. Use guardrails to catch problematic content.
>
> 3. **Application level**: Wrap agent invocations in try/catch, implement retry with backoff, have fallback to human escalation.
>
> The key is that errors should result in helpful messages to users, not cryptic failures."

### Q3: "How do you secure an Agent that can take actions?"

**Answer:**
> "Several layers:
>
> 1. **IAM**: Agent's execution role has least-privilege access to only the Lambda functions it needs.
>
> 2. **Lambda permissions**: Each Lambda function validates inputs and has its own least-privilege role.
>
> 3. **Guardrails**: Filter sensitive content in inputs and outputs.
>
> 4. **Business logic**: Tools validate user authorization before taking actions (e.g., can this user modify this order?).
>
> 5. **Audit logging**: Log all agent actions for compliance review.
>
> 6. **Confirmation**: For destructive actions, require user confirmation before executing."

---

## Summary

```
BEDROCK AGENTS:
├── WHAT: Multi-step reasoning + tool use
├── WHEN: Tasks requiring actions or complex reasoning
├── HOW: LLM + Action Groups (Lambda) + optional KB
├── COST: 2-10x more than simple KB queries
└── KEY: ReAct pattern (Reasoning + Acting)

COMPONENTS:
├── Instructions: System prompt defining persona
├── Action Groups: Lambda functions as tools
├── Knowledge Bases: Optional RAG integration
├── Guardrails: Safety and compliance
└── Sessions: Multi-turn conversation memory

BEST PRACTICES:
├── Limit iterations to control cost
├── Design tools defensively (handle errors)
├── Use guardrails for sensitive actions
├── Log everything for audit
└── Confirm before destructive actions
```
