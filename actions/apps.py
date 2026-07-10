"""
actions/apps.py — Browser and application launcher (detached from agent)
"""

import logging
import os
import random
import shutil
from datetime import datetime
from pathlib import Path

from utils.process import spawn_detached, spawn_and_wait, _kill_pid
from actions.templates.vscode import random_vscode_snippet


def open_browser(urls=None, duration_min=15, duration_max=30):
    """Open a URL in the default browser, detached from agent."""
    if not urls:
        urls = ["https://www.google.com"]

    url      = random.choice(urls)
    duration = random.randint(duration_min, duration_max)

    browsers = ["firefox", "chromium-browser", "chromium", "google-chrome", "xdg-open"]
    browser  = None
    for b in browsers:
        if os.system(f"which {b} > /dev/null 2>&1") == 0:
            browser = b
            break

    if not browser:
        logging.error("No browser found on system")
        return

    logging.info(f"Opening {browser}: {url} for {duration}s")
    spawn_and_wait([browser, url], duration)
    logging.info(f"Browser session closed: {url}")


def open_vscode():
    """
    Open VS Code with a random Python code snippet, then run the code.
    Flow: create file → open VS Code → wait (reviewing) → run code → close.
    Mirrors Windows open_vscode_with_code() exactly.
    File is kept after close — cleanup.py deletes it after 4 days.
    """
    if os.system("which code > /dev/null 2>&1") != 0:
        logging.warning("VS Code (code) not found on system")
        return

    snippet   = random_vscode_snippet()
    docs_dir  = Path.home() / "Documents"
    docs_dir.mkdir(exist_ok=True)
    tmp_name  = f"lisa_snippet_{random.randint(1000, 9999)}.py"
    tmp_path  = str(docs_dir / tmp_name)

    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(snippet)

        # Open VS Code with the file — detached via spawn
        pid = spawn_detached(["code", tmp_path])
        logging.info(f"VS Code opened: {tmp_name}")

        # Simulate reviewing / editing the code
        review_time = random.randint(30, 60)
        logging.info(f"Reviewing code for {review_time}s")
        import time
        time.sleep(review_time)

        # Run the code in a visible terminal window via spawn
        run_cmd  = f"python3 {tmp_path}; sleep 10"
        term_pid = spawn_detached(["gnome-terminal", "--", "bash", "-c", run_cmd])
        logging.info(f"Running code: python3 {tmp_name}")

        # Wait for execution + terminal to close
        time.sleep(15)

        # Close VS Code
        os.system("pkill -f 'code.*lisa_snippet'")
        if pid:
            _kill_pid(pid)
        logging.info("VS Code closed")

    except Exception as e:
        logging.error(f"VS Code action failed: {e}")
        os.system("pkill -f 'code.*lisa_snippet'")

def open_pdf_via_spawn(pdf_path: str):
    """
    Open PDF via spawn binary so systemd is parent, not agent.
    Kill by process name after reading — mirrors Windows taskkill /IM Acrobat.exe.
    """
    import time
    pdf_viewers = ["atril", "mupdf", "okular", "xreader", "evince"]
    viewer = next((v for v in pdf_viewers if shutil.which(v)), None)
    if not viewer:
        logging.warning("No PDF viewer found — skipping open")
        return
    read_time = 25  # fixed — caller controls timing
    spawn_detached([viewer, pdf_path])
    logging.info(f"PDF opened: {viewer}")
    time.sleep(read_time)
    os.system(f"pkill -x {viewer} > /dev/null 2>&1")
    logging.info("PDF closed")


def open_image_via_spawn(image_path: str):
    """
    Open image via spawn binary so systemd is parent, not agent.
    Kill by process name after reading — mirrors Windows taskkill /IM Microsoft.Photos.exe.
    """
    import time
    img_viewers = ["eog", "shotwell", "gpicview", "feh"]
    viewer = next((v for v in img_viewers if shutil.which(v)), None)
    if not viewer:
        logging.warning("No image viewer found — skipping open")
        return
    read_time = 25
    spawn_detached([viewer, image_path])
    logging.info(f"Image opened: {viewer}")
    time.sleep(read_time)
    os.system(f"pkill -x {viewer} > /dev/null 2>&1")
    logging.info("Image closed")
