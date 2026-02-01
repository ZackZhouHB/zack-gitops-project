"""
Confluence Loader - Enterprise wiki integration for RAG

This module demonstrates how to build a Confluence connector for RAG systems.
It can work in two modes:
1. MOCK mode (default) - Returns sample data for learning/testing
2. LIVE mode - Connects to real Confluence instance

Real-world usage requires:
- Confluence Cloud: API token from https://id.atlassian.com/manage-profile/security/api-tokens
- Confluence Server: Personal access token or OAuth

Example API calls:
- List spaces: GET /wiki/rest/api/space
- List pages in space: GET /wiki/rest/api/content?spaceKey=TEAM&type=page
- Get page content: GET /wiki/rest/api/content/{id}?expand=body.storage,version,ancestors
"""

import logging
from typing import List, Optional, Dict
from dataclasses import dataclass
import httpx
from bs4 import BeautifulSoup

from .base import LoadedDocument

logger = logging.getLogger(__name__)


@dataclass
class ConfluencePage:
    """Represents a Confluence page"""
    id: str
    title: str
    space_key: str
    content: str
    url: str
    author: Optional[str] = None
    last_modified: Optional[str] = None
    labels: Optional[List[str]] = None
    parent_title: Optional[str] = None
    version: Optional[int] = None


# Sample mock data for learning/testing without real Confluence
MOCK_PAGES = [
    {
        "id": "12345",
        "title": "AWS Infrastructure Standards",
        "space_key": "INFRA",
        "content": """
        <h1>AWS Infrastructure Standards</h1>
        <p>This document outlines our AWS infrastructure standards and best practices.</p>
        
        <h2>EC2 Instance Naming Convention</h2>
        <p>All EC2 instances must follow the naming pattern: <code>{env}-{app}-{role}-{number}</code></p>
        <ul>
            <li>env: prod, staging, dev</li>
            <li>app: application name</li>
            <li>role: web, api, worker, db</li>
            <li>number: 01, 02, etc.</li>
        </ul>
        
        <h2>Required Tags</h2>
        <table>
            <tr><th>Tag</th><th>Required</th><th>Example</th></tr>
            <tr><td>Environment</td><td>Yes</td><td>production</td></tr>
            <tr><td>Owner</td><td>Yes</td><td>platform-team</td></tr>
            <tr><td>CostCenter</td><td>Yes</td><td>CC-1234</td></tr>
        </table>
        
        <h2>Security Groups</h2>
        <p>Never open port 22 to 0.0.0.0/0. Use bastion hosts or SSM Session Manager.</p>
        """,
        "author": "Platform Team",
        "labels": ["aws", "standards", "infrastructure"],
    },
    {
        "id": "12346",
        "title": "Kubernetes Deployment Guide",
        "space_key": "INFRA",
        "content": """
        <h1>Kubernetes Deployment Guide</h1>
        <p>How to deploy applications to our EKS clusters.</p>
        
        <h2>Prerequisites</h2>
        <ul>
            <li>kubectl configured with cluster access</li>
            <li>Docker image pushed to ECR</li>
            <li>Helm chart prepared</li>
        </ul>
        
        <h2>Deployment Steps</h2>
        <ol>
            <li>Update values.yaml with your configuration</li>
            <li>Run: <code>helm upgrade --install myapp ./chart -n namespace</code></li>
            <li>Verify: <code>kubectl get pods -n namespace</code></li>
        </ol>
        
        <h2>Rollback</h2>
        <p>To rollback: <code>helm rollback myapp 1 -n namespace</code></p>
        """,
        "author": "DevOps Team",
        "labels": ["kubernetes", "eks", "deployment"],
    },
    {
        "id": "12347",
        "title": "Incident Response Runbook",
        "space_key": "OPS",
        "content": """
        <h1>Incident Response Runbook</h1>
        <p>Steps to follow during production incidents.</p>
        
        <h2>Severity Levels</h2>
        <table>
            <tr><th>Level</th><th>Description</th><th>Response Time</th></tr>
            <tr><td>P1</td><td>Service down</td><td>15 minutes</td></tr>
            <tr><td>P2</td><td>Degraded performance</td><td>1 hour</td></tr>
            <tr><td>P3</td><td>Minor issue</td><td>4 hours</td></tr>
        </table>
        
        <h2>P1 Response Steps</h2>
        <ol>
            <li>Acknowledge in PagerDuty</li>
            <li>Join incident Slack channel #incidents</li>
            <li>Check CloudWatch dashboards</li>
            <li>Review recent deployments</li>
            <li>Escalate if not resolved in 30 minutes</li>
        </ol>
        """,
        "author": "SRE Team",
        "labels": ["incident", "runbook", "operations"],
    },
]


class ConfluenceLoader:
    """
    Load content from Confluence wiki.
    
    Supports two modes:
    - mock=True (default): Uses sample data for learning
    - mock=False: Connects to real Confluence (requires credentials)
    
    Real Confluence setup:
        loader = ConfluenceLoader(
            base_url="https://yourcompany.atlassian.net",
            username="your-email@company.com",
            api_token="your-api-token",
            mock=False
        )
    """
    
    def __init__(
        self,
        base_url: str = "https://confluence.example.com",
        username: Optional[str] = None,
        api_token: Optional[str] = None,
        mock: bool = True
    ):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.api_token = api_token
        self.mock = mock
        
        if not mock and (not username or not api_token):
            raise ValueError("username and api_token required for live mode")
        
        if not mock:
            self.client = httpx.Client(
                timeout=30.0,
                auth=(username, api_token),
                headers={"Accept": "application/json"}
            )
    
    def list_spaces(self) -> List[Dict]:
        """List all accessible Confluence spaces"""
        if self.mock:
            return [
                {"key": "INFRA", "name": "Infrastructure", "type": "global"},
                {"key": "OPS", "name": "Operations", "type": "global"},
                {"key": "DEV", "name": "Development", "type": "global"},
            ]
        
        # Real API call
        resp = self.client.get(f"{self.base_url}/wiki/rest/api/space")
        resp.raise_for_status()
        return resp.json().get("results", [])
    
    def list_pages(self, space_key: str, limit: int = 100) -> List[Dict]:
        """List pages in a space"""
        if self.mock:
            return [p for p in MOCK_PAGES if p["space_key"] == space_key]
        
        # Real API call
        resp = self.client.get(
            f"{self.base_url}/wiki/rest/api/content",
            params={
                "spaceKey": space_key,
                "type": "page",
                "limit": limit,
                "expand": "version"
            }
        )
        resp.raise_for_status()
        return resp.json().get("results", [])
    
    def get_page(self, page_id: str) -> ConfluencePage:
        """Get full page content"""
        if self.mock:
            for p in MOCK_PAGES:
                if p["id"] == page_id:
                    return ConfluencePage(
                        id=p["id"],
                        title=p["title"],
                        space_key=p["space_key"],
                        content=p["content"],
                        url=f"{self.base_url}/wiki/spaces/{p['space_key']}/pages/{p['id']}",
                        author=p.get("author"),
                        labels=p.get("labels", [])
                    )
            raise ValueError(f"Page {page_id} not found")
        
        # Real API call
        resp = self.client.get(
            f"{self.base_url}/wiki/rest/api/content/{page_id}",
            params={"expand": "body.storage,version,ancestors,metadata.labels"}
        )
        resp.raise_for_status()
        data = resp.json()
        
        return ConfluencePage(
            id=data["id"],
            title=data["title"],
            space_key=data["space"]["key"],
            content=data["body"]["storage"]["value"],
            url=f"{self.base_url}{data['_links']['webui']}",
            author=data.get("version", {}).get("by", {}).get("displayName"),
            last_modified=data.get("version", {}).get("when"),
            labels=[l["name"] for l in data.get("metadata", {}).get("labels", {}).get("results", [])],
            version=data.get("version", {}).get("number")
        )
    
    def _parse_html(self, html: str) -> str:
        """Convert Confluence HTML to clean text"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove Confluence macros that don't contain useful text
        for macro in soup.find_all('ac:structured-macro'):
            macro.decompose()
        
        # Convert tables to markdown-ish format
        for table in soup.find_all('table'):
            rows = []
            for tr in table.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                rows.append(" | ".join(cells))
            table.replace_with("\n".join(rows) + "\n")
        
        # Convert code blocks
        for code in soup.find_all('code'):
            code.replace_with(f"`{code.get_text()}`")
        
        return soup.get_text(separator='\n', strip=True)
    
    def load_page(self, page_id: str) -> LoadedDocument:
        """Load a single page as LoadedDocument"""
        page = self.get_page(page_id)
        
        # Parse HTML to text
        text_content = self._parse_html(page.content)
        
        # Build structured document
        doc_content = f"""# {page.title}

**Space:** {page.space_key}
**Author:** {page.author or 'Unknown'}
**Labels:** {', '.join(page.labels) if page.labels else 'None'}
**URL:** {page.url}

---

{text_content}
"""
        
        logger.info(f"Loaded Confluence page: {page.title}")
        
        return LoadedDocument(
            content=doc_content,
            filename=page.url,
            source_type="confluence",
            size_bytes=len(doc_content.encode()),
            checksum=LoadedDocument.calculate_checksum(doc_content.encode()),
            metadata={
                "page_id": page.id,
                "title": page.title,
                "space": page.space_key,
                "author": page.author,
                "labels": page.labels,
                "url": page.url
            }
        )
    
    def load_space(self, space_key: str, limit: int = 100) -> List[LoadedDocument]:
        """Load all pages from a space"""
        pages = self.list_pages(space_key, limit)
        documents = []
        
        for page_info in pages:
            try:
                page_id = page_info["id"] if isinstance(page_info, dict) else page_info.id
                doc = self.load_page(page_id)
                documents.append(doc)
            except Exception as e:
                logger.error(f"Failed to load page {page_info}: {e}")
        
        logger.info(f"Loaded {len(documents)} pages from space {space_key}")
        return documents
    
    def load_all_spaces(self, limit_per_space: int = 50) -> List[LoadedDocument]:
        """Load pages from all accessible spaces"""
        spaces = self.list_spaces()
        all_docs = []
        
        for space in spaces:
            space_key = space["key"] if isinstance(space, dict) else space.key
            docs = self.load_space(space_key, limit_per_space)
            all_docs.extend(docs)
        
        return all_docs


# Example usage and testing
if __name__ == "__main__":
    # Mock mode - no credentials needed
    loader = ConfluenceLoader(mock=True)
    
    print("=== Spaces ===")
    for space in loader.list_spaces():
        print(f"  {space['key']}: {space['name']}")
    
    print("\n=== Pages in INFRA ===")
    for page in loader.list_pages("INFRA"):
        print(f"  {page['id']}: {page['title']}")
    
    print("\n=== Load a page ===")
    doc = loader.load_page("12345")
    print(f"Title: {doc.metadata['title']}")
    print(f"Content preview: {doc.content[:200]}...")
