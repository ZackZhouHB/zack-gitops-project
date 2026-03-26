"""Escalation tool — DynamoDB backend.

Replaces local PostgreSQL-based escalation_tool.py.
Records escalation requests in DynamoDB for tracking.
"""
import uuid
import logging
from datetime import datetime, timezone

import boto3
from pydantic import BaseModel

from config import AWS_REGION, DYNAMODB_ESCALATIONS_TABLE

logger = logging.getLogger("escalation_tool")


class EscalationResponse(BaseModel):
    success: bool
    escalation_id: str = ""
    status: str = "pending"
    message: str = ""


def _get_table():
    """Get DynamoDB table resource."""
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(DYNAMODB_ESCALATIONS_TABLE)


async def escalate(
    reason: str,
    conversation_summary: str,
    priority: str = "medium",
) -> EscalationResponse:
    """Record an escalation to a human engineer.
    
    Args:
        reason: Why this needs human review
        conversation_summary: Brief summary of findings so far
        priority: low, medium, or high
    
    Returns:
        EscalationResponse with escalation ID and status
    """
    try:
        table = _get_table()
        escalation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        table.put_item(Item={
            "escalation_id": escalation_id,
            "reason": reason,
            "conversation_summary": conversation_summary,
            "priority": priority,
            "status": "pending",
            "created_at": now,
        })
        
        logger.info(f"Escalation created: {escalation_id} (priority: {priority})")
        
        return EscalationResponse(
            success=True,
            escalation_id=escalation_id,
            status="pending",
            message=f"Escalated to human engineer (priority: {priority}). "
                    f"Escalation ID: {escalation_id}. "
                    f"A team member will review this shortly.",
        )
        
    except Exception as e:
        logger.error(f"Escalation failed: {e}")
        return EscalationResponse(
            success=False,
            message=f"Failed to create escalation: {str(e)}",
        )
