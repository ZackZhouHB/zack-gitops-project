# Jira MCP Server

Exposes Jira Cloud operations as MCP-compatible tools.

## Tools

| Tool | Description | Read/Write |
|------|-------------|-----------|
| `search_issues` | Search with JQL | Read |
| `create_ticket` | Create a new ticket | **Write** |
| `get_ticket` | Get ticket details | Read |
| `update_ticket` | Update ticket fields | **Write** |
| `add_comment` | Add comment to ticket | **Write** |

## Run Locally

```bash
# stdio transport (for agent integration)
python server.py

# HTTP transport (for testing / Docker)
python server.py --transport http --port 8002
```

## Environment Variables

```
JIRA_URL=https://your-site.atlassian.net
JIRA_EMAIL=your.email@example.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=PLAT
```

## Test

```bash
# After starting with HTTP transport:
curl http://localhost:8002/health
```
