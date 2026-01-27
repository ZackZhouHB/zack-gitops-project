"""Base connector interface and mock connectors"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BaseConnector(ABC):
    """Abstract base class for data source connectors"""
    
    @abstractmethod
    async def fetch(self, last_sync: datetime = None) -> List[Dict[str, Any]]:
        """Fetch documents from source"""
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return source identifier"""
        pass


class MockJiraConnector(BaseConnector):
    """Mock Jira connector for demo purposes"""
    
    MOCK_TICKETS = [
        {
            "id": "PROJ-101",
            "title": "Implement user authentication",
            "description": "Add OAuth2 authentication flow with JWT tokens. Support SSO integration.",
            "status": "Done",
            "assignee": "john.doe",
            "labels": ["security", "backend"]
        },
        {
            "id": "PROJ-102", 
            "title": "Fix memory leak in RAG service",
            "description": "Memory usage grows over time. Need to implement proper cleanup of embedding cache.",
            "status": "In Progress",
            "assignee": "jane.smith",
            "labels": ["bug", "performance"]
        },
        {
            "id": "PROJ-103",
            "title": "Add PDF support for document upload",
            "description": "Users need to upload PDF documents. Implement text extraction with PyPDF.",
            "status": "To Do",
            "assignee": None,
            "labels": ["feature", "documents"]
        }
    ]
    
    async def fetch(self, last_sync: datetime = None) -> List[Dict[str, Any]]:
        return [
            {
                "content": f"[{t['id']}] {t['title']}\n\nStatus: {t['status']}\nAssignee: {t['assignee'] or 'Unassigned'}\n\n{t['description']}",
                "source": f"jira:{t['id']}",
                "metadata": {"type": "ticket", "status": t["status"], "labels": t["labels"]}
            }
            for t in self.MOCK_TICKETS
        ]
    
    def get_source_name(self) -> str:
        return "jira"


class MockConfluenceConnector(BaseConnector):
    """Mock Confluence connector for demo purposes"""
    
    MOCK_PAGES = [
        {
            "id": "12345",
            "title": "RAG Architecture Overview",
            "content": """# RAG Architecture

Our RAG system consists of:
1. Document ingestion pipeline
2. Vector database (Weaviate)
3. Embedding service (Titan)
4. LLM for generation (Claude)

## Data Flow
Documents -> Chunking -> Embedding -> Vector Store -> Retrieval -> LLM -> Response
""",
            "space": "ENGINEERING"
        },
        {
            "id": "12346",
            "title": "Deployment Runbook",
            "content": """# Deployment Runbook

## Prerequisites
- AWS credentials configured
- Docker installed
- Access to ECR

## Steps
1. Build images: `docker-compose build`
2. Push to ECR
3. Update EKS deployment
4. Verify health checks
""",
            "space": "DEVOPS"
        }
    ]
    
    async def fetch(self, last_sync: datetime = None) -> List[Dict[str, Any]]:
        return [
            {
                "content": f"# {p['title']}\n\n{p['content']}",
                "source": f"confluence:{p['id']}",
                "metadata": {"type": "wiki", "space": p["space"]}
            }
            for p in self.MOCK_PAGES
        ]
    
    def get_source_name(self) -> str:
        return "confluence"


class ConnectorRegistry:
    """Registry for managing data source connectors"""
    
    def __init__(self):
        self.connectors: Dict[str, BaseConnector] = {}
    
    def register(self, connector: BaseConnector):
        self.connectors[connector.get_source_name()] = connector
        logger.info(f"Registered connector: {connector.get_source_name()}")
    
    async def fetch_all(self, last_sync: datetime = None) -> List[Dict[str, Any]]:
        """Fetch from all registered connectors"""
        all_docs = []
        for name, connector in self.connectors.items():
            try:
                docs = await connector.fetch(last_sync)
                all_docs.extend(docs)
                logger.info(f"Fetched {len(docs)} docs from {name}")
            except Exception as e:
                logger.error(f"Failed to fetch from {name}: {e}")
        return all_docs
