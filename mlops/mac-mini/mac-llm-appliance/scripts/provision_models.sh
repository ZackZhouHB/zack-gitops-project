#!/bin/bash

# provision_models.sh
# Purpose: Downloads and prepares specific models based on selected tier.
# Usage: ./provision_models.sh [tier]

TIER=$1

if [ -z "$TIER" ]; then
    echo "Usage: ./provision_models.sh [tier1|tier2|tier3]"
    exit 1
fi

echo "Provisioning models for $TIER..."

# Check if Ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Error: Ollama is not running. Please run 'ollama serve' first."
    exit 1
fi

case $TIER in
  tier1)
    echo "Pulling Tier 1 Models (Office Assistant)..."
    ollama pull llama3.2:3b
    ollama pull llama3.1:8b
    ;;
  tier2)
    echo "Pulling Tier 2 Models (Knowledge Worker)..."
    ollama pull llama3.1:8b
    ollama pull qwen2.5:32b
    ollama pull nomic-embed-text # For RAG
    ;;
  tier3)
    echo "Pulling Tier 3 Models (Research Station)..."
    ollama pull llama3.3:70b
    ollama pull qwen2.5:32b
    ollama pull nomic-embed-text
    ;;
  *)
    echo "Invalid tier selected. Options: tier1, tier2, tier3"
    exit 1
    ;;
esac

echo "Model provisioning complete."
ollama list
