# Updatable Activity Agent

This is an updatable Linux activity agent that runs in a continuous loop and supports automatic updates through a mutex system.

## Features

- **Continuous Operation**: Runs in a `while True` loop performing agent tasks
- **Automatic Updates**: Monitors for new versions and updates itself through the mutex system
- **Mutex-based User Isolation**: Ensures only one agent instance per user/template
- **Database Integration**: Loads configuration from PostgreSQL database
- **Application Simulation**: Simulates user activity in various applications
- **Heartbeat Support**: Sends regular status updates to backend
- **Plugin System**: Supports loading custom plugins for extended functionality

## Prerequisites

- Python 3.8+
- PostgreSQL database with the required schema
- Nuitka for compilation
- Required Python packages:
  - psycopg2
  - psutil
  - Other dependencies as specified in the agent

## Database Setup

The agent expects a PostgreSQL database with the following configuration:

```python
DATABASE_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "database": "lisa_dev",
    "user": "lisa",
    "password": "pass"
}
```

Make sure your database contains:
- `behavior_templates` table with user templates
- `applications_template` table with application configurations
- `agents` table for agent registration
- `agent_builds` table for tracking builds

## Building the Agent

### 1. Compile with Nuitka

Use the provided builder script to compile the agent:

```bash
# Build agent for a specific template
python3 fixed_updatable_agent_builder.py build <template_id> --name <agent_name>

# Example
python3 fixed_updatable_agent_builder.py build 1 --name agent_template_1
```

The compiled binary will be placed in `/opt/agent_builds/` by default.

### 2. Deploy the Agent

Deploy the compiled agent to the target location:

```bash
# Deploy agent
python3 fixed_updatable_agent_builder.py deploy <template_id> <user_id>

# Example
python3 fixed_updatable_agent_builder.py deploy 1 USER_001
```

## Launching the Agent

### Direct Execution

Run the compiled agent directly:

```bash
# Run with template ID and user ID
./agent <template_id> <user_id>

# Example
./agent 1 USER_001
```

### Using Systemd (Recommended)

The deployment script creates a systemd service. You can manage it with:

```bash
# Start the agent
sudo systemctl start activity-agent-template-1-user-USER_001

# Enable auto-start on boot
sudo systemctl enable activity-agent-template-1-user-USER_001

# Check status
sudo systemctl status activity-agent-template-1-user-USER_001

# View logs
sudo journalctl -u activity-agent-template-1-user-USER_001 -f

# Stop the agent
sudo systemctl stop activity-agent-template-1-user-USER_001
```

## Agent Operation

Once launched, the agent will:

1. **Initialize**: Connect to database, load configuration, acquire mutex
2. **Main Loop**: Continuously run in a `while True` loop:
   - Check for updates every 5 minutes through the mutex system
   - Perform agent tasks based on work schedule
   - Simulate user activities in applications
   - Handle inactive periods (breaks, non-work hours)
   - Send heartbeats to backend (if enabled)

## Updating the Agent

### Automatic Updates

The agent monitors for updates automatically:

1. **Update Check**: Every 5 minutes, the agent checks the database for new builds
2. **Version Comparison**: Compares current version hash with latest build
3. **Self-Update**: If a new version is found:
   - Launches the new binary
   - New instance acquires mutex (killing old instance)
   - Seamless transition with minimal downtime

### Manual Update Process

To update an agent manually:

1. **Build New Version**:
   ```bash
   # Make changes to complete_updatable_agent.py
   # Then build
   python3 fixed_updatable_agent_builder.py build <template_id>
   ```

2. **Deploy New Version**:
   ```bash
   python3 fixed_updatable_agent_builder.py deploy <template_id> <user_id>
   ```

3. **Restart Service** (if using systemd):
   ```bash
   sudo systemctl restart activity-agent-template-1-user-USER_001
   ```

### Update Mechanism

The update process works through the mutex system:

1. New agent binary is deployed to the system
2. Running agent detects new version in database
3. Running agent launches new binary
4. New binary tries to acquire mutex for the user
5. Mutex manager detects existing agent and sends SIGTERM
6. Old agent performs graceful shutdown
7. New agent acquires mutex and starts operation

## Monitoring

### View Running Agents

List all running agents:

```bash
python3 fixed_updatable_agent_builder.py list-running
```

### Check Agent Builds

List available builds:

```bash
python3 fixed_updatable_agent_builder.py list-builds
```

### Agent Logs

Logs are written to:
- `/var/log/activity_agent/updatable_agent.log` (if permissions allow)
- `/tmp/updatable_agent.log` (fallback)

### Mutex Files

Mutex lock files are stored in:
- `/var/run/activity_agents/` (primary)
- `/tmp/activity_agents/` (fallback)

Format: `agent_user_<user_id>_template_<template_id>.lock`

## Configuration

### Work Schedule

Defined in the behavior template:
```json
{
  "work_schedule": {
    "start_time": "09:00",
    "end_time": "18:00",
    "breaks": [
      {"start": "12:00", "duration_minutes": 60}
    ]
  }
}
```

### Applications

Applications can be:
1. **Built-in**: Hardcoded in the agent (Terminal, Firefox, VSCode, etc.)
2. **Database**: Defined in `applications_template` table
3. **Plugins**: Loaded from plugin directory

### Heartbeat Configuration

```python
HEARTBEAT_CONFIG = {
    "enabled": True,
    "backend_url": "http://localhost:8000/api/agents/heartbeat",
    "interval_hours": 24,
    "include_statistics": True,
    "api_key": "sk-agent-heartbeat-key-2024"
}
```

## Troubleshooting

### Agent Won't Start

1. Check database connectivity
2. Verify template exists in database
3. Check mutex directory permissions
4. Review logs for errors

### Agent Not Updating

1. Verify new build exists in database
2. Check update monitoring is enabled
3. Ensure mutex system is working
4. Check agent has permission to launch new processes

### Multiple Instances

The mutex system prevents multiple instances. If you see duplicates:
1. Check mutex files in `/var/run/activity_agents/`
2. Manually remove stale lock files
3. Use `pkill` to terminate orphaned processes

## Security Considerations

1. **Database Credentials**: Store securely, consider using environment variables
2. **Mutex Permissions**: Ensure proper permissions on mutex directories
3. **Binary Permissions**: Compiled agents should have appropriate execute permissions
4. **Update Security**: Verify binary integrity before auto-updates

## Development

To modify the agent:

1. Edit `complete_updatable_agent.py`
2. Test changes locally
3. Build new version with the builder
4. Deploy and monitor the update process

## Support

For issues or questions:
1. Check agent logs
2. Verify database connectivity
3. Review systemd service status
4. Examine mutex lock files
