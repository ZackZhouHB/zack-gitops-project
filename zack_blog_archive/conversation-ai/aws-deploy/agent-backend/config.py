"""AWS deployment configuration.

All values are injected via ECS task environment variables.
Locally, use a .env file for testing.
"""
import os

# AWS Region
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")

# Bedrock LLM
BEDROCK_MODEL_ID = os.getenv(
    "BEDROCK_MODEL_ID",
    "apac.anthropic.claude-sonnet-4-20250514-v1:0"
)

# Bedrock Knowledge Base
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID", "")

# DynamoDB tables
DYNAMODB_CHECKLISTS_TABLE = os.getenv("DYNAMODB_CHECKLISTS_TABLE", "platform-health-checklists")
DYNAMODB_ESCALATIONS_TABLE = os.getenv("DYNAMODB_ESCALATIONS_TABLE", "platform-health-escalations")

# EFS mount path for chat history
EFS_MOUNT_PATH = os.getenv("EFS_MOUNT_PATH", "/mnt/efs")
SESSIONS_DIR = os.path.join(EFS_MOUNT_PATH, "sessions")

# Agent settings
RECURSION_LIMIT = int(os.getenv("RECURSION_LIMIT", "25"))
