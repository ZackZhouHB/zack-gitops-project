"""Incident Triage Workflow — structured multi-step incident diagnosis.

Graph structure:
  gather_symptoms → search_docs → [branch] → known_fix / investigate / escalate → END

Branches:
  - known_fix:   Found matching docs + high confidence → checklist of fix steps
  - investigate:  Found partial info → diagnostic checklist + next steps
  - escalate:     No matches or critical severity → hand off to human engineer
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from agent.state import AgentState
from agent.prompts import SYSTEM_PROMPT

import json
import boto3
from config import BEDROCK_MODEL_ID, AWS_REGION


def _call_llm(messages: list, max_tokens: int = 2048) -> str:
    """Quick synchronous LLM call for workflow nodes."""
    from langchain_aws import ChatBedrockConverse
    session = boto3.Session(region_name=AWS_REGION)
    llm = ChatBedrockConverse(
        model=BEDROCK_MODEL_ID,
        client=session.client("bedrock-runtime"),
        max_tokens=max_tokens,
        temperature=0.1,
    )
    response = llm.invoke(messages)
    content = response.content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return content


async def gather_symptoms_node(state: AgentState) -> dict:
    """Extract incident details from the user's message.

    Uses LLM to parse: component, symptoms, severity, environment.
    """
    messages = state["messages"]
    user_msg = ""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            user_msg = m.content
            break

    extraction_prompt = f"""Extract incident details from the user's message. If not mentioned, use "unknown".
Return ONLY valid JSON, no other text.

User message: "{user_msg}"

Return format:
{{"component": "...", "symptoms": "...", "severity": "low|medium|high|critical", "environment": "..."}}

Rules:
- component: the infrastructure service or tool affected (e.g., EventBridge, Lambda, Bedrock, Terraform, Lakehouse)
- symptoms: what went wrong, error messages, unexpected behavior
- severity: low (cosmetic), medium (degraded), high (broken), critical (outage)
- environment: dev, staging, production, or unknown
"""

    result = _call_llm([
        SystemMessage(content="You are a JSON extraction assistant. Return ONLY valid JSON."),
        HumanMessage(content=extraction_prompt),
    ])

    try:
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[1].rsplit("```", 1)[0]
        extracted = json.loads(clean)
    except (json.JSONDecodeError, IndexError):
        extracted = {"component": "unknown", "symptoms": user_msg, "severity": "medium", "environment": "unknown"}

    return {
        "current_workflow": "incident_triage",
        "workflow_step": 1,
        "workflow_status": "gathering_symptoms",
        "workflow_data": extracted,
    }


async def search_docs_node(state: AgentState) -> dict:
    """Search knowledge base and run incident assessment."""
    from tools.incident_tool import assess_incident

    data = state.get("workflow_data", {})
    component = data.get("component", "unknown")
    symptoms = data.get("symptoms", "")
    severity = data.get("severity", "medium")

    result = await assess_incident(
        component=component,
        symptoms=symptoms,
        severity=severity,
    )

    return {
        "workflow_step": 2,
        "workflow_status": "docs_searched",
        "incident_result": result.model_dump(),
        "tool_calls_log": state.get("tool_calls_log", []) + [{
            "name": "assess_incident",
            "input": {"component": component, "symptoms": symptoms[:100], "severity": severity},
            "output_length": len(result.model_dump_json()),
            "latency_ms": 0,
        }],
    }


def route_after_search(state: AgentState) -> str:
    """Branch based on incident assessment.

    - known_fix:   confidence >= 0.6 and severity != critical → provide fix steps
    - investigate:  confidence 0.3-0.6 → need more info, provide diagnostic steps
    - escalate:     confidence < 0.3 OR severity critical → hand off to human
    """
    incident = state.get("incident_result", {})
    confidence = incident.get("confidence", 0)
    severity = state.get("workflow_data", {}).get("severity", "medium")

    if severity == "critical":
        return "escalate"
    elif confidence >= 0.6:
        return "known_fix"
    elif confidence >= 0.3:
        return "investigate"
    else:
        return "escalate"


async def known_fix_node(state: AgentState) -> dict:
    """Handle known issue — provide fix steps and create a checklist."""
    from tools.dynamodb_tool import create_checklist
    from tools.kb_tool import kb_search, format_context_for_llm

    incident = state.get("incident_result", {})
    data = state.get("workflow_data", {})

    # Get relevant doc content for the LLM
    search = kb_search(f"{data.get('component', '')} {data.get('symptoms', '')} fix resolution", top_k=3)
    doc_context = format_context_for_llm(search) if search.get("success") else "No additional docs found."

    actions = incident.get("suggested_actions", [])
    if actions:
        checklist = await create_checklist(
            title=f"Incident Fix: {data.get('component', 'Unknown')}",
            items=actions,
        )
        checklist_info = f"Checklist created (ID: {checklist.checklist_id[:8]}) with {len(checklist.items)} steps."
    else:
        checklist_info = "No specific checklist created."

    response_text = _call_llm([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""The user reported an incident. I found a known fix.

Component: {data.get('component')}
Symptoms: {data.get('symptoms')}
Severity: {data.get('severity')}
Diagnosis: {incident.get('diagnosis')}
Confidence: {incident.get('confidence')}
Suggested actions: {json.dumps(actions)}
Related docs: {incident.get('related_docs', [])}
{checklist_info}

Relevant documentation:
{doc_context[:3000]}

Provide a clear, actionable response:
1. Explain the likely cause
2. List the fix steps (reference the checklist)
3. Mention what to watch for after applying the fix"""),
    ])

    return {
        "messages": [AIMessage(content=response_text)],
        "workflow_step": 3,
        "workflow_status": "completed",
    }


async def investigate_node(state: AgentState) -> dict:
    """Handle uncertain case — provide diagnostic steps."""
    from tools.dynamodb_tool import create_checklist

    incident = state.get("incident_result", {})
    data = state.get("workflow_data", {})

    diagnostic_steps = [
        f"Check CloudWatch logs for {data.get('component', 'the component')}",
        "Review recent deployment history (last 24h)",
        "Verify IAM permissions and role trust policies",
        "Check resource quotas and service limits",
        "Test connectivity to dependent services",
        "Compare current config against last known good state",
    ]

    checklist = await create_checklist(
        title=f"Diagnostic: {data.get('component', 'Unknown')} Investigation",
        items=diagnostic_steps,
    )

    response_text = _call_llm([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""The user reported an incident but I'm not fully confident in the diagnosis.

Component: {data.get('component')}
Symptoms: {data.get('symptoms')}
Severity: {data.get('severity')}
Diagnosis: {incident.get('diagnosis')}
Confidence: {incident.get('confidence')}
Related docs: {incident.get('related_docs', [])}

I've created a diagnostic checklist (ID: {checklist.checklist_id[:8]}) with {len(checklist.items)} investigation steps.

Provide a response that:
1. Explains what we know so far
2. Lists the diagnostic steps to narrow down the cause
3. Tells the user to come back with findings for further help"""),
    ])

    return {
        "messages": [AIMessage(content=response_text)],
        "workflow_step": 3,
        "workflow_status": "investigating",
    }


async def escalate_node(state: AgentState) -> dict:
    """Handle critical or unknown case — escalate to human engineer."""
    from tools.escalation_tool import escalate

    data = state.get("workflow_data", {})
    incident = state.get("incident_result", {})

    result = await escalate(
        reason=f"Incident: {data.get('component', 'unknown')} — {data.get('severity', 'unknown')} severity, low confidence diagnosis",
        conversation_summary=f"Component: {data.get('component')}, Symptoms: {data.get('symptoms', '')[:200]}, Diagnosis: {incident.get('diagnosis', 'none')}",
        priority="high" if data.get("severity") == "critical" else "medium",
    )

    response_text = _call_llm([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""The user reported an incident that needs human intervention.

Component: {data.get('component')}
Symptoms: {data.get('symptoms')}
Severity: {data.get('severity')}
Escalation ID: {result.escalation_id}

This was escalated because: {'Critical severity' if data.get('severity') == 'critical' else 'Low confidence diagnosis — the issue is not in our knowledge base'}

Inform the user that:
1. The incident has been escalated (reference ID: {result.escalation_id})
2. A human engineer will review it
3. In the meantime, suggest basic troubleshooting (check logs, recent changes)"""),
    ])

    return {
        "messages": [AIMessage(content=response_text)],
        "workflow_step": 3,
        "workflow_status": "escalated",
    }
