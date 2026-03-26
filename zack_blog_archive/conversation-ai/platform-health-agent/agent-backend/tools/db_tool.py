"""Database tool — manage checklists and save workflow progress in PostgreSQL."""

import uuid
import json
import psycopg2
from pydantic import BaseModel

from config import POSTGRES_URL


class Checklist(BaseModel):
    """A tracked checklist for accreditation requirements."""
    id: str
    title: str
    items: list[dict]
    completed: int
    total: int


def _get_conn():
    """Get a PostgreSQL connection."""
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


async def create_checklist(title: str, items: list[str]) -> Checklist:
    """Create a new checklist with items in PostgreSQL.

    Uses the existing schema: checklists (UUID PK) + checklist_items (FK).
    """
    checklist_id = str(uuid.uuid4())

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO checklists (id, title, checklist_type, created_at) VALUES (%s::uuid, %s, %s, NOW())",
            (checklist_id, title, "accreditation"),
        )
        checklist_items = []
        for desc in items:
            cur.execute(
                "INSERT INTO checklist_items (checklist_id, description, status) VALUES (%s::uuid, %s, 'pending') RETURNING id",
                (checklist_id, desc),
            )
            item_id = cur.fetchone()[0]
            checklist_items.append({
                "id": str(item_id),
                "description": desc,
                "status": "pending",
                "notes": "",
            })
        conn.commit()
    finally:
        conn.close()

    return Checklist(
        id=checklist_id,
        title=title,
        items=checklist_items,
        completed=0,
        total=len(checklist_items),
    )


async def get_checklist(checklist_id: str) -> Checklist:
    """Retrieve a checklist by ID."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, title FROM checklists WHERE id = %s::uuid", (checklist_id,))
        row = cur.fetchone()
        if not row:
            return Checklist(id=checklist_id, title="Not found", items=[], completed=0, total=0)
        cur.execute(
            "SELECT id, description, status, notes FROM checklist_items WHERE checklist_id = %s::uuid ORDER BY id",
            (checklist_id,),
        )
        items = [{"id": str(r[0]), "description": r[1], "status": r[2], "notes": r[3] or ""} for r in cur.fetchall()]
        completed = sum(1 for i in items if i["status"] == "done")
        return Checklist(id=str(row[0]), title=row[1], items=items, completed=completed, total=len(items))
    finally:
        conn.close()


async def save_progress(conversation_id: str, workflow_state: dict) -> dict:
    """Save workflow progress to PostgreSQL for later resume."""
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS workflow_progress (
                conversation_id TEXT PRIMARY KEY,
                state JSONB NOT NULL,
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute(
            """INSERT INTO workflow_progress (conversation_id, state, updated_at)
               VALUES (%s, %s, NOW())
               ON CONFLICT (conversation_id) DO UPDATE SET state = %s, updated_at = NOW()""",
            (conversation_id, json.dumps(workflow_state), json.dumps(workflow_state)),
        )
        conn.commit()
        return {"saved": True, "conversation_id": conversation_id}
    finally:
        conn.close()
