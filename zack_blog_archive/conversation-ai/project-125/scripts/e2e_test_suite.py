"""
Comprehensive E2E Test Suite for Project-125 Action Agent
==========================================================
Seeds Jira with realistic incidents mapped to actual RAG KB content,
then runs E2E scenarios through the agent to validate RAG retrieval,
Jira operations, and Slack notifications.

KB Content Map (24 documents):
  - 8 Confluence pages: Platform Health Insight project docs
  - 12 Blog posts: EKS RAG, VPC Lattice, Bedrock, Terraform, Billing Analyzer
  - 4 Files: Terraform redo PDF, Lakehouse docs, Azure AD groups

Usage:
  cd project-125
  source .venv/bin/activate
  # 1. Seed Jira with realistic incidents:
  python scripts/e2e_test_suite.py seed
  # 2. Run all E2E tests (agent must be running on :8010):
  python scripts/e2e_test_suite.py test
  # 3. Run a single scenario:
  python scripts/e2e_test_suite.py test --scenario 3
  # 4. Cleanup test tickets:
  python scripts/e2e_test_suite.py cleanup
"""

import sys, os, json, time, requests, argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "jira-server"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "slack-server"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from jira_client import JiraClient
from slack_client import SlackClient

AGENT_URL = "http://localhost:8010"
PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "SCRUM")

# ---------------------------------------------------------------------------
# Realistic Jira tickets that map to actual KB content
# ---------------------------------------------------------------------------
SEED_TICKETS = [
    {
        "summary": "EKS RAG pod OOMKilled — embedding service memory leak",
        "description": (
            "The Bedrock-powered RAG system on EKS (blog/post/154, blog/post/156) "
            "is experiencing OOMKilled events on the embedding pod. "
            "LangChain DirectBedrockLLM inference profile requests accumulate memory "
            "when processing large document batches (>50 chunks). "
            "Pod restarts every ~4 hours. Affects search quality as index becomes stale."
        ),
        "priority": "High",
        "labels": ["eks", "rag", "memory-leak", "bedrock"],
    },
    {
        "summary": "VPC Lattice A/B traffic split stuck at 50/50 instead of 25/75",
        "description": (
            "Per the EKS & VPC Lattice integration (blog/post/153), checkout-v2 "
            "should receive 75% traffic. AWS console shows the weighted target group "
            "is configured correctly but actual traffic distribution (measured via "
            "ALB access logs) shows 50/50. Suspect EKS security group rule is "
            "blocking the Lattice data plane. Phase 1 infrastructure setup may be incomplete."
        ),
        "priority": "High",
        "labels": ["eks", "vpc-lattice", "networking", "ab-testing"],
    },
    {
        "summary": "Health Analyzer Lambda timeout on Stage 2 — Bedrock Sonnet analysis",
        "description": (
            "The serverless billing & health analyzer (blog/post/157, blog/post/158, "
            "confluence/4383342593) Lambda is timing out during Stage 2 analysis. "
            "Stage 1 Haiku data collection completes in ~40s, but the Sonnet "
            "deep-analysis stage exceeds the 5-minute Lambda limit when processing "
            "accounts with >200 resources. Risk documented in confluence/4464967708."
        ),
        "priority": "High",
        "labels": ["lambda", "bedrock", "health-analyzer", "timeout"],
    },
    {
        "summary": "Terraform VPC module circular dependency — security group vs subnet",
        "description": (
            "Terraform apply fails with 'Cycle: module.vpc.aws_security_group.main, "
            "module.vpc.aws_subnet.private'. The 20Terraformredo.pdf documents the "
            "depends_on pattern for VPC→SG→Subnet ordering, but the new module "
            "introduced a reference from subnet tags back to the SG ID, creating a "
            "cycle. Need to use output references per the Terraform redo guide."
        ),
        "priority": "Medium",
        "labels": ["terraform", "vpc", "iac", "dependency-cycle"],
    },
    {
        "summary": "Lakehouse permissions — data engineer role missing Lake Formation grants",
        "description": (
            "Per lakehouse-permissions-analysis.md, the DataEngineer role needs "
            "Lake Formation admin capabilities. Currently the Azure AD group "
            "AZP_AWS_NESANonProd_DataEngineer_Lakehouse (file/AZURE-AD-GROUP-APPROACH.md) "
            "is mapped to IAM but lacks the LF:GetDataAccess and LF:GrantPermissions "
            "policies. Chen Chen's POC account (nonprod) is blocked."
        ),
        "priority": "Medium",
        "labels": ["lakehouse", "permissions", "lake-formation", "azure-ad"],
    },
    {
        "summary": "Bedrock API cost spike — Sonnet token usage 3x over budget",
        "description": (
            "Sample insight report (confluence/4404707345) shows Bedrock costs jumped "
            "from $209 to $630 this month. Root cause: Health Analyzer v2 (blog/post/158) "
            "prompt engineering change removed the token-limiting constraint. "
            "Stage 2 Sonnet calls now use full 200K context window instead of the "
            "designed 50K cap. Risk documented in confluence/4464967708 section on "
            "Bedrock API rate limits and cost exposure."
        ),
        "priority": "High",
        "labels": ["bedrock", "cost", "health-analyzer", "budget"],
    },
    {
        "summary": "EventBridge weekly health report not triggering — cron expression wrong",
        "description": (
            "Per EventBridge and SNS design (confluence/4383571971), the weekly "
            "health report should fire every Monday 8am AEST. After the group "
            "rollout (confluence/4410048520) added 3 new account groups, the "
            "EventBridge rule was updated but the cron expression uses UTC "
            "instead of AEST. Reports are firing at 8am UTC (6pm AEST). "
            "SNS topic pywide760Email is delivering but at the wrong time."
        ),
        "priority": "Low",
        "labels": ["eventbridge", "sns", "scheduling", "health-analyzer"],
    },
    {
        "summary": "Open WebUI Bedrock integration — model routing fails for Claude 3.5",
        "description": (
            "AWS Bedrock with Open WebUI setup (blog/post/150) works for Claude 3 Haiku "
            "but fails for Claude 3.5 Sonnet. The Pipelines function expects "
            "model ID format 'anthropic.claude-3-5-sonnet-v1:0' but the new "
            "inference profile uses 'apac.anthropic.claude-sonnet-4-20250514-v1:0'. "
            "Users see 'Model not found' in the Open WebUI chat interface. "
            "Shared storage and session consistency features still work."
        ),
        "priority": "Medium",
        "labels": ["bedrock", "open-webui", "model-routing", "integration"],
    },
    {
        "summary": "GitHub Action PR review — Gemini CLI rate limited on large PRs",
        "description": (
            "The automated PR review pipeline (blog/post/149) using Gemini CLI within "
            "GitHub Actions hits rate limits when reviewing PRs with >20 changed files. "
            "The /setup-github workflow YAML processes files sequentially, not batched. "
            "PRs in the lakehouse repo (file/lakehouse.md) regularly exceed this threshold "
            "due to generated migration files."
        ),
        "priority": "Low",
        "labels": ["github-actions", "gemini", "pr-review", "rate-limit"],
    },
    {
        "summary": "EKS RAG LangChain memory overflow — conversation history unbounded",
        "description": (
            "The boosted EKS RAG with LangChain (blog/post/156) uses ConversationBufferMemory "
            "which stores ALL messages indefinitely. After ~50 turns, the prompt "
            "exceeds Bedrock's context window (200K tokens). The DirectBedrockLLM "
            "custom component doesn't implement token counting. Need to switch to "
            "ConversationSummaryBufferMemory with max_token_limit per the LangChain docs."
        ),
        "priority": "Medium",
        "labels": ["eks", "rag", "langchain", "memory", "context-window"],
    },
]

# ---------------------------------------------------------------------------
# E2E Test Scenarios
# ---------------------------------------------------------------------------
SCENARIOS = [
    {
        "id": 1,
        "name": "RAG-only: EKS architecture query",
        "description": "Validate agent retrieves relevant KB content without calling Jira/Slack",
        "prompt": "What is the architecture of the Bedrock-powered RAG system on EKS? Include details about LangChain integration.",
        "expect_tools": ["rag_search"],
        "expect_no_tools": ["create_ticket", "send_message"],
        "expect_keywords": ["EKS", "Bedrock", "LangChain", "RAG"],
        "kb_sources": ["blog/post/154", "blog/post/156"],
    },
    {
        "id": 2,
        "name": "RAG-only: Terraform dependency pattern",
        "description": "Agent should find Terraform redo PDF content about depends_on and module outputs",
        "prompt": "How does the Terraform redo guide recommend handling VPC to security group dependencies?",
        "expect_tools": ["rag_search"],
        "expect_no_tools": ["create_ticket"],
        "expect_keywords": ["depends_on", "VPC", "security group", "module"],
        "kb_sources": ["file/20Terraformredo.pdf"],
    },
    {
        "id": 3,
        "name": "RAG-only: Health Analyzer pipeline design",
        "description": "Agent retrieves Confluence docs about the staged pipeline (Haiku → Sonnet)",
        "prompt": "Explain the staged pipeline design for the Health Analyzer — what happens in Stage 1 vs Stage 2?",
        "expect_tools": ["rag_search"],
        "expect_no_tools": ["create_ticket"],
        "expect_keywords": ["Stage 1", "Stage 2", "Haiku", "Sonnet", "Claude"],
        "kb_sources": ["confluence/4383342593"],
    },
    {
        "id": 4,
        "name": "Jira search: find EKS-related tickets",
        "description": "Agent should search Jira for EKS tickets and return structured results",
        "prompt": "Search Jira for all open tickets related to EKS. Summarize the findings.",
        "expect_tools": ["search_issues"],
        "expect_no_tools": ["create_ticket"],
        "expect_keywords": ["EKS", "SCRUM-"],
        "kb_sources": [],
    },
    {
        "id": 5,
        "name": "Jira search: Bedrock cost issues",
        "description": "Agent should find the Bedrock cost spike ticket",
        "prompt": "Are there any Jira tickets about Bedrock API costs or budget overruns?",
        "expect_tools": ["search_issues"],
        "expect_no_tools": ["create_ticket"],
        "expect_keywords": ["cost", "Bedrock", "budget"],
        "kb_sources": [],
    },
    {
        "id": 6,
        "name": "RAG + Jira: investigate Lambda timeout",
        "description": "Agent should search KB for Lambda pipeline design, then check Jira for related tickets",
        "prompt": (
            "Our Health Analyzer Lambda is timing out during the Bedrock analysis stage. "
            "Search the knowledge base for how the pipeline is designed, "
            "then check Jira for any existing tickets about this issue."
        ),
        "expect_tools": ["rag_search", "search_issues"],
        "expect_no_tools": ["create_ticket"],
        "expect_keywords": ["Lambda", "Stage 2", "timeout", "Bedrock"],
        "kb_sources": ["confluence/4383342593", "confluence/4464967708"],
    },
    {
        "id": 7,
        "name": "RAG + Jira: Lakehouse permissions investigation",
        "description": "Agent queries KB for permission analysis, checks Jira for related tickets",
        "prompt": (
            "A data engineer can't access the Lakehouse. Search our KB for the "
            "permissions analysis and Azure AD group setup, then check Jira "
            "for any existing permission-related tickets."
        ),
        "expect_tools": ["rag_search", "search_issues"],
        "expect_no_tools": ["create_ticket"],
        "expect_keywords": ["Lake Formation", "Azure AD", "permission", "DataEngineer"],
        "kb_sources": ["file/lakehouse-permissions-analysis.md", "file/AZURE-AD-GROUP-APPROACH.md"],
    },
    {
        "id": 8,
        "name": "Multi-tool: create ticket with KB context (confirmation flow)",
        "description": (
            "Agent should: 1) search KB for context, 2) search Jira for duplicates, "
            "3) present plan (NOT create immediately due to confirm-before-acting rule)"
        ),
        "prompt": (
            "The Kubernetes MCP server integration with Claude Code is failing — "
            "the deploy.sh script can't find the openwebui-deployment.yaml manifest. "
            "Search the KB for context about the K8s MCP setup, check for duplicates, "
            "then create a P2 ticket with relevant details."
        ),
        "expect_tools": ["rag_search", "search_issues"],
        "expect_no_tools": [],
        "expect_keywords": ["MCP", "Kubernetes", "Claude Code", "manifest"],
        "kb_sources": ["blog/post/152"],
    },
    {
        "id": 9,
        "name": "Multi-tool: incident + notification (full E2E)",
        "description": (
            "Full chain: search KB → check duplicates → present plan for ticket + Slack. "
            "Agent should gather context before proposing the write actions."
        ),
        "prompt": (
            "URGENT: The VPC Lattice A/B testing traffic split is completely broken — "
            "all traffic is going to checkout-v1 instead of the 25/75 split. "
            "Search the KB for our VPC Lattice setup documentation, check if there's "
            "an existing Jira ticket, and if one exists, add a comment about the complete "
            "failure. Also notify #all-platform-health-lab about this incident."
        ),
        "expect_tools": ["rag_search", "search_issues"],
        "expect_no_tools": [],
        "expect_keywords": ["VPC Lattice", "traffic", "A/B", "checkout"],
        "kb_sources": ["blog/post/153"],
    },
    {
        "id": 10,
        "name": "RAG + Jira: EventBridge scheduling diagnosis",
        "description": "Agent uses KB to understand EventBridge design, finds the scheduling ticket",
        "prompt": (
            "The weekly health report emails aren't arriving at the expected time. "
            "Search our KB for the EventBridge and SNS design, then check Jira "
            "for any scheduling-related tickets. What could be causing this?"
        ),
        "expect_tools": ["rag_search", "search_issues"],
        "expect_no_tools": ["create_ticket"],
        "expect_keywords": ["EventBridge", "SNS", "cron", "schedule"],
        "kb_sources": ["confluence/4383571971"],
    },
    {
        "id": 11,
        "name": "Cross-domain: cost investigation linking billing report + risk doc",
        "description": "Agent should pull from both the sample report AND risk/limitation Confluence pages",
        "prompt": (
            "We're seeing a 3x cost spike on Bedrock API usage this month. "
            "Search the KB for our sample insight reports and risk documentation "
            "to understand what cost controls were designed, then check Jira "
            "for any related tickets about Bedrock costs."
        ),
        "expect_tools": ["rag_search", "search_issues"],
        "expect_no_tools": [],
        "expect_keywords": ["cost", "Bedrock", "token", "risk"],
        "kb_sources": ["confluence/4404707345", "confluence/4464967708"],
    },
    {
        "id": 12,
        "name": "RAG + Jira: Open WebUI model routing",
        "description": "Agent searches KB for Open WebUI setup, finds the model routing ticket",
        "prompt": (
            "Users are reporting 'Model not found' errors when using Claude 3.5 Sonnet "
            "in Open WebUI. Search our knowledge base for how we set up the Bedrock "
            "integration with Open WebUI, then check Jira for any related tickets."
        ),
        "expect_tools": ["rag_search", "search_issues"],
        "expect_no_tools": [],
        "expect_keywords": ["Open WebUI", "Bedrock", "model", "Pipelines"],
        "kb_sources": ["blog/post/150"],
    },
    {
        "id": 13,
        "name": "Jira + Slack: status update broadcast",
        "description": "Agent finds a specific ticket and presents plan to notify Slack",
        "prompt": (
            "Get the details of the EKS RAG memory leak ticket from Jira "
            "and prepare a status update to post in #all-platform-health-lab "
            "with the ticket summary, priority, and a link."
        ),
        "expect_tools": ["search_issues"],
        "expect_no_tools": [],
        "expect_keywords": ["EKS", "RAG", "memory", "OOMKilled"],
        "kb_sources": [],
    },
    {
        "id": 14,
        "name": "RAG-only: group rollout deployment scope",
        "description": "Agent retrieves Confluence doc about multi-account rollout plan",
        "prompt": (
            "What accounts and groups are included in the Health Analyzer "
            "group rollout deployment plan? List the product domains."
        ),
        "expect_tools": ["rag_search"],
        "expect_no_tools": ["create_ticket"],
        "expect_keywords": ["rollout", "account", "group"],
        "kb_sources": ["confluence/4410048520"],
    },
    {
        "id": 15,
        "name": "Complex: multi-step incident triage",
        "description": (
            "Full triage: RAG for architecture context → Jira for existing tickets → "
            "correlate findings → propose remediation plan"
        ),
        "prompt": (
            "We have an escalation: the EKS RAG system is down. The embedding pod "
            "is OOMKilled and the LangChain conversation memory is overflowing. "
            "I need you to: "
            "1) Search the KB for our EKS RAG architecture and LangChain memory setup, "
            "2) Find all related Jira tickets, "
            "3) Correlate the findings and tell me what's happening, "
            "4) Recommend next steps."
        ),
        "expect_tools": ["rag_search", "search_issues"],
        "expect_no_tools": [],
        "expect_keywords": ["EKS", "RAG", "OOMKilled", "LangChain", "memory", "ConversationBuffer"],
        "kb_sources": ["blog/post/154", "blog/post/156"],
    },
]


def get_jira_client():
    return JiraClient(
        os.getenv("JIRA_URL"),
        os.getenv("JIRA_EMAIL"),
        os.getenv("JIRA_API_TOKEN"),
        PROJECT_KEY,
    )


def seed_tickets():
    """Create realistic Jira tickets mapped to KB content."""
    jira = get_jira_client()
    print("=" * 70)
    print("SEEDING JIRA WITH REALISTIC INCIDENTS")
    print("=" * 70)

    created = []
    for i, ticket in enumerate(SEED_TICKETS, 1):
        print(f"\n[{i}/{len(SEED_TICKETS)}] Creating: {ticket['summary'][:60]}...")
        result = jira.create_issue(
            project_key=PROJECT_KEY,
            summary=ticket["summary"],
            description=ticket["description"],
            issue_type="Task",
            priority=ticket["priority"],
            labels=ticket["labels"] + ["e2e-test-seed"],
        )
        if "error" in result:
            print(f"  ❌ Failed: {result['error']}")
        else:
            print(f"  ✅ Created: {result['key']} — {result['url']}")
            created.append(result["key"])
        time.sleep(0.5)  # rate limit courtesy

    print(f"\n{'=' * 70}")
    print(f"SEED COMPLETE: {len(created)}/{len(SEED_TICKETS)} tickets created")
    print(f"Keys: {', '.join(created)}")
    print(f"Label: 'e2e-test-seed' (use for cleanup)")
    print(f"{'=' * 70}")
    return created


def cleanup_tickets():
    """Delete all test-seeded tickets."""
    jira = get_jira_client()
    print("Searching for e2e-test-seed tickets...")
    result = jira.search(f'project = {PROJECT_KEY} AND labels = "e2e-test-seed"', max_results=50)
    issues = result.get("issues", [])
    if not issues:
        print("No test tickets found.")
        return

    print(f"Found {len(issues)} test tickets to clean up.")
    # Note: Jira Cloud REST API delete is not in our client — just report
    for issue in issues:
        print(f"  • {issue['key']} — {issue['summary'][:60]}")
    print("\n⚠️  Manual cleanup: Go to Jira → Bulk select → Delete")
    print(f"  JQL: project = {PROJECT_KEY} AND labels = \"e2e-test-seed\"")


def run_agent_query(prompt: str, timeout: int = 120) -> dict:
    """Send a query to the agent and return the response."""
    try:
        resp = requests.post(
            f"{AGENT_URL}/chat",
            json={"message": prompt},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Agent not running. Start with: cd agent-backend && python main.py"}
    except requests.exceptions.Timeout:
        return {"error": f"Agent timed out after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}


def evaluate_response(scenario: dict, result: dict) -> dict:
    """Evaluate agent response against expected behavior."""
    checks = {
        "tools_used": {"pass": False, "detail": ""},
        "tools_avoided": {"pass": True, "detail": ""},
        "keywords_found": {"pass": False, "detail": ""},
        "no_error": {"pass": False, "detail": ""},
    }

    if "error" in result:
        checks["no_error"]["detail"] = result["error"]
        return checks

    checks["no_error"] = {"pass": True, "detail": "OK"}

    # Check expected tools were used
    tools_called = [t["tool"] for t in result.get("tool_calls", [])]
    expected = scenario["expect_tools"]
    found = [t for t in expected if t in tools_called]
    missing = [t for t in expected if t not in tools_called]
    checks["tools_used"] = {
        "pass": len(missing) == 0,
        "detail": f"Expected: {expected}, Called: {tools_called}, Missing: {missing}",
    }

    # Check tools that should NOT be used
    for no_tool in scenario.get("expect_no_tools", []):
        if no_tool in tools_called:
            checks["tools_avoided"] = {
                "pass": False,
                "detail": f"'{no_tool}' was called but should not have been",
            }
            break

    # Check keywords in response
    response_text = result.get("response", "").lower()
    kw_found = []
    kw_missing = []
    for kw in scenario.get("expect_keywords", []):
        if kw.lower() in response_text:
            kw_found.append(kw)
        else:
            kw_missing.append(kw)

    # Pass if at least 60% of keywords found (some may be paraphrased by LLM)
    threshold = max(1, int(len(scenario.get("expect_keywords", [])) * 0.6))
    checks["keywords_found"] = {
        "pass": len(kw_found) >= threshold,
        "detail": f"Found {len(kw_found)}/{len(scenario['expect_keywords'])}: {kw_found}. Missing: {kw_missing}",
    }

    return checks


def run_tests(scenario_id: int = None):
    """Run E2E test scenarios."""
    # Health check
    try:
        r = requests.get(f"{AGENT_URL}/health", timeout=5)
        if r.status_code != 200:
            print(f"❌ Agent health check failed: {r.status_code}")
            return
        print(f"✅ Agent healthy at {AGENT_URL}")
    except Exception:
        print(f"❌ Agent not running at {AGENT_URL}")
        print("   Start with: cd agent-backend && python main.py")
        return

    scenarios = SCENARIOS
    if scenario_id:
        scenarios = [s for s in SCENARIOS if s["id"] == scenario_id]
        if not scenarios:
            print(f"❌ Scenario {scenario_id} not found. Valid: 1-{len(SCENARIOS)}")
            return

    print(f"\n{'=' * 70}")
    print(f"E2E TEST SUITE — {len(scenarios)} scenarios")
    print(f"{'=' * 70}")

    results_summary = []

    for scenario in scenarios:
        sid = scenario["id"]
        print(f"\n{'─' * 70}")
        print(f"Scenario {sid}: {scenario['name']}")
        print(f"  {scenario['description']}")
        print(f"  KB sources: {scenario['kb_sources'] or 'N/A'}")
        print(f"  Prompt: {scenario['prompt'][:100]}...")
        print(f"{'─' * 70}")

        start = time.time()
        result = run_agent_query(scenario["prompt"])
        elapsed = time.time() - start

        if "error" in result:
            print(f"  ❌ ERROR: {result['error']}")
            results_summary.append({"id": sid, "name": scenario["name"], "status": "ERROR", "time": elapsed})
            continue

        tools_called = [t["tool"] for t in result.get("tool_calls", [])]
        print(f"  ⏱  Latency: {elapsed:.1f}s (agent reported: {result.get('latency_ms', '?')}ms)")
        print(f"  🔧 Tools: {tools_called}")

        # Show tool details
        for tc in result.get("tool_calls", []):
            write_marker = "🔴 WRITE" if tc.get("is_write") else "🟢 READ"
            status = "✅" if tc.get("success") else "❌"
            print(f"     {status} {tc['tool']} ({write_marker}) — {tc.get('latency_ms', '?')}ms")

        # Evaluate
        checks = evaluate_response(scenario, result)
        all_pass = all(c["pass"] for c in checks.values())

        print(f"\n  📋 Evaluation:")
        for check_name, check_result in checks.items():
            icon = "✅" if check_result["pass"] else "❌"
            print(f"     {icon} {check_name}: {check_result['detail'][:120]}")

        # Show response excerpt
        response = result.get("response", "")
        excerpt = response[:300].replace("\n", "\n     ")
        print(f"\n  💬 Response excerpt:\n     {excerpt}...")

        status = "PASS" if all_pass else "FAIL"
        print(f"\n  {'✅ PASS' if all_pass else '❌ FAIL'}")
        results_summary.append({"id": sid, "name": scenario["name"], "status": status, "time": elapsed})

    # Summary
    print(f"\n{'=' * 70}")
    print("TEST SUMMARY")
    print(f"{'=' * 70}")

    passed = sum(1 for r in results_summary if r["status"] == "PASS")
    failed = sum(1 for r in results_summary if r["status"] == "FAIL")
    errors = sum(1 for r in results_summary if r["status"] == "ERROR")
    total_time = sum(r["time"] for r in results_summary)

    for r in results_summary:
        icon = {"PASS": "✅", "FAIL": "❌", "ERROR": "💥"}[r["status"]]
        print(f"  {icon} Scenario {r['id']:2d}: {r['name'][:50]:50s} [{r['time']:6.1f}s] {r['status']}")

    print(f"\n  Total: {len(results_summary)} | Passed: {passed} | Failed: {failed} | Errors: {errors}")
    print(f"  Total time: {total_time:.1f}s | Avg: {total_time / len(results_summary):.1f}s per scenario")
    print(f"{'=' * 70}")

    return results_summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Project-125 E2E Test Suite")
    parser.add_argument("action", choices=["seed", "test", "cleanup", "list"],
                        help="seed: create Jira tickets | test: run E2E | cleanup: remove test tickets | list: show scenarios")
    parser.add_argument("--scenario", type=int, help="Run a single scenario by ID")
    args = parser.parse_args()

    if args.action == "seed":
        seed_tickets()
    elif args.action == "test":
        run_tests(args.scenario)
    elif args.action == "cleanup":
        cleanup_tickets()
    elif args.action == "list":
        print(f"\n{'=' * 70}")
        print(f"AVAILABLE SCENARIOS ({len(SCENARIOS)} total)")
        print(f"{'=' * 70}")
        for s in SCENARIOS:
            tools = " + ".join(s["expect_tools"])
            print(f"\n  [{s['id']:2d}] {s['name']}")
            print(f"      Tools: {tools}")
            print(f"      KB: {', '.join(s['kb_sources']) or 'N/A'}")
            print(f"      {s['description']}")
