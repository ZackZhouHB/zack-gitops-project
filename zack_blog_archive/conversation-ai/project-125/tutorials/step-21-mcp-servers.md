# Step 21: Building MCP Servers — Making Tools Portable and Reusable

> **What you'll learn**: What MCP is, why it matters, how to build MCP servers for Jira and Slack, and how to connect them to a LangGraph agent.  
> **Why this matters**: MCP is the emerging industry standard for tool interoperability. Building MCP servers means your tools work with any agent — not just yours.  
> **Time**: ~30 minutes reading + 20 minutes hands-on  
> **Prerequisites**: Steps 19-20 completed (Jira + Slack APIs understood), `mcp` package installed

---

## 21.1 What Is MCP (Model Context Protocol)?

MCP is a **standard protocol** created by Anthropic for connecting AI agents to external tools and data sources. Think of it as **USB-C for AI tools** — one universal connector instead of a different cable for every device.

### The Problem MCP Solves

```
WITHOUT MCP:

LangGraph Agent         ←→  Custom Jira code (Python)
CrewAI Agent            ←→  Different Jira code (Python)
Claude Desktop          ←→  Yet another Jira code
Cursor IDE              ←→  And another one

4 agents × 1 tool = 4 implementations to maintain
```

```
WITH MCP:

LangGraph Agent  ─┐
CrewAI Agent     ─┤
Claude Desktop   ─┼──  MCP Protocol  ──→  Jira MCP Server (ONE implementation)
Cursor IDE       ─┘
OpenAI Agent     ─┘

5 agents × 1 tool = 1 implementation, 5 consumers
```

### MCP Architecture

```
┌────────────────┐     ┌──────────────┐     ┌──────────────────┐
│  MCP Client    │────→│  MCP Protocol│────→│  MCP Server      │
│  (your agent)  │     │  (transport) │     │  (tool provider)  │
│                │     │              │     │                   │
│  Discovers     │     │  • stdio     │     │  Exposes tools:   │
│  tools, calls  │     │  • HTTP/SSE  │     │  • search_issues  │
│  them by name  │     │  • WebSocket │     │  • create_ticket  │
└────────────────┘     └──────────────┘     └──────────────────┘
```

**Key insight**: The MCP server doesn't know or care who's calling it. It just exposes tools with names, descriptions, and input schemas. Any MCP client can discover and use them.

---

## 21.2 MCP Server Structure

Each MCP server is a standalone Python process:

```
mcp-servers/jira-server/
├── server.py          # MCP entry point with @mcp.tool() decorators
├── jira_client.py     # Raw REST API wrapper (from step 19)
├── config.py          # Environment variables
├── requirements.txt   # mcp, requests, python-dotenv
├── Dockerfile         # For Docker deployment
└── README.md          # How to run/test
```

The separation is intentional:
- `jira_client.py` = pure API logic (no MCP dependency, testable alone)
- `server.py` = MCP wrapper (thin layer that exposes client methods as tools)

---

## 21.3 Building the Jira MCP Server

### Step 1: Install the MCP SDK

```bash
pip install mcp requests python-dotenv
```

### Step 2: The Client Layer (jira_client.py)

This is the same API code from step 19, wrapped in a class:

```python
from base64 import b64encode
import requests

class JiraClient:
    def __init__(self, url, email, api_token, default_project="PLAT"):
        self.url = url.rstrip("/")
        self.default_project = default_project
        token = b64encode(f"{email}:{api_token}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    def search(self, jql, max_results=10):
        resp = requests.get(
            f"{self.url}/rest/api/3/search",
            headers=self._headers,
            params={"jql": jql, "maxResults": max_results,
                    "fields": "summary,status,priority,labels"},
        )
        # ... parse and return results

    def create_issue(self, project_key, summary, description, ...):
        # ... POST to /rest/api/3/issue
```

> **Why separate client from server?** You can test the Jira API logic without MCP. You can also reuse the client in other contexts (scripts, tests, other frameworks).

### Step 3: The MCP Server (server.py)

```python
from mcp.server.fastmcp import FastMCP
from jira_client import JiraClient

mcp = FastMCP("jira-server")
jira = JiraClient(url=..., email=..., api_token=...)

@mcp.tool()
def search_issues(jql: str, max_results: int = 10) -> dict:
    """Search Jira issues using JQL.

    Use this to find existing tickets, check for duplicates before creating.
    Always search before creating to avoid duplicates.

    Args:
        jql: JQL query string
        max_results: Maximum results (default: 10)

    Returns:
        dict with 'total' and 'issues' list
    """
    return jira.search(jql=jql, max_results=max_results)

@mcp.tool()
def create_ticket(summary: str, description: str = "", ...) -> dict:
    """Create a new Jira ticket.

    IMPORTANT: Always search for duplicates first.
    Should only be called AFTER human approval.
    """
    return jira.create_issue(...)
```

**What FastMCP does for you:**
1. Reads the function **type hints** → generates input JSON schema
2. Reads the **docstring** → sets the tool description (this is what the LLM sees!)
3. Handles **transport** (stdio or HTTP) automatically
4. Manages **tool discovery** — clients can list all available tools

> **The docstring IS the routing logic.** When the LLM sees `"Always search for duplicates first"`, it learns to call `search_issues` before `create_ticket`. This is the same pattern as your existing platform-health-agent tools.

### Step 4: Run and Test

```bash
# stdio mode (for agent integration via langchain-mcp-adapters)
python mcp-servers/jira-server/server.py

# HTTP mode (for testing, Docker, browser-based tools)
python mcp-servers/jira-server/server.py --transport http --port 8002
```

---

## 21.4 Building the Slack MCP Server

Same pattern, different API:

```python
from mcp.server.fastmcp import FastMCP
from slack_client import SlackClient

mcp = FastMCP("slack-server")
slack = SlackClient(bot_token=...)

@mcp.tool()
def send_message(channel: str, text: str) -> dict:
    """Send a message to a Slack channel.

    Use this to notify teams about incidents, ticket creation, or status updates.
    The bot must be a member of the target channel.
    """
    return slack.post_message(channel=channel, text=text)

@mcp.tool()
def create_thread(channel: str, summary: str, details: str) -> dict:
    """Send summary to channel, then add details as thread reply.

    Recommended pattern: main message = brief summary,
    thread = detailed KB context, root cause, actions.
    """
    main = slack.post_message(channel=channel, text=summary)
    reply = slack.post_message(channel=main["channel"], text=details,
                               thread_ts=main["ts"])
    return {"message_ts": main["ts"], "thread_ts": reply["ts"]}
```

### Slack MCP Server Tools

| Tool | Purpose | Read/Write |
|------|---------|-----------|
| `send_message` | Post to channel | Write |
| `create_thread` | Summary + threaded details | Write |
| `reply_in_thread` | Add to existing thread | Write |
| `list_channels` | Discover available channels | Read |
| `send_rich_notification` | Block Kit formatted card | Write |

---

## 21.5 Connecting MCP Servers to LangGraph

This is where it all comes together. The `langchain-mcp-adapters` library bridges MCP servers with LangGraph:

```bash
pip install langchain-mcp-adapters
```

### Using MultiServerMCPClient

```python
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent

# Connect to multiple MCP servers
async with MultiServerMCPClient({
    "jira": {
        "command": "python",
        "args": ["mcp-servers/jira-server/server.py"],
        "transport": "stdio",
    },
    "slack": {
        "command": "python",
        "args": ["mcp-servers/slack-server/server.py"],
        "transport": "stdio",
    }
}) as client:
    # Get all tools from all servers
    tools = client.get_tools()
    # tools = [search_issues, create_ticket, get_ticket, update_ticket,
    #          add_comment, send_message, create_thread, ...]

    # Create agent with MCP tools + existing direct tools
    all_tools = tools + [rag_search, assess_incident]  # Mix MCP + direct
    agent = create_react_agent(model, all_tools)
```

**What happens under the hood:**
1. `MultiServerMCPClient` spawns each MCP server as a subprocess
2. Communicates via stdio (stdin/stdout JSON messages)
3. Discovers tools automatically (name, description, schema)
4. Wraps each MCP tool as a LangChain `StructuredTool`
5. Agent calls tools by name — MCP client routes to the right server

### Tool Discovery Flow

```
Agent startup:
  1. MCP Client → Jira Server: "list your tools"
     ← [search_issues, create_ticket, get_ticket, update_ticket, add_comment]

  2. MCP Client → Slack Server: "list your tools"
     ← [send_message, create_thread, reply_in_thread, list_channels, send_rich_notification]

  3. Agent now has 10 MCP tools + existing direct tools
     LLM sees all tool descriptions, picks the right one per query

During conversation:
  User: "Create a ticket for API latency and notify Slack"
  Agent → MCP Client → Jira Server: search_issues("API latency")
  Agent → MCP Client → Jira Server: create_ticket(...)
  Agent → MCP Client → Slack Server: send_message(...)
```

---

## 21.6 Transport Options

| Transport | When to Use | How It Works |
|-----------|------------|-------------|
| **stdio** | Agent integration (recommended) | Server runs as subprocess, communicates via stdin/stdout |
| **streamable-http** | Docker, testing, multiple clients | Server runs as HTTP service on a port |

For our project:
- **Development**: stdio (simplest — agent spawns servers automatically)
- **Docker Compose**: HTTP transport (each server is a container with a port)

---

## 21.7 MCP vs Direct Tools — When to Use Which

| Factor | Direct Tool | MCP Server |
|--------|------------|-----------|
| Simplicity | ✅ Fewer moving parts | ❌ Extra process per server |
| Reusability | ❌ Tied to your framework | ✅ Works with any MCP client |
| Testing | ❌ Must test within agent | ✅ Testable independently |
| Portfolio | — | ✅ Shows MCP competency |
| Performance | ✅ In-process, faster | ❌ IPC overhead (small) |

**Our approach**: Use MCP for **new external integrations** (Jira, Slack) where portability matters. Keep existing tools as **direct tools** (rag_search, assess_incident) since they're tightly coupled to local infrastructure.

---

## 21.8 Testing MCP Servers

### Test with MCP Inspector (CLI tool)

```bash
# Install MCP inspector
npx @modelcontextprotocol/inspector

# Connect to your server
npx @modelcontextprotocol/inspector python mcp-servers/jira-server/server.py
```

This opens a browser UI where you can:
- See all discovered tools
- Call tools with test inputs
- View responses

### Test programmatically

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server = StdioServerParameters(
    command="python",
    args=["mcp-servers/jira-server/server.py"],
)

async with stdio_client(server) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()

        # List tools
        tools = await session.list_tools()
        print(f"Available tools: {[t.name for t in tools.tools]}")

        # Call a tool
        result = await session.call_tool("search_issues", {
            "jql": "project = PLAT AND status = Open"
        })
        print(result)
```

---

## 21.9 What We Built

```
mcp-servers/
├── jira-server/
│   ├── server.py         # 5 MCP tools: search, create, get, update, comment
│   ├── jira_client.py    # Jira REST API v3 wrapper
│   ├── Dockerfile        # HTTP transport for Docker
│   └── requirements.txt  # mcp, requests, python-dotenv
│
└── slack-server/
    ├── server.py         # 5 MCP tools: send, thread, reply, list, rich notify
    ├── slack_client.py   # Slack Web API wrapper
    ├── Dockerfile        # HTTP transport for Docker
    └── requirements.txt  # mcp, requests, python-dotenv
```

**10 MCP tools total** — all discoverable, all callable by any MCP-compatible agent.

---

## 21.10 Key Takeaways

1. **MCP separates tool logic from agent framework** — write once, use everywhere
2. **FastMCP reads type hints + docstrings** — that's your tool schema + description
3. **Docstrings ARE routing logic** — the LLM reads them to decide when to call each tool
4. **Client/server separation** — API wrapper is pure Python, MCP layer is thin
5. **stdio for dev, HTTP for Docker** — two transports, same code
6. **langchain-mcp-adapters** bridges MCP → LangGraph seamlessly
7. **Test servers independently** — MCP Inspector or programmatic client

---

**Previous**: [Step 20 — Slack API Basics](step-20-slack-api-basics.md)  
**Next**: [Step 22 — Action Agent Integration](step-22-action-agent.md) — wire MCP tools into LangGraph with confirmation flow

*Created 2026-03-26 — Project 125, Phase C*
