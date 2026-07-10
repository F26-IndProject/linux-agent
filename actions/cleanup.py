"""
actions/cleanup.py — Delete agent-created files older than N days
==================================================================
Runs at agent startup and every 24 hours.
Cleans:
  - LibreOffice documents  → ~/Documents/lisa_doc_*.odt
  - LibreOffice sheets     → ~/Documents/lisa_sheet_*.ods / *.csv
  - Text editor snippets   → /tmp/lisa_edit_*.py
  - Received attachments   → ~/Downloads/LISA_Attachments/*
"""

import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path


MAX_AGE_DAYS = 4


def _delete_old_files(folder: str, patterns: list, max_age_days: int = MAX_AGE_DAYS):
    """Delete files in folder matching any pattern that are older than max_age_days."""
    folder_path = Path(os.path.expanduser(folder))
    if not folder_path.exists():
        return 0

    cutoff = datetime.now() - timedelta(days=max_age_days)
    deleted = 0

    for pattern in patterns:
        for file in folder_path.glob(pattern):
            try:
                if not file.is_file():
                    continue
                modified = datetime.fromtimestamp(file.stat().st_mtime)
                if modified < cutoff:
                    file.unlink()
                    logging.info(f"Cleanup: deleted old file {file.name} (modified {modified.date()})")
                    deleted += 1
            except Exception as e:
                logging.warning(f"Cleanup: could not delete {file.name}: {e}")

    return deleted


def run_cleanup():
    """Run all cleanup tasks — call at startup and every 24 hours."""
    logging.info("Running scheduled file cleanup (files older than 4 days)")
    total = 0

    # LibreOffice documents and spreadsheets created by office.py
    total += _delete_old_files(
        "~/Documents",
        ["lisa_doc_*.odt", "lisa_doc_*.txt", "lisa_sheet_*.ods", "lisa_sheet_*.csv"]
    )

    # Text editor snippets created by apps.py
    total += _delete_old_files(
        "/tmp",
        ["lisa_edit_*.py"]
    )

    # Received email attachments
    total += _delete_old_files(
        "~/Downloads/LISA_Attachments",
        ["*.*"]
    )

    logging.info(f"Cleanup complete — {total} file(s) deleted")


def cleanup_loop():
    """Background thread — runs cleanup at startup then every 24 hours."""
    run_cleanup()
    while True:
        time.sleep(24 * 60 * 60)  # 24 hours
        run_cleanup()
