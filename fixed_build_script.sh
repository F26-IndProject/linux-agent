#!/bin/bash

# Скрипт для сборки единого исполняемого файла Enhanced Linux Activity Agent
set -e

echo "Building Enhanced Linux Activity Agent with Plugin Support..."

# Проверяем наличие необходимых файлов
if [ ! -f "enhanced_agent.py" ]; then
    echo "Error: enhanced_agent.py not found in current directory"
    exit 1
fi

if [ ! -f "plugin_manager.py" ]; then
    echo "Error: plugin_manager.py not found in current directory"
    exit 1
fi

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "Python3 is required but not installed. Installing..."
    sudo apt update
    sudo apt install -y python3 python3-pip
fi

# Устанавливаем PyInstaller
echo "Installing PyInstaller..."
pip3 install pyinstaller

# Создаем spec файл для PyInstaller
cat > activity_agent.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-
# Enhanced Linux Activity Agent with Plugin Support

block_cipher = None

a = Analysis(
    ['enhanced_agent.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('plugin_manager.py', '.'),
    ],
    hiddenimports=[
        'subprocess',
        'logging',
        'json',
        'datetime',
        'random',
        'time',
        'os',
        'sys',
        'shutil',
        'urllib.request',
        'tempfile',
        'pathlib',
        'importlib.util',
        'collections',
        'threading',
        'signal',
        'functools',
        'itertools',
        'socket',
        'platform'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'PyQt5',
        'PySide2',
        'wx'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Исключаем ненужные модули для уменьшения размера
a.binaries = [x for x in a.binaries if not x[0].startswith('lib')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='activity_agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
EOF

# Сборка
echo "Building executable..."
pyinstaller --clean activity_agent.spec

# Проверяем результат
if [ -f "dist/activity_agent" ]; then
    echo "Build successful!"
    echo "Executable: $(pwd)/dist/activity_agent"
    echo "Size: $(du -h dist/activity_agent | cut -f1)"
    
    # Делаем файл исполняемым
    chmod +x dist/activity_agent
    
    # Тестируем базовый функционал
    echo "Testing basic functionality..."
    if ./dist/activity_agent --help > /dev/null 2>&1; then
        echo "✅ Basic functionality test passed"
    else
        echo "❌ Basic functionality test failed"
    fi
    
    # Создаем инсталлятор
    echo "Creating installer script..."
    cat > dist/install_agent.sh << 'INSTALL_EOF'
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

INSTALL_EOF

    chmod +x dist/install_agent.sh
    
    # Создаем README файл
    cat > dist/README.md << 'README_EOF'
# Enhanced Linux Activity Agent

## Overview
This is an enhanced version of the Linux Activity Agent with plugin support, allowing you to easily add new applications through JSON configuration files.

## Features
- **Plugin System**: Add new applications via JSON templates
- **Python Extensions**: Create custom logic with Python classes
- **Smart Scheduling**: Work hours, break times, intelligent activity patterns
- **System Integration**: Systemd service, automatic startup, logging
- **Easy Management**: CLI commands for plugin creation and management

## Quick Start
1. Extract files to a directory
2. Run: `sudo ./install_agent.sh`
3. Start agent: `sudo systemctl start activity-agent`

## Plugin Management
```bash
# List available plugins
sudo activity_agent --list-plugins

# Create new plugin
sudo activity_agent --create-plugin "Discord"

# Edit plugin configuration
sudo nano /opt/linux_agent/plugins/configs/discord.json

# Restart to load changes
sudo systemctl restart activity-agent
```

## Plugin Directory Structure
```
/opt/linux_agent/plugins/
├── configs/          # JSON plugin configurations
│   ├── discord.json
│   ├── telegram.json
│   └── your_app.json
└── scripts/          # Optional Python extensions
    ├── telegram.py
    └── your_app.py
```

## Monitoring
```bash
# View logs
sudo journalctl -u activity-agent -f

# Check status
sudo systemctl status activity-agent

# Stop agent
sudo systemctl stop activity-agent
```

## Configuration
Main user configuration: `/opt/linux_agent/configs/user_config.json`
Plugin configurations: `/opt/linux_agent/plugins/configs/*.json`

For detailed documentation and examples, visit the project repository.
README_EOF
    
    echo ""
    echo "Files created:"
    echo "  - dist/activity_agent (main executable)"
    echo "  - dist/install_agent.sh (installer script)"
    echo "  - dist/README.md (documentation)"
    echo ""
    echo "Usage:"
    echo "  1. Copy all files from dist/ to target machine"
    echo "  2. Run: sudo ./install_agent.sh"
    echo "  3. Agent will be installed with plugin support enabled"
    echo ""
    echo "Testing the build:"
    echo "  ./dist/activity_agent --help"
    echo "  ./dist/activity_agent --list-plugins"
    
else
    echo "Build failed!"
    exit 1
fi

# Опционально: создаем архив для распространения
echo "Creating distribution archive..."
cd dist
tar -czf enhanced_linux_activity_agent.tar.gz activity_agent install_agent.sh README.md
echo "Distribution package: dist/enhanced_linux_activity_agent.tar.gz"

echo ""
echo "Build process completed successfully!"
echo "Enhanced Linux Activity Agent with Plugin Support is ready for deployment."