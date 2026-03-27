# Slack MCP Server

Exposes Slack messaging operations as MCP-compatible tools.

## Tools

| Tool | Description | Read/Write |
|------|-------------|-----------|
| `send_message` | Send a message to a channel | **Write** |
| `create_thread` | Post summary + thread reply | **Write** |
| `reply_in_thread` | Reply to existing thread | **Write** |
| `list_channels` | List channels bot can access | Read |
| `send_rich_notification` | Block Kit formatted card | **Write** |

## Run Locally

```bash
# stdio transport (for agent integration)
python server.py

# HTTP transport (for testing / Docker)
python server.py --transport http --port 8003
```

## Environment Variables

```
SLACK_BOT_TOKEN=xoxb-your-token-here
SLACK_DEFAULT_CHANNEL=#platform-alerts
```

## Test

```bash
# After starting with HTTP transport:
curl http://localhost:8003/health
```
