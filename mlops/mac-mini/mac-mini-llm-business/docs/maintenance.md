# Maintenance Guide

## Routine Maintenance Schedule

| Task | Frequency | Time Required |
|------|-----------|---------------|
| Check service status | Weekly | 5 min |
| Review logs | Weekly | 10 min |
| Update models | Monthly | 30-60 min |
| System updates | Monthly | 30 min |
| Full backup | Monthly | 1-2 hours |
| Security audit | Quarterly | 30 min |

---

## Weekly Health Check

### 1. Verify Services Running

```bash
# Check Ollama
pgrep -x ollama && echo "Ollama: Running" || echo "Ollama: STOPPED"

# Check Open WebUI
docker ps | grep open-webui && echo "WebUI: Running" || echo "WebUI: STOPPED"

# Check disk space
df -h /

# Check memory
memory_pressure
```

### 2. Quick Service Test

```bash
# Test Ollama API
curl -s http://localhost:11434/api/tags | head -20

# Test a model
ollama run llama3.2:3b "Say hello" --verbose
```

### 3. Review Logs

```bash
# Ollama logs
tail -100 /var/log/ollama.log

# Docker/WebUI logs
docker logs --tail 100 open-webui

# System errors
log show --predicate 'eventType == logEvent and messageType == error' --last 24h
```

---

## Monthly Updates

### Update Ollama

```bash
brew upgrade ollama
brew services restart ollama
```

### Update Open WebUI

```bash
docker pull ghcr.io/open-webui/open-webui:main
docker stop open-webui
docker rm open-webui
docker run -d \
  --name open-webui \
  --restart always \
  -p 3000:8080 \
  -v open-webui-data:/app/backend/data \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  ghcr.io/open-webui/open-webui:main
```

### Update Models (Optional)

```bash
# List current models
ollama list

# Pull latest version of a model
ollama pull llama3.1:8b

# Remove old unused models
ollama rm old-model-name
```

### macOS Updates

```bash
# Check for updates
softwareupdate --list

# Install security updates only
softwareupdate --install --recommended
```

---

## Backup Procedures

### What to Backup

1. **Open WebUI data** (user accounts, chat history, settings)
2. **Custom model configurations** (Modelfiles)
3. **System configuration** (launchd plists)

### Backup Script

```bash
#!/bin/bash
BACKUP_DIR="/Volumes/Backup/llm-appliance"
DATE=$(date +%Y%m%d)

mkdir -p "$BACKUP_DIR/$DATE"

# Backup Open WebUI data
docker run --rm \
  -v open-webui-data:/data \
  -v "$BACKUP_DIR/$DATE":/backup \
  alpine tar czf /backup/webui-data.tar.gz /data

# Backup Ollama models list
ollama list > "$BACKUP_DIR/$DATE/models.txt"

# Backup custom Modelfiles
cp -r ~/.ollama/Modelfiles "$BACKUP_DIR/$DATE/" 2>/dev/null || true

# Backup launchd configs
cp /Library/LaunchDaemons/com.ollama.* "$BACKUP_DIR/$DATE/" 2>/dev/null || true

echo "Backup complete: $BACKUP_DIR/$DATE"
```

### Restore Procedure

```bash
BACKUP_DIR="/Volumes/Backup/llm-appliance/20240115"

# Restore WebUI data
docker run --rm \
  -v open-webui-data:/data \
  -v "$BACKUP_DIR":/backup \
  alpine tar xzf /backup/webui-data.tar.gz -C /

# Re-pull models from list
while read model; do
  ollama pull "$model"
done < "$BACKUP_DIR/models.txt"
```

---

## Troubleshooting

### Ollama Won't Start

```bash
# Check if port is in use
lsof -i :11434

# Kill stuck process
pkill -9 ollama

# Restart via brew
brew services restart ollama

# Or start manually
ollama serve
```

### Open WebUI Not Accessible

```bash
# Check container status
docker ps -a | grep open-webui

# View logs
docker logs open-webui

# Restart container
docker restart open-webui

# If corrupted, recreate
docker stop open-webui && docker rm open-webui
# Then run docker run command from setup
```

### Out of Memory

```bash
# Check what's using memory
top -o MEM

# Clear Ollama model cache
curl -X DELETE http://localhost:11434/api/cache

# Unload models
curl http://localhost:11434/api/generate -d '{"model": "llama3.1:8b", "keep_alive": 0}'

# Use smaller models
```

### Slow Performance

```bash
# Check CPU/Memory
top -l 1 | head -10

# Check thermal throttling
pmset -g thermlog

# Reduce concurrent users
# Switch to smaller models
```

### Disk Full

```bash
# Check disk usage
df -h

# Find large files
du -sh ~/.ollama/models/*

# Remove unused models
ollama rm unused-model

# Clean Docker
docker system prune -a
```

---

## Performance Tuning

### Optimize for Speed

```bash
# Use quantized models
ollama pull llama3.1:8b-instruct-q4_K_M

# Reduce context window in Modelfile
PARAMETER num_ctx 2048

# Enable Metal acceleration (default on M-series)
export OLLAMA_METAL=1
```

### Optimize for Quality

```bash
# Use higher quantization
ollama pull llama3.1:8b-instruct-q6_K

# Increase context window
PARAMETER num_ctx 8192

# Adjust temperature
PARAMETER temperature 0.7
```

### Memory Management

```bash
# Set model unload timeout (seconds)
export OLLAMA_KEEP_ALIVE=300

# Limit concurrent models
export OLLAMA_MAX_LOADED_MODELS=1
```

---

## Security Maintenance

### Quarterly Security Audit

```bash
# Run security audit script
sudo llm-security-audit

# Check for unauthorized access
log show --predicate 'process == "sshd"' --last 30d

# Verify firewall
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# Check FileVault
fdesetup status

# Review user accounts
dscl . list /Users | grep -v '^_'
```

### Rotate Admin Password

1. System Preferences > Users & Groups
2. Select admin account
3. Change Password
4. Update documentation securely

### Update Open WebUI Admin

1. Log into Open WebUI as admin
2. Go to Settings > Admin
3. Change password
4. Review user list, remove inactive accounts

---

## Emergency Procedures

### Complete System Reset

```bash
# Stop all services
brew services stop ollama
docker stop open-webui

# Remove all data (DESTRUCTIVE)
rm -rf ~/.ollama
docker volume rm open-webui-data

# Re-run provisioning
cd /path/to/provisioning
./setup.sh
```

### Remote Recovery (if SSH enabled)

```bash
ssh admin@mac-mini-ip
sudo reboot  # If unresponsive

# After reboot, verify services
brew services list
docker ps
```

### Hardware Failure

1. Replace Mac Mini with spare unit
2. Restore from latest backup
3. Re-pull models
4. Verify functionality
5. Update DNS/IP if changed

---

## Support Escalation

### Level 1 (Customer IT)
- Service restarts
- Basic troubleshooting
- User account management

### Level 2 (Your Support)
- Model updates
- Configuration changes
- Performance tuning

### Level 3 (Advanced)
- Custom model training
- Security incidents
- Hardware replacement
