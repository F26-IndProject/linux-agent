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
from datetime import datetime
from pathlib import Path

from utils.process import spawn_and_wait
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

    # Convert to ODT using LibreOffice headless
    try:
        os.system(
            f'libreoffice --headless --convert-to odt --outdir "{_docs_dir()}" "{txt_path}" '
            f'> /dev/null 2>&1'
        )
        # Remove the intermediate txt file if ODT was created
        if filepath.exists():
            txt_path.unlink(missing_ok=True)
        else:
            # Conversion failed, use txt
            filepath = txt_path
    except Exception:
        filepath = txt_path

    duration = random.randint(duration_min, duration_max)
    logging.info(f"Created document: {filepath.name}, opening for {duration}s")

    # Open in LibreOffice Writer (detached from agent)
    spawn_and_wait(["libreoffice", "--norestore", "--writer", str(filepath)], duration)
    os.system("pkill -f soffice > /dev/null 2>&1")
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

    # Convert to ODS using LibreOffice headless
    ods_path = filepath.with_suffix(".ods")
    try:
        os.system(
            f'libreoffice --headless --convert-to ods --outdir "{_docs_dir()}" "{filepath}" '
            f'> /dev/null 2>&1'
        )
        if ods_path.exists():
            filepath.unlink(missing_ok=True)
            filepath = ods_path
    except Exception:
        pass

    duration = random.randint(duration_min, duration_max)
    logging.info(f"Created spreadsheet: {filepath.name}, opening for {duration}s")

    spawn_and_wait(["libreoffice", "--norestore", "--calc", str(filepath)], duration)
    os.system("pkill -f soffice > /dev/null 2>&1")
    logging.info(f"Calc session closed: {filepath.name}")
