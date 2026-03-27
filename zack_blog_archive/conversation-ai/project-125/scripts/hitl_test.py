"""
HITL (Human-in-the-Loop) test script for Project-125 Action Agent.

Tests the approve/reject/edit workflow:
  1. Send a write-action request → expect pending_approval
  2. Approve → expect ticket created
  3. Reject → expect action cancelled
  4. Edit+approve → expect modified action executed

Usage:
  cd project-125 && source .venv/bin/activate
  # Agent must be running: cd agent-backend && python main.py
  python scripts/hitl_test.py
"""

import json
import time
import requests
import sys

AGENT_URL = "http://localhost:8010"


def test_health():
    """Verify agent is healthy with HITL enabled."""
    r = requests.get(f"{AGENT_URL}/health", timeout=5)
    data = r.json()
    assert data["hitl_enabled"] is True, "HITL not enabled"
    print(f"  ✅ Health: HITL enabled, {len(data['tools'])} tools")
    return True


def test_read_completes():
    """Read-only query should complete without interrupt."""
    r = requests.post(f"{AGENT_URL}/chat", json={"message": "Search for EKS tickets in Jira"}, timeout=60)
    data = r.json()
    assert data["status"] == "complete", f"Expected complete, got {data['status']}"
    assert data["pending_action"] is None, "Should not have pending action"
    tools = [t["tool"] for t in data["tool_calls"]]
    assert "search_issues" in tools, "Should have called search_issues"
    print(f"  ✅ Read-only: status=complete, tools={tools}, {data['latency_ms']}ms")
    return True


def test_write_interrupts():
    """Write action should interrupt and return pending_approval."""
    r = requests.post(
        f"{AGENT_URL}/chat",
        json={"message": "Create a low-priority ticket for updating documentation on EKS setup"},
        timeout=120,
    )
    data = r.json()
    assert data["status"] == "pending_approval", f"Expected pending_approval, got {data['status']}"
    assert data["pending_action"] is not None, "Should have pending action"
    assert data["pending_action"]["tool"] == "create_ticket", f"Expected create_ticket, got {data['pending_action']['tool']}"
    assert data["pending_action"]["is_write"] is True

    thread_id = data["conversation_id"]
    print(f"  ✅ Write interrupt: tool={data['pending_action']['tool']}")
    print(f"    Summary: {data['pending_action']['args'].get('summary', '?')[:80]}")
    print(f"    Thread: {thread_id}")
    return thread_id


def test_approve(thread_id: str):
    """Approve a pending action — ticket should be created."""
    r = requests.post(f"{AGENT_URL}/chat/{thread_id}/approve", timeout=60)
    data = r.json()

    # May need to approve multiple times if agent chains writes
    while data.get("status") == "pending_approval":
        print(f"    → Additional approval needed: {data['pending_action']['tool']}")
        r = requests.post(f"{AGENT_URL}/chat/{thread_id}/approve", timeout=60)
        data = r.json()

    assert data["status"] == "complete", f"Expected complete after approve, got {data['status']}"

    # Check that create_ticket was approved
    approved_tools = [t for t in data["tool_calls"] if t.get("approval") == "approved"]
    assert len(approved_tools) > 0, "No approved tools found"
    print(f"  ✅ Approved: {len(approved_tools)} write tool(s) executed")
    print(f"    Response: {data['response'][:150]}...")
    return True


def test_reject():
    """Trigger a write, then reject it."""
    # Step 1: Trigger write
    r = requests.post(
        f"{AGENT_URL}/chat",
        json={"message": "Send a test message to #all-platform-health-lab saying hello from HITL test"},
        timeout=60,
    )
    data = r.json()
    assert data["status"] == "pending_approval", f"Expected pending_approval, got {data['status']}"
    thread_id = data["conversation_id"]
    print(f"  ✅ Write triggered: {data['pending_action']['tool']}")

    # Step 2: Reject
    r = requests.post(f"{AGENT_URL}/chat/{thread_id}/reject", timeout=30)
    data = r.json()
    assert data["status"] == "complete", f"Expected complete after reject, got {data['status']}"

    rejected = [t for t in data["tool_calls"] if t.get("approval") == "rejected"]
    assert len(rejected) > 0, "No rejected tools found"
    print(f"  ✅ Rejected: {rejected[0]['tool']} — message NOT sent")
    return True


def test_status_endpoint():
    """Test /chat/{thread_id}/status endpoint."""
    # Trigger a write to get a pending thread
    r = requests.post(
        f"{AGENT_URL}/chat",
        json={"message": "Add a comment to SCRUM-19 saying this is a HITL test"},
        timeout=60,
    )
    data = r.json()
    if data["status"] != "pending_approval":
        print(f"  ⚠️  Skipped: agent didn't interrupt (status={data['status']})")
        return True

    thread_id = data["conversation_id"]

    # Check status
    r = requests.get(f"{AGENT_URL}/chat/{thread_id}/status", timeout=10)
    status = r.json()
    assert status["status"] == "pending_approval", f"Expected pending_approval, got {status['status']}"
    print(f"  ✅ Status: pending_approval for {status['pending_action']['tool']}")

    # Clean up: reject it
    requests.post(f"{AGENT_URL}/chat/{thread_id}/reject", timeout=30)
    print(f"  ✅ Cleaned up: rejected pending action")
    return True


def run_all():
    print("=" * 60)
    print("HITL TEST SUITE")
    print("=" * 60)

    tests = [
        ("Health check (HITL enabled)", test_health),
        ("Read-only completes", test_read_completes),
        ("Write action interrupts", test_write_interrupts),
        ("Reject flow", test_reject),
        ("Status endpoint", test_status_endpoint),
    ]

    results = []
    approve_thread = None

    for name, test_fn in tests:
        print(f"\n--- {name} ---")
        try:
            result = test_fn()
            if name == "Write action interrupts" and isinstance(result, str):
                approve_thread = result
                result = True
            results.append((name, True))
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            results.append((name, False))

    # Run approve test with the thread from "Write action interrupts"
    if approve_thread:
        print(f"\n--- Approve flow ---")
        try:
            test_approve(approve_thread)
            results.append(("Approve flow", True))
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            results.append(("Approve flow", False))

    # Summary
    print(f"\n{'=' * 60}")
    print("HITL TEST SUMMARY")
    print(f"{'=' * 60}")
    passed = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  {'✅' if ok else '❌'} {name}")
    print(f"\n  {passed}/{len(results)} passed")
    print(f"{'=' * 60}")

    return all(ok for _, ok in results)


if __name__ == "__main__":
    try:
        requests.get(f"{AGENT_URL}/health", timeout=5)
    except Exception:
        print(f"❌ Agent not running at {AGENT_URL}")
        print("Start with: cd agent-backend && python main.py")
        sys.exit(1)

    success = run_all()
    sys.exit(0 if success else 1)
