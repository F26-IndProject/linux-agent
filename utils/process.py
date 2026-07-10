"""
utils/process.py — Launch processes via spawn binary (Linux equivalent of spawn.exe).
spawn does a double-fork so the app's parent is systemd --user, not python3.
"""
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def _get_spawn_path():
    """
    Find spawn binary — mirrors Windows get_spawner_path() exactly.
    When frozen (compiled): sys.executable = dist/agent
      -> parent = dist/ -> parent = ~/linux-agent/ where spawn lives
    When running as script: use __file__ to navigate to root.
    """
    if getattr(sys, 'frozen', False):
        exe_dir  = os.path.dirname(sys.executable)
        base_dir = os.path.dirname(exe_dir)
    else:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "spawn")


SPAWN_BIN = _get_spawn_path()


def spawn_detached(cmd, cwd=None, env=None):
    """
    Launch a command via the spawn binary.
    spawn double-forks so the launched process is reparented to systemd --user.
    Returns the grandchild PID, or None on failure.
    """
    if not Path(SPAWN_BIN).exists():
        logging.error(f"spawn binary not found at {SPAWN_BIN} — compile it with: gcc -o spawn spawn.c")
        return None
    try:
        proc = subprocess.Popen(
            [SPAWN_BIN] + cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
            cwd=cwd,
            env=env
        )
        out, _ = proc.communicate(timeout=5)
        pid_str = out.decode().strip()
        if pid_str.isdigit():
            return int(pid_str)
        return None
    except Exception as e:
        logging.error(f"spawn_detached failed: {e}")
        return None


def spawn_and_wait(cmd, duration_seconds, cwd=None):
    """Spawn a detached process, wait for the duration, then kill it."""
    pid = spawn_detached(cmd, cwd=cwd)
    if pid:
        time.sleep(duration_seconds)
        _kill_pid(pid)
    return pid


def _kill_pid(pid):
    """Kill a process by PID, SIGTERM first then SIGKILL."""
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(2)
        try:
            os.kill(pid, 0)
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    except ProcessLookupError:
        pass
    except Exception as e:
        logging.error(f"Failed to kill PID {pid}: {e}")


def kill_by_name(process_name):
    """Kill all processes matching a name using pkill."""
    try:
        subprocess.run(
            ["pkill", "-f", process_name],
            capture_output=True, timeout=10
        )
    except Exception as e:
        logging.error(f"pkill {process_name} failed: {e}")
