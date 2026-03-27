"""
Guardrails unit tests — validates all 5 guardrail checks independently.

Usage:
  cd project-125 && source .venv/bin/activate
  python scripts/guardrails_test.py
"""

import sys
from pathlib import Path

# Add agent-backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "agent-backend"))

from eval.guardrails import (
    check_pii,
    check_topic,
    check_token_budget,
    check_loop,
    check_hallucination,
    run_input_guardrails,
    run_output_guardrails,
)


def test_pii_detection():
    """Test PII pattern detection and masking."""
    print("\n── PII Detection ──")
    tests = [
        ("SSN 123-45-6789 is mine", True, "SSN", "[SSN-REDACTED]"),
        ("Card: 4111-2222-3333-4444", True, "Credit Card", "[CC-REDACTED]"),
        ("Email me at john@gmail.com", True, "Personal Email", "[EMAIL-REDACTED]"),
        ("AWS key AKIAIOSFODNN7EXAMPLE", True, "AWS", "[AWS-KEY-REDACTED]"),
        ("Normal text about EKS clusters", False, None, None),
        ("My phone is 555-123-4567", True, "Phone", "[PHONE-REDACTED]"),
    ]

    passed = 0
    for text, expect_pii, label_hint, mask_hint in tests:
        result = check_pii(text, mode="block")

        has_pii = len(result.violations) > 0
        if has_pii != expect_pii:
            print(f"  ❌ FAIL: '{text[:40]}...' — expected PII={expect_pii}, got {has_pii}")
            continue

        if expect_pii:
            if not result.sanitized_text or mask_hint not in result.sanitized_text:
                print(f"  ❌ FAIL: '{text[:40]}...' — mask not found in sanitized text")
                continue
            if not result.passed:
                passed += 1
                print(f"  ✅ Blocked: '{text[:40]}...' → {result.sanitized_text[:60]}")
            else:
                print(f"  ❌ FAIL: PII found but not blocked in 'block' mode")
                continue
        else:
            passed += 1
            print(f"  ✅ Clean:  '{text[:40]}...'")

    print(f"  Score: {passed}/{len(tests)}")
    return passed == len(tests)


def test_topic_filter():
    """Test topic relevance filtering."""
    print("\n── Topic Filter ──")
    tests = [
        ("What is the EKS architecture?", True),
        ("Search Jira for Lambda timeouts", True),
        ("How's the weather today?", False),
        ("Tell me a joke about cats", False),
        ("What stock price is AAPL at?", False),
        ("Bedrock API costs are too high", True),
        ("Random ambiguous text", True),  # Ambiguous = allow with warning
    ]

    passed = 0
    for text, expect_pass in tests:
        result = check_topic(text)

        if result.passed != expect_pass:
            print(f"  ❌ FAIL: '{text[:40]}...' — expected pass={expect_pass}, got {result.passed}")
            continue

        passed += 1
        icon = "✅ Allow" if result.passed else "🚫 Block"
        warnings = f" (warnings: {len(result.violations)})" if result.violations else ""
        print(f"  {icon}: '{text[:40]}...'{warnings}")

    print(f"  Score: {passed}/{len(tests)}")
    return passed == len(tests)


def test_token_budget():
    """Test token budget enforcement."""
    print("\n── Token Budget ──")
    tests = [
        ("Short message", 0, 50000, True, False),   # Well within budget
        ("Short message", 49000, 50000, True, True), # Low budget warning
        ("Short message", 50000, 50000, False, False), # Over budget
    ]

    passed = 0
    for text, conv_tokens, max_tokens, expect_pass, expect_warn in tests:
        result = check_token_budget(text, conv_tokens, max_tokens)

        if result.passed != expect_pass:
            print(f"  ❌ FAIL: tokens={conv_tokens}/{max_tokens} — expected pass={expect_pass}, got {result.passed}")
            continue

        has_warn = any(v.severity == "warn" for v in result.violations)
        if has_warn != expect_warn:
            print(f"  ❌ FAIL: tokens={conv_tokens}/{max_tokens} — expected warn={expect_warn}, got {has_warn}")
            continue

        passed += 1
        icon = "✅" if result.passed else "🚫"
        print(f"  {icon}: tokens={conv_tokens}/{max_tokens} pass={result.passed} warn={has_warn}")

    print(f"  Score: {passed}/{len(tests)}")
    return passed == len(tests)


def test_loop_protection():
    """Test agent loop detection."""
    print("\n── Loop Protection ──")
    tests = [
        # No loop — different tools
        ([{"tool": "rag_search", "args": {"q": "a"}},
          {"tool": "search_issues", "args": {"q": "b"}},
          {"tool": "rag_search", "args": {"q": "c"}}], True),
        # Loop — same tool + same args 3x
        ([{"tool": "rag_search", "args": {"q": "same"}},
          {"tool": "rag_search", "args": {"q": "same"}},
          {"tool": "rag_search", "args": {"q": "same"}}], False),
        # Not enough calls
        ([{"tool": "rag_search", "args": {"q": "same"}}], True),
    ]

    passed = 0
    for tool_calls, expect_pass in tests:
        result = check_loop(tool_calls)

        if result.passed != expect_pass:
            print(f"  ❌ FAIL: {len(tool_calls)} calls — expected pass={expect_pass}, got {result.passed}")
            continue

        passed += 1
        icon = "✅" if result.passed else "🚫"
        print(f"  {icon}: {len(tool_calls)} calls, loop={not result.passed}")

    print(f"  Score: {passed}/{len(tests)}")
    return passed == len(tests)


def test_hallucination_check():
    """Test output grounding check."""
    print("\n── Hallucination Check ──")
    tests = [
        # Well-grounded response
        ("The EKS cluster uses Bedrock for RAG queries",
         ["EKS cluster architecture uses Bedrock API for RAG and LangChain"],
         True),
        # Completely ungrounded response
        ("Jupiter is the largest planet in the solar system",
         ["EKS cluster architecture uses Bedrock API"],
         False),
        # No tool results = skip
        ("Any response here", [], True),
    ]

    passed = 0
    for response, tool_results, expect_no_violations in tests:
        result = check_hallucination(response, tool_results)

        has_violations = len(result.violations) > 0
        if has_violations == expect_no_violations and tool_results:
            print(f"  ❌ FAIL: expected violations={not expect_no_violations}, got {has_violations}")
            continue

        passed += 1
        icon = "✅"
        if has_violations:
            icon = "⚠️"
            score = result.violations[0].details.get("overlap_ratio", "?")
            print(f"  {icon}: Low grounding ({score}) — '{response[:40]}...'")
        else:
            print(f"  {icon}: Well-grounded — '{response[:40]}...'")

    print(f"  Score: {passed}/{len(tests)}")
    return passed == len(tests)


def test_combined_input():
    """Test combined input guardrails."""
    print("\n── Combined Input Guardrails ──")
    tests = [
        ("Search for EKS issues", True),
        ("What's the weather?", False),
        ("SSN 123-45-6789 search Jira", True),  # PII warn but topic ok in warn mode
        ("Create ticket with SSN 123-45-6789", True),  # PII warn but doesn't block in warn mode
    ]

    passed = 0
    for text, expect_pass in tests:
        result = run_input_guardrails(text, pii_mode="warn")

        if result.passed != expect_pass:
            print(f"  ❌ FAIL: '{text[:40]}...' — expected pass={expect_pass}, got {result.passed}")
            for v in result.violations:
                print(f"        violation: [{v.guardrail}] {v.severity}: {v.message}")
            continue

        passed += 1
        icon = "✅" if result.passed else "🚫"
        warns = sum(1 for v in result.violations if v.severity == "warn")
        blocks = sum(1 for v in result.violations if v.severity == "block")
        print(f"  {icon}: '{text[:40]}...' (warns={warns}, blocks={blocks})")

    print(f"  Score: {passed}/{len(tests)}")
    return passed == len(tests)


if __name__ == "__main__":
    print("=" * 60)
    print("GUARDRAILS UNIT TESTS")
    print("=" * 60)

    results = {
        "PII Detection": test_pii_detection(),
        "Topic Filter": test_topic_filter(),
        "Token Budget": test_token_budget(),
        "Loop Protection": test_loop_protection(),
        "Hallucination Check": test_hallucination_check(),
        "Combined Input": test_combined_input(),
    }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results.items():
        icon = "✅" if passed else "❌"
        print(f"  {icon} {name}")

    total = sum(results.values())
    print(f"\n  {total}/{len(results)} test suites passed")
    print("=" * 60)
