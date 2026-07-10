"""
actions/templates/text.py — Content templates for text editor sessions
"""

import random
from datetime import datetime


CODE_SNIPPETS = [
    '''#!/usr/bin/env python3
"""Simple HTTP health check server."""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "healthy"}).encode())

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    server.serve_forever()
''',
    '''#!/bin/bash
# Backup script
DATE=$(date +%F)
BACKUP_DIR="/var/backups"
tar czf "$BACKUP_DIR/backup-$DATE.tar.gz" /etc /home
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
echo "Backup completed: $DATE"
''',
    '''# Configuration notes
# Last updated: {date}

## Server settings
- Max connections: 100
- Timeout: 30s
- Log level: INFO

## Database
- Host: db.internal
- Port: 5432
- Pool size: 20

## TODO
- [ ] Update SSL certificates
- [ ] Review firewall rules
- [ ] Check disk usage on prod
''',
    '''import logging
import os

def setup_config():
    """Load configuration from environment."""
    config = {{
        "debug": os.getenv("DEBUG", "false").lower() == "true",
        "port": int(os.getenv("PORT", "8000")),
        "db_url": os.getenv("DATABASE_URL"),
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
    }}
    logging.basicConfig(level=getattr(logging, config["log_level"]))
    return config

if __name__ == "__main__":
    cfg = setup_config()
    print(f"Starting on port {{cfg['port']}}")
''',
]

NOTE_TEMPLATES = [
    "Meeting notes — {date}\n\nAttendees: Team Alpha\n\nDiscussion points:\n- Sprint review\n- Upcoming deadlines\n- Resource planning\n\nAction items:\n- Follow up on deployment timeline\n- Update documentation\n",
    "Research notes — {date}\n\nTopic: Infrastructure improvements\n\nFindings:\n- Current response time: ~200ms\n- Target: <100ms\n- Bottleneck: database queries\n\nNext steps:\n- Profile slow queries\n- Consider read replicas\n",
    "TODO list — {date}\n\n1. Review pull requests\n2. Update CI pipeline\n3. Write unit tests for auth module\n4. Schedule 1:1 with team lead\n5. Clean up old branches\n",
]


def random_code_snippet():
    snippet = random.choice(CODE_SNIPPETS)
    return snippet.replace("{date}", datetime.now().strftime("%Y-%m-%d"))


def random_note():
    note = random.choice(NOTE_TEMPLATES)
    return note.replace("{date}", datetime.now().strftime("%B %d, %Y"))
