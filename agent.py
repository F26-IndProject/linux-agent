"""
LISA Linux Agent — main entry point
====================================
Connects directly to PostgreSQL. Same architecture as the Windows agent.
All child processes are spawned via double-fork so agent never appears
as the parent in the process tree.
"""
import argparse
import getpass
import logging
import os
import random
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
import yaml
from dotenv import load_dotenv
import signal
import subprocess
from actions import apps, office, email, smb, ssh, cron, files, cleanup, terminal
from client.server_api import send_heartbeat_to_server
from client.database import DatabaseManager
from utils.logger import setup_logger
# ─── CONFIGURATION ────────────────────────────────────────────────────────────
load_dotenv()
SERVER_IP   = os.getenv("SERVER_IP")
SERVER_PORT = int(os.getenv("SERVER_PORT", 8000))
HEARTBEAT_URL = f"http://{SERVER_IP}:{SERVER_PORT}/api/agents/heartbeat"
HEARTBEAT_INTERVAL_SECONDS = 300
# ────────────────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="LISA Linux Agent")
parser.add_argument("--debug", action="store_true")
args = parser.parse_args()
username = getpass.getuser()
def _get_or_create_agent_id(username: str) -> str:
    """
    Load a stable agent ID from disk, or generate one once and save it.
    This ensures the same ID survives reboots, MAC changes, and hostname changes.
    """
    id_file = Path.home() / ".lisa_agent_id"
    if id_file.exists():
        stored = id_file.read_text().strip()
        if stored:
            return stored
    new_id = f"agent_{username}_{uuid.uuid4().hex[:12]}"
    id_file.write_text(new_id)
    return new_id
AGENT_ID = _get_or_create_agent_id(username)
LOG_FILE = Path("logs/agent.log")
LOG_FILE.parent.mkdir(exist_ok=True)
if args.debug:
    if LOG_FILE.exists():
        LOG_FILE.unlink()
        print("[*] Debug mode: cleared old log file")
    for lock_file in Path().glob("*.lock"):
        try:
            lock_file.unlink()
            print(f"[*] Debug mode: removed lock file {lock_file.name}")
        except Exception as e:
            print(f"[!] Could not remove lock file {lock_file.name}: {e}")
def _launch_log_writer():
    """Launch log_writer via spawn binary so parent = systemd."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "log_writer"],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            return
        if getattr(sys, 'frozen', False):
            base = Path(sys.executable).parent.parent  # dist/ -> linux-agent/
        else:
            base = Path(__file__).parent               # ~/linux-agent/
        spawn  = base / "spawn"
        writer = base / "log_writer" / "log_writer"
        if spawn.exists() and writer.exists():
            subprocess.Popen(
                [str(spawn), str(writer)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL
            )
            time.sleep(1)
    except Exception as e:
        print(f"[!] Could not launch log_writer: {e}")
_launch_log_writer()
logger = setup_logger()
LOCK_FILE = Path(f"{AGENT_ID}.lock")
# Shared database manager
db = DatabaseManager()
# Shared mutable role state
agent_role_state = {"role": None, "activities": [], "loaded_at": None}
role_lock = threading.Lock()
def check_singleton():
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
        logger.info("Removed stale lock file from previous session")
    LOCK_FILE.touch()
    logger.info(f"Lock file created: {LOCK_FILE}")
def cleanup_singleton():
    if LOCK_FILE.exists():
        LOCK_FILE.unlink()
        logger.info(f"Lock file removed: {LOCK_FILE}")
CONFIG_PATH = Path("config/settings.yaml")
PATHS_PATH  = Path("config/paths.yaml")
ROLES_DIR   = Path("roles")
def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)
def load_config():
    settings  = load_yaml(CONFIG_PATH)
    paths     = load_yaml(PATHS_PATH)
    role_name = settings["role"]
    role_file = ROLES_DIR / f"{role_name}.yaml"
    role      = load_yaml(role_file)
    logger.info(f"Loaded role: {role_name}")
    return settings, paths, role
def load_role_activities(role_name: str):
    role_file = ROLES_DIR / f"{role_name}.yaml"
    if role_file.exists():
        role_data = load_yaml(role_file)
        activities = role_data.get("activities", [])
        logger.info(f"Loaded role '{role_name}' from YAML ({len(activities)} actions)")
        return activities
    logger.info(f"No YAML for role '{role_name}' — checking database")
    activities = db.get_role_definition(role_name)
    if activities:
        return activities
    logger.warning(f"Role '{role_name}' not found in YAML or database — keeping current role")
    return None
def _check_break():
    try:
        brk = db.get_agent_break(AGENT_ID)
        if brk:
            cur_time = datetime.now().time()
            start    = datetime.strptime(brk['break_start'], "%H:%M").time()
            end      = datetime.strptime(brk['break_end'],   "%H:%M").time()
            if start <= cur_time <= end:
                return True, f"break time: {brk['name']} ({brk['break_start']}–{brk['break_end']})"
    except Exception:
        pass
    return False, None
def is_work_time(settings):
    # 1. Public holiday check
    try:
        if db.is_public_holiday():
            return False, "public holiday"
    except Exception:
        pass
    # 2. Agent-specific schedule from DB
    try:
        schedule = db.get_agent_schedule(AGENT_ID)
        if schedule:
            now      = datetime.now()
            weekday  = now.isoweekday()
            cur_time = now.time()
            start    = datetime.strptime(schedule['work_start'], "%H:%M").time()
            end      = datetime.strptime(schedule['work_end'],   "%H:%M").time()
            if start <= end:
                in_time = start <= cur_time <= end
            else:
                in_time = cur_time >= start or cur_time <= end
            in_hours = weekday in schedule['work_days'] and in_time
            if in_hours:
                on_break, break_reason = _check_break()
                if on_break:
                    return False, break_reason
                return True, None
            return False, f"Assigned schedule: {schedule['name']} ({schedule['work_start']}–{schedule['work_end']})"
    except Exception:
        pass
    # 3. Fall back to local schedule
    now        = datetime.now()
    weekday    = now.isoweekday()
    cur_time   = now.time()
    work_days  = settings.get("work_days", [1, 2, 3, 4, 5])
    work_start = settings.get("work_start", "09:00")
    work_end   = settings.get("work_end",   "18:00")
    start = datetime.strptime(work_start, "%H:%M").time()
    end   = datetime.strptime(work_end,   "%H:%M").time()
    if start <= end:
        in_time = start <= cur_time <= end
    else:
        in_time = cur_time >= start or cur_time <= end
    in_hours = weekday in work_days and in_time
    if in_hours:
        on_break, break_reason = _check_break()
        if on_break:
            return False, break_reason
        return True, None
    return False, f"local schedule ({work_start}–{work_end})"
def weighted_choice(activities):
    weights = [a.get("weight", 1) for a in activities]
    return random.choices(activities, weights=weights, k=1)[0]
def run_action(action, paths, settings):
    action_type = action.get("action", "sleep")
    delay = action.get("delay", 0)
    if delay:
        logger.info(f"Waiting {delay}s before action: {action_type}")
        time.sleep(delay)
    logger.info(f"Running action: {action_type}")
    try:
        if action_type == "open_browser":
            apps.open_browser(urls=action.get("urls"))
        elif action_type == "open_text_editor":
            apps.open_vscode()
        elif action_type == "word_document":
            office.create_word_document()
        elif action_type == "excel_spreadsheet":
            office.create_excel_spreadsheet()
        elif action_type == "send_email":
            email.send_email(recipients=action.get("recipients"))
        elif action_type == "read_email":
            email.read_email()
        elif action_type == "open_thunderbird":
            email.open_thunderbird()
        elif action_type == "terminal_commands":
            commands = action.get("commands", None)
            if commands:
                cmd = random.choice(commands)
            else:
                cmd = action.get("command", "whoami")
            terminal.run_commands(
                commands=[cmd],
                visible=action.get("visible", True)
            )
        elif action_type == "run_bash":
            commands = action.get("commands", None)
            if commands:
                cmd = random.choice(commands)
            else:
                cmd = action.get("command", "whoami")
            terminal.run_commands(commands=[cmd])
        elif action_type == "run_systemctl":
            commands = action.get("commands", None)
            if commands:
                cmd = random.choice(commands)
            else:
                cmd = action.get("command", "systemctl status")
            terminal.run_commands(commands=[cmd])
        elif action_type == "libreoffice_writer":
            office.create_word_document()
        elif action_type == "libreoffice_calc":
            office.create_excel_spreadsheet()
        elif action_type == "thunderbird_send":
            email.send_email(recipients=action.get("recipients"))
        elif action_type == "thunderbird_read":
            email.read_email()
        elif action_type == "smb_access":
            smb.access_share(
                server=action.get("server", SERVER_IP),
                share=action.get("share", "share"),
                mode=action.get("smb_action", "browse")
            )
        elif action_type == "ssh_connect":
            targets = action.get("targets") or action.get("ssh_connections")
            if targets:
                entry        = random.choice(targets)
                ssh_host     = entry.get("host", SERVER_IP)
                ssh_user     = entry.get("username", username)
                ssh_pass     = entry.get("password", "")
            else:
                ssh_host     = action.get("host", SERVER_IP)
                ssh_user     = action.get("username", username)
                ssh_pass     = action.get("password", "")
            ssh.connect(
                host=ssh_host,
                username=ssh_user,
                password=ssh_pass,
                duration_seconds=action.get("duration", 30)
            )
        elif action_type == "manage_cron":
            cron.manage_cron(
                jobs=action.get("jobs"),
                operations=action.get("operations"),
                agent_id=AGENT_ID,
                db=db
            )
        elif action_type == "create_file":
            files.create_file(
                path=action.get("path", "~/Documents/notes.txt"),
                content=action.get("content")
            )
        elif action_type == "edit_file":
            files.edit_file(path=action.get("path", "~/Documents/notes.txt"))
        elif action_type == "sleep":
            min_secs = action.get("min_seconds", 30)
            max_secs = action.get("max_seconds", 120)
            secs = random.randint(min_secs, max_secs)
            logger.info(f"Idle for {secs} seconds (range: {min_secs}–{max_secs})")
            time.sleep(secs)
        else:
            logger.warning(f"Unknown action type: {action_type}")
        db.update_agent_status(AGENT_ID, action_type)
        db.log_activity(
            agent_id=AGENT_ID,
            activity_type=action_type,
            activity_data={
                "action":    action_type,
                "details":   action,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    except Exception as e:
        logger.error(f"Action '{action_type}' failed: {e}")
        db.log_activity(
            agent_id=AGENT_ID,
            activity_type="error",
            activity_data={"action": action_type, "error": str(e)}
        )
def heartbeat_loop():
    while True:
        try:
            with role_lock:
                agent_role = agent_role_state["role"]
                loaded_at  = agent_role_state["loaded_at"]
            send_heartbeat_to_server(
                url=HEARTBEAT_URL,
                agent_id=AGENT_ID,
                username=username,
                role=agent_role or "user"
            )
            db_role = db.get_agent_role(AGENT_ID)
            if db_role and db_role != agent_role:
                new_activities = load_role_activities(db_role)
                if new_activities:
                    with role_lock:
                        agent_role_state["role"]       = db_role
                        agent_role_state["activities"] = new_activities
                        agent_role_state["loaded_at"]  = datetime.utcnow()
                    logger.info(f"Role changed to: {db_role} — activities reloaded ({len(new_activities)} actions)")
            elif db_role and loaded_at:
                updated_at = db.get_role_updated_at(db_role)
                if updated_at:
                    ua = updated_at.replace(tzinfo=None) if hasattr(updated_at, 'tzinfo') else updated_at
                    la = loaded_at.replace(tzinfo=None)  if hasattr(loaded_at, 'tzinfo')  else loaded_at
                    if ua > la:
                        new_activities = load_role_activities(db_role)
                        if new_activities:
                            with role_lock:
                                agent_role_state["activities"] = new_activities
                                agent_role_state["loaded_at"]  = datetime.utcnow()
                            logger.info(f"Custom role '{db_role}' was updated — activities reloaded ({len(new_activities)} actions)")
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
        time.sleep(HEARTBEAT_INTERVAL_SECONDS)
def _handle_sigterm(signum, frame):
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    raise KeyboardInterrupt
def main():
    signal.signal(signal.SIGTERM, _handle_sigterm)
    check_singleton()
    logger.info(f"LISA Linux Agent starting. Agent ID: {AGENT_ID}, User: {username}")
    if not db.connect():
        logger.error("Cannot connect to database. Exiting.")
        cleanup_singleton()
        sys.exit(1)
    try:
        settings, paths, role_data = load_config()
        activities = role_data.get("activities", [])
        role_name  = settings.get("role", "user")
        if not activities:
            logger.error("No activities defined in role file. Exiting.")
            return
        db.ensure_agent_exists(AGENT_ID, username, role_name)
        db_role = db.get_agent_role(AGENT_ID)
        if db_role and db_role != role_name:
            logger.info(f"DB role '{db_role}' overrides config role '{role_name}' — loading DB role")
            db_activities = load_role_activities(db_role)
            if db_activities:
                role_name  = db_role
                activities = db_activities
            else:
                logger.warning(f"Could not load DB role '{db_role}' — using config role '{role_name}'")
        with role_lock:
            agent_role_state["role"]       = role_name
            agent_role_state["activities"] = activities
            agent_role_state["loaded_at"]  = datetime.utcnow()
        t = threading.Thread(target=heartbeat_loop, daemon=True)
        t.start()
        logger.info(f"Heartbeat thread started — sending to {HEARTBEAT_URL}")
        c = threading.Thread(target=cleanup.cleanup_loop, daemon=True)
        c.start()
        logger.info("Cleanup thread started — removes files older than 4 days every 24h")
        # Default interval from settings.yaml — DB can override per agent
        default_interval_min = settings.get("activity_interval_min", 120)
        default_interval_max = settings.get("activity_interval_max", 300)
        was_idle    = False
        idle_reason = None
        while True:
            active, reason = is_work_time(settings)
            if not active:
                if not was_idle:
                    logger.info(f"Agent not working — {reason}")
                was_idle    = True
                idle_reason = reason
                time.sleep(300)
                continue
            if was_idle:
                logger.info("Agent resuming work")
                was_idle    = False
                idle_reason = None
            with role_lock:
                activities = list(agent_role_state["activities"])
            activity = weighted_choice(activities)
            run_action(activity, paths, settings)
            # Check DB for interval override — falls back to settings.yaml defaults
            db_interval  = db.get_agent_interval(AGENT_ID)
            interval_min = db_interval['interval_min'] if db_interval and db_interval.get('interval_min') else default_interval_min
            interval_max = db_interval['interval_max'] if db_interval and db_interval.get('interval_max') else default_interval_max
            wait = random.randint(interval_min, interval_max)
            logger.info(f"Waiting {wait}s before next activity")
            time.sleep(wait)
    except KeyboardInterrupt:
        logger.info("Stopped by user (Ctrl+C)")
    finally:
        db.disconnect()
        cleanup_singleton()
if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
#if __name__ == "__main__":
#    main()
