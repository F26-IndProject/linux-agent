# LISA Linux Agent — Setup Guide

Complete step-by-step guide for deploying the LISA Linux agent on a target VM. This guide assumes the LISA server (backend + database + frontend) is already running.

---

## Prerequisites

- Ubuntu Desktop 22.04 LTS
- Server VM running with backend on `192.168.100.10`
- Network connectivity between this VM and the server

---

## 1. Switch from Wayland to X11

The LISA agent uses `xdotool` to send keystrokes to running applications. `xdotool` works on X11 but does not work on Wayland. Ubuntu Desktop 22.04 defaults to Wayland so this step is mandatory.

```
sudo nano /etc/gdm3/custom.conf
```

Find the line `#WaylandEnable=false` and uncomment it:

```
WaylandEnable=false
```

Save and reboot:

```
sudo reboot
```

Verify you are on X11:

```
echo $XDG_SESSION_TYPE
```

Expected output: `x11`. If it says `wayland` the config did not take — re-check the file.

---

## 2. Install Dependencies

```
sudo apt update
sudo apt install -y python3-pip python3-venv git xdotool xvfb postgresql-client firefox xterm gnome-terminal nano htop curl gcc patchelf
```

Install Visual Studio Code:

```
sudo snap install code --classic
```

Verify xdotool is working correctly with X11:

```
xdotool getactivewindow
```

This should return a window ID number. If it errors, X11 is not set up correctly — go back to step 1.

---

## 3. Clone the Agent Repository

```
cd ~
git clone https://github.com/LISA-SWP25/linux-agent.git
cd linux-agent
```

---

## 4. Set Up Python Virtual Environment

```
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install psycopg2-binary psutil requests
```

---

## 5. Configure the Agent

Set the server IP variable:

```
SERVER_IP=192.168.100.10
```

Patch the agent configuration to point at the server:

```
sed -i "s|\"host\": \"127.0.0.1\"|\"host\": \"${SERVER_IP}\"|" modified_updatable_agent.py
sed -i "s|\"password\": \"pass\"|\"password\": \"lisa_password_2026\"|" modified_updatable_agent.py
sed -i "s|\"backend_url\": \"http://localhost:8000/api/agents/heartbeat\"|\"backend_url\": \"http://${SERVER_IP}:8000/api/agents/heartbeat\"|" modified_updatable_agent.py
```

Verify the changes took effect:

```
grep -E "host|password|backend_url" modified_updatable_agent.py | head -10
```

---

## 6. Test Database Connectivity

Confirm this VM can reach the server's PostgreSQL database:

```
PGPASSWORD=lisa_password_2026 psql -h 192.168.100.10 -U lisa -d lisa_dev -c "SELECT version();"
```

Expected output: a PostgreSQL version string. If connection is refused, check that port 5432 is open on the server VM and that `pg_hba.conf` allows remote connections.

---

## 7. Test the Agent in Foreground

Run the agent manually to confirm everything works before setting up the service:

```
cd ~/linux-agent
source venv/bin/activate
python3 modified_updatable_agent.py 1 lisalinux
```

Replace `lisalinux` with your actual username and `1` with your template ID.

Expected output includes:
- `Connected to PostgreSQL database`
- `Loaded config for template 1`
- `Initial heartbeat sent: True`
- Agent opening Terminal, Firefox, or Visual Studio Code

> **Note:** The agent only runs during configured working hours (default 09:00–18:00). If testing outside those hours see section 11 for how to change the schedule.

---

## 8. Verify Heartbeat Reached the Server

From the server VM browser:

```
http://localhost:3000/agent/lisalinux
```

Or via the API:

```
curl http://localhost:8000/api/agents/active
```

The agent should appear as active with a recent `last_seen` timestamp.

---

## 9. Build the Agent Binary (Optional)

Not needed because we will configure daemon for the agent below

## 10. Install as a SystemD User Service (Autostart)

Here we have only one daemon for role 1. for any role, you must create a system daemon for it by simple changing
/home/lisalinux/linux-agent/modified_updatable_agent.py 1 lisalinux
to
/home/lisalinux/linux-agent/modified_updatable_agent.py [1 to 5] lisalinux

Create the service directory:

```
mkdir -p ~/.config/systemd/user
```


Create the service file:

```
nano ~/.config/systemd/user/lisa-agent.service
```

Paste:

```
[Unit]
Description=LISA Linux Agent
After=graphical-session.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/lisalinux/linux-agent
ExecStart=/home/lisalinux/linux-agent/venv/bin/python3 /home/lisalinux/linux-agent/modified_updatable_agent.py 1 lisalinux
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical-session.target

```

Enable and start the service:

```
systemctl --user daemon-reload
systemctl --user enable lisa-agent.service
systemctl --user start lisa-agent.service
```

Watch the logs:

```
journalctl --user -u lisa-agent -f
```

---

## 11. Enable Auto-Login (Required for Unattended Operation)

The agent runs as a user service and requires a logged-in graphical session. For the agent to start automatically on reboot without manual login, enable auto-login:

```
sudo nano /etc/gdm3/custom.conf
```

Add under `[daemon]`:

```
AutomaticLoginEnable=true
AutomaticLogin=lisalinux
```

Replace `lisalinux` with your actual username. On reboot the VM will log in automatically, start the graphical session, and the agent service will start without any manual intervention.

---

## 12. Change Working Hours for Testing

The agent only simulates activity during configured working hours. To run at any time during testing, update the schedule on the server VM:

**Set to all day:**

```
sudo docker exec lisa_postgres_quick psql -U lisa -d lisa_dev -c "UPDATE behavior_templates SET template_data = template_data::jsonb || '{\"work_schedule\": {\"start_time\": \"00:00\", \"end_time\": \"23:59\", \"breaks\": []}}' WHERE id = 1;"
```

**Restore to normal hours:**

```
sudo docker exec lisa_postgres_quick psql -U lisa -d lisa_dev -c "UPDATE behavior_templates SET template_data = template_data::jsonb || '{\"work_schedule\": {\"start_time\": \"09:00\", \"end_time\": \"18:00\", \"breaks\": [{\"start\": \"12:00\", \"duration_minutes\": 60}, {\"start\": \"15:30\", \"duration_minutes\": 15}]}}' WHERE id = 1;"
```

After changing the schedule, restart the agent so it picks up the new configuration.

---

## 13. Verify Agent Is Not Running as Parent Process

This confirms the mandatory requirement that launched applications must not show the agent as their parent process.

While the agent is running and has opened an application:

```
ps -eo pid,ppid,user,comm --forest | grep -E "lisalinux|firefox|gnome-terminal|code" | head -30
```

Note the PPID of any launched application, then check what that process is:

```
ps -p <PPID> -o pid,ppid,comm
```

Expected result:

```
PID    PPID COMMAND
1505      1 systemd
```

The parent should be `systemd` — not `python3` or the agent binary. The correct process tree is:

```
systemd (1)
└── systemd --user (1505)
    └── gnome-terminal / firefox / code
```

The agent never appears as the parent process of any launched application. Requirement met.

---

## Troubleshooting

**Agent finds no applications**
Check that `is_active = true` for all applications in the database:
```
sudo docker exec lisa_postgres_quick psql -U lisa -d lisa_dev -c "UPDATE applications_template SET is_active = true;"
```

**xdotool fails with "Can't open display"**
The service started before the graphical session was ready. Check that auto-login is configured and that the service is a user service (`systemctl --user`), not a system service (`sudo systemctl`).

**Agent stuck after "Initial heartbeat sent: True"**
The agent is outside working hours. Either wait until 09:00 or change the schedule using the commands in section 12.

**Heartbeat 500 error from backend**
The `os_type` column is too short. Fix on the server VM:
```
sudo docker exec lisa_postgres_quick psql -U lisa -d lisa_dev -c "ALTER TABLE agents ALTER COLUMN os_type TYPE VARCHAR(100);"
```

**PyCharm not found warning**
PyCharm is listed in the template but not installed. This is a warning only — the agent continues with the other applications. To silence it, disable PyCharm in the database:
```
sudo docker exec lisa_postgres_quick psql -U lisa -d lisa_dev -c "UPDATE applications_template SET is_active = false WHERE name = 'PyCharm';"
```

