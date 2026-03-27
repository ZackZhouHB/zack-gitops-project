"""
Jira Cloud REST API Client — Project 125

Thin wrapper around Jira Cloud REST API v3.
No framework dependencies — just requests + base64.
"""

import logging
from base64 import b64encode

import requests

logger = logging.getLogger("jira-client")


class JiraClient:
    """Jira Cloud REST API v3 client."""

    def __init__(self, url: str, email: str, api_token: str, default_project: str = "PLAT"):
        self.url = url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.default_project = default_project
        self._headers = self._build_headers()

    def _build_headers(self) -> dict:
        if not self.email or not self.api_token:
            return {}
        token = b64encode(f"{self.email}:{self.api_token}".encode()).decode()
        return {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _text_to_adf(self, text: str) -> dict:
        """Convert plain text to Atlassian Document Format (ADF)."""
        paragraphs = text.split("\n\n") if text else [""]
        content = []
        for para in paragraphs:
            if para.strip():
                content.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": para.strip()}],
                })
        if not content:
            content = [{"type": "paragraph", "content": [{"type": "text", "text": " "}]}]
        return {"type": "doc", "version": 1, "content": content}

    def search(self, jql: str, max_results: int = 10) -> dict:
        """Search issues with JQL."""
        # Jira Cloud migrated to /rest/api/3/search/jql (2026)
        resp = requests.get(
            f"{self.url}/rest/api/3/search/jql",
            headers=self._headers,
            params={
                "jql": jql,
                "maxResults": max_results,
                "fields": "summary,status,priority,labels,created,updated,assignee",
            },
            timeout=15,
        )

        if resp.status_code != 200:
            return {"error": f"Search failed ({resp.status_code})", "details": resp.text[:300]}

        data = resp.json()
        issues = []
        for issue in data.get("issues", []):
            f = issue["fields"]
            issues.append({
                "key": issue["key"],
                "summary": f.get("summary", ""),
                "status": f.get("status", {}).get("name", "Unknown"),
                "priority": (f.get("priority") or {}).get("name", "Unknown"),
                "labels": f.get("labels", []),
                "created": f.get("created", ""),
                "assignee": f.get("assignee", {}).get("displayName", "Unassigned") if f.get("assignee") else "Unassigned",
                "url": f"{self.url}/browse/{issue['key']}",
            })

        # New /search/jql endpoint uses 'isLast' instead of 'total'
        return {"total": data.get("total", len(issues)), "issues": issues}

    def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str = "",
        issue_type: str = "Task",
        priority: str = "Medium",
        labels: list[str] | None = None,
    ) -> dict:
        """Create a new issue."""
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": self._text_to_adf(description),
                "issuetype": {"name": issue_type},
                "priority": {"name": priority},
                "labels": labels or [],
            }
        }

        resp = requests.post(
            f"{self.url}/rest/api/3/issue",
            headers=self._headers,
            json=payload,
            timeout=15,
        )

        if resp.status_code == 201:
            data = resp.json()
            return {
                "key": data["key"],
                "id": data["id"],
                "url": f"{self.url}/browse/{data['key']}",
            }
        else:
            return {"error": f"Create failed ({resp.status_code})", "details": resp.text[:300]}

    def get_issue(self, issue_key: str) -> dict:
        """Get issue details."""
        resp = requests.get(
            f"{self.url}/rest/api/3/issue/{issue_key}",
            headers=self._headers,
            timeout=15,
        )

        if resp.status_code != 200:
            return {"error": f"Get failed ({resp.status_code})", "details": resp.text[:300]}

        data = resp.json()
        f = data["fields"]
        return {
            "key": data["key"],
            "summary": f.get("summary", ""),
            "status": f.get("status", {}).get("name", "Unknown"),
            "priority": (f.get("priority") or {}).get("name", "Unknown"),
            "labels": f.get("labels", []),
            "description_preview": self._extract_adf_text(f.get("description"))[:500],
            "created": f.get("created", ""),
            "updated": f.get("updated", ""),
            "assignee": f.get("assignee", {}).get("displayName", "Unassigned") if f.get("assignee") else "Unassigned",
            "comment_count": f.get("comment", {}).get("total", 0),
            "url": f"{self.url}/browse/{data['key']}",
        }

    def update_issue(self, issue_key: str, fields: dict) -> dict:
        """Update issue fields."""
        resp = requests.put(
            f"{self.url}/rest/api/3/issue/{issue_key}",
            headers=self._headers,
            json={"fields": fields},
            timeout=15,
        )

        if resp.status_code == 204:
            return {"success": True, "issue_key": issue_key}
        else:
            return {"success": False, "error": f"Update failed ({resp.status_code})", "details": resp.text[:300]}

    def add_comment(self, issue_key: str, text: str) -> dict:
        """Add a comment to an issue."""
        resp = requests.post(
            f"{self.url}/rest/api/3/issue/{issue_key}/comment",
            headers=self._headers,
            json={"body": self._text_to_adf(text)},
            timeout=15,
        )

        if resp.status_code == 201:
            return {"success": True, "comment_id": resp.json()["id"], "issue_key": issue_key}
        else:
            return {"success": False, "error": f"Comment failed ({resp.status_code})", "details": resp.text[:300]}

    def _extract_adf_text(self, adf: dict | None) -> str:
        """Extract plain text from ADF document."""
        if not adf:
            return ""
        texts = []
        for block in adf.get("content", []):
            for inline in block.get("content", []):
                if inline.get("type") == "text":
                    texts.append(inline.get("text", ""))
        return "\n".join(texts)
