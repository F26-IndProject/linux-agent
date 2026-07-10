"""
actions/cron.py — Cron job management
Linux equivalent of Windows Scheduled Tasks.
Mirrors Windows 3-phase manage_scheduled_task logic exactly.
"""
import logging
import subprocess


def manage_cron(jobs=None, operations=None, agent_id=None, db=None):
    """
    Manage cron jobs in 3 phases — mirrors Windows manage_scheduled_task exactly.

    Phase 1 — delete/restore: affect whether jobs get created
    Phase 2 — add jobs, skipping deleted ones
    Phase 3 — enable/disable/run: require job to exist
    """
    operations = operations or []

    # Phase 1 — process delete/restore operations first
    deleted = db.get_deleted_crons(agent_id) if db and agent_id else []
    for op_entry in operations:
        op   = op_entry.get("operation", "enable")
        name = op_entry.get("name", "")
        if op == "delete":
            if name not in deleted:
                _remove_cron_job(name)
            if db and agent_id:
                db.mark_cron_deleted(agent_id, name)
        elif op == "restore":
            if db and agent_id:
                db.restore_cron(agent_id, name)
            logging.info(f"Cron job '{name}' restored — will be recreated")

    # Phase 2 — add jobs, skipping deleted ones
    # If a job appears in both jobs list AND deleted list, user re-added it — restore it
    if jobs:
        deleted = db.get_deleted_crons(agent_id) if db and agent_id else []
        for job in jobs:
            name = job.get("name", "lisa-job")
            if name in deleted:
                # Job was re-added to the role — restore it automatically
                if db and agent_id:
                    db.restore_cron(agent_id, name)
                    logging.info(f"Cron job '{name}' restored — will be recreated")
            _add_cron_job(
                name=name,
                schedule=job.get("schedule", "0 * * * *"),
                command=job.get("command", "echo lisa-cron")
            )

    # Phase 3 — enable/disable/run: require job to exist
    for op_entry in operations:
        op   = op_entry.get("operation", "enable")
        name = op_entry.get("name", "")
        if   op == "enable":  _enable_cron_job(name)
        elif op == "disable": _disable_cron_job(name)
        elif op == "run":     _run_cron_job_now(name)


def _get_crontab():
    """Return current crontab lines."""
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def _set_crontab(content):
    """Write new crontab content."""
    proc = subprocess.run(
        ["crontab", "-"], input=content,
        capture_output=True, text=True
    )
    return proc.returncode == 0


def _add_cron_job(name, schedule, command):
    """Add a cron job. Uses a comment marker to identify LISA-managed jobs."""
    marker    = f"# LISA:{name}"
    cron_line = f"{schedule} {command} {marker}"
    existing  = _get_crontab()
    if marker in existing:
        logging.info(f"Cron job '{name}' already exists — skipping")
        return
    new_crontab = existing.rstrip("\n") + "\n" + cron_line + "\n"
    if _set_crontab(new_crontab):
        logging.info(f"Cron job added: {name} ({schedule})")
    else:
        logging.error(f"Failed to add cron job: {name}")


def _remove_cron_job(name):
    """Remove a cron job by its LISA marker name."""
    marker   = f"# LISA:{name}"
    existing = _get_crontab()
    lines    = existing.split("\n")
    filtered = [l for l in lines if marker not in l]
    if _set_crontab("\n".join(filtered)):
        logging.info(f"Cron job removed: {name}")
    else:
        logging.error(f"Failed to remove cron job: {name}")


def _disable_cron_job(name):
    """Comment out a cron job so it no longer runs on schedule."""
    marker   = f"# LISA:{name}"
    existing = _get_crontab()
    lines    = existing.split("\n")
    new_lines = []
    changed   = False
    for line in lines:
        if marker in line and not line.startswith("#DISABLED#"):
            new_lines.append(f"#DISABLED# {line}")
            changed = True
        else:
            new_lines.append(line)
    if changed and _set_crontab("\n".join(new_lines)):
        logging.info(f"Cron job disabled: {name}")
    else:
        logging.info(f"Cron job '{name}' already disabled or not found")


def _enable_cron_job(name):
    """Re-enable a disabled cron job."""
    marker   = f"# LISA:{name}"
    existing = _get_crontab()
    lines    = existing.split("\n")
    new_lines = []
    changed   = False
    for line in lines:
        if marker in line and line.startswith("#DISABLED# "):
            new_lines.append(line.replace("#DISABLED# ", "", 1))
            changed = True
        else:
            new_lines.append(line)
    if changed and _set_crontab("\n".join(new_lines)):
        logging.info(f"Cron job enabled: {name}")
    else:
        logging.info(f"Cron job '{name}' already enabled or not found")


def _run_cron_job_now(name):
    """Run a cron job immediately regardless of its schedule."""
    marker   = f"# LISA:{name}"
    existing = _get_crontab()
    command  = None
    for line in existing.split("\n"):
        if marker in line:
            parts = line.split()
            if len(parts) > 5:
                if parts[0] == "#DISABLED#":
                    parts = parts[1:]
                cmd_parts = parts[5:]
                cmd_str   = " ".join(cmd_parts)
                cmd_str   = cmd_str.split(f"# LISA:{name}")[0].strip()
                command   = cmd_str
            break
    if not command:
        logging.warning(f"Cron job '{name}' not found — cannot run")
        return
    logging.info(f"Running cron job now: {name} — {command}")
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            logging.info(f"Cron job '{name}' ran successfully")
            if result.stdout:
                logging.info(f"Output: {result.stdout[:300]}")
        else:
            logging.warning(f"Cron job '{name}' failed: {result.stderr[:200]}")
    except subprocess.TimeoutExpired:
        logging.warning(f"Cron job '{name}' timed out")
    except Exception as e:
        logging.error(f"Cron job '{name}' error: {e}")
