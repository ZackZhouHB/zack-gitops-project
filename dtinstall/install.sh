#!/bin/bash
# Simplified POC Script (tree only)
set -e

echo "Installing tree..."
sudo yum install -y tree

# Verify
if command -v tree >/dev/null; then
    echo "Success! tree $(tree --version)"
else
    echo "Installation failed!"
    exit 1
fi
