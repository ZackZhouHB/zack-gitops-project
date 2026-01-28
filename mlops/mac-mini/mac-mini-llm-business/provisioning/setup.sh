#!/bin/bash
# Mac Mini LLM Appliance - Main Provisioning Script
# Run with: sudo ./setup.sh

set -e

echo "=========================================="
echo "Mac Mini LLM Appliance Provisioning"
echo "=========================================="

# Detect memory for tier recommendation
MEMORY_GB=$(( $(sysctl -n hw.memsize) / 1073741824 ))
echo "Detected Memory: ${MEMORY_GB}GB"

# Check if running as root for system-level installs
if [[ $EUID -ne 0 ]]; then
   echo "Note: Run with sudo for full system configuration"
fi

# 1. Install Homebrew if not present
if ! command -v brew &> /dev/null; then
    echo "[1/6] Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo "[1/6] Homebrew already installed"
fi

# 2. Install Ollama
echo "[2/6] Installing Ollama..."
if ! command -v ollama &> /dev/null; then
    brew install ollama
else
    echo "Ollama already installed, updating..."
    brew upgrade ollama || true
fi

# 3. Install Docker (for Open WebUI)
echo "[3/6] Installing Docker..."
if ! command -v docker &> /dev/null; then
    brew install --cask docker
    echo "Please open Docker Desktop to complete setup, then re-run this script"
    open -a Docker
    exit 0
else
    echo "Docker already installed"
fi

# 4. Start Ollama service
echo "[4/6] Starting Ollama service..."
brew services start ollama || ollama serve &
sleep 3

# 5. Deploy Open WebUI
echo "[5/6] Deploying Open WebUI..."
docker pull ghcr.io/open-webui/open-webui:main

# Stop existing container if running
docker stop open-webui 2>/dev/null || true
docker rm open-webui 2>/dev/null || true

# Run Open WebUI
docker run -d \
  --name open-webui \
  --restart always \
  -p 3000:8080 \
  -v open-webui-data:/app/backend/data \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  -e WEBUI_AUTH=true \
  -e ENABLE_SIGNUP=false \
  ghcr.io/open-webui/open-webui:main

echo "[6/6] Pulling recommended models based on ${MEMORY_GB}GB memory..."

# Model selection based on memory
if [ "$MEMORY_GB" -ge 64 ]; then
    echo "Enterprise tier detected - pulling large models..."
    ollama pull llama3.1:70b-instruct-q4_K_M
    ollama pull qwen2.5:32b
    ollama pull deepseek-coder-v2:16b
elif [ "$MEMORY_GB" -ge 48 ]; then
    echo "Business tier detected..."
    ollama pull llama3.1:70b-instruct-q3_K_M
    ollama pull qwen2.5:32b
    ollama pull mixtral:8x7b
elif [ "$MEMORY_GB" -ge 24 ]; then
    echo "Professional tier detected..."
    ollama pull llama3.1:8b
    ollama pull mistral-nemo:12b
    ollama pull deepseek-coder:6.7b
else
    echo "Starter tier detected..."
    ollama pull llama3.2:3b
    ollama pull phi3:mini
    ollama pull mistral:7b-instruct-q4_K_M
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Access Open WebUI at: http://localhost:3000"
echo "Ollama API at: http://localhost:11434"
echo ""
echo "First-time setup:"
echo "1. Open http://localhost:3000"
echo "2. Create admin account"
echo "3. Disable signup in Admin Settings"
echo ""
echo "Next steps:"
echo "- Run ./models.sh to customize models"
echo "- Run ./security.sh to harden system"
echo "- Run ../evaluation/benchmark.sh to test performance"
