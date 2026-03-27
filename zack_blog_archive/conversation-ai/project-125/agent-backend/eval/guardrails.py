"""
Guardrails Module — Runtime safety checks for the action agent.

Three guardrail layers:
  1. INPUT guardrails: Run before the agent processes the message
  2. OUTPUT guardrails: Run before returning the response to the user
  3. TOOL guardrails: Run inside the tool_node before tool execution

Each guardrail returns a GuardrailResult:
  - passed: True if check passed (safe to proceed)
  - violations: List of detected issues
  - sanitized_text: Input with PII masked (for PII guardrail)
"""

import re
import os
import sys
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# Add project root for config
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import MAX_TOKENS_PER_CONVERSATION, RECURSION_LIMIT


@dataclass
class Violation:
    """A single guardrail violation."""
    guardrail: str
    severity: str   # "block" | "warn" | "info"
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""
    passed: bool
    violations: list[Violation] = field(default_factory=list)
    sanitized_text: str | None = None

    def merge(self, other: "GuardrailResult") -> "GuardrailResult":
        """Merge two results. Fails if either failed."""
        return GuardrailResult(
            passed=self.passed and other.passed,
            violations=self.violations + other.violations,
            sanitized_text=other.sanitized_text or self.sanitized_text,
        )


# ── PII Detection Guardrail ──

PII_PATTERNS = {
    "ssn": {
        "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
        "label": "Social Security Number",
        "mask": "[SSN-REDACTED]",
    },
    "credit_card": {
        "pattern": r"\b(?:\d{4}[- ]?){3}\d{4}\b",
        "label": "Credit Card Number",
        "mask": "[CC-REDACTED]",
    },
    "email_personal": {
        "pattern": r"\b[a-zA-Z0-9._%+-]+@(?:gmail|yahoo|hotmail|outlook)\.\w+\b",
        "label": "Personal Email Address",
        "mask": "[EMAIL-REDACTED]",
    },
    "phone_us": {
        "pattern": r"\b(?:\+1[-.]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "label": "US Phone Number",
        "mask": "[PHONE-REDACTED]",
    },
    "aws_key": {
        "pattern": r"\bAKIA[0-9A-Z]{16}\b",
        "label": "AWS Access Key ID",
        "mask": "[AWS-KEY-REDACTED]",
    },
    "aws_secret": {
        "pattern": r"\b[A-Za-z0-9/+=]{40}\b",
        "label": "Possible AWS Secret Key",
        "mask": "[AWS-SECRET-REDACTED]",
    },
}


def check_pii(text: str, mode: str = "warn") -> GuardrailResult:
    """
    Scan text for PII patterns. Returns sanitized_text with PII masked.

    mode:
      - "warn": Log warning but allow (sanitized_text provided)
      - "block": Fail the guardrail if PII found
    """
    violations = []
    sanitized = text

    for pii_type, config in PII_PATTERNS.items():
        matches = re.findall(config["pattern"], text)
        if matches:
            for match in matches:
                sanitized = sanitized.replace(match, config["mask"])

            violations.append(Violation(
                guardrail="pii_detection",
                severity="block" if mode == "block" else "warn",
                message=f"Detected {config['label']}: {len(matches)} instance(s)",
                details={"type": pii_type, "count": len(matches)},
            ))

    passed = not any(v.severity == "block" for v in violations)

    return GuardrailResult(
        passed=passed,
        violations=violations,
        sanitized_text=sanitized if violations else None,
    )


# ── Topic Filter Guardrail ──

ALLOWED_TOPICS = [
    "platform health", "infrastructure", "EKS", "kubernetes",
    "AWS", "Bedrock", "Lambda", "cost", "billing",
    "incident", "ticket", "Jira", "deployment",
    "RAG", "LangChain", "Weaviate", "monitoring",
    "VPC", "Terraform", "Lakehouse", "EventBridge",
    "health analyzer", "NESA", "report", "notification",
    "Slack", "status update", "triage", "escalation",
    "permission", "security", "networking", "DNS",
    "bug", "issue", "error", "timeout", "OOM",
]

OFF_TOPIC_SIGNALS = [
    "weather", "recipe", "joke", "movie", "song",
    "stock price", "sports score", "dating",
    "write me a poem", "tell me a story",
    "political opinion", "religious",
]


def check_topic(text: str) -> GuardrailResult:
    """
    Check if the query is within the platform health domain.
    Uses keyword matching (in production, use an LLM classifier).
    """
    text_lower = text.lower()

    # Check for off-topic signals
    off_topic_found = [s for s in OFF_TOPIC_SIGNALS if s in text_lower]
    if off_topic_found:
        return GuardrailResult(
            passed=False,
            violations=[Violation(
                guardrail="topic_filter",
                severity="block",
                message=f"Off-topic request detected: {', '.join(off_topic_found)}",
                details={"signals": off_topic_found},
            )],
        )

    # Check for on-topic signals
    on_topic_found = [t for t in ALLOWED_TOPICS if t.lower() in text_lower]
    if on_topic_found:
        return GuardrailResult(passed=True)

    # Ambiguous: allow but warn
    return GuardrailResult(
        passed=True,
        violations=[Violation(
            guardrail="topic_filter",
            severity="info",
            message="No clear topic match — proceeding with caution",
            details={"query_snippet": text[:100]},
        )],
    )


# ── Token Budget Guardrail ──

def check_token_budget(
    message: str,
    conversation_tokens: int = 0,
    max_tokens: int = None,
) -> GuardrailResult:
    """
    Check if the conversation is within token budget.
    Uses rough estimate: 1 token ≈ 4 chars.
    """
    max_budget = max_tokens or MAX_TOKENS_PER_CONVERSATION
    estimated_msg_tokens = len(message) // 4

    total = conversation_tokens + estimated_msg_tokens
    remaining = max_budget - total

    if remaining <= 0:
        return GuardrailResult(
            passed=False,
            violations=[Violation(
                guardrail="token_budget",
                severity="block",
                message=f"Token budget exhausted: {total}/{max_budget}",
                details={"total": total, "max": max_budget, "remaining": 0},
            )],
        )

    if remaining < max_budget * 0.1:  # <10% remaining
        return GuardrailResult(
            passed=True,
            violations=[Violation(
                guardrail="token_budget",
                severity="warn",
                message=f"Token budget low: {remaining} remaining ({total}/{max_budget})",
                details={"total": total, "max": max_budget, "remaining": remaining},
            )],
        )

    return GuardrailResult(passed=True)


# ── Loop Protection Guardrail ──

def check_loop(
    tool_calls: list[dict],
    max_repeats: int = 3,
) -> GuardrailResult:
    """
    Detect if the agent is stuck in a loop (calling same tool with same args).
    """
    if len(tool_calls) < max_repeats:
        return GuardrailResult(passed=True)

    # Check last N calls for identical patterns
    recent = tool_calls[-max_repeats:]
    signatures = []
    for tc in recent:
        sig = f"{tc.get('tool', '')}:{json.dumps(tc.get('args', {}), sort_keys=True)}"
        signatures.append(sig)

    if len(set(signatures)) == 1:
        return GuardrailResult(
            passed=False,
            violations=[Violation(
                guardrail="loop_protection",
                severity="block",
                message=f"Agent loop detected: {recent[0].get('tool', '?')} called {max_repeats}x with same args",
                details={"tool": recent[0].get("tool"), "repeat_count": max_repeats},
            )],
        )

    return GuardrailResult(passed=True)


# ── Hallucination Check (output guardrail) ──

def check_hallucination(
    response: str,
    tool_results: list[str],
    threshold: float = 0.3,
) -> GuardrailResult:
    """
    Basic hallucination check: response should reference tool results.
    Measures word overlap between response and combined tool results.

    In production, use an LLM-as-judge for proper grounding checks.
    """
    if not tool_results or not response:
        return GuardrailResult(passed=True)

    # Combine all tool results
    tool_text = " ".join(tool_results).lower()
    tool_words = set(tool_text.split())

    response_words = set(response.lower().split())

    # Remove common stop words
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                  "being", "have", "has", "had", "do", "does", "did", "will",
                  "would", "could", "should", "may", "might", "must", "shall",
                  "can", "to", "of", "in", "for", "on", "with", "at", "by",
                  "from", "as", "into", "through", "during", "before", "after",
                  "and", "but", "or", "not", "no", "so", "if", "than",
                  "this", "that", "these", "those", "it", "its", "i", "we",
                  "you", "they", "he", "she", "me", "him", "her", "us", "them"}

    tool_words -= stop_words
    response_words -= stop_words

    if not response_words:
        return GuardrailResult(passed=True)

    overlap = len(response_words & tool_words)
    ratio = overlap / len(response_words)

    if ratio < threshold:
        return GuardrailResult(
            passed=True,  # Don't block, just warn
            violations=[Violation(
                guardrail="hallucination_check",
                severity="warn",
                message=f"Low grounding score: {ratio:.2f} (threshold: {threshold})",
                details={"overlap_ratio": round(ratio, 2), "threshold": threshold},
            )],
        )

    return GuardrailResult(passed=True)


# ── Combined Input Guardrails ──

def run_input_guardrails(
    message: str,
    conversation_tokens: int = 0,
    pii_mode: str = "warn",
) -> GuardrailResult:
    """Run all input guardrails. Returns combined result."""
    result = GuardrailResult(passed=True)

    result = result.merge(check_pii(message, mode=pii_mode))
    result = result.merge(check_topic(message))
    result = result.merge(check_token_budget(message, conversation_tokens))

    for v in result.violations:
        level = logging.WARNING if v.severity == "warn" else logging.ERROR
        logger.log(level, f"[{v.guardrail}] {v.message}")

    return result


# ── Combined Output Guardrails ──

def run_output_guardrails(
    response: str,
    tool_results: list[str] = None,
    tool_calls: list[dict] = None,
) -> GuardrailResult:
    """Run all output guardrails. Returns combined result."""
    result = GuardrailResult(passed=True)

    # PII in output
    result = result.merge(check_pii(response, mode="warn"))

    # Hallucination check
    if tool_results:
        result = result.merge(check_hallucination(response, tool_results))

    # Loop protection
    if tool_calls:
        result = result.merge(check_loop(tool_calls))

    for v in result.violations:
        level = logging.WARNING if v.severity == "warn" else logging.ERROR
        logger.log(level, f"[{v.guardrail}] {v.message}")

    return result
