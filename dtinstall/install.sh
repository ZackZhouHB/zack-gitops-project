#!/bin/bash
# Simplified POC Script (htop only)
set -e

echo "Installing htop..."
sudo yum install -y htop

# Verify
if command -v htop >/dev/null; then
    echo "Success! htop $(htop --version | head -n1)"
else
    echo "Installation failed!"
    exit 1
fi
