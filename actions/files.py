"""
actions/files.py — File creation, editing, and management
"""

import logging
import os
import random
import shutil
from datetime import datetime
from pathlib import Path

from actions.templates.text import random_note


def create_file(path="~/Documents/notes.txt", content=None):
    """Create a file with the given content."""
    path = os.path.expanduser(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if content is None:
        content = random_note()

    # Expand timestamp placeholders
    content = content.replace("{timestamp}", datetime.now().isoformat())
    content = content.replace("{date}", datetime.now().strftime("%Y-%m-%d"))

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    logging.info(f"File created: {path}")


def edit_file(path="~/Documents/notes.txt"):
    """Append a timestamped note to an existing file."""
    path = os.path.expanduser(path)

    if not os.path.exists(path):
        create_file(path)
        return

    note = f"\n--- Update at {datetime.now().isoformat()} ---\n"
    note += random.choice([
        "Reviewed the latest changes.\n",
        "Updated the configuration section.\n",
        "Added notes from the meeting.\n",
        "Corrected formatting issues.\n",
        "Appended new requirements.\n",
    ])

    with open(path, "a", encoding="utf-8") as f:
        f.write(note)

    # Reset file if it gets too large
    if os.path.getsize(path) > 4096:
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"File reset at {datetime.now().isoformat()}\n")

    logging.info(f"File edited: {path}")


def copy_file(src="~/Documents/notes.txt", dst=None):
    """Copy a file to a new location."""
    src = os.path.expanduser(src)
    if not os.path.exists(src):
        logging.warning(f"Source file not found: {src}")
        return

    if dst is None:
        name = Path(src).stem
        ext  = Path(src).suffix
        dst  = str(Path(src).parent / f"{name}_copy_{datetime.now():%H%M%S}{ext}")

    shutil.copy2(src, dst)
    logging.info(f"File copied: {src} → {dst}")


def delete_file(path):
    """Delete a file."""
    path = os.path.expanduser(path)
    if os.path.exists(path):
        os.unlink(path)
        logging.info(f"File deleted: {path}")
    else:
        logging.warning(f"File not found for deletion: {path}")
