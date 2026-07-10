"""
client/server_api.py — Communication with the LISA backend server
"""

import logging
import platform
from datetime import datetime

import requests


def send_heartbeat_to_server(url: str, agent_id: str, username: str, role: str,
                              current_activity: str = None):
    payload = {
        "agent_id":   agent_id,
        "name":       username,
        "username":   username,
        "status":     "active",
        "os_type":    f"Linux-{platform.release()[:30]}",
        "role":       role,
        "timestamp":  datetime.utcnow().isoformat(),
        "system_info": {
            "platform":  platform.system(),
            "release":   platform.release(),
            "machine":   platform.machine(),
            "processor": platform.processor()[:50],
            "hostname":  platform.node(),
        },
        "last_activity": current_activity or f"Running as {role}"
    }

    if current_activity:
        payload["current_activity"] = {
            "application": current_activity,
            "timestamp":   datetime.utcnow().isoformat()
        }

    headers = {
        "Authorization": "Bearer sk-agent-heartbeat-key-2024",
        "Content-Type":  "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code in (200, 201):
            logging.info(f"Heartbeat sent — activity: {current_activity or 'idle'}")
        else:
            logging.warning(
                f"Heartbeat returned {response.status_code}: {response.text[:200]}"
            )
    except requests.ConnectionError:
        logging.error(f"Cannot reach server at {url}")
    except requests.Timeout:
        logging.error("Heartbeat timed out")
    except Exception as e:
        logging.error(f"Heartbeat failed: {e}")
