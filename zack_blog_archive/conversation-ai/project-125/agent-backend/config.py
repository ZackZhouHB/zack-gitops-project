"""Project 125 agent backend configuration — loaded from environment variables."""

import os
from dotenv import load_dotenv

load_dotenv()

# AWS Bedrock
AWS_PROFILE = os.getenv("AWS_PROFILE", "sandboxtest")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-southeast-2")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "apac.anthropic.claude-sonnet-4-20250514-v1:0")
BEDROCK_EMBED_MODEL_ID = os.getenv("BEDROCK_EMBED_MODEL_ID", "amazon.titan-embed-text-v2:0")
EMBED_DIMENSIONS = int(os.getenv("EMBED_DIMENSIONS", "1024"))

# Infrastructure (shared with platform-health-agent)
WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://localhost:8080")
POSTGRES_URL = os.getenv("POSTGRES_URL", "postgresql://agent:agent@localhost:5432/agent_db")

# Jira
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "SCRUM")

# MCP Servers (when using HTTP transport in Docker)
JIRA_MCP_URL = os.getenv("JIRA_MCP_URL", "")
SLACK_MCP_URL = os.getenv("SLACK_MCP_URL", "")

# Agent guardrails
RECURSION_LIMIT = int(os.getenv("RECURSION_LIMIT", "25"))
TOOL_TIMEOUT_SECONDS = int(os.getenv("TOOL_TIMEOUT_SECONDS", "10"))
MAX_TOKENS_PER_CONVERSATION = int(os.getenv("MAX_TOKENS_PER_CONVERSATION", "50000"))

# HITL
APPROVAL_TIMEOUT_SECONDS = int(os.getenv("APPROVAL_TIMEOUT_SECONDS", "300"))
