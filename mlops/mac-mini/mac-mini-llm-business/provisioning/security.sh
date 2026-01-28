#!/bin/bash
# Security Hardening Script for Mac Mini LLM Appliance

set -e

echo "=========================================="
echo "Security Hardening"
echo "=========================================="

# Check for root
if [[ $EUID -ne 0 ]]; then
   echo "This script requires sudo for system-level changes"
   echo "Run: sudo ./security.sh"
   exit 1
fi

# 1. Firewall Configuration
echo "[1/7] Configuring firewall..."
/usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on
/usr/libexec/ApplicationFirewall/socketfilterfw --setblockall off
/usr/libexec/ApplicationFirewall/socketfilterfw --setstealthmode on

# Allow only necessary services
echo "Firewall enabled with stealth mode"

# 2. Disable unnecessary services
echo "[2/7] Disabling unnecessary services..."
# Disable remote login if not needed
systemsetup -setremotelogin off 2>/dev/null || true
# Disable remote management
/System/Library/CoreServices/RemoteManagement/ARDAgent.app/Contents/Resources/kickstart -deactivate -stop 2>/dev/null || true

# 3. Configure automatic updates
echo "[3/7] Configuring automatic security updates..."
defaults write /Library/Preferences/com.apple.SoftwareUpdate AutomaticCheckEnabled -bool true
defaults write /Library/Preferences/com.apple.SoftwareUpdate AutomaticDownload -bool true
defaults write /Library/Preferences/com.apple.SoftwareUpdate CriticalUpdateInstall -bool true

# 4. Secure Ollama binding
echo "[4/7] Securing Ollama configuration..."
OLLAMA_PLIST="/Library/LaunchDaemons/com.ollama.ollama.plist"

# Create secure launchd config for Ollama
cat > "$OLLAMA_PLIST" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ollama.ollama</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/ollama</string>
        <string>serve</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>OLLAMA_HOST</key>
        <string>127.0.0.1:11434</string>
        <key>OLLAMA_ORIGINS</key>
        <string>http://localhost:3000,http://127.0.0.1:3000</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/ollama.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/ollama.error.log</string>
</dict>
</plist>
EOF

chmod 644 "$OLLAMA_PLIST"
launchctl load "$OLLAMA_PLIST" 2>/dev/null || true

# 5. Create dedicated service user (optional)
echo "[5/7] Service user configuration..."
# Uncomment to create dedicated user
# sysadminctl -addUser llmservice -password "$(openssl rand -base64 32)" -home /var/empty -shell /usr/bin/false

# 6. Set up log rotation
echo "[6/7] Configuring log rotation..."
cat > /etc/newsyslog.d/ollama.conf << 'EOF'
# logfilename                    [owner:group]  mode  count  size   when  flags
/var/log/ollama.log                             644   5      10240  *     J
/var/log/ollama.error.log                       644   5      10240  *     J
EOF

# 7. Network isolation recommendations
echo "[7/7] Network security recommendations..."
cat << 'EOF'

========================================
NETWORK SECURITY RECOMMENDATIONS
========================================

For maximum security, configure the following on your network:

1. VLAN Isolation
   - Place Mac Mini on dedicated VLAN
   - Allow only necessary client IPs to access ports 3000, 11434

2. Firewall Rules (on network firewall)
   - ALLOW: Internal network -> Mac Mini:3000 (Web UI)
   - ALLOW: Internal network -> Mac Mini:11434 (API, if needed)
   - DENY: Mac Mini -> Internet (air-gap)
   - ALLOW: Mac Mini -> Internal DNS only

3. DNS Configuration
   - Point to internal DNS only
   - Block external DNS queries

4. Proxy Configuration (if internet needed for updates)
   - Route through corporate proxy
   - Whitelist only: brew.sh, ollama.com, ghcr.io

5. Physical Security
   - Lock Mac Mini in secure location
   - Disable USB ports if not needed (via MDM)

EOF

# 8. Create security audit script
cat > /usr/local/bin/llm-security-audit << 'AUDIT'
#!/bin/bash
echo "=== LLM Appliance Security Audit ==="
echo ""
echo "Firewall Status:"
/usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
echo ""
echo "Listening Ports:"
lsof -i -P | grep LISTEN
echo ""
echo "Ollama Process:"
ps aux | grep ollama | grep -v grep
echo ""
echo "Docker Containers:"
docker ps
echo ""
echo "Recent Auth Failures:"
log show --predicate 'eventMessage contains "authentication"' --last 1h 2>/dev/null | tail -20
echo ""
echo "Disk Encryption:"
fdesetup status
AUDIT
chmod +x /usr/local/bin/llm-security-audit

echo ""
echo "=========================================="
echo "Security Hardening Complete"
echo "=========================================="
echo ""
echo "Run 'sudo llm-security-audit' to verify security status"
echo ""
echo "IMPORTANT: Additional manual steps recommended:"
echo "1. Enable FileVault disk encryption"
echo "2. Set firmware password"
echo "3. Configure MDM enrollment"
echo "4. Set up network firewall rules"
echo "5. Create admin account with strong password"
echo "6. Disable guest account"
