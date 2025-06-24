#!/bin/bash

# Установщик Enhanced Linux Activity Agent with Plugin Support
set -e

AGENT_PATH="./activity_agent"
INSTALL_DIR="/opt/linux_agent"
SERVICE_FILE="/etc/systemd/system/activity-agent.service"

echo "Enhanced Linux Activity Agent Installer"
echo "======================================="
echo "Features: Plugin support, JSON configuration, Python extensions"

# Проверяем права root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root (use sudo)" 
   exit 1
fi

# Проверяем наличие файла агента
if [ ! -f "$AGENT_PATH" ]; then
    echo "Error: activity_agent file not found in current directory"
    exit 1
fi

# Создаем директорию установки
echo "Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Копируем агента в рабочую директорию
echo "Installing agent to $INSTALL_DIR..."
cp "$AGENT_PATH" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/activity_agent"

# Также копируем в системную директорию для удобства
echo "Installing agent to /usr/local/bin..."
cp "$AGENT_PATH" "/usr/local/bin/activity_agent"
chmod +x "/usr/local/bin/activity_agent"

# Копируем plugin_manager.py в директорию плагинов
echo "Setting up plugin system..."
mkdir -p "$INSTALL_DIR/plugins"
if [ -f "plugin_manager.py" ]; then
    cp "plugin_manager.py" "$INSTALL_DIR/plugins/"
    echo "Plugin manager copied to $INSTALL_DIR/plugins/"
fi

# Запускаем установку зависимостей и настройку системы
echo "Installing dependencies and setting up service..."
"$INSTALL_DIR/activity_agent" --install

echo ""
echo "Installation completed successfully!"
echo "============================================"
echo "Agent installed to: $INSTALL_DIR/activity_agent"
echo "System binary: /usr/local/bin/activity_agent"
echo "Service: activity-agent.service"
echo "Plugin directory: $INSTALL_DIR/plugins/"
echo ""
echo "Available commands:"
echo "  sudo systemctl start activity-agent    # Start the agent"
echo "  sudo systemctl status activity-agent   # Check status"
echo "  sudo systemctl stop activity-agent     # Stop the agent"
echo ""
echo "Plugin management:"
echo "  sudo activity_agent --list-plugins              # List installed plugins"
echo "  sudo activity_agent --create-plugin 'App Name'  # Create new plugin template"
echo ""
echo "Logs and monitoring:"
echo "  sudo journalctl -u activity-agent -f   # View real-time logs"
echo "  tail -f /var/log/activity_agent/activity_agent.log  # View log file"
echo ""
echo "Plugin configuration directory: $INSTALL_DIR/plugins/configs/"
echo "Add your JSON plugin files there and restart the agent to load them."

