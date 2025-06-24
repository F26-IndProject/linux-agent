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
1. Extract files to a directory (activity_agent + install_agent.sh)
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
