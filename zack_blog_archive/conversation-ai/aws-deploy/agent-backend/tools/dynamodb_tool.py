"""DynamoDB checklist tool.

Replaces the local PostgreSQL-based db_tool.py.
Stores checklists in DynamoDB with on-demand billing.
"""
import uuid
import logging
from datetime import datetime, timezone

import boto3
from pydantic import BaseModel

from config import AWS_REGION, DYNAMODB_CHECKLISTS_TABLE

logger = logging.getLogger("dynamodb_tool")


class ChecklistResponse(BaseModel):
    success: bool
    checklist_id: str = ""
    title: str = ""
    items: list[dict] = []
    message: str = ""


def _get_table():
    """Get DynamoDB table resource."""
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(DYNAMODB_CHECKLISTS_TABLE)


async def create_checklist(title: str, items: list[str]) -> ChecklistResponse:
    """Create a new checklist in DynamoDB.
    
    Args:
        title: Name of the checklist
        items: List of action item strings
    
    Returns:
        ChecklistResponse with the created checklist details
    """
    try:
        table = _get_table()
        checklist_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        checklist_items = [
            {"item_text": item, "completed": False}
            for item in items
        ]
        
        table.put_item(Item={
            "checklist_id": checklist_id,
            "title": title,
            "items": checklist_items,
            "created_at": now,
            "updated_at": now,
        })
        
        logger.info(f"Created checklist '{title}' with {len(items)} items: {checklist_id}")
        
        return ChecklistResponse(
            success=True,
            checklist_id=checklist_id,
            title=title,
            items=checklist_items,
            message=f"Checklist '{title}' created with {len(items)} items.",
        )
        
    except Exception as e:
        logger.error(f"Failed to create checklist: {e}")
        return ChecklistResponse(
            success=False,
            message=f"Failed to create checklist: {str(e)}",
        )
