"""
client/database.py — Direct PostgreSQL connection for Linux agent
"""
import json
import logging
import os
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
import psycopg2
from dotenv import load_dotenv
load_dotenv()
DB_CONFIG = {
    "host":     os.getenv("DB_HOST"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}
class DatabaseManager:
    def __init__(self):
        self.connection = None
        self._lock = threading.Lock()
    def connect(self) -> bool:
        try:
            self.connection = psycopg2.connect(**DB_CONFIG)
            logging.info("Connected to PostgreSQL database directly")
            return True
        except Exception as e:
            logging.error(f"Database connection failed: {e}")
            return False
    def disconnect(self):
        if self.connection:
            self.connection.close()
            logging.info("Disconnected from database")
    def _execute(self, query: str, params: tuple = None):
        with self._lock:
            try:
                with self.connection.cursor() as cursor:
                    cursor.execute(query, params)
                    if cursor.description:
                        columns = [d[0] for d in cursor.description]
                        return [dict(zip(columns, row)) for row in cursor.fetchall()]
                    else:
                        self.connection.commit()
                        return []
            except Exception as e:
                logging.error(f"Query failed: {e}")
                if self.connection:
                    self.connection.rollback()
                return []
    def ensure_agent_exists(self, agent_id: str, username: str, role: str) -> Optional[int]:
        results = self._execute(
            "SELECT id FROM agents WHERE agent_id = %s",
            (agent_id,)
        )
        if results:
            existing_role = self._execute(
                "SELECT agent_role FROM agents WHERE agent_id = %s",
                (agent_id,)
            )
            if not existing_role or not existing_role[0].get('agent_role'):
                self._execute(
                    "UPDATE agents SET agent_role = %s WHERE agent_id = %s",
                    (role, agent_id)
                )
            return results[0]['id']
        logging.info(f"Creating agent record in database: {agent_id}")
        self._execute(
            """
            INSERT INTO agents (agent_id, name, status, os_type, config, last_seen, agent_role)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                agent_id,
                username,
                "active",
                "Linux",
                json.dumps({"role": role}),
                datetime.utcnow(),
                role
            )
        )
        results = self._execute(
            "SELECT id FROM agents WHERE agent_id = %s",
            (agent_id,)
        )
        return results[0]['id'] if results else None
    def get_agent_role(self, agent_id: str) -> Optional[str]:
        results = self._execute(
            "SELECT agent_role FROM agents WHERE agent_id = %s",
            (agent_id,)
        )
        if results and results[0]['agent_role']:
            return results[0]['agent_role']
        return None
    def get_agent_schedule(self, agent_id: str) -> Optional[Dict]:
        results = self._execute(
            """
            SELECT s.name, s.work_days, s.work_start, s.work_end
            FROM agents a
            JOIN agent_schedules s ON s.id = a.agent_schedule_id
            WHERE a.agent_id = %s
            """,
            (agent_id,)
        )
        if not results:
            return None
        row = results[0]
        days = row['work_days']
        if isinstance(days, str):
            days = json.loads(days)
        return {
            'name':       row['name'],
            'work_days':  days,
            'work_start': row['work_start'],
            'work_end':   row['work_end']
        }
    def get_agent_break(self, agent_id: str) -> Optional[Dict]:
        results = self._execute(
            """
            SELECT b.name, b.break_start, b.break_end
            FROM agents a
            JOIN break_times b ON b.id = a.agent_break_id
            WHERE a.agent_id = %s
            """,
            (agent_id,)
        )
        if not results:
            return None
        row = results[0]
        return {
            'name':        row['name'],
            'break_start': row['break_start'],
            'break_end':   row['break_end']
        }
    def is_public_holiday(self) -> bool:
        results = self._execute(
            "SELECT id FROM public_holidays WHERE date = CURRENT_DATE LIMIT 1"
        )
        return bool(results)
    def get_role_definition(self, role_name: str) -> Optional[List[Dict]]:
        try:
            results = self._execute(
                """
                SELECT actions FROM agent_role_definitions
                WHERE name = %s AND is_active = TRUE
                """,
                (role_name,)
            )
            if not results:
                return None
            actions = results[0]['actions']
            if isinstance(actions, str):
                actions = json.loads(actions)
            activities = []
            for action_type, config in actions.items():
                activity = {"action": action_type}
                activity.update(config)
                activities.append(activity)
            logging.info(f"Loaded custom role '{role_name}' from database ({len(activities)} actions)")
            return activities
        except Exception as e:
            logging.error(f"Failed to fetch role definition '{role_name}': {e}")
            return None
    def update_agent_status(self, agent_id: str, last_activity: str):
        self._execute(
            """
            UPDATE agents
            SET status = 'active',
                last_seen = %s,
                last_activity = %s,
                updated_at = %s
            WHERE agent_id = %s
            """,
            (datetime.utcnow(), last_activity, datetime.utcnow(), agent_id)
        )
    def get_role_updated_at(self, role_name: str):
        results = self._execute(
            "SELECT updated_at FROM agent_role_definitions WHERE name = %s AND is_active = TRUE",
            (role_name,)
        )
        if results and results[0].get('updated_at'):
            return results[0]['updated_at']
        return None
    def get_deleted_tasks(self, agent_id: str) -> List[str]:
        results = self._execute(
            "SELECT task_name FROM agent_deleted_tasks WHERE agent_id = %s",
            (agent_id,)
        )
        return [r['task_name'] for r in results]
    def mark_task_deleted(self, agent_id: str, task_name: str):
        self._execute(
            """
            INSERT INTO agent_deleted_tasks (agent_id, task_name)
            VALUES (%s, %s)
            ON CONFLICT (agent_id, task_name) DO NOTHING
            """,
            (agent_id, task_name)
        )
    def restore_task(self, agent_id: str, task_name: str):
        self._execute(
            "DELETE FROM agent_deleted_tasks WHERE agent_id = %s AND task_name = %s",
            (agent_id, task_name)
        )
    def get_deleted_crons(self, agent_id: str) -> List[str]:
        """Return cron job names that have been deleted for this agent."""
        results = self._execute(
            "SELECT job_name FROM agent_deleted_crons WHERE agent_id = %s",
            (agent_id,)
        )
        return [r['job_name'] for r in results]
    def mark_cron_deleted(self, agent_id: str, job_name: str):
        """Record that a cron job was deleted — prevents recreation."""
        self._execute(
            """
            INSERT INTO agent_deleted_crons (agent_id, job_name)
            VALUES (%s, %s)
            ON CONFLICT (agent_id, job_name) DO NOTHING
            """,
            (agent_id, job_name)
        )
    def restore_cron(self, agent_id: str, job_name: str):
        """Remove the deleted-cron record — allows the job to be recreated again."""
        self._execute(
            "DELETE FROM agent_deleted_crons WHERE agent_id = %s AND job_name = %s",
            (agent_id, job_name)
        )
    def log_activity(self, agent_id: str, activity_type: str, activity_data: Dict[str, Any]):
        results = self._execute(
            "SELECT id FROM agents WHERE agent_id = %s",
            (agent_id,)
        )
        if not results:
            logging.error(f"Agent not found in DB: {agent_id}")
            return
        internal_id = results[0]['id']
        self._execute(
            """
            INSERT INTO agent_activities (agent_id, activity_type, activity_data, timestamp)
            VALUES (%s, %s, %s, %s)
            """,
            (
                internal_id,
                activity_type,
                json.dumps(activity_data),
                datetime.utcnow()
            )
        )
        logging.info(f"Activity logged to DB: {activity_type}")
