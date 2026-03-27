# Step 25 — Docker Containerization

## Goal

Package the entire project-125 stack into Docker containers so it can run with a single `docker compose up -d` command, making it portable for cloud deployment.

## What Gets Containerized

| Service | Container | Port | Image |
|---------|-----------|------|-------|
| Weaviate | project-125-vectordb | 8080 | cr.weaviate.io/semitechnologies/weaviate:1.28.4 |
| PostgreSQL | project-125-postgres | 5432 | postgres:16-alpine |
| Jira MCP Server | project-125-jira-mcp | 8002 | python:3.12-slim (custom) |
| Slack MCP Server | project-125-slack-mcp | 8003 | python:3.12-slim (custom) |
| Agent Backend | project-125-backend | 8010 | python:3.12-slim (custom) |
| Streamlit Frontend | project-125-frontend | 8502 | python:3.12-slim (custom) |

## Key Design Decisions

### 1. Dual-Mode Imports for MCP Clients
The agent imports Jira/Slack client modules directly (not via MCP HTTP protocol). In Docker, these files are volume-mounted into `/app/clients/`:

```python
# agent/graph.py — works in both Docker and local dev
try:
    from clients.jira_client import JiraClient      # Docker
    from clients.slack_client import SlackClient
except ImportError:
    sys.path.insert(0, "../../mcp-servers/jira-server")  # Local dev
    from jira_client import JiraClient
```

### 2. Weaviate Connection Modes
`connect_to_local()` only works for localhost. For Docker DNS names, use `connect_to_custom()`:

```python
if host in ("localhost", "127.0.0.1"):
    return weaviate.connect_to_local(host=host, port=port)
else:
    return weaviate.connect_to_custom(
        http_host=host, http_port=port, http_secure=False,
        grpc_host=host, grpc_port=50051, grpc_secure=False,
    )
```

### 3. Shared Weaviate Data
The compose file bind-mounts platform-health-agent's Weaviate data directory so both projects share the same 198 KB chunks without re-ingestion:

```yaml
volumes:
  - ../platform-health-agent/data/weaviate:/var/lib/weaviate
```

### 4. AWS Credentials
SSO token refresh needs a writable cache directory, so `~/.aws` is mounted read-write:

```yaml
volumes:
  - ~/.aws:/root/.aws  # NOT :ro — SSO needs writable cache
```

## Startup

```bash
cd project-125

# One command — starts all 6 services
docker compose up -d

# Check all healthy
docker compose ps

# Open the UI
open http://localhost:8502
```

## Real-World Issues Encountered

### Issue #9: Weaviate Image Has No curl
**Symptoms**: Healthcheck `curl -f http://localhost:8080/...` fails — container marked unhealthy  
**Root Cause**: Weaviate's Alpine-based image doesn't include curl  
**Fix**: Use `wget -q --spider` instead — available in Alpine

### Issue #10: AWS SSO Cache Read-Only Error
**Symptoms**: `OSError: [Errno 30] Read-only file system: '/root/.aws/sso/cache/tmp...'`  
**Root Cause**: `~/.aws` mounted as `:ro` but SSO token refresh writes to `sso/cache/`  
**Fix**: Mount without `:ro` — accept read-write for local dev

### Issue #11: MCP FastMCP.run() API Changed
**Symptoms**: `TypeError: FastMCP.run() got an unexpected keyword argument 'host'`  
**Root Cause**: `host`/`port` are constructor params in newer MCP versions, not `run()` params  
**Fix**: Set `mcp.settings.host` and `mcp.settings.port` before calling `run()`

### Issue #12: Weaviate connect_to_local Fails for Docker DNS
**Symptoms**: `Connection refused` when agent connects to `vectordb:8080`  
**Root Cause**: `connect_to_local()` hardcodes gRPC to `localhost:50051`. Docker DNS name `vectordb` doesn't resolve with this method  
**Fix**: Use `connect_to_custom()` which accepts explicit gRPC host/port

## Validation Results — 17/17 Tests Passing

| Category | Tests | Result |
|----------|-------|--------|
| Infrastructure (Weaviate, Postgres) | 4 | ✅ All pass |
| MCP Servers (Jira, Slack) | 2 | ✅ Running (HTTP transport) |
| Agent Backend (11 tools, HITL) | 1 | ✅ Pass |
| Guardrails (off-topic, PII, joke) | 3 | ✅ All blocked/masked |
| RAG Tool (Confluence, blog) | 2 | ✅ Both retrieve sources |
| Jira Integration | 1 | ✅ JQL search works |
| Multi-Tool (RAG + Jira) | 1 | ✅ Both tools called |
| HITL (interrupt + reject) | 1 | ✅ Write paused, reject works |
| Frontend (health, page load) | 2 | ✅ Streamlit accessible |

## Port Map (Final)

```
localhost:8080  → Weaviate (vector search)
localhost:5432  → PostgreSQL (state)
localhost:8002  → Jira MCP Server (streamable-http)
localhost:8003  → Slack MCP Server (streamable-http)
localhost:8010  → Agent Backend (FastAPI + LangGraph)
localhost:8502  → Streamlit Frontend (Chat + HITL)
```
