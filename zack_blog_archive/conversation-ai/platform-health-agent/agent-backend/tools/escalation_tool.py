"""Escalation tool — hand off to human review with full context."""

import uuid
import json
from pydantic import BaseModel

from config import POSTGRES_URL


class EscalationResult(BaseModel):
    """Result of an escalation request."""
    escalation_id: str
    reason: str
    context_summary: str
    priority: str  # low, medium, high
    status: str  # pending, acknowledged


def _get_conn():
    """Get a PostgreSQL connection."""
    import psycopg2
    url = POSTGRES_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "")
    user_pass, host_db = url.split("@")
    user, password = user_pass.split(":")
    host_port, db = host_db.split("/")
    host, port = host_port.split(":")
    if host == "postgres":
        host = "localhost"
    return psycopg2.connect(host=host, port=int(port), user=user, password=password, dbname=db)


async def escalate(
    reason: str,
    conversation_summary: str,
    priority: str = "medium",
) -> EscalationResult:
    """Escalate to human review when the agent cannot resolve confidently.

    Triggers when:
    - Confidence is below threshold
    - User explicitly asks for a human
    - Workflow encounters an unrecoverable error
    - Action requires human approval
    """
    escalation_id = str(uuid.uuid4())[:8]

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS escalations (
                id TEXT PRIMARY KEY,
                reason TEXT NOT NULL,
                context_summary TEXT,
                priority TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute(
            "INSERT INTO escalations (id, reason, context_summary, priority) VALUES (%s, %s, %s, %s)",
            (escalation_id, reason, conversation_summary, priority),
        )
        conn.commit()
    except Exception:
        conn.rollback()
    finally:
        conn.close()

    return EscalationResult(
        escalation_id=escalation_id,
        reason=reason,
        context_summary=conversation_summary,
        priority=priority,
        status="pending",
    )
