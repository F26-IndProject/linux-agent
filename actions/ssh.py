"""
actions/ssh.py — SSH connections to other machines
===================================================
Linux equivalent of Windows RDP via wfreerdp.
Opens a visible terminal window with an interactive SSH session,
holds for the configured duration, then closes.
Works for both Linux and Windows SSH targets.
Spawned via spawn binary so systemd is parent, not python3.
"""

import logging
import os
import random
import time
import psutil

from utils.process import spawn_detached, _kill_pid


def connect(host="", username="", password="", duration_seconds=30):
    """
    Open a visible terminal window with an interactive SSH session.
    Mirrors Windows RDP — spawns wfreerdp visibly, holds, then kills.
    Uses sshpass for password auth, gnome-terminal for visible window.
    Works for both Linux and Windows SSH targets.
    """
    if not host or not username:
        logging.warning("SSH target not configured")
        return

    duration = duration_seconds or random.randint(15, 45)
    logging.info(f"SSH session opened to {username}@{host} — holding for {duration}s")

    # Build the ssh command — StrictHostKeyChecking=no to avoid prompts
    if password:
        ssh_cmd = (
            f"sshpass -p {password} ssh "
            f"-o StrictHostKeyChecking=no "
            f"-o UserKnownHostsFile=/dev/null "
            f"-o LogLevel=ERROR "
            f"{username}@{host}"
        )
    else:
        ssh_cmd = (
            f"ssh "
            f"-o StrictHostKeyChecking=no "
            f"-o UserKnownHostsFile=/dev/null "
            f"-o LogLevel=ERROR "
            f"{username}@{host}"
        )

    # Open visible terminal running the SSH session
    # sleep after ssh exits keeps the window open for the full duration
    terminal_cmd = ["gnome-terminal", "--", "bash", "-c",
                    f"{ssh_cmd}; sleep {duration}"]

    pid = spawn_detached(terminal_cmd)
    if not pid:
        logging.error("Failed to launch terminal for SSH session")
        return

    # Hold for the configured duration
    time.sleep(duration)

    # Close the terminal
    _kill_pid(pid)
    for p in psutil.process_iter(["pid", "cmdline"]):
        try:
            if any("ssh" in a for a in (p.info["cmdline"] or [])):
                p.terminate()
        except Exception:
            pass
    logging.info(f"SSH session to {host} closed")
