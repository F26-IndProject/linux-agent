"""
actions/smb.py — SMB network share access via smbclient
=========================================================
Linux equivalent of Windows net use + file I/O.
Mirrors Windows smb.py browse session exactly:
  - List all files
  - Read all text files
  - Edit an existing file (append content)
  - Create a new file then delete it
  - Copy a file then delete the copy
"""

import logging
import os
import random
import subprocess
import tempfile
import time
from datetime import datetime

from utils.process import spawn_detached


EDIT_TEMPLATES = [
    "Updated by team member on {date}. Changes reviewed and approved.",
    "Note added {date}: Please review before end of day.",
    "Revision {date}: Minor corrections applied. Version incremented.",
    "Checked on {date}. All items verified and signed off.",
    "Amendment {date}: Additional information appended per manager request.",
    "Follow-up {date}: Awaiting confirmation from stakeholders.",
    "Review complete {date}: No further changes required at this time.",
]

NEW_FILE_CONTENTS = [
    "Meeting summary\nDate: {date}\nAttendees: team members\nDecisions: approved Q3 plan\nAction items: update timeline by Friday.",
    "Status update\nDate: {date}\nAll tasks on track. No blockers identified. Proceeding as planned.",
    "Incident log\nDate: {date}\nMinor issue detected and resolved. Root cause identified. No further impact expected.",
    "Project note\nDate: {date}\nMilestone reached. Deliverable submitted for review. Awaiting feedback.",
]


def access_share(server="", share="", username="", password="", mode="browse"):
    if not server:
        logging.warning("No SMB server specified")
        return

    share_path = f"//{server}/{share}"
    logging.info(f"Accessing SMB share: {share_path}")

    try:
        # Step 1 — List all files
        file_list = _list_share(share_path, username, password)
        time.sleep(random.randint(2, 4))

        if mode == "browse":
            # Step 2 — Read all text files
            _read_all_files(share_path, username, password, file_list)
            time.sleep(random.randint(2, 4))

            # Step 3 — Edit an existing file
            _edit_existing_file(share_path, username, password, file_list)
            time.sleep(random.randint(2, 4))

            # Step 4 — Create a new file then delete it
            _create_new_file(share_path, username, password)
            time.sleep(random.randint(2, 4))

            # Step 5 — Copy a file then delete the copy
            _copy_file(share_path, username, password, file_list)

        time.sleep(random.randint(5, 15))

    except Exception as e:
        logging.error(f"SMB access failed for {share_path}: {e}")

    logging.info(f"SMB session completed: {share_path}")


def _smb_cmd(share_path, username, password, command, capture_output=False):
    """Run a single smbclient command via spawn so parent = systemd, not agent.
    Returns stdout if capture_output=True."""
    cmd = ["smbclient", share_path]
    if username:
        cmd += ["-U", f"{username}%{password}"]
    else:
        cmd += ["-N"]
    cmd += ["-c", command]

    tmp_path = None
    try:
        # Write output to temp file — spawn can't capture stdout directly
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name

        # Build shell command that redirects output to temp file
        shell_parts = []
        for part in cmd:
            shell_parts.append(f'"{part}"' if " " in part else part)
        shell_cmd = " ".join(shell_parts) + f" > {tmp_path} 2>&1"

        pid = spawn_detached(["bash", "-c", shell_cmd])

        if pid:
            # Poll until process finishes (max 30s)
            for _ in range(60):
                if not os.path.exists(f"/proc/{pid}"):
                    break
                time.sleep(0.5)
        elif pid is None:
            logging.error("smbclient not installed — install with: sudo apt install smbclient")
            return None

        stdout = ""
        try:
            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                stdout = f.read()
        except Exception:
            pass

        if "NT_STATUS" in stdout and "NT_STATUS_OK" not in stdout:
            logging.warning(f"smbclient '{command[:40]}' failed: {stdout[:200]}")
            return None

        logging.info(f"smbclient '{command[:40]}' succeeded")
        return stdout if capture_output else None

    except Exception as e:
        logging.error(f"smbclient error: {e}")
        return None
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _list_share(share_path, username, password):
    """List all files on the share. Returns list of filenames."""
    output = _smb_cmd(share_path, username, password, "ls", capture_output=True)
    files = []
    if output:
        for line in output.splitlines():
            parts = line.strip().split()
            if parts and parts[0] not in (".", "..") and len(parts) >= 2:
                name = parts[0]
                # Skip directories (marked with D)
                if "D" not in parts[1]:
                    files.append(name)
        logging.info(f"Share contents ({len(files)} files): {', '.join(files[:10])}")
    return files


def _read_all_files(share_path, username, password, file_list):
    """Download and read every text file on the share."""
    text_exts = {".txt", ".md", ".csv", ".log"}
    text_files = [f for f in file_list if os.path.splitext(f)[1].lower() in text_exts]

    if not text_files:
        logging.info("No readable text files found on share")
        return

    for filename in text_files:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            _smb_cmd(share_path, username, password, f"get {filename} {tmp_path}")
            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            logging.info(
                f"Read file: {filename} ({len(content)} chars)\n"
                f"--- content ---\n{content.strip()[:200]}\n--- end ---"
            )
            time.sleep(random.randint(2, 5))
        except Exception as e:
            logging.error(f"Could not read {filename}: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _edit_existing_file(share_path, username, password, file_list):
    """Download a random text file, append content, upload it back."""
    text_exts = {".txt", ".md"}
    text_files = [f for f in file_list if os.path.splitext(f)[1].lower() in text_exts]

    if not text_files:
        logging.info("No editable files found on share — skipping edit")
        return

    filename = random.choice(text_files)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        # Download
        _smb_cmd(share_path, username, password, f"get {filename} {tmp_path}")

        # Check size — reset if over 2KB (mirrors Windows logic)
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 2048:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(f"File reset on {datetime.now().strftime('%Y-%m-%d')}\n")
            logging.info(f"Reset oversized file on share: {filename}")
        else:
            addition = random.choice(EDIT_TEMPLATES).format(
                date=datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            with open(tmp_path, "a", encoding="utf-8") as f:
                f.write(f"\n{addition}")
            logging.info(f"Edited file on share: {filename} — appended: {addition}")

        # Upload back
        _smb_cmd(share_path, username, password, f"put {tmp_path} {filename}")

    except Exception as e:
        logging.error(f"Share edit failed: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _create_new_file(share_path, username, password):
    """Create a new timestamped file on the share then delete it."""
    filename = f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    content  = random.choice(NEW_FILE_CONTENTS).format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        _smb_cmd(share_path, username, password, f"put {tmp_path} {filename}")
        logging.info(f"Created file on share: {filename}\n--- content ---\n{content}\n--- end ---")

        time.sleep(random.randint(3, 8))

        _smb_cmd(share_path, username, password, f"del {filename}")
        logging.info(f"Deleted temp file from share: {filename}")

    except Exception as e:
        logging.error(f"Share write failed: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _copy_file(share_path, username, password, file_list):
    """Download a random file, upload it with a new name, then delete the copy."""
    text_exts = {".txt", ".md"}
    text_files = [f for f in file_list if os.path.splitext(f)[1].lower() in text_exts]

    if not text_files:
        return

    src_name = random.choice(text_files)
    base, ext = os.path.splitext(src_name)
    dst_name  = f"{base}_copy_{datetime.now().strftime('%H%M%S')}{ext}"

    with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name

    try:
        _smb_cmd(share_path, username, password, f"get {src_name} {tmp_path}")
        _smb_cmd(share_path, username, password, f"put {tmp_path} {dst_name}")
        logging.info(f"Copied file on share: {src_name} → {dst_name}")

        time.sleep(random.randint(2, 5))

        _smb_cmd(share_path, username, password, f"del {dst_name}")
        logging.info(f"Deleted copy from share: {dst_name}")

    except Exception as e:
        logging.error(f"Share copy failed: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
