"""
utils/log_writer.py — Remote log receiver
==========================================
Launched by agent.py via spawn binary (parent = systemd).
Listens on localhost:19999 for log records sent by agent.py
and writes them to logs/agent.log.

Run standalone (launched automatically by agent.py):
  python3 utils/log_writer.py
"""

import logging
import logging.handlers
import pickle
import socketserver
import struct
import sys
from pathlib import Path

HOST     = "127.0.0.1"
PORT     = 19999
LOG_FILE = "logs/agent.log"
LOCK_FILE = "/tmp/lisa_log_writer.lock"


class LogRecordStreamHandler(socketserver.StreamRequestHandler):
    """Receives pickled LogRecord objects and writes them to the local logger."""

    def handle(self):
        while True:
            try:
                header = self.connection.recv(4)
                if len(header) < 4:
                    break
                slen = struct.unpack(">L", header)[0]
                data = b""
                while len(data) < slen:
                    chunk = self.connection.recv(slen - len(data))
                    if not chunk:
                        break
                    data += chunk
                obj    = pickle.loads(data)
                record = logging.makeLogRecord(obj)
                logging.getLogger(record.name).handle(record)
            except Exception:
                break


class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


if __name__ == "__main__":
    # Prevent multiple instances using a lock file
    lock = Path(LOCK_FILE)
    if lock.exists():
        try:
            pid = int(lock.read_text().strip())
            Path(f"/proc/{pid}").stat()
            sys.exit(0)  # already running
        except (ValueError, OSError):
            pass  # stale lock — continue
    lock.write_text(str(__import__("os").getpid()))

    import atexit
    atexit.register(lambda: lock.unlink(missing_ok=True))

    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s [%(process)d]: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ]
    )

    server = LogRecordSocketReceiver((HOST, PORT), LogRecordStreamHandler)
    server.serve_forever()
