#!/bin/bash

# setup_env.sh
# Purpose: Prepares a clean Mac environment for LLM Appliance deployment.
# Usage: ./setup_env.sh

set -e

echo "Starting Mac LLM Appliance Setup..."

# 1. Install Homebrew (if not present)
if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "Homebrew is already installed."
fi

# 2. Install Ollama (Inference Engine)
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    brew install ollama
else
    echo "Ollama is already installed."
fi

# 3. Install Docker (Required for OpenWebUI)
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing Docker Desktop (Cask)..."
    echo "NOTE: This may require user password and GUI interaction."
    brew install --cask docker
else
    echo "Docker is already installed."
fi

# 4. Create Service Directory for Persistence
SERVICE_DIR="$HOME/llm-appliance"
mkdir -p "$SERVICE_DIR"
echo "Created service directory at $SERVICE_DIR"

echo "Setup Complete."
echo "ACTION REQUIRED: Please start Docker Desktop manually if it is not running."
echo "ACTION REQUIRED: Run 'ollama serve' in a separate terminal before provisioning models."
