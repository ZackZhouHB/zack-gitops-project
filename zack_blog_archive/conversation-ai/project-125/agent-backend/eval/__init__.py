"""
Eval module — Phase F: Evaluation pipeline + runtime guardrails.

Components:
  - golden_test_set: 22 curated test cases across 5 categories
  - runner: Batch evaluation with 5-metric scoring
  - guardrails: Runtime safety checks (PII, topic, token, loop, hallucination)
"""

from eval.guardrails import (
    run_input_guardrails,
    run_output_guardrails,
    check_pii,
    check_topic,
    check_token_budget,
    check_loop,
    check_hallucination,
    GuardrailResult,
    Violation,
)
