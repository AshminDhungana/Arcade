#!/bin/bash
# Post-install script for Arcade Agent Debian package
# Sets proper permissions on config directory and files

set -e

CONFIG_DIR="/etc/arcade-agent"
CONFIG_FILE="$CONFIG_DIR/agent.config.json"

# Create config directory with proper permissions
mkdir -p "$CONFIG_DIR"
chmod 755 "$CONFIG_DIR"

# If config file exists, ensure it's readable by the agent user
if [ -f "$CONFIG_FILE" ]; then
    chmod 600 "$CONFIG_FILE"
    # Try to detect the arcade agent user (typically created by package or service)
    if id "arcade-agent" &>/dev/null; then
        chown arcade-agent:arcade-agent "$CONFIG_FILE"
    fi
fi

# Reload systemd daemon if service file exists
if [ -f /etc/systemd/system/arcade-agent.service ]; then
    systemctl daemon-reload >/dev/null 2>&1 || true
fi

exit 0
