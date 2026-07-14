"""
actions/office.py — LibreOffice Writer and Calc document creation
Documents are created headless, then optionally opened in LibreOffice GUI (detached).
"""

import csv
import logging
import os
import random
import tempfile
import time
import psutil
from datetime import datetime
from pathlib import Path

from utils.process import spawn_and_wait, spawn_detached
from actions.templates.office import random_document_content, random_spreadsheet_data


def _docs_dir():
    """Get the Documents directory, create if missing."""
    d = Path.home() / "Documents"
    d.mkdir(exist_ok=True)
    return d


def create_word_document(duration_min=20, duration_max=40):
    """
    Create a text document and open it in LibreOffice Writer (detached).
    """
    content = random_document_content()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lisa_doc_{timestamp}.odt"
    filepath = _docs_dir() / filename

    # Write content as plain text first
    txt_path = filepath.with_suffix(".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Convert to ODT via spawn so parent = systemd, not agent
    try:
        pid = spawn_detached([
            "libreoffice", "--headless", "--convert-to", "odt",
            "--outdir", str(_docs_dir()), str(txt_path)
        ])
        if pid:
            for _ in range(60):  # poll up to 30s
                if filepath.exists():
                    break
                time.sleep(0.5)
        if filepath.exists():
            txt_path.unlink(missing_ok=True)
        else:
            filepath = txt_path
    except Exception:
        filepath = txt_path

    duration = random.randint(duration_min, duration_max)
    logging.info(f"Created document: {filepath.name}, opening for {duration}s")

    # Open in LibreOffice Writer (detached from agent)
    spawn_and_wait(["libreoffice", "--norestore", "--writer", str(filepath)], duration)
    for p in psutil.process_iter(["name"]):
        try:
            if "soffice" in p.name():
                p.terminate()
        except Exception:
            pass
    logging.info(f"Writer session closed: {filepath.name}")


def create_excel_spreadsheet(duration_min=20, duration_max=40):
    """
    Create a CSV spreadsheet and open it in LibreOffice Calc (detached).
    """
    headers, rows = random_spreadsheet_data()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lisa_sheet_{timestamp}.csv"
    filepath = _docs_dir() / filename

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    # Convert to ODS via spawn so parent = systemd, not agent
    ods_path = filepath.with_suffix(".ods")
    try:
        pid = spawn_detached([
            "libreoffice", "--headless", "--convert-to", "ods",
            "--outdir", str(_docs_dir()), str(filepath)
        ])
        if pid:
            for _ in range(60):  # poll up to 30s
                if ods_path.exists():
                    break
                time.sleep(0.5)
        if ods_path.exists():
            filepath.unlink(missing_ok=True)
            filepath = ods_path
    except Exception:
        pass

    duration = random.randint(duration_min, duration_max)
    logging.info(f"Created spreadsheet: {filepath.name}, opening for {duration}s")

    spawn_and_wait(["libreoffice", "--norestore", "--calc", str(filepath)], duration)
    for p in psutil.process_iter(["name"]):
        try:
            if "soffice" in p.name():
                p.terminate()
        except Exception:
            pass
    logging.info(f"Calc session closed: {filepath.name}")
