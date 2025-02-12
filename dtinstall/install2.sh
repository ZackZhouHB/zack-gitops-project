#!/bin/bash
# Script to install Dynatrace OneAgent based on OS detection
set -e

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
elif [ -f /etc/redhat-release ]; then
    OS="rhel"
else
    echo "Unable to detect OS"
    exit 1
fi

echo "Detected OS: $OS"

# Install based on OS
case $OS in
    "ubuntu")
        echo "Installing on Ubuntu..."
        sudo /bin/sh Dynatrace-OneAgent-Linux-1.0.0.sh
        ;;
    "rhel"|"centos")
        echo "Installing on RHEL/CentOS..."
        su -c '/bin/sh Dynatrace-OneAgent-Linux-1.0.0.sh'
        ;;
    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac

# Verify installation
if [ $? -eq 0 ]; then
    echo "Installation completed successfully!"
else
    echo "Installation failed!"
    exit 1
fi