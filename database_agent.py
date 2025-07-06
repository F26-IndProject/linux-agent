#!/usr/bin/env python3


"""
Enhanced Unified Linux Activity Agent with Database Configuration
"""

import os
import sys
import time
import json
import subprocess
import logging
import random
import shutil
import urllib.request
import urllib.parse
import tempfile
import threading
import socket
import platform
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Конфигурация базы данных
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "lisa_dev",
    "user": "lisa",
    "password": "pass"
}

# Жёсткая конфигурация heartbeat (НЕ ИЗМЕНЯЕТСЯ ПОЛЬЗОВАТЕЛЕМ)
HEARTBEAT_CONFIG = {
    "enabled": True,
    "backend_url": "http://localhost:8000/api/agents/heartbeat",
    "interval_hours": 24,
    "include_statistics": True,
    "api_key": "sk-agent-heartbeat-key-2024", 
    "timeout_seconds": 30,
    "retry_count": 3,
    "retry_delay_seconds": 60
}

def setup_logging(log_level='INFO'):
    """Настраивает систему логирования"""
    log_dir = "/var/log/activity_agent"
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except PermissionError:
            log_dir = "/tmp"
    
    log_file = os.path.join(log_dir, "activity_agent.log")
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

class DatabaseManager:
    """Менеджер для работы с базой данных"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
    
    def connect(self) -> bool:
        """Подключение к базе данных"""
        try:
            self.connection = psycopg2.connect(**self.config)
            logging.info("Connected to PostgreSQL database")
            return True
        except Exception as e:
            logging.error(f"Failed to connect to database: {e}")
            return False
    
    def disconnect(self):
        """Отключение от базы данных"""
        if self.connection:
            self.connection.close()
            logging.info("Disconnected from database")
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Выполнение SQL запроса"""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params)
                
                # Если это SELECT запрос
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    self.connection.commit()
                    return []
        except Exception as e:
            logging.error(f"Database query failed: {e}")
            if self.connection:
                self.connection.rollback()
            return []
    
    def get_user_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """Получает шаблон пользователя по ID"""
        query = """
        SELECT bt.*, r.name as role_name, r.category as role_category
        FROM behavior_templates bt
        LEFT JOIN roles r ON bt.role_id = r.id
        WHERE bt.id = %s AND bt.is_active = true
        """
        
        results = self.execute_query(query, (template_id,))
        return results[0] if results else None
    
    def get_application_templates(self, app_names: List[str]) -> List[Dict[str, Any]]:
        """Получает шаблоны приложений по именам"""
        if not app_names:
            return []
        
        placeholders = ','.join(['%s'] * len(app_names))
        query = f"""
        SELECT * FROM applications_template
        WHERE name IN ({placeholders}) AND is_active = true
        """
        
        return self.execute_query(query, tuple(app_names))
    
    def update_agent_status(self, agent_id: str, status: str, last_activity: str = None):
        """Обновляет статус агента"""
        query = """
        UPDATE agents 
        SET status = %s, last_seen = %s, last_activity = %s, updated_at = %s
        WHERE agent_id = %s
        """
        
        self.execute_query(query, (
            status,
            datetime.now(),
            last_activity,
            datetime.now(),
            agent_id
        ))
    
    def log_agent_activity(self, agent_id: str, activity_type: str, activity_data: Dict[str, Any]):
        """Логирует активность агента"""
        # Сначала получаем внутренний ID агента
        query = "SELECT id FROM agents WHERE agent_id = %s"
        results = self.execute_query(query, (agent_id,))
        
        if not results:
            logging.error(f"Agent {agent_id} not found in database")
            return
        
        internal_agent_id = results[0]['id']
        
        # Логируем активность
        insert_query = """
        INSERT INTO agent_activities (agent_id, activity_type, activity_data)
        VALUES (%s, %s, %s)
        """
        
        self.execute_query(insert_query, (
            internal_agent_id,
            activity_type,
            json.dumps(activity_data)
        ))

class DatabaseConfigManager:
    """Менеджер конфигураций для работы с базой данных"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def load_agent_config(self, template_id: int, agent_id: str = None) -> Optional[Dict[str, Any]]:
        """Загружает полную конфигурацию агента из базы данных"""
        # Получаем шаблон пользователя
        user_template = self.db_manager.get_user_template(template_id)
        if not user_template:
            logging.error(f"User template {template_id} not found")
            return None
        
        # Парсим данные шаблона
        template_data = user_template['template_data']
        
        # Базовая конфигурация из шаблона
        config = {
            "template_id": template_id,
            "agent_id": agent_id or f"AGENT_{random.randint(100000, 999999)}",
            "username": template_data.get('username', 'agent_user'),
            "full_name": template_data.get('full_name', 'Agent User'),
            "role": user_template.get('role_name', 'User'),
            "role_category": user_template.get('role_category', 'General'),
            "work_schedule": template_data.get('work_schedule', {
                "start_time": "09:00",
                "end_time": "18:00",
                "breaks": [{"start": "12:00", "duration_minutes": 60}]
            }),
            "operating_system": user_template.get('os_type', 'linux'),
            "applications_used": template_data.get('applications_used', []),
            "activity_pattern": template_data.get('activity_pattern', 'Regular office hours'),
            "department": template_data.get('department', 'General'),
            "location": template_data.get('location', 'Office'),
        }
        
        # Получаем кастомные приложения если они есть
        custom_apps = template_data.get('custom_applications', [])
        if custom_apps:
            app_templates = self.db_manager.get_application_templates(custom_apps)
            config['custom_applications'] = {
                app['name']: app['template_config'] for app in app_templates
            }
        
        logging.info(f"Loaded config for template {template_id}: {config['username']}")
        logging.info(f"Applications: {config['applications_used']}")
        logging.info(f"Custom applications: {list(config.get('custom_applications', {}).keys())}")
        
        return config

class DatabaseActivityAgent:
    """Агент активности с подключением к базе данных"""
    
    def __init__(self, template_id: int, agent_id: str = None):
        self.template_id = template_id
        self.agent_id = agent_id
        
        # Инициализация базы данных
        self.db_manager = DatabaseManager(DATABASE_CONFIG)
        if not self.db_manager.connect():
            raise Exception("Failed to connect to database")
        
        # Загрузка конфигурации
        self.config_manager = DatabaseConfigManager(self.db_manager)
        self.config = self.config_manager.load_agent_config(template_id, agent_id)
        
        if not self.config:
            raise Exception(f"Failed to load configuration for template {template_id}")
        
        self.agent_id = self.config['agent_id']
        
        # Инициализация переменных состояния
        self.current_app = None
        self.app_start_time = None
        self.session_duration = random.randint(300, 900)
        self.start_time = time.time()
        
        # Обновляем статус агента в БД
        self.db_manager.update_agent_status(self.agent_id, "starting", "Agent initialization")
    
    def get_builtin_applications(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает встроенные приложения (ваш существующий код)"""
        return {
            "Visual Studio Code": {
                "open": "/usr/bin/code --no-sandbox --user-data-dir=/tmp/vscode-root",
                "close": "pkill -f code",
                "activities": [
                    {
                        "description": "Opening a file",
                        "commands": [
                            "xdotool key ctrl+o",
                            "sleep 0.5",
                            "xdotool type 'main.py'",
                            "xdotool key Return"
                        ]
                    },
                    {
                        "description": "Typing code",
                        "commands": [
                            "xdotool type 'print(\"Hello World\")'",
                            "xdotool key Return", 
                            "xdotool key ctrl+s"
                        ]
                    }
                ]
            },
            "leafpad": {
                "open": "leafpad",
                "close": "pkill -f leafpad",
                "activities": [
                    {
                        "description": "Создание нового файла",
                        "commands": [
                            "xdotool key ctrl+n",
                            "sleep 1",
                            "xdotool type 'Заметки на сегодня'",
                            "xdotool key Return"
                        ]
                    }
                ]
            },
            "Terminal": {
                "open": "gnome-terminal || xfce4-terminal || xterm",
                "close": "pkill -f 'gnome-terminal|xfce4-terminal|xterm'",
                "activities": [
                    {
                        "description": "System information check",
                        "commands": [
                            "xdotool type 'uname -a'",
                            "xdotool key Return",
                            "sleep 2"
                        ]
                    }
                ]
            }
        }
    
    def get_available_applications(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает доступные приложения (встроенные + кастомные)"""
        # Встроенные приложения
        builtin_apps = self.get_builtin_applications()
        
        # Фильтруем только те приложения, которые указаны в конфигурации пользователя
        available_apps = {}
        for app_name in self.config.get('applications_used', []):
            if app_name in builtin_apps:
                available_apps[app_name] = builtin_apps[app_name]
        
        # Добавляем кастомные приложения
        custom_apps = self.config.get('custom_applications', {})
        for app_name, app_config in custom_apps.items():
            # Конвертируем формат из БД в формат агента
            available_apps[app_name] = self.convert_db_app_config(app_config)
        
        return available_apps
    
    def convert_db_app_config(self, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Конвертирует конфигурацию приложения из формата БД в формат агента"""
        execution = db_config.get('execution', {})
        activities_db = db_config.get('activities', [])
        
        # Конвертируем активности из формата БД в формат агента
        activities = []
        for activity in activities_db:
            commands = []
            for cmd in activity.get('commands', []):
                if cmd['type'] == 'key_combination':
                    commands.append(f"xdotool key {cmd['keys']}")
                elif cmd['type'] == 'type_text':
                    commands.append(f"xdotool type '{cmd['text']}'")
                elif cmd['type'] == 'wait':
                    commands.append(f"sleep {cmd['time']}")
                # Добавляем delay если есть
                if 'delay' in cmd and cmd['delay'] > 0:
                    commands.append(f"sleep {cmd['delay']}")
            
            activities.append({
                "description": activity.get('description', activity.get('name', 'Activity')),
                "commands": commands
            })
        
        return {
            "open": execution.get('open_command', ''),
            "close": execution.get('close_command', ''),
            "activities": activities
        }
    
    def run_command(self, command):
        """Выполняет команду и логирует результат"""
        start_time = time.time()
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            duration = time.time() - start_time
            
            # Логируем в БД
            self.db_manager.log_agent_activity(
                self.agent_id,
                "command_execution",
                {
                    "command": command,
                    "duration": duration,
                    "success": result.returncode == 0,
                    "output": result.stdout[:500] if result.stdout else None,
                    "error": result.stderr[:500] if result.stderr else None
                }
            )
            
            if result.returncode == 0:
                logging.debug(f"SUCCESS: {command} (duration: {duration:.2f}s)")
            else:
                logging.warning(f"COMMAND FAILED: {command} - {result.stderr}")
        except Exception as e:
            duration = time.time() - start_time
            logging.error(f"ERROR: {command} (duration: {duration:.2f}s) - {e}")
            
            # Логируем ошибку в БД
            self.db_manager.log_agent_activity(
                self.agent_id,
                "command_error",
                {
                    "command": command,
                    "duration": duration,
                    "error": str(e)
                }
            )
    
    def open_application(self, app_name):
        """Открывает приложение"""
        available_apps = self.get_available_applications()
        app_config = available_apps.get(app_name)
        
        if not app_config:
            logging.warning(f"Application {app_name} not found in configuration")
            return False
        
        open_cmd = app_config.get('open')
        if not open_cmd:
            logging.warning(f"No open command for {app_name}")
            return False
        
        logging.info(f"Opening {app_name}...")
        self.run_command(open_cmd)
        
        self.current_app = app_name
        self.app_start_time = time.time()
        
        # Обновляем статус в БД
        self.db_manager.update_agent_status(self.agent_id, "active", f"Opened {app_name}")
        
        # Логируем активность
        self.db_manager.log_agent_activity(
            self.agent_id,
            "app_opened",
            {"application": app_name, "timestamp": datetime.now().isoformat()}
        )
        
        return True
    
    def close_application(self, app_name):
        """Закрывает приложение"""
        available_apps = self.get_available_applications()
        app_config = available_apps.get(app_name)
        
        if app_config and 'close' in app_config:
            logging.info(f"Closing {app_name}")
            self.run_command(app_config['close'])
        
        # Логируем закрытие
        if self.current_app:
            session_duration = time.time() - self.app_start_time if self.app_start_time else 0
            self.db_manager.log_agent_activity(
                self.agent_id,
                "app_closed",
                {
                    "application": self.current_app,
                    "session_duration": session_duration,
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        self.current_app = None
        self.app_start_time = None
    
    def simulate_activity(self, app_name):
        """Эмулирует активность в приложении"""
        available_apps = self.get_available_applications()
        app_config = available_apps.get(app_name)
        
        if not app_config or 'activities' not in app_config:
            return False
        
        activities = app_config['activities']
        if not activities:
            return False
        
        activity = random.choice(activities)
        activity_name = activity.get('description', 'Unknown Activity')
        
        logging.info(f"Simulating activity in {app_name}: {activity_name}")
        
        # Логируем начало активности
        self.db_manager.log_agent_activity(
            self.agent_id,
            "activity_started",
            {
                "application": app_name,
                "activity": activity_name,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Выполняем команды активности
        for cmd in activity.get('commands', []):
            self.run_command(cmd)
            time.sleep(random.uniform(1, 3))
        
        # Логируем завершение активности
        self.db_manager.log_agent_activity(
            self.agent_id,
            "activity_completed",
            {
                "application": app_name,
                "activity": activity_name,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return True
    
    def should_switch_app(self):
        """Определяет, нужно ли переключиться на другое приложение"""
        if not self.current_app or not self.app_start_time:
            return True
        
        elapsed = time.time() - self.app_start_time
        return elapsed >= self.session_duration
    
    def get_next_app(self):
        """Выбирает следующее приложение для работы"""
        available_apps = self.get_available_applications()
        app_names = list(available_apps.keys())
        
        if not app_names:
            return None
        
        # Исключаем текущее приложение
        if self.current_app in app_names:
            app_names.remove(self.current_app)
        
        return random.choice(app_names) if app_names else None
    
    def is_work_time(self):
        """Проверяет, рабочее ли время"""
        current_time = datetime.now().time()
        schedule = self.config.get('work_schedule', {})
        
        start_time = datetime.strptime(schedule.get('start_time', '09:00'), '%H:%M').time()
        end_time = datetime.strptime(schedule.get('end_time', '18:00'), '%H:%M').time()
        
        return start_time <= current_time <= end_time
    
    def run(self):
        """Основной цикл работы агента"""
        logging.info(f"Starting Database Activity Agent")
        logging.info(f"Agent ID: {self.agent_id}")
        logging.info(f"Template ID: {self.template_id}")
        logging.info(f"User: {self.config.get('full_name', 'Unknown')}")
        logging.info(f"Role: {self.config.get('role', 'Unknown')}")
        logging.info(f"Available applications: {list(self.get_available_applications().keys())}")
        
        # Обновляем статус
        self.db_manager.update_agent_status(self.agent_id, "running", "Agent started")
        
        try:
            while True:
                # Проверяем рабочее время
                if not self.is_work_time():
                    if self.current_app:
                        logging.info("Work time ended, closing current application")
                        self.close_application(self.current_app)
                    
                    self.db_manager.update_agent_status(self.agent_id, "idle", "Outside work hours")
                    logging.info("Outside work hours, sleeping...")
                    time.sleep(300)
                    continue
                
                # Переключение приложений
                if self.should_switch_app():
                    if self.current_app:
                        self.close_application(self.current_app)
                    
                    # Пауза между приложениями
                    pause_time = random.randint(30, 120)
                    logging.info(f"Pausing for {pause_time} seconds between applications")
                    time.sleep(pause_time)
                    
                    # Открываем новое приложение
                    next_app = self.get_next_app()
                    if next_app and self.open_application(next_app):
                        self.session_duration = random.randint(300, 900)
                        time.sleep(5)
                
                # Эмулируем активность
                if self.current_app:
                    self.simulate_activity(self.current_app)
                
                # Пауза между активностями
                activity_pause = random.randint(10, 60)
                time.sleep(activity_pause)
                
        except KeyboardInterrupt:
            logging.info("Agent stopped by user")
            self.db_manager.update_agent_status(self.agent_id, "stopped", "Stopped by user")
            if self.current_app:
                self.close_application(self.current_app)
        except Exception as e:
            logging.error(f"Agent crashed: {e}")
            self.db_manager.update_agent_status(self.agent_id, "error", f"Agent crashed: {str(e)}")
            if self.current_app:
                self.close_application(self.current_app)
            raise
        finally:
            self.db_manager.disconnect()

def main():
    """Главная функция"""
    setup_logging()
    
    # Получаем template_id из аргументов командной строки или переменной окружения
    template_id = None
    agent_id = None
    
    if len(sys.argv) > 1:
        try:
            template_id = int(sys.argv[1])
        except ValueError:
            print("Usage: python agent.py <template_id> [agent_id]")
            sys.exit(1)
    
    if len(sys.argv) > 2:
        agent_id = sys.argv[2]
    
    # Также можно получить из переменных окружения
    if not template_id:
        template_id = os.environ.get('AGENT_TEMPLATE_ID')
        if template_id:
            template_id = int(template_id)
    
    if not agent_id:
        agent_id = os.environ.get('AGENT_ID')
    
    if not template_id:
        print("Error: template_id is required")
        print("Usage: python agent.py <template_id> [agent_id]")
        print("Or set AGENT_TEMPLATE_ID environment variable")
        sys.exit(1)
    
    try:
        # Создаем и запускаем агента
        agent = DatabaseActivityAgent(template_id, agent_id)
        agent.run()
    except Exception as e:
        logging.error(f"Failed to start agent: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
