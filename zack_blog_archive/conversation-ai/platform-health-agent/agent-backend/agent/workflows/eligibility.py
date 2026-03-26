"""Eligibility Check Workflow — demonstrates agentic branching and state.

This is a multi-step workflow that:
1. Gathers required info (qualification, jurisdiction, target level)
2. Checks eligibility via policy tool
3. Branches based on result:
   - Eligible → create checklist → provide next steps
   - Not eligible → explain gaps → suggest alternatives
   - Uncertain → escalate to human

Graph structure:
  gather_info → check_policy → [branch] → eligible_path / ineligible_path / escalate
                                         → END

This is what makes it "agentic" vs simple RAG:
- Multiple steps with state carried between them
- Conditional branching based on tool results
- Can loop back to gather more info if needed
"""

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from agent.state import AgentState
from agent.prompts import SYSTEM_PROMPT

import json
import boto3
from config import BEDROCK_MODEL_ID, AWS_REGION, AWS_PROFILE


def _call_llm(messages: list, max_tokens: int = 2048) -> str:
    """Quick synchronous LLM call for workflow nodes."""
    from langchain_aws import ChatBedrockConverse
    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
    llm = ChatBedrockConverse(
        model=BEDROCK_MODEL_ID,
        client=session.client("bedrock-runtime"),
        max_tokens=max_tokens,
        temperature=0.1,
    )
    response = llm.invoke(messages)
    return response.content


async def gather_info_node(state: AgentState) -> dict:
    """Extract qualification details from the conversation.

    Uses LLM to parse the user's message and identify:
    - qualification (degree name)
    - jurisdiction (where obtained)
    - target accreditation level
    """
    messages = state["messages"]
    user_msg = ""
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            user_msg = m.content
            break

    extraction_prompt = f"""Extract the following from the user's message. If not mentioned, use "unknown".
Return ONLY valid JSON, no other text.

User message: "{user_msg}"

Return format:
{{"qualification": "...", "jurisdiction": "...", "accreditation_level": "..."}}

Rules:
- qualification: the teaching degree/qualification name
- jurisdiction: Australian state (NSW, VIC, etc.) or country if overseas
- accreditation_level: Provisional, Proficient, Highly Accomplished, or Lead (default: Provisional)
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
        extracted = {"qualification": "unknown", "jurisdiction": "unknown", "accreditation_level": "Provisional"}

    return {
        "current_workflow": "eligibility_check",
        "workflow_step": 1,
        "workflow_status": "gathering_info",
        "workflow_data": extracted,
    }


async def check_policy_node(state: AgentState) -> dict:
    """Run the eligibility check using the policy tool."""
    from tools.policy_tool import check_eligibility

    data = state.get("workflow_data", {})
    qualification = data.get("qualification", "unknown")
    jurisdiction = data.get("jurisdiction", "NSW")
    level = data.get("accreditation_level", "Provisional")

    result = await check_eligibility(
        qualification=qualification,
        jurisdiction=jurisdiction,
        accreditation_level=level,
    )

    return {
        "workflow_step": 2,
        "workflow_status": "policy_checked",
        "policy_result": result.model_dump(),
        "tool_calls_log": state.get("tool_calls_log", []) + [{
            "name": "check_eligibility",
            "input": {"qualification": qualification, "jurisdiction": jurisdiction, "level": level},
            "output_length": len(result.model_dump_json()),
            "latency_ms": 0,
        }],
    }


def route_after_policy(state: AgentState) -> str:
    """Branch based on eligibility result.

    This is the key branching logic that makes it a workflow:
    - eligible=True → "eligible" path (create checklist, next steps)
    - eligible=False → "ineligible" path (explain gaps)
    - eligible=None → "uncertain" path (escalate)
    """
    policy = state.get("policy_result", {})
    eligible = policy.get("eligible")

    if eligible is True:
        return "eligible"
    elif eligible is False:
        return "ineligible"
    else:
        return "uncertain"


async def eligible_path_node(state: AgentState) -> dict:
    """Handle eligible case — create checklist and provide next steps."""
    from tools.db_tool import create_checklist

    policy = state.get("policy_result", {})
    data = state.get("workflow_data", {})
    level = data.get("accreditation_level", "Provisional")

    next_steps = policy.get("next_steps", [])
    if not next_steps:
        next_steps = [
            f"Submit {level} accreditation application to NESA",
            "Prepare supporting documentation",
            "Complete Working with Children Check (WWCC)",
            "Provide certified copies of qualifications",
        ]

    checklist = await create_checklist(
        title=f"{level} Accreditation Checklist",
        items=next_steps,
    )

    response_text = _call_llm([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""The user asked about eligibility for {level} accreditation.

Policy check result:
- Eligible: YES
- Requirements met: {policy.get('requirements_met', [])}
- Confidence: {policy.get('confidence', 0)}

A checklist has been created (ID: {checklist.id[:8]}) with {checklist.total} items:
{json.dumps(next_steps, indent=2)}

Provide a warm, helpful response confirming their eligibility and listing the checklist items.
Mention the checklist ID so they can reference it later."""),
    ])

    return {
        "messages": [AIMessage(content=response_text)],
        "workflow_step": 3,
        "workflow_status": "completed",
    }


async def ineligible_path_node(state: AgentState) -> dict:
    """Handle ineligible case — explain gaps and suggest alternatives."""
    policy = state.get("policy_result", {})
    data = state.get("workflow_data", {})

    response_text = _call_llm([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""The user asked about eligibility for {data.get('accreditation_level', 'Provisional')} accreditation.

Policy check result:
- Eligible: NO
- Requirements met: {policy.get('requirements_met', [])}
- Requirements missing: {policy.get('requirements_missing', [])}
- Confidence: {policy.get('confidence', 0)}

Provide a supportive response explaining what requirements are missing and what steps they can take.
If applicable, suggest alternative pathways or lower accreditation levels they might qualify for."""),
    ])

    return {
        "messages": [AIMessage(content=response_text)],
        "workflow_step": 3,
        "workflow_status": "completed",
    }


async def uncertain_path_node(state: AgentState) -> dict:
    """Handle uncertain case — escalate to human review."""
    from tools.escalation_tool import escalate

    data = state.get("workflow_data", {})

    result = await escalate(
        reason=f"Cannot determine eligibility for {data.get('accreditation_level', 'unknown')} — complex case",
        conversation_summary=f"User with {data.get('qualification', 'unknown')} from {data.get('jurisdiction', 'unknown')}",
        priority="medium",
    )

    response_text = _call_llm([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"""I couldn't confidently determine the user's eligibility.
The case has been escalated to human review (ID: {result.escalation_id}).

Inform the user that their case requires individual assessment by a NESA staff member.
Provide the escalation reference number and expected next steps."""),
    ])

    return {
        "messages": [AIMessage(content=response_text)],
        "workflow_step": 3,
        "workflow_status": "escalated",
    }
