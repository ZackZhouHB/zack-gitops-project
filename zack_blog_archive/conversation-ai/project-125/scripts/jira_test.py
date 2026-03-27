#!/usr/bin/env python3
"""
Jira Cloud API Test Script — Project 125 Phase B

Tests all CRUD operations against Jira Cloud REST API v3.
Run: python scripts/jira_test.py

Prerequisites:
  - Jira Cloud free tier set up
  - .env file with JIRA_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY
"""

import os
import sys
import json
import requests
from base64 import b64encode
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

JIRA_URL = os.getenv("JIRA_URL")  # e.g., https://your-site.atlassian.net
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY", "PLAT")


def get_auth_header() -> dict:
    """Basic auth header for Jira Cloud REST API."""
    token = b64encode(f"{JIRA_EMAIL}:{JIRA_API_TOKEN}".encode()).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def check_config():
    """Verify all required environment variables are set."""
    missing = []
    for var in ["JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"]:
        if not os.getenv(var):
            missing.append(var)
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("   Copy .env.example to .env and fill in your Jira credentials.")
        sys.exit(1)
    print(f"✅ Config loaded: {JIRA_URL} ({JIRA_EMAIL})")


# ─────────────────────────────────────
# Test 1: Connectivity — Get Server Info
# ─────────────────────────────────────
def test_connectivity():
    """Verify we can reach the Jira instance."""
    print("\n── Test 1: Connectivity ──")
    url = f"{JIRA_URL}/rest/api/3/serverInfo"
    resp = requests.get(url, headers=get_auth_header())

    if resp.status_code == 200:
        info = resp.json()
        print(f"✅ Connected to: {info.get('baseUrl')}")
        print(f"   Version: {info.get('version')}")
        print(f"   Deployment: {info.get('deploymentType')}")
        return True
    else:
        print(f"❌ Failed ({resp.status_code}): {resp.text[:200]}")
        return False


# ─────────────────────────────────────
# Test 2: Get Project
# ─────────────────────────────────────
def test_get_project():
    """Verify the project exists."""
    print(f"\n── Test 2: Get Project ({JIRA_PROJECT_KEY}) ──")
    url = f"{JIRA_URL}/rest/api/3/project/{JIRA_PROJECT_KEY}"
    resp = requests.get(url, headers=get_auth_header())

    if resp.status_code == 200:
        project = resp.json()
        print(f"✅ Project found: {project['key']} — {project['name']}")
        print(f"   Type: {project.get('projectTypeKey')}")
        return True
    else:
        print(f"❌ Project {JIRA_PROJECT_KEY} not found ({resp.status_code})")
        print(f"   Create a project with key '{JIRA_PROJECT_KEY}' in Jira first.")
        return False


# ─────────────────────────────────────
# Test 3: Create a Ticket
# ─────────────────────────────────────
def test_create_ticket() -> str | None:
    """Create a test ticket and return the issue key."""
    print("\n── Test 3: Create Ticket ──")
    url = f"{JIRA_URL}/rest/api/3/issue"
    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": "[TEST] API latency spike — connection pool exhaustion",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "Test ticket created by project-125 jira_test.py. "
                                "This simulates an agent-created ticket enriched with KB context.",
                            }
                        ],
                    },
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "KB Context: Past incidents suggest connection pool "
                                "exhaustion as root cause. Runbook: check max_connections "
                                "and idle_timeout settings.",
                            }
                        ],
                    },
                ],
            },
            "issuetype": {"name": "Task"},
            "priority": {"name": "Medium"},
            "labels": ["agent-created", "test", "api-latency"],
        }
    }

    resp = requests.post(url, headers=get_auth_header(), json=payload)

    if resp.status_code == 201:
        issue = resp.json()
        key = issue["key"]
        print(f"✅ Created: {key}")
        print(f"   URL: {JIRA_URL}/browse/{key}")
        print(f"   ID: {issue['id']}")
        return key
    else:
        print(f"❌ Failed ({resp.status_code}): {resp.text[:300]}")
        return None


# ─────────────────────────────────────
# Test 4: Search with JQL
# ─────────────────────────────────────
def test_search_jql(issue_key: str = None):
    """Search for tickets using JQL."""
    print("\n── Test 4: Search (JQL) ──")
    jql = f'project = {JIRA_PROJECT_KEY} AND labels = "agent-created" ORDER BY created DESC'
    # Jira Cloud migrated from /rest/api/3/search to /rest/api/3/search/jql (2026)
    url = f"{JIRA_URL}/rest/api/3/search/jql"
    params = {"jql": jql, "maxResults": 5, "fields": "summary,status,priority,labels,created"}

    resp = requests.get(url, headers=get_auth_header(), params=params)

    if resp.status_code == 200:
        results = resp.json()
        issues = results.get("issues", [])
        total = results.get("total", len(issues))
        print(f"✅ Found {total} issue(s) matching JQL:")
        for issue in issues:
            fields = issue["fields"]
            print(f"   {issue['key']}: {fields['summary']}")
            print(f"     Status: {fields['status']['name']}, Priority: {fields['priority']['name']}")
        return True
    else:
        print(f"❌ Search failed ({resp.status_code}): {resp.text[:200]}")
        return False


# ─────────────────────────────────────
# Test 5: Get Ticket Details
# ─────────────────────────────────────
def test_get_ticket(issue_key: str):
    """Get full details for a specific ticket."""
    print(f"\n── Test 5: Get Ticket ({issue_key}) ──")
    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}"
    resp = requests.get(url, headers=get_auth_header())

    if resp.status_code == 200:
        issue = resp.json()
        fields = issue["fields"]
        print(f"✅ {issue['key']}: {fields['summary']}")
        print(f"   Status: {fields['status']['name']}")
        print(f"   Priority: {fields['priority']['name']}")
        print(f"   Labels: {fields.get('labels', [])}")
        print(f"   Created: {fields['created']}")
        return True
    else:
        print(f"❌ Failed ({resp.status_code}): {resp.text[:200]}")
        return False


# ─────────────────────────────────────
# Test 6: Update Ticket (Add Comment)
# ─────────────────────────────────────
def test_add_comment(issue_key: str):
    """Add a comment to an existing ticket."""
    print(f"\n── Test 6: Add Comment ({issue_key}) ──")
    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}/comment"
    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "🤖 Agent update: KB search found 3 related incidents. "
                            "Root cause likely connection pool exhaustion (confidence: 92%). "
                            "Suggested action: increase max_connections to 200.",
                        }
                    ],
                }
            ],
        }
    }

    resp = requests.post(url, headers=get_auth_header(), json=payload)

    if resp.status_code == 201:
        comment = resp.json()
        print(f"✅ Comment added (ID: {comment['id']})")
        return True
    else:
        print(f"❌ Failed ({resp.status_code}): {resp.text[:200]}")
        return False


# ─────────────────────────────────────
# Test 7: Update Ticket Fields
# ─────────────────────────────────────
def test_update_ticket(issue_key: str):
    """Update ticket fields (priority, labels)."""
    print(f"\n── Test 7: Update Ticket ({issue_key}) ──")
    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}"
    payload = {
        "fields": {
            "priority": {"name": "High"},
            "labels": ["agent-created", "test", "api-latency", "escalated"],
        }
    }

    resp = requests.put(url, headers=get_auth_header(), json=payload)

    if resp.status_code == 204:
        print(f"✅ Updated: priority → High, added 'escalated' label")
        return True
    else:
        print(f"❌ Failed ({resp.status_code}): {resp.text[:200]}")
        return False


# ─────────────────────────────────────
# Test 8: Transition Ticket (Change Status)
# ─────────────────────────────────────
def test_transition_ticket(issue_key: str):
    """Get available transitions and optionally move to 'In Progress'."""
    print(f"\n── Test 8: Transitions ({issue_key}) ──")
    url = f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions"
    resp = requests.get(url, headers=get_auth_header())

    if resp.status_code == 200:
        transitions = resp.json().get("transitions", [])
        print(f"✅ Available transitions:")
        for t in transitions:
            print(f"   [{t['id']}] {t['name']} → {t['to']['name']}")

        # Try to move to "In Progress" if available
        in_progress = next((t for t in transitions if "progress" in t["name"].lower()), None)
        if in_progress:
            resp2 = requests.post(
                url,
                headers=get_auth_header(),
                json={"transition": {"id": in_progress["id"]}},
            )
            if resp2.status_code == 204:
                print(f"✅ Transitioned to: {in_progress['to']['name']}")
            else:
                print(f"⚠️ Transition failed ({resp2.status_code})")
        return True
    else:
        print(f"❌ Failed ({resp.status_code}): {resp.text[:200]}")
        return False


# ─────────────────────────────────────
# Main — Run All Tests
# ─────────────────────────────────────
def main():
    print("=" * 60)
    print("  Jira Cloud API Test Suite — Project 125")
    print("=" * 60)

    check_config()

    # Connectivity
    if not test_connectivity():
        print("\n⛔ Cannot connect to Jira. Check URL and credentials.")
        sys.exit(1)

    # Project
    if not test_get_project():
        sys.exit(1)

    # Create
    issue_key = test_create_ticket()
    if not issue_key:
        print("\n⛔ Could not create ticket. Check project key and permissions.")
        sys.exit(1)

    # Search
    test_search_jql(issue_key)

    # Get details
    test_get_ticket(issue_key)

    # Add comment
    test_add_comment(issue_key)

    # Update fields
    test_update_ticket(issue_key)

    # Transitions
    test_transition_ticket(issue_key)

    # Summary
    print("\n" + "=" * 60)
    print("  ✅ All Jira API tests passed!")
    print(f"  Test ticket: {JIRA_URL}/browse/{issue_key}")
    print("  You can delete it manually or leave it for agent testing.")
    print("=" * 60)


if __name__ == "__main__":
    main()
