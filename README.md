# Linux Activity Agent

A sophisticated Linux user activity emulation system with auto-update capabilities, user isolation through mutexes, and comprehensive monitoring.

## Features

- **Auto-Updates**: Agents automatically detect and install new versions without downtime
- **User Isolation**: Mutex-based system ensures only one agent per user
- **Heartbeat Monitoring**: Regular status reports with detailed statistics
- **Plugin System**: Extensible architecture for custom applications
- **Database Integration**: Full configuration and activity logging via PostgreSQL
- **Binary Compilation**: Nuitka-based compilation for production deployment
- **SystemD Integration**: Professional service management with auto-restart

## Requirements

- Ubuntu 20.04+ / Debian 10+ / CentOS 8+
- Python 3.8+
- PostgreSQL 12+
- X11 (for GUI applications)
- systemd

## Quick Start

### 1. Install Dependencies

```bash
# System packages
sudo apt update
sudo apt install -y python3 python3-pip postgresql postgresql-contrib
sudo apt install -y build-essential xvfb xdotool

# Python packages
pip3 install psycopg2-binary psutil nuitka
```

### 2. Setup Database

```bash
# Connect database
psql -h localhost -U lisa -d lisa_dev
password: pass

### 3. Deploy Agent

```bash
# Clone repository
git clone https://github.com/yourusername/linux-activity-agent.git
cd linux-activity-agent

# Build agent binary
sudo python3 updatable_agent_builder.py build 1 --name agent_v1

# Deploy for user
sudo python3 updatable_agent_builder.py deploy 1 USER_001

# Start agent service
sudo systemctl start activity-agent-template-1-user-USER_001
sudo systemctl enable activity-agent-template-1-user-USER_001
```

## Project Structure

```
linux-activity-agent/
├── complete_updatable_agent.py      # Main agent source code
├── updatable_agent_builder.py       # Build and deployment tool
├── setup/
│   ├── create_tables.sql           # Database schema
│   └── sample_data.sql             # Example templates
├── plugins/                        # Plugin directory (optional)
│   └── example_plugin.py
├── docs/
│   ├── DEPLOYMENT.md              # Detailed deployment guide
│   ├── CONFIGURATION.md           # Configuration reference
│   └── API.md                     # API documentation
└── README.md
```

## Configuration

### Behavior Templates

Define user behavior patterns in the database:

```sql
INSERT INTO behavior_templates (name, template_data, role_id) VALUES (
    'Developer Template',
    '{
        "user_id": "DEV_001",
        "username": "developer",
        "work_schedule": {
            "start_time": "09:00",
            "end_time": "18:00",
            "breaks": [{"start": "12:00", "duration_minutes": 60}]
        },
        "applications_used": ["Terminal", "Firefox", "Visual Studio Code"]
    }'::jsonb,
    1
);
```

### Application Templates

Define application behaviors:

```sql
INSERT INTO applications_template (name, template_config) VALUES (
    'Visual Studio Code',
    '{
        "execution": {
            "open_command": "code",
            "close_command": "pkill -f code"
        },
        "activities": [
            {
                "name": "Write code",
                "commands": [
                    {"type": "type_text", "text": "print(\"Hello World\")"},
                    {"type": "key_combination", "keys": "ctrl+s"}
                ]
            }
        ]
    }'::jsonb
);
```

## Auto-Update System

The agent automatically checks for updates every 5 minutes:

1. Update configuration in database
2. Build new version: `sudo python3 updatable_agent_builder.py build 1`
3. Agent detects and installs update automatically
4. Zero downtime - old agent gracefully hands over to new version

## Monitoring

### View Running Agents

```bash
# List all running agents
sudo python3 updatable_agent_builder.py list-running

# Check specific service
sudo systemctl status activity-agent-template-1-user-USER_001

# View logs
sudo journalctl -u activity-agent-template-1-user-USER_001 -f
```

### Database Monitoring

```sql
-- Agent status
SELECT * FROM agents ORDER BY last_seen DESC;

-- Recent activities
SELECT * FROM agent_activities ORDER BY created_at DESC LIMIT 20;

-- Agent statistics
SELECT agent_id, COUNT(*) as activity_count 
FROM agent_activities 
GROUP BY agent_id;
```

## Plugin System

Create custom applications by adding Python files to `/opt/linux_agent/plugins/`:

```python
# example_plugin.py
def get_application_config():
    return {
        "MyCustomApp": {
            "open": "myapp",
            "close": "pkill -f myapp",
            "activities": [
                {
                    "description": "Custom activity",
                    "commands": ["xdotool type 'Hello from plugin'"]
                }
            ]
        }
    }
```

## Key Components

### 1. Agent Core (complete_updatable_agent.py)
- Main activity emulation engine
- Work schedule management
- Application lifecycle control
- Activity simulation

### 2. Builder (updatable_agent_builder.py)
- Binary compilation with Nuitka
- Deployment automation
- SystemD service creation
- Version management

### 3. Managers
- **HeartbeatManager**: Sends periodic status updates to backend
- **AgentMutexManager**: Ensures single instance per user
- **AgentUpdateManager**: Handles automatic updates
- **PluginManager**: Loads and manages plugins
- **DatabaseManager**: Handles all database operations

## Command Reference

### Builder Commands

```bash
# Build agent
sudo python3 updatable_agent_builder.py build <template_id> [--name <name>]

# Deploy agent
sudo python3 updatable_agent_builder.py deploy <template_id> <user_id> [--target <path>]

# Start agent
sudo python3 updatable_agent_builder.py start <template_id> <user_id>

# Stop agent
sudo python3 updatable_agent_builder.py stop <template_id> <user_id>

# List builds
sudo python3 updatable_agent_builder.py list-builds [--template <id>]

# List running agents
sudo python3 updatable_agent_builder.py list-running
```

### Direct Execution (Development)

```bash
# Run directly from source
python3 complete_updatable_agent.py <template_id> <user_id>

# With virtual display
Xvfb :99 -screen 0 1920x1080x24 &
DISPLAY=:99 python3 complete_updatable_agent.py <template_id> <user_id>
```

## Database Schema

### Core Tables

1. **roles** - User role definitions
2. **behavior_templates** - User behavior configurations
3. **applications_template** - Application configurations
4. **agents** - Agent instances
5. **agent_builds** - Build history and versions
6. **agent_activities** - Activity logs

## Security Considerations

- Database credentials should be stored securely
- Mutex system prevents duplicate agents
- Graceful shutdown on signals (SIGTERM, SIGINT)
- Comprehensive error handling and logging
- SystemD service isolation
- Limited file system access

## Troubleshooting

### Agent Won't Start
```bash
# Check logs
sudo journalctl -u activity-agent-template-1-user-USER_001 -n 50

# Check mutex
ls -la /var/run/activity_agents/

# Verify database connection
psql -h localhost -U lisa -d lisa_dev -c "SELECT 1;"
```

### Update Not Working
```bash
# Check build status
psql -h localhost -U lisa -d lisa_dev -c "SELECT * FROM agent_builds ORDER BY created_at DESC;"

# Force update check (restart service)
sudo systemctl restart activity-agent-template-1-user-USER_001
```

### Application Not Found
```bash
# Install missing applications
sudo apt install firefox xterm

# Or update template to use only installed apps
UPDATE behavior_templates SET template_data = jsonb_set(
    template_data, 
    '{applications_used}', 
    '["Terminal"]'::jsonb
) WHERE id = 1;
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

- Issues: https://github.com/yourusername/linux-activity-agent/issues
- Wiki: https://github.com/yourusername/linux-activity-agent/wiki

## Acknowledgments

- Built with Python, PostgreSQL, and love
- Uses Nuitka for binary compilation
- Inspired by real-world automation needs
