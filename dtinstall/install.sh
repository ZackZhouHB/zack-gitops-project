#!/bin/bash
# POC Installation Script - Installs htop (non-critical system monitor)
set -e  # Exit immediately if any command fails

# Define package name (small, safe package for testing)
PACKAGE_NAME="htop"

echo "Starting POC installation of ${PACKAGE_NAME}..."

# Update package lists (for Ubuntu/Debian)
echo "Updating package lists..."
sudo apt-get update -qq  # -qq reduces output noise

# Install the package
echo "Installing ${PACKAGE_NAME}..."
sudo apt-get install -y -qq "${PACKAGE_NAME}"

# Verify installation
if command -v "${PACKAGE_NAME}" >/dev/null 2>&1; then
    echo "Success: ${PACKAGE_NAME} installed!"
    echo "Version: $(${PACKAGE_NAME} --version | head -n1)"
else
    echo "Error: ${PACKAGE_NAME} installation failed!"
    exit 1
fi

echo "POC installation completed!"