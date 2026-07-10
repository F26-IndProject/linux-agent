"""
actions/email.py — Send and read email via Thunderbird
=======================================================
Linux equivalent of Windows Outlook COM automation.

Thunderbird must already be installed and have the agent's email account
configured (same precondition as Windows requiring Outlook pre-configured).

Sending:
  thunderbird -compose "to=...,subject=...,body=...,attachment=..."
  xdotool key ctrl+Return  (triggers Send inside the compose window)

Reading (headless):
  imaplib connects directly to IMAP server using .env credentials.
  Mirrors Windows read_outlook_inbox() exactly — no Thunderbird window.
  Replies sent via smtplib STARTTLS.
  Attachments downloaded to ~/Downloads/LISA_Attachments/ and opened
  via spawn binary (systemd as parent, not python3).
"""

import email as email_lib
import email.header
import imaplib
import logging
import os
import random
import shutil
import smtplib
import ssl
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.parse import quote

from dotenv import load_dotenv

from utils.process import spawn_detached, spawn_and_wait, _kill_pid
from actions.templates.email import random_subject, random_body, random_reply

load_dotenv()

# ── Mail credentials from .env ────────────────────────────────────────────────
MAIL_SERVER    = os.getenv("MAIL_SERVER", "mail.lisa.local")
MAIL_IMAP_PORT = int(os.getenv("MAIL_IMAP_PORT", 993))
MAIL_SMTP_PORT = int(os.getenv("MAIL_SMTP_PORT", 587))
MAIL_USER      = os.getenv("MAIL_USER", "")
MAIL_PASSWORD  = os.getenv("MAIL_PASSWORD", "")

# ── Attachment directories and types (mirrors Windows office.py) ──────────────
RECV_ATTACHMENTS_DIR = Path.home() / "Downloads" / "LISA_Attachments"
IMAGE_EXTENSIONS     = {".jpg", ".jpeg", ".png", ".bmp", ".gif"}
WORD_EXTENSIONS      = {".docx", ".doc", ".odt", ".odf"}
PDF_EXTENSIONS       = {".pdf"}
ALL_EXTENSIONS       = IMAGE_EXTENSIONS | WORD_EXTENSIONS | PDF_EXTENSIONS

def _get_agent_base_dir():
    """Get agent root directory — works both frozen (PyInstaller) and as script."""
    if getattr(sys, 'frozen', False):
        exe_dir  = Path(sys.executable).parent  # dist/
        return exe_dir.parent                    # ~/linux-agent/
    return Path(__file__).parent.parent          # ~/linux-agent/

ATTACHMENTS_DIR = _get_agent_base_dir() / "attachments"

# Sorted queue for attachment picking (same approach as Windows agent)
_attachment_queue_index = 0


def _pick_next_attachment():
    """Pick the next attachment in sorted queue order (same as Windows agent)."""
    global _attachment_queue_index

    if not ATTACHMENTS_DIR.exists():
        return None

    supported = {".jpg", ".jpeg", ".png", ".pdf", ".docx", ".doc", ".odt"}
    files = sorted([
        f for f in ATTACHMENTS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in supported
    ])

    if not files:
        return None

    chosen = files[_attachment_queue_index % len(files)]
    _attachment_queue_index += 1
    return chosen


def _xdotool_available():
    """Check if xdotool is installed."""
    return os.system("which xdotool > /dev/null 2>&1") == 0


def _open_received_attachment_and_close(save_path: str):
    """
    Open a received attachment via spawn (systemd as parent, not python3).
    Mirrors Windows _open_received_attachment_and_close().
    Routes by file type — opens, waits 25-35s, then kills.
    """
    ext = Path(save_path).suffix.lower()
    read_time = random.randint(25, 35)

    if ext in WORD_EXTENSIONS:
        # LibreOffice Writer
        pid = spawn_detached(["libreoffice", "--writer", save_path])
        if pid:
            logging.info(f"Word attachment opened: {Path(save_path).name}, reading for {read_time}s")
            time.sleep(read_time)
            _kill_pid(pid)
            logging.info(f"Word attachment closed: {Path(save_path).name}")

    elif ext in PDF_EXTENSIONS:
        from actions.apps import open_pdf_via_spawn
        logging.info(f"PDF attachment opened: {Path(save_path).name}, reading for {read_time}s")
        open_pdf_via_spawn(save_path)
        logging.info(f"PDF attachment closed: {Path(save_path).name}")
    elif ext in IMAGE_EXTENSIONS:
        from actions.apps import open_image_via_spawn
        logging.info(f"Image attachment opened: {Path(save_path).name}, reading for {read_time}s")
        open_image_via_spawn(save_path)
        logging.info(f"Image attachment closed: {Path(save_path).name}")

    else:
        logging.warning(f"Unsupported attachment type: {ext} — skipping open")


def _handle_received_attachments(msg_obj):
    """
    Download all attachments from a received email, open and close the first.
    Mirrors Windows _handle_received_attachments() exactly.
    """
    try:
        RECV_ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
        first = True
        for part in msg_obj.walk():
            if part.get_content_disposition() != "attachment":
                continue
            filename = part.get_filename()
            if not filename:
                continue
            filename = email_lib.header.decode_header(filename)[0][0]
            if isinstance(filename, bytes):
                filename = filename.decode(errors="replace")
            ext = Path(filename).suffix.lower()
            if ext not in ALL_EXTENSIONS:
                continue
            save_path = str(RECV_ATTACHMENTS_DIR / filename)
            with open(save_path, "wb") as f:
                f.write(part.get_payload(decode=True))
            logging.info(f"Attachment downloaded: {filename}")
            if first:
                _open_received_attachment_and_close(save_path)
                first = False
    except Exception as e:
        logging.error(f"Attachment handling failed: {e}")


def _reply_to_email(from_addr: str, subject: str, message_id: str):
    """
    Send a reply via smtplib STARTTLS on port 587.
    Mirrors Windows _reply_to_email() — uses .env credentials.
    """
    try:
        reply_body = random_reply()
        reply_subject = subject if subject.startswith("Re:") else f"Re: {subject}"

        msg = MIMEMultipart()
        msg["From"]       = MAIL_USER
        msg["To"]         = from_addr
        msg["Subject"]    = reply_subject
        msg["In-Reply-To"] = message_id
        msg["References"]  = message_id
        msg.attach(MIMEText(reply_body, "plain"))

        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with smtplib.SMTP(MAIL_SERVER, MAIL_SMTP_PORT, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.login(MAIL_USER, MAIL_PASSWORD)
            smtp.sendmail(MAIL_USER, from_addr, msg.as_string())

        logging.info(f"Reply sent to {from_addr}: {reply_subject}")

    except Exception as e:
        logging.error(f"Reply failed: {e}")


def send_email(recipients=None):
    """
    Send an email by opening Thunderbird's compose window pre-filled
    with subject, body, and optional attachment, then trigger Send via xdotool.
    Mirrors Windows agent's send_outlook_email() — uses Thunderbird's own
    configured account, no credentials stored.
    """
    if not recipients:
        logging.warning("No recipients configured — skipping send")
        return

    # Filter own email from recipients before picking — mirrors Windows logic
    filtered = [r for r in recipients if r.lower() != MAIL_USER.lower()]
    logging.info(f"Own email: {MAIL_USER} — filtered to {len(filtered)}/{len(recipients)} recipients")
    if not filtered:
        logging.warning("No valid recipients after filtering own email — skipping send")
        return
    to_addr = random.choice(filtered)
    subject  = random_subject()
    body     = random_body()

    compose_parts = [
        f"to={quote(to_addr)}",
        f"subject={quote(subject)}",
        f"body={quote(body)}",
    ]

    attachment_path = None
    if random.random() < 0.8:
        attachment = _pick_next_attachment()
        if attachment:
            compose_parts.append(f"attachment={quote(str(attachment.resolve()))}")
            attachment_path = str(attachment.name)

    compose_str = ",".join(compose_parts)

    logging.info(f"Sending email to {to_addr}: {subject}" +
                 (f" [attachment: {attachment_path}]" if attachment_path else ""))

    pid = spawn_detached(["thunderbird", "-compose", compose_str])
    if not pid:
        logging.error("Failed to launch Thunderbird compose window")
        return

    logging.info(f"Thunderbird compose window opened (PID {pid})")
    time.sleep(6)

    if _xdotool_available():
        os.system("xdotool search --sync --onlyvisible --class Thunderbird windowfocus 2>/dev/null")
        time.sleep(1)
        os.system("xdotool key ctrl+Return")
        logging.info("Send triggered via xdotool (Ctrl+Return)")
        time.sleep(3)
    else:
        logging.warning("xdotool not installed — compose window opened but send not triggered. "
                        "Install with: sudo apt install xdotool")
        time.sleep(10)

    _kill_pid(pid)
    logging.info(f"Email session closed: {to_addr}")


def read_email():
    """
    Read up to 3 unread emails via IMAP (headless — no Thunderbird window).
    Mirrors Windows read_outlook_inbox() exactly:
      - Skips self-emails and bounce senders
      - Marks as read
      - Waits 7-10s per message (simulate reading)
      - Downloads and opens attachments
      - Replies to each message
    Credentials from .env (MAIL_SERVER, MAIL_IMAP_PORT, MAIL_USER, MAIL_PASSWORD).
    """
    if not MAIL_USER or not MAIL_PASSWORD:
        logging.error("MAIL_USER or MAIL_PASSWORD not set in .env — skipping read")
        return

    logging.info(f"Connecting to IMAP: {MAIL_SERVER}:{MAIL_IMAP_PORT}")

    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with imaplib.IMAP4_SSL(MAIL_SERVER, MAIL_IMAP_PORT, ssl_context=context) as imap:
            imap.login(MAIL_USER, MAIL_PASSWORD)
            imap.select("INBOX")

            own_email = MAIL_USER.lower()
            logging.info(f"Own email: {own_email} — will skip self-emails and bounces")

            # Search for unread messages
            _, msg_nums = imap.search(None, "UNSEEN")
            msg_list = msg_nums[0].split()

            if not msg_list:
                logging.info("IMAP: no unread emails found")
                return

            # Process newest first (reverse order), up to 3
            unread_count = 0
            for num in reversed(msg_list):
                if unread_count >= 3:
                    break

                try:
                    _, msg_data = imap.fetch(num, "(RFC822)")
                    raw = msg_data[0][1]
                    msg_obj = email_lib.message_from_bytes(raw)

                    # Extract fields
                    from_addr = email_lib.utils.parseaddr(msg_obj.get("From", ""))[1].lower()
                    subject_raw = msg_obj.get("Subject", "")
                    subject = email_lib.header.decode_header(subject_raw)[0][0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(errors="replace")
                    message_id = msg_obj.get("Message-ID", "")
                    sender_name = email_lib.utils.parseaddr(msg_obj.get("From", ""))[0]

                    # Skip self-emails
                    if from_addr == own_email:
                        logging.info(f"Skipping self-email: {subject}")
                        imap.store(num, "+FLAGS", "\\Seen")
                        continue

                    # Skip bounce/system senders
                    if any(x in from_addr for x in ("mailer-daemon", "postmaster", "noreply", "no-reply")):
                        logging.info(f"Skipping system email from {from_addr}")
                        imap.store(num, "+FLAGS", "\\Seen")
                        continue

                    logging.info(f"Reading unread email from {sender_name}: {subject}")

                    # Mark as read
                    imap.store(num, "+FLAGS", "\\Seen")

                    # Simulate reading time (7-10 seconds)
                    time.sleep(random.randint(7, 10))

                    # Handle attachments
                    _handle_received_attachments(msg_obj)

                    # Reply
                    _reply_to_email(from_addr, subject, message_id)

                    unread_count += 1

                except Exception as e:
                    logging.error(f"Error processing email: {e}")
                    continue

            if unread_count == 0:
                logging.info("IMAP: no eligible unread emails found")
            else:
                logging.info(f"IMAP: processed {unread_count} unread email(s)")

    except Exception as e:
        logging.error(f"IMAP read inbox failed: {e}")


def open_thunderbird(duration_min=30, duration_max=60):
    """Open Thunderbird mail client (detached from agent) for a browsing session."""
    duration = random.randint(duration_min, duration_max)
    logging.info(f"Opening Thunderbird for {duration}s")
    spawn_and_wait(["thunderbird"], duration)
    logging.info("Thunderbird session closed")
