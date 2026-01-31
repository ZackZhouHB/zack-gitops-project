# Remote Ollama Access from MacBook to Windows PC (WSL)

> **Date:** 2026-01-31  
> **Purpose:** Enable MacBook to call Ollama running on Desktop PC (WSL2) for local LLM inference  
> **Week 1 Deliverable:** Python script that switches between Bedrock and remote Ollama

---

## Environment

| Machine | Role | IP |
|---------|------|-----|
| MacBook Pro M4 | Client (development) | 192.168.50.x |
| Windows PC + WSL2 | Ollama server (RTX 5070 Ti) | 192.168.50.61 (Windows LAN) |
| WSL2 internal | Ollama process | 172.29.34.203 (virtual network) |

---

## The Problem

WSL2 uses a **virtual network** (`172.29.x.x`) that's not directly accessible from other machines on your home WiFi. By default, Ollama only listens on `127.0.0.1` (localhost), making it inaccessible even from Windows host.

**Solution:** Configure Ollama to listen on all interfaces + set up Windows port forwarding.

---

## Steps

### Step 1: Find Windows LAN IP

On Windows PowerShell:
```powershell
ipconfig
```
Look for WLAN adapter IPv4: `192.168.50.61`

### Step 2: Find WSL2 Internal IP

In WSL terminal:
```bash
ip addr | grep eth0
```
Result: `172.29.34.203`

### Step 3: Configure Ollama to Listen on All Interfaces

Ollama runs as a systemd service. Create an override file:

```bash
sudo mkdir -p /etc/systemd/system/ollama.service.d
sudo tee /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
EOF

sudo systemctl daemon-reload
sudo systemctl restart ollama
```

Verify it's listening on `0.0.0.0`:
```bash
sudo ss -tlnp | grep 11434
# Should show: 0.0.0.0:11434 (not 127.0.0.1:11434)
```

### Step 4: Windows Port Forwarding (WSL → LAN)

On Windows PowerShell **as Administrator**:

```powershell
# Forward port 11434 from Windows to WSL
netsh interface portproxy add v4tov4 listenport=11434 listenaddress=0.0.0.0 connectport=11434 connectaddress=172.29.34.203

# Open Windows Firewall
New-NetFirewallRule -DisplayName "Ollama" -Direction Inbound -LocalPort 11434 -Protocol TCP -Action Allow
```

To verify port forwarding:
```powershell
netsh interface portproxy show all
```

To remove later (if needed):
```powershell
netsh interface portproxy delete v4tov4 listenport=11434 listenaddress=0.0.0.0
```

### Step 5: Test from MacBook

```bash
curl http://192.168.50.61:11434/api/tags
```

Expected output:
```json
{"models":[{"name":"qwen3-coder:latest",...},{"name":"gpt-oss-gpu:latest",...}]}
```

---

## Troubleshooting

### Issue: "address already in use" when running `ollama serve`

**Cause:** Ollama systemd service is running, or another process holds the port.

**Fix:**
```bash
# Check what's using the port
sudo lsof -i :11434

# If it's the systemd service, don't run manually - configure the service instead
sudo systemctl status ollama
```

### Issue: Models disappeared after manual `ollama serve`

**Cause:** Running `ollama serve` manually with different env vars creates a separate instance with empty model directory.

**Fix:** Don't run manually. Configure the systemd service with the override file (Step 3).

### Issue: `curl: Connection reset by peer` from Mac

**Cause:** Ollama still listening on `127.0.0.1` only.

**Fix:** Verify the override file exists and restart:
```bash
cat /etc/systemd/system/ollama.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart ollama
sudo ss -tlnp | grep 11434  # Must show 0.0.0.0
```

### Issue: Windows firewall blocking

**Fix:** Run PowerShell as Administrator for the firewall rule, or manually add via Windows Defender Firewall GUI.

---

## Network Flow Diagram

```
┌─────────────────┐         ┌─────────────────────────────────────────────┐
│   MacBook Pro   │         │              Windows PC                     │
│  192.168.50.x   │         │           192.168.50.61                     │
│                 │         │                                             │
│  curl/python    │────────▶│  Port 11434 ──▶ netsh portproxy ──┐        │
│                 │  WiFi   │                                    │        │
└─────────────────┘         │         ┌──────────────────────────┘        │
                            │         │                                   │
                            │         ▼                                   │
                            │  ┌─────────────────────────────────────┐   │
                            │  │            WSL2                      │   │
                            │  │        172.29.34.203                 │   │
                            │  │                                      │   │
                            │  │   Ollama (0.0.0.0:11434)            │   │
                            │  │   ├── qwen3-coder (30.5B)           │   │
                            │  │   ├── gpt-oss-gpu (20.9B)           │   │
                            │  │   └── gpt-oss (20.9B)               │   │
                            │  │                                      │   │
                            │  │   GPU: RTX 5070 Ti (16GB)           │   │
                            │  └─────────────────────────────────────┘   │
                            └─────────────────────────────────────────────┘
```

---

## Validation

```bash
# From MacBook - list models
curl http://192.168.50.61:11434/api/tags

# From MacBook - test inference
curl http://192.168.50.61:11434/api/generate -d '{
  "model": "gpt-oss-gpu:latest",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

---

## Next Step

Use `llm_client.py` to switch between Bedrock (cloud) and Ollama (local GPU) with one config change.
