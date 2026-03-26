"""Incident tool — triage infrastructure incidents using RAG + pattern matching."""

from pydantic import BaseModel
from tools.rag_tool import rag_search, format_context_for_llm


class IncidentAssessment(BaseModel):
    """Structured output from incident triage."""
    component: str
    symptoms: str
    severity: str
    known_pattern: bool  # True if we found a matching doc
    diagnosis: str
    confidence: float  # 0.0 to 1.0
    suggested_actions: list[str]
    related_docs: list[str]


# Known component patterns for quick matching
KNOWN_COMPONENTS = {
    "eventbridge": {
        "keywords": ["schedule", "cron", "trigger", "rule", "target"],
        "common_issues": [
            "Cron expression timezone mismatch (use Australia/Sydney)",
            "EventBridge Scheduler IAM role missing lambda:InvokeFunction",
            "Rule target not receiving events — check DLQ for failures",
        ],
    },
    "lambda": {
        "keywords": ["timeout", "memory", "cold start", "invocation", "runtime"],
        "common_issues": [
            "Lambda timeout — increase from default 3s for Bedrock calls",
            "Memory exceeded — Bedrock responses can be large",
            "Environment variable missing (SNS topic ARN, Bedrock model ID)",
        ],
    },
    "sns": {
        "keywords": ["notification", "email", "publish", "subscription", "topic"],
        "common_issues": [
            "Email subscription requires confirmation click",
            "SNS message size limit 256KB — large reports may be truncated",
            "Publish permission missing — Lambda needs sns:Publish on specific topic ARN",
        ],
    },
    "bedrock": {
        "keywords": ["model", "inference", "throttle", "token", "prompt"],
        "common_issues": [
            "Model ID requires inference profile prefix (apac.anthropic...)",
            "Throttling — reduce concurrent requests or request quota increase",
            "Token limit exceeded — chunk input or use staged pipeline",
        ],
    },
    "terraform": {
        "keywords": ["state", "plan", "apply", "drift", "provider"],
        "common_issues": [
            "State lock — another process holds the lock, check DynamoDB",
            "Provider version mismatch — pin versions in required_providers",
            "Drift detected — resources modified outside Terraform",
        ],
    },
    "lakehouse": {
        "keywords": ["databricks", "permissions", "catalog", "schema", "unity"],
        "common_issues": [
            "Unity Catalog permissions — check GRANT hierarchy (catalog → schema → table)",
            "Service principal missing USE CATALOG permission",
            "External location credential not configured for S3 path",
        ],
    },
}


async def assess_incident(
    component: str,
    symptoms: str,
    severity: str = "medium",
) -> IncidentAssessment:
    """Triage an incident by searching docs and matching known patterns.

    Steps:
    1. Match component to known patterns
    2. Search knowledge base for relevant docs
    3. Combine findings into a structured assessment
    """
    component_lower = component.lower().strip()

    # Step 1: Check known patterns
    matched_component = None
    for comp_key, comp_data in KNOWN_COMPONENTS.items():
        if comp_key in component_lower or any(kw in component_lower for kw in comp_data["keywords"]):
            matched_component = comp_key
            break

    # Step 2: Search knowledge base
    search_query = f"{component} {symptoms} troubleshooting fix"
    search_result = await rag_search(search_query, top_k=3)

    related_docs = [r["title"] for r in search_result.results] if search_result.success else []
    has_docs = len(related_docs) > 0

    # Step 3: Build assessment
    suggested_actions = []
    diagnosis = ""

    if matched_component:
        known_issues = KNOWN_COMPONENTS[matched_component]["common_issues"]
        # Check if symptoms match any known issue
        symptom_lower = symptoms.lower()
        for issue in known_issues:
            if any(word in symptom_lower for word in issue.lower().split()[:3]):
                suggested_actions.append(issue)

        if not suggested_actions:
            suggested_actions = known_issues[:2]  # Show top 2 common issues

        diagnosis = f"Component '{component}' matched known pattern '{matched_component}'. "
        if has_docs:
            diagnosis += f"Found {len(related_docs)} related docs in knowledge base."
        confidence = 0.7 if suggested_actions else 0.4
    elif has_docs:
        diagnosis = f"No known pattern for '{component}', but found {len(related_docs)} related docs."
        suggested_actions = ["Review related documentation", "Check CloudWatch logs for the component"]
        confidence = 0.4
    else:
        diagnosis = f"No known pattern or documentation found for '{component}'."
        suggested_actions = ["Check CloudWatch logs", "Review recent deployments", "Escalate to on-call engineer"]
        confidence = 0.2

    return IncidentAssessment(
        component=component,
        symptoms=symptoms,
        severity=severity,
        known_pattern=matched_component is not None,
        diagnosis=diagnosis,
        confidence=confidence,
        suggested_actions=suggested_actions,
        related_docs=related_docs,
    )
