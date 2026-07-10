"""
actions/terminal.py — Run shell commands in a visible terminal.
Linux equivalent of Windows run_cmd / run_powershell.
Opens a terminal emulator, runs the command, holds it open, then kills it.
"""

import logging
import random
import subprocess
import time

from utils.process import spawn_detached, _kill_pid


DEFAULT_COMMANDS = [
    "ls -la ~",
    "df -h",
    "uptime",
    "whoami",
    "date",
    "free -m",
    "ps aux | head -10",
    "cat /etc/hostname",
]


def run_commands(commands=None, visible=True):
    if not commands:
        commands = DEFAULT_COMMANDS

    cmd = random.choice(commands)

    if not visible:
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                logging.info(f"Command succeeded: {cmd}")
            else:
                logging.warning(f"Command failed: {cmd} — {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            logging.warning(f"Command timed out: {cmd}")
        except Exception as e:
            logging.error(f"Command error: {cmd} — {e}")
        return

    wait = random.randint(15, 25)

    terminal_cmds = [
        ["gnome-terminal", "--", "bash", "-c", f"{cmd}; sleep {wait}"],
        ["xfce4-terminal", "-e", f"bash -c '{cmd}; sleep {wait}'"],
        ["xterm", "-e", f"bash -c '{cmd}; sleep {wait}'"],
    ]

    for term_cmd in terminal_cmds:
        pid = spawn_detached(term_cmd)
        if pid:
            logging.info(f"Terminal window open for {wait}s")
            time.sleep(wait)
            _kill_pid(pid)
            logging.info("Terminal window closed")
            return

    logging.warning("No terminal emulator found — running hidden")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            logging.info(f"Command succeeded: {cmd}")
        else:
            logging.warning(f"Command failed: {cmd} — {result.stderr[:200]}")
    except Exception as e:
        logging.error(f"Command error: {cmd} — {e}")
