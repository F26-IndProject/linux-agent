#!/bin/bash
# install.sh
# =====================
# Full setup script for LISA Linux Agent
#
# BEFORE RUNNING:
#   1. Clone the repo:   git clone https://github.com/F26-IndProject/linux-agent.git
#   2. Edit .env:        cd linux-agent && nano .env
#   3. Run this script:  chmod +x install.sh && ./install.sh
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"
echo "=== LISA Linux Agent — Full Setup ==="
echo ""
# ── Ask for password upfront ──────────────────────────────────────────────────
echo "User $(whoami) will be configured as the RDP login user."
read -s -p "Enter the login password for $(whoami): " USER_PASSWORD
echo ""
# ── Validate sudo access ──────────────────────────────────────────────────────
echo "$USER_PASSWORD" | sudo -S true 2>/dev/null || { echo "ERROR: Incorrect password or no sudo access."; exit 1; }
# ── 1. Install system dependencies ───────────────────────────────────────────
echo "[1/7] Installing system dependencies..."
echo "$USER_PASSWORD" | sudo -S apt update
echo "$USER_PASSWORD" | sudo -S apt install -y openssh-server atril mupdf xdotool smbclient sshpass gcc python3-pip patchelf winpr-utils
# ── 2. Install Python dependencies ───────────────────────────────────────────
echo "[2/7] Installing Python dependencies..."
pip install -r requirements.txt
# ── 3. Compile binaries ───────────────────────────────────────────────────────
echo "[3/7] Compiling binaries..."
gcc -o spawn spawn.c
rm -rf build log_writer log_writer.spec
pyinstaller --onedir --name log_writer --distpath . utils/log_writer.py
# ── 4. Compile agent ──────────────────────────────────────────────────────────
echo "[4/7] Compiling agent..."
rm -rf build dist agent.spec
pyinstaller --onefile --name agent agent.py
# ── Copy attachments to dist ──────────────────────────────────────────────────
cp -r attachments dist/
# ── 5. Setup Linux as RDP target ─────────────────────────────────────────────
echo "[5/7] Setting up Linux as RDP target..."
mkdir -p ~/.local/share/gnome-remote-desktop
winpr-makecert -silent -rdp -path ~/.local/share/gnome-remote-desktop tls
chmod 600 ~/.local/share/gnome-remote-desktop/tls.key
chmod 644 ~/.local/share/gnome-remote-desktop/tls.crt
grdctl rdp set-tls-key ~/.local/share/gnome-remote-desktop/tls.key
grdctl rdp set-tls-cert ~/.local/share/gnome-remote-desktop/tls.crt
grdctl rdp set-credentials "$(whoami)" "$USER_PASSWORD"
systemctl --user stop gnome-remote-desktop
grdctl rdp disable
grdctl rdp enable
systemctl --user start gnome-remote-desktop
systemctl --user enable gnome-remote-desktop
if ss -tlnp | grep -q 3389; then
    echo "RDP is listening on port 3389 ✓"
else
    echo "WARNING: RDP is NOT listening on port 3389 — check gnome-remote-desktop status"
fi
# ── Disable Thunderbird send confirmation dialog ──────────────────────────────
echo 'user_pref("mail.warn_on_send_accel_key", false);' >> ~/.thunderbird/*.default-release/prefs.js
# ── 6. Setup autostart service ───────────────────────────────────────────────
echo ""
echo "[6/7] Setting up systemd service..."
systemctl --user stop lisa-agent 2>/dev/null || true
systemctl --user disable lisa-agent 2>/dev/null || true
chmod +x setup_autostart.sh
./setup_autostart.sh
# ── Disable sleep, hibernate and lock screen ──────────────────────────────────
gsettings set org.gnome.desktop.screensaver lock-enabled false
gsettings set org.gnome.desktop.session idle-delay 0
echo "$USER_PASSWORD" | sudo -S systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
echo ""
echo "=== Setup Complete ==="
echo ""
