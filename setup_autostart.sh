#!/bin/bash
# setup_autostart.sh
# =====================
# Run this script ONCE to register the LISA Linux agent as a systemd
# user service that starts automatically when the user logs in.
#
# HOW TO RUN:
#   cd ~/linux-agent
#   chmod +x setup_autostart.sh
#   ./setup_autostart.sh
#
# HOW TO CHECK STATUS:
#   systemctl --user status lisa-agent
#
# HOW TO VIEW LOGS:
#   journalctl --user -u lisa-agent -f
#
# HOW TO STOP:
#   systemctl --user stop lisa-agent
#
# HOW TO REMOVE:
#   systemctl --user stop lisa-agent
#   systemctl --user disable lisa-agent
#   rm ~/.config/systemd/user/lisa-agent.service
set -e
AGENT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENT_BIN="$AGENT_DIR/dist/agent"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/lisa-agent.service"
echo "=== LISA Linux Agent Autostart Setup ==="
# Check compiled agent binary exists
if [ ! -f "$AGENT_BIN" ]; then
    echo "ERROR: compiled agent not found at $AGENT_BIN"
    echo "Run: pyinstaller --onefile --name agent agent.py"
    exit 1
fi
echo "Agent found: $AGENT_BIN"
# Create systemd user directory
mkdir -p "$SERVICE_DIR"
# Write the service file
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=LISA Linux Agent
After=graphical-session.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$AGENT_DIR
Environment=PATH=/home/$USER/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin
Environment=DISPLAY=:0
ExecStart=$AGENT_BIN
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical-session.target
EOF
echo "Service file created: $SERVICE_FILE"
# Reload systemd and enable the service
systemctl --user daemon-reload
systemctl --user enable lisa-agent
systemctl --user start lisa-agent
echo ""
echo "SUCCESS: LISA agent service created and started."
echo ""
echo "To check status:  systemctl --user status lisa-agent"
echo "To view logs:     journalctl --user -u lisa-agent -f"
echo "To stop:          systemctl --user stop lisa-agent"
echo "To restart:       systemctl --user restart lisa-agent"
