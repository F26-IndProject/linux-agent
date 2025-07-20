#!/usr/bin/env python3
"""
Модифицированный Linux Activity Agent с циклом while True
Поддерживает автоматические обновления через мьютексы
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
import urllib.error
import tempfile
import threading
import socket
import platform
import psycopg2
import importlib.util
import psutil
import signal
import fcntl
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

# Конфигурация базы данных
DATABASE_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "database": "lisa_dev",
    "user": "lisa",
    "password": "pass"
}

# Конфигурация мьютексов и обновлений
MUTEX_CONFIG = {
    "mutex_dir": "/var/run/activity_agents",
    "fallback_mutex_dir": "/tmp/activity_agents",
    "update_check_interval": 300,  # 5 минут
    "version_file": "/tmp/agent_versions.json"
}

# Конфигурация heartbeat
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

# Конфигурация основного цикла
MAIN_LOOP_CONFIG = {
    "activity_min_pause": 10,      # Минимальная пауза между активностями (сек)
    "activity_max_pause": 60,      # Максимальная пауза между активностями (сек)
    "app_switch_min_pause": 30,    # Минимальная пауза при смене приложений (сек)
    "app_switch_max_pause": 120,   # Максимальная пауза при смене приложений (сек)
    "non_work_check_interval": 300, # Интервал проверки в нерабочее время (сек)
    "break_check_interval": 180,   # Интервал проверки во время перерыва (сек)
    "inactive_period_min": 60,     # Минимальный период неактивности (сек)
    "inactive_period_max": 300,    # Максимальный период неактивности (сек)
    "app_session_min": 300,        # Минимальная сессия в приложении (сек)
    "app_session_max": 900         # Максимальная сессия в приложении (сек)
}

def setup_logging(log_level='INFO'):
    """Настраивает систему логирования"""
    log_dir = "/var/log/activity_agent"
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except PermissionError:
            log_dir = "/tmp"
    
    log_file = os.path.join(log_dir, "updatable_agent.log")
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s %(levelname)s [%(process)d]: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

class HeartbeatManager:
    """Менеджер heartbeat для отправки статуса на сервер"""
    
    def __init__(self, config: Dict[str, Any], agent_instance):
        self.config = config
        self.agent = agent_instance
        self.enabled = config.get('enabled', False)
        self.backend_url = config.get('backend_url', '')
        self.interval_hours = config.get('interval_hours', 24)
        self.include_statistics = config.get('include_statistics', True)
        self.api_key = config.get('api_key', '')
        self.timeout_seconds = config.get('timeout_seconds', 30)
        self.retry_count = config.get('retry_count', 3)
        self.retry_delay_seconds = config.get('retry_delay_seconds', 60)
        
        self.last_heartbeat = None
        self.heartbeat_thread = None
        self.stop_event = threading.Event()
        self.statistics = {
            'total_commands': 0,
            'successful_commands': 0,
            'failed_commands': 0,
            'applications_opened': {},
            'activities_performed': {},
            'session_start_time': datetime.now().isoformat(),
            'total_uptime': 0,
            'inactive_periods': 0,
            'total_inactive_time': 0
        }
        
        if self.enabled:
            logging.info(f"Heartbeat Manager initialized - URL: {self.backend_url}")
    
    def start(self):
        """Запускает heartbeat поток"""
        if not self.enabled:
            return
        
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return
        
        self.stop_event.clear()
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.heartbeat_thread.start()
        logging.info("Heartbeat thread started")
    
    def stop(self):
        """Останавливает heartbeat поток"""
        if not self.enabled:
            return
        
        self.stop_event.set()
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        logging.info("Heartbeat thread stopped")
    
    def _heartbeat_loop(self):
        """Основной цикл отправки heartbeat'ов"""
        while not self.stop_event.is_set():
            try:
                success = self.send_heartbeat()
                if success:
                    self.last_heartbeat = datetime.now()
                    logging.debug(f"Heartbeat sent successfully at {self.last_heartbeat}")
                
                interval_seconds = self.interval_hours * 3600
                self.stop_event.wait(interval_seconds)
                
            except Exception as e:
                logging.error(f"Error in heartbeat loop: {e}")
                self.stop_event.wait(60)
    
    def send_heartbeat(self) -> bool:
        """Отправляет heartbeat на бэкенд"""
        if not self.enabled or not self.backend_url:
            return False
        
        heartbeat_data = self._prepare_heartbeat_data()
        
        for attempt in range(self.retry_count):
            try:
                success = self._send_request(heartbeat_data)
                if success:
                    return True
                
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay_seconds)
                
            except Exception as e:
                logging.error(f"Heartbeat attempt {attempt + 1} error: {e}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay_seconds)
        
        return False
    
    def _prepare_heartbeat_data(self) -> Dict[str, Any]:
        """Подготавливает данные для heartbeat'а"""
        current_app = self.agent.current_app or "None"
        
        # Определяем является ли приложение плагином
        is_plugin = False
        if self.agent.plugin_manager.enabled and current_app:
            plugin_apps = self.agent.plugin_manager.get_plugin_applications()
            is_plugin = current_app in plugin_apps
        
        # Получаем количество доступных приложений
        available_apps = self.agent.get_available_applications()
        available_apps_count = len(available_apps)
        
        # Получаем количество плагинов
        total_plugins = 0
        if self.agent.plugin_manager.enabled:
            total_plugins = len(self.agent.plugin_manager.loaded_plugins)
        
        # Вычисляем uptime
        agent_uptime = time.time() - self.agent.start_time
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.agent.agent_id,
            "username": self.agent.config.get('username', 'unknown'),
            "role": self.agent.config.get('role', 'Unknown'),
            "department": self.agent.config.get('department', 'Unknown'),
            "location": self.agent.config.get('location', 'Unknown'),
            "system_info": {
                "hostname": platform.node(),
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": psutil.cpu_count(),
                "agent_version": "2.1.0-updatable-while-true",
                "updatable_agent": True,
                "mutex_support": True,
                "running_mode": "while_true"
            },
            "status": self.agent.current_status,
            "statistics": {
                "agent_uptime": agent_uptime,
                "current_app": current_app,
                "plugin_mode": self.agent.plugin_manager.enabled,
                "total_plugins": total_plugins,
                "available_apps": available_apps_count,
                "current_plugin_stats": {},
                "loop_iterations": self.agent.loop_iterations,
                "last_activity_time": self.agent.last_activity_time
            },
            "current_activity": {
                "application": current_app,
                "is_plugin": is_plugin,
                "in_inactive_period": self.agent.in_inactive_period
            }
        }
        
        if self.include_statistics:
            self.statistics['total_uptime'] = agent_uptime
            data["detailed_statistics"] = self.statistics.copy()
        
        return data
    
    def _send_request(self, data: Dict[str, Any]) -> bool:
        """Отправляет HTTP запрос с heartbeat данными"""
        try:
            json_data = json.dumps(data, ensure_ascii=False).encode('utf-8')
            
            req = urllib.request.Request(
                self.backend_url,
                data=json_data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}',
                    'User-Agent': f'updatable-linux-activity-agent-while-true/{self.agent.agent_id}',
                    'X-Agent-Version': '2.1.0-updatable-while-true'
                }
            )
            
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                if response.status == 200:
                    return True
                else:
                    logging.error(f"Heartbeat failed with status {response.status}")
                    return False
                    
        except Exception as e:
            logging.error(f"Error sending heartbeat: {e}")
            return False
    
    def update_statistics(self, stat_type: str, data: Dict[str, Any] = None):
        """Обновляет статистику для включения в heartbeat"""
        if not self.include_statistics:
            return
        
        try:
            if stat_type == 'command_executed':
                self.statistics['total_commands'] += 1
                if data and data.get('success'):
                    self.statistics['successful_commands'] += 1
                else:
                    self.statistics['failed_commands'] += 1
            
            elif stat_type == 'app_opened':
                app_name = data.get('application') if data else 'Unknown'
                if app_name not in self.statistics['applications_opened']:
                    self.statistics['applications_opened'][app_name] = 0
                self.statistics['applications_opened'][app_name] += 1
            
            elif stat_type == 'activity_performed':
                activity_key = f"{data.get('application', 'Unknown')}:{data.get('activity', 'Unknown')}" if data else 'Unknown'
                if activity_key not in self.statistics['activities_performed']:
                    self.statistics['activities_performed'][activity_key] = 0
                self.statistics['activities_performed'][activity_key] += 1
            
            elif stat_type == 'inactive_period':
                self.statistics['inactive_periods'] += 1
                if data and 'duration' in data:
                    self.statistics['total_inactive_time'] += data['duration']
            
        except Exception as e:
            logging.error(f"Error updating statistics: {e}")
    
    def force_heartbeat(self) -> bool:
        """Принудительно отправляет heartbeat"""
        logging.info("Forcing immediate heartbeat")
        return self.send_heartbeat()
    
    def get_last_heartbeat_info(self) -> Dict[str, Any]:
        """Возвращает информацию о последнем heartbeat'е"""
        return {
            "enabled": self.enabled,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "backend_url": self.backend_url,
            "interval_hours": self.interval_hours
        }

class AgentMutexManager:
    """Менеджер мьютексов для управления агентами пользователей"""
    
    def __init__(self, user_id: str, template_id: int):
        self.user_id = user_id
        self.template_id = template_id
        self.mutex_name = f"agent_user_{user_id}_template_{template_id}"
        self.mutex_file = None
        
        # Пробуем создать основную директорию, если не получается - используем fallback
        primary_dir = MUTEX_CONFIG["mutex_dir"]
        fallback_dir = MUTEX_CONFIG["fallback_mutex_dir"]
        
        try:
            os.makedirs(primary_dir, exist_ok=True)
            # Проверяем, можем ли писать в директорию
            test_file = Path(primary_dir) / "test_write"
            test_file.touch()
            test_file.unlink()
            self.mutex_dir = primary_dir
            logging.info(f"Using primary mutex directory: {primary_dir}")
        except (PermissionError, OSError) as e:
            logging.warning(f"Cannot use {primary_dir}: {e}, falling back to {fallback_dir}")
            os.makedirs(fallback_dir, exist_ok=True)
            self.mutex_dir = fallback_dir
            logging.info(f"Using fallback mutex directory: {fallback_dir}")
        
        self.mutex_path = Path(self.mutex_dir) / f"{self.mutex_name}.lock"
        
    def acquire_mutex(self) -> bool:
        """Захватывает мьютекс для данного пользователя"""
        try:
            # Проверяем, есть ли уже запущенный агент для этого пользователя
            if self._is_mutex_locked():
                logging.info(f"Found existing agent for user {self.user_id}, terminating...")
                self._terminate_existing_agent()
            
            # Создаем новый мьютекс
            self.mutex_file = open(self.mutex_path, 'w')
            fcntl.flock(self.mutex_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Записываем информацию о процессе
            mutex_info = {
                "pid": os.getpid(),
                "user_id": self.user_id,
                "template_id": self.template_id,
                "started_at": datetime.now().isoformat(),
                "version": self._get_agent_version(),
                "running_mode": "while_true"
            }
            
            self.mutex_file.write(json.dumps(mutex_info, indent=2))
            self.mutex_file.flush()
            
            logging.info(f"Mutex acquired for user {self.user_id}")
            return True
            
        except (OSError, IOError) as e:
            logging.error(f"Failed to acquire mutex: {e}")
            return False
    
    def release_mutex(self):
        """Освобождает мьютекс"""
        try:
            if self.mutex_file:
                fcntl.flock(self.mutex_file.fileno(), fcntl.LOCK_UN)
                self.mutex_file.close()
                self.mutex_file = None
            
            if self.mutex_path.exists():
                self.mutex_path.unlink()
                
            logging.info(f"Mutex released for user {self.user_id}")
        except Exception as e:
            logging.error(f"Error releasing mutex: {e}")
    
    def _is_mutex_locked(self) -> bool:
        """Проверяет, заблокирован ли мьютекс"""
        if not self.mutex_path.exists():
            return False
        
        try:
            with open(self.mutex_path, 'r') as f:
                mutex_info = json.load(f)
                pid = mutex_info.get('pid')
                
                # Проверяем, существует ли процесс
                if pid and psutil.pid_exists(pid):
                    return True
                else:
                    # Процесс не существует, удаляем устаревший мьютекс
                    self.mutex_path.unlink()
                    return False
        except Exception:
            return False
    
    def _terminate_existing_agent(self):
        """Корректно завершает существующий агент"""
        try:
            with open(self.mutex_path, 'r') as f:
                mutex_info = json.load(f)
                pid = mutex_info.get('pid')
                
                if pid and psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    
                    # Сначала пытаемся graceful shutdown
                    logging.info(f"Sending SIGTERM to process {pid}")
                    process.terminate()
                    
                    # Ждем до 10 секунд
                    try:
                        process.wait(timeout=10)
                        logging.info(f"Process {pid} terminated gracefully")
                    except psutil.TimeoutExpired:
                        # Если не помогло, используем SIGKILL
                        logging.warning(f"Force killing process {pid}")
                        process.kill()
                        process.wait(timeout=5)
                
        except Exception as e:
            logging.error(f"Error terminating existing agent: {e}")
    
    def _get_agent_version(self) -> str:
        """Получает версию агента"""
        try:
            binary_path = sys.argv[0]
            with open(binary_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()[:16]
        except Exception:
            return "unknown"

class AgentUpdateManager:
    """Менеджер обновлений агентов"""
    
    def __init__(self, user_id: str, template_id: int, db_manager):
        self.user_id = user_id
        self.template_id = template_id
        self.db_manager = db_manager
        self.current_version = self._get_current_version()
        self.update_thread = None
        self.stop_event = threading.Event()
        self.last_check_time = 0
    
    def start_update_monitoring(self):
        """Запускает мониторинг обновлений"""
        if self.update_thread and self.update_thread.is_alive():
            return
        
        self.stop_event.clear()
        self.update_thread = threading.Thread(target=self._update_monitor_loop, daemon=True)
        self.update_thread.start()
        logging.info("Update monitoring started")
    
    def stop_update_monitoring(self):
        """Останавливает мониторинг обновлений"""
        self.stop_event.set()
        if self.update_thread:
            self.update_thread.join(timeout=5)
    
    def check_for_updates_sync(self) -> bool:
        """Синхронная проверка обновлений (для основного цикла)"""
        current_time = time.time()
        
        # Проверяем не слишком ли часто
        if current_time - self.last_check_time < MUTEX_CONFIG["update_check_interval"]:
            return False
        
        self.last_check_time = current_time
        return self._check_for_updates()
    
    def _update_monitor_loop(self):
        """Основной цикл мониторинга обновлений"""
        initial_delay = 300  # 5 минут
        logging.info(f"Waiting {initial_delay} seconds before first update check...")
        self.stop_event.wait(initial_delay)

        while not self.stop_event.is_set():
            try:
                if self._check_for_updates():
                    logging.info("Update available, initiating update process...")
                    self._initiate_update()
                
                self.stop_event.wait(MUTEX_CONFIG["update_check_interval"])
                
            except Exception as e:
                logging.error(f"Error in update monitor: {e}")
                self.stop_event.wait(60)
    
    def _check_for_updates(self) -> bool:
        """Проверяет наличие обновлений"""
        try:
            # Проверяем в БД, есть ли новые сборки для нашего шаблона
            query = """
            SELECT binary_path, build_config, created_at
            FROM agent_builds 
            WHERE agent_id IN (
                SELECT id FROM agents WHERE template_id = %s
            )
            AND build_status = 'completed'
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            results = self.db_manager.execute_query(query, (self.template_id,))
            
            if not results:
                return False
            
            latest_build = results[0]
            build_config = latest_build['build_config']
            
            # Сравниваем версии
            if isinstance(build_config, str):
                build_config = json.loads(build_config)
            
            latest_version = build_config.get('version_hash', 'unknown')
            
            if latest_version != self.current_version:
                logging.info(f"New version available: {latest_version} (current: {self.current_version})")
                return True
            
            return False
            
        except Exception as e:
            logging.error(f"Error checking for updates: {e}")
            return False
    
    def _initiate_update(self):
        """Инициирует процесс обновления"""
        try:
            # Получаем путь к новому бинарнику
            new_binary_path = self._get_latest_binary_path()
            
            if not new_binary_path or not Path(new_binary_path).exists():
                logging.error("New binary not found")
                return
            
            # Запускаем новый агент (он сам убьет текущий через мьютекс)
            self._launch_new_agent(new_binary_path)
            
        except Exception as e:
            logging.error(f"Error during update: {e}")
    
    def _get_latest_binary_path(self) -> Optional[str]:
        """Получает путь к последнему скомпилированному бинарнику"""
        try:
            query = """
            SELECT binary_path
            FROM agent_builds 
            WHERE agent_id IN (
                SELECT id FROM agents WHERE template_id = %s
            )
            AND build_status = 'completed'
            AND binary_path IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
            """
            
            results = self.db_manager.execute_query(query, (self.template_id,))
            
            if results:
                return results[0]['binary_path']
            
            return None
            
        except Exception as e:
            logging.error(f"Error getting latest binary path: {e}")
            return None
    
    def _launch_new_agent(self, binary_path: str):
        """Запускает новый агент"""
        try:
            # Запускаем новый процесс
            cmd = [binary_path, str(self.template_id), f"USER_{self.user_id}"]
            
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            logging.info(f"Launched new agent: {binary_path}")
            
            # Даем новому агенту время запуститься и захватить мьютекс
            time.sleep(5)
            
            # Завершаем текущий процесс
            logging.info("Exiting current agent for update")
            os._exit(0)
            
        except Exception as e:
            logging.error(f"Error launching new agent: {e}")
    
    def _get_current_version(self) -> str:
        """Получает текущую версию агента"""
        try:
            binary_path = sys.argv[0]
            with open(binary_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()[:16]
        except Exception:
            return "unknown"

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
        if results:
            template = results[0]
            # Обрабатываем template_data
            if isinstance(template['template_data'], str):
                template['template_data'] = json.loads(template['template_data'])
            return template
        return None
    
    def get_application_templates(self, app_names: List[str]) -> List[Dict[str, Any]]:
        """Получает шаблоны приложений по именам"""
        if not app_names:
            return []
        
        placeholders = ','.join(['%s'] * len(app_names))
        query = f"""
        SELECT * FROM applications_template
        WHERE name IN ({placeholders}) AND is_active = true
        """
        
        results = self.execute_query(query, tuple(app_names))
        processed_results = []
        for app in results:
            config = app['template_config']
            if isinstance(config, str):
                config = json.loads(config)
            app['template_config'] = config
            processed_results.append(app)
        
        return processed_results
    
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
        query = "SELECT id FROM agents WHERE agent_id = %s"
        results = self.execute_query(query, (agent_id,))
        
        if not results:
            logging.error(f"Agent {agent_id} not found in database")
            return
        
        internal_agent_id = results[0]['id']
        
        insert_query = """
        INSERT INTO agent_activities (agent_id, activity_type, activity_data)
        VALUES (%s, %s, %s)
        """
        
        self.execute_query(insert_query, (
            internal_agent_id,
            activity_type,
            json.dumps(activity_data)
        ))

class PluginManager:
    """Менеджер плагинов для расширения функциональности агента"""
    
    def __init__(self, plugin_config: Dict[str, Any]):
        self.enabled = plugin_config.get('enabled', False)
        self.plugins_directory = plugin_config.get('plugins_directory', '/opt/linux_agent/plugins')
        self.auto_load = plugin_config.get('auto_load', True)
        self.fallback_to_builtin = plugin_config.get('fallback_to_builtin', True)
        self.loaded_plugins = {}
        
        if self.enabled and self.auto_load:
            self.load_plugins()
    
    def load_plugins(self):
        """Загружает плагины из директории"""
        if not os.path.exists(self.plugins_directory):
            logging.warning(f"Plugins directory {self.plugins_directory} not found")
            return
        
        for file_path in Path(self.plugins_directory).glob("*.py"):
            try:
                self.load_plugin(file_path)
            except Exception as e:
                logging.error(f"Failed to load plugin {file_path}: {e}")
    
    def load_plugin(self, plugin_path: Path):
        """Загружает отдельный плагин"""
        plugin_name = plugin_path.stem
        
        spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, 'get_application_config'):
                self.loaded_plugins[plugin_name] = module
                logging.info(f"Plugin {plugin_name} loaded successfully")
            else:
                logging.warning(f"Plugin {plugin_name} missing required functions")
    
    def get_plugin_applications(self) -> Dict[str, Dict[str, Any]]:
        """Получает приложения от всех загруженных плагинов"""
        plugin_apps = {}
        
        for plugin_name, plugin_module in self.loaded_plugins.items():
            try:
                if hasattr(plugin_module, 'get_application_config'):
                    apps = plugin_module.get_application_config()
                    plugin_apps.update(apps)
                    logging.debug(f"Plugin {plugin_name} provided {len(apps)} applications")
            except Exception as e:
                logging.error(f"Error getting applications from plugin {plugin_name}: {e}")
        
        return plugin_apps

class DatabaseConfigManager:
    """Менеджер конфигураций для работы с базой данных"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
    
    def load_agent_config(self, template_id: int, agent_id: str = None) -> Optional[Dict[str, Any]]:
        """Загружает полную конфигурацию агента из базы данных"""
        user_template = self.db_manager.get_user_template(template_id)
        if not user_template:
            logging.error(f"User template {template_id} not found")
            return None
        
        template_data = user_template['template_data']
        
        config = {
            "template_id": template_id,
            "agent_id": agent_id or f"AGENT_{random.randint(100000, 999999)}",
            "user_id": template_data.get('user_id', str(template_id)),
            "username": template_data.get('username', 'agent_user'),
            "full_name": template_data.get('full_name', 'Agent User'),
            "role": user_template.get('role_name', template_data.get('role', 'User')),
            "role_category": user_template.get('role_category', 'General'),
            "work_schedule": template_data.get('work_schedule', {
                "start_time": "09:00",
                "end_time": "18:00",
                "breaks": [{"start": "12:00", "duration_minutes": 60}]
            }),
            "operating_system": template_data.get('operating_system', 
                                               user_template.get('os_type', 'Linux')),
            "applications_used": template_data.get('applications_used', []),
            "activity_pattern": template_data.get('activity_pattern', 'Regular office hours'),
            "department": template_data.get('department', 'General'),
            "location": template_data.get('location', 'Office'),
            "plugin_support": template_data.get('plugin_support', {
                "enabled": False,
                "plugins_directory": "/opt/linux_agent/plugins",
                "auto_load": False,
                "fallback_to_builtin": True
            })
        }
        
        custom_apps = template_data.get('custom_applications', [])
        if custom_apps:
            app_templates = self.db_manager.get_application_templates(custom_apps)
            config['custom_applications'] = {
                app['name']: app['template_config'] for app in app_templates
            }
        
        logging.info(f"Loaded config for template {template_id}: {config['username']}")
        logging.info(f"User ID: {config['user_id']}")
        logging.info(f"Operating System: {config['operating_system']}")
        logging.info(f"Applications: {config['applications_used']}")
        logging.info(f"Custom applications: {list(config.get('custom_applications', {}).keys())}")
        logging.info(f"Plugin support: {config['plugin_support']['enabled']}")
        
        return config

class DatabaseActivityAgent:
    """Главный класс агента активности с циклом while True"""
    
    def __init__(self, template_id: int, agent_id: str = None):
        self.template_id = template_id
        self.agent_id = agent_id
        self.running = True
        self.shutdown_requested = False
        
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
        
        # Инициализация менеджера мьютексов
        self.mutex_manager = AgentMutexManager(self.config['user_id'], template_id)
        
        # Захватываем мьютекс (это убьет предыдущую копию, если она есть)
        if not self.mutex_manager.acquire_mutex():
            raise Exception("Failed to acquire mutex")
        
        # Регистрируем обработчик сигналов для graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Инициализация менеджера плагинов
        self.plugin_manager = PluginManager(self.config.get('plugin_support', {}))
        
        # Инициализация переменных состояния
        self.current_app = None
        self.app_start_time = None
        self.session_duration = random.randint(
            MAIN_LOOP_CONFIG["app_session_min"], 
            MAIN_LOOP_CONFIG["app_session_max"]
        )
        self.start_time = time.time()
        self.current_status = "starting"
        self.loop_iterations = 0
        self.last_activity_time = time.time()
        self.in_inactive_period = False
        self.inactive_start_time = None
        
        # Инициализация HeartbeatManager
        self.heartbeat_manager = HeartbeatManager(HEARTBEAT_CONFIG, self)
        
        # Обновляем статус агента в БД
        self.db_manager.update_agent_status(self.agent_id, "starting", "Agent initialization")
        
        # Запускаем heartbeat
        self.heartbeat_manager.start()
        logging.info("Heartbeat manager started")
        
        # Инициализация менеджера обновлений
        self.update_manager = AgentUpdateManager(self.config['user_id'], template_id, self.db_manager)
        self.update_manager.start_update_monitoring()
        logging.info("Update monitoring started")
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для graceful shutdown"""
        logging.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
        self.running = False
    
    def get_builtin_applications(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает встроенные приложения - минимальный набор"""
        builtin_apps = {
        "Doom": {
            "open": "chocolate-doom || doom || gzdoom || zdoom || prboom-plus",
            "close": "pkill -f 'doom|chocolate|gzdoom|zdoom|prboom'",
            "activities": [
                {
                    "description": "Start new game",
                    "commands": [
                        "sleep 3",
                        "xdotool key Return",
                        "sleep 2",
                        "xdotool key Return",
                        "sleep 1"
                    ]
                },
                {
                    "description": "Move forward and shoot",
                    "commands": [
                        "xdotool keydown w",
                        "sleep 2",
                        "xdotool keyup w",
                        "xdotool key space",
                        "sleep 1",
                        "xdotool key space",
                        "sleep 0.5"
                    ]
                },
                {
                    "description": "Look around and move",
                    "commands": [
                        "xdotool keydown a",
                        "sleep 1",
                        "xdotool keyup a",
                        "xdotool keydown d",
                        "sleep 1", 
                        "xdotool keyup d",
                        "xdotool keydown s",
                        "sleep 1",
                        "xdotool keyup s"
                    ]
                },
                {
                    "description": "Strafe and shoot demons",
                    "commands": [
                        "xdotool keydown Left",
                        "sleep 0.5",
                        "xdotool keyup Left",
                        "xdotool key space space space",
                        "xdotool keydown Right", 
                        "sleep 0.5",
                        "xdotool keyup Right",
                        "xdotool key space"
                    ]
                },
                {
                    "description": "Open doors and explore",
                    "commands": [
                        "xdotool keydown w",
                        "sleep 1",
                        "xdotool keyup w",
                        "xdotool key space",
                        "sleep 2",
                        "xdotool keydown w",
                        "sleep 1.5",
                        "xdotool keyup w"
                    ]
                },
                {
                    "description": "Switch weapons",
                    "commands": [
                        "xdotool key 2",
                        "sleep 1",
                        "xdotool key space space",
                        "xdotool key 3", 
                        "sleep 1",
                        "xdotool key space"
                    ]
                },
                {
                    "description": "Intense demon fighting",
                    "commands": [
                        "xdotool key space space space",
                        "xdotool keydown a",
                        "sleep 0.3",
                        "xdotool keyup a",
                        "xdotool key space space",
                        "xdotool keydown d",
                        "sleep 0.3", 
                        "xdotool keyup d",
                        "xdotool key space space space"
                    ]
                },
                {
                    "description": "Run and gun tactics",
                    "commands": [
                        "xdotool keydown w",
                        "xdotool key space",
                        "sleep 0.5",
                        "xdotool key space",
                        "sleep 0.5",
                        "xdotool keyup w",
                        "xdotool keydown s",
                        "sleep 0.8",
                        "xdotool keyup s"
                    ]
                },
                {
                    "description": "Collect items and health",
                    "commands": [
                        "xdotool keydown w",
                        "sleep 2",
                        "xdotool keyup w",
                        "sleep 1",
                        "xdotool keydown a",
                        "sleep 1",
                        "xdotool keyup a"
                    ]
                },
                {
                    "description": "Boss fight sequence",
                    "commands": [
                        "xdotool key 4",
                        "sleep 0.5",
                        "xdotool key space space space",
                        "xdotool keydown Left",
                        "sleep 1",
                        "xdotool keyup Left",
                        "xdotool key space space",
                        "xdotool keydown Right",
                        "sleep 1",
                        "xdotool keyup Right",
                        "xdotool key space space space"
                    ]
                }
            ]
        }
    }
        return builtin_apps
    


    def get_available_applications(self) -> Dict[str, Dict[str, Any]]:
        """Возвращает доступные приложения (встроенные + кастомные + плагины + из БД по требованию)"""
        available_apps = {}
    
        # 1. Получаем встроенные приложения
        builtin_apps = self.get_builtin_applications()
    
        # 2. Собираем список приложений, которых нет во встроенных, но они указаны в applications_used
        missing_apps = []
        applications_used = self.config.get('applications_used', [])
    
        for app_name in applications_used:
            if app_name in builtin_apps:
                # Если есть во встроенных - добавляем
                available_apps[app_name] = builtin_apps[app_name]
                logging.debug(f"Loaded builtin application: {app_name}")
            else:
            # Если нет во встроенных - помечаем для поиска в БД
                missing_apps.append(app_name)
                logging.info(f"Application '{app_name}' not found in builtin, will search in database")
    
        # 3. Ищем недостающие приложения в БД
        if missing_apps:
            logging.info(f"Searching {len(missing_apps)} missing applications in database: {missing_apps}")
            try:
                db_apps = self.db_manager.get_application_templates(missing_apps)
                for app in db_apps:
                    app_name = app['name']
                    app_config = self.convert_db_app_config(app['template_config'])
                    available_apps[app_name] = app_config
                    logging.info(f"Loaded application from database: {app_name}")
                
                    # Удаляем из списка недостающих
                    if app_name in missing_apps:
                        missing_apps.remove(app_name)
            except Exception as e:
                logging.error(f"Error loading applications from database: {e}")
    
    # 4. Логируем приложения, которые не найдены нигде
        if missing_apps:
            logging.warning(f"Applications not found anywhere: {missing_apps}")
            for app_name in missing_apps:
                logging.warning(f"Application '{app_name}' from applications_used not found in builtin or database")
    
    # 5. Добавляем кастомные приложения из custom_applications (как было раньше)
        custom_apps = self.config.get('custom_applications', {})
        for app_name, app_config in custom_apps.items():
            if app_name not in available_apps:  # Избегаем дублирования
                available_apps[app_name] = self.convert_db_app_config(app_config)
                logging.debug(f"Loaded custom application: {app_name}")
            else:
                logging.debug(f"Custom application '{app_name}' already loaded, skipping")
    
    # 6. Добавляем приложения из плагинов (если включены)
        if self.plugin_manager.enabled:
            plugin_apps = self.plugin_manager.get_plugin_applications()
            for app_name, app_config in plugin_apps.items():
                if app_name not in available_apps:  # Избегаем дублирования
                    available_apps[app_name] = app_config
                    logging.debug(f"Loaded plugin application: {app_name}")
                else:
                    logging.debug(f"Plugin application '{app_name}' already loaded, skipping")
    
        logging.info(f"Total applications loaded: {len(available_apps)} - {list(available_apps.keys())}")
    
        return available_apps
    
    def convert_db_app_config(self, db_config: Dict[str, Any]) -> Dict[str, Any]:
        """Конвертирует конфигурацию приложения из формата БД в формат агента"""
        if 'execution' in db_config:
            execution = db_config['execution']
            activities_db = db_config.get('activities', [])
            
            activities = []
            for activity in activities_db:
                commands = []
                for cmd in activity.get('commands', []):
                    if cmd.get('type') == 'key_combination':
                        commands.append(f"xdotool key {cmd.get('keys', '')}")
                    elif cmd.get('type') == 'type_text':
                        text = cmd.get('text', '').replace("'", "\\'")
                        commands.append(f"xdotool type '{text}'")
                    elif cmd.get('type') == 'wait':
                        commands.append(f"sleep {cmd.get('time', 1)}")
                    elif cmd.get('type') == 'mouse_click':
                        x = cmd.get('x', 100)
                        y = cmd.get('y', 100)
                        button = cmd.get('button', 1)
                        commands.append(f"xdotool mousemove {x} {y} click {button}")
                    
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
        elif 'open' in db_config and 'activities' in db_config:
            return db_config
        else:
            return {
                "open": db_config.get('open_command', ''),
                "close": db_config.get('close_command', ''),
                "activities": db_config.get('activities', [])
            }
    
    def run_command(self, command):
        """Выполняет команду и логирует результат"""
        start_time = time.time()
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            duration = time.time() - start_time
            success = result.returncode == 0
            
            # Обновляем статистику heartbeat
            self.heartbeat_manager.update_statistics('command_executed', {'success': success})
            
            # Логируем в БД
            self.db_manager.log_agent_activity(
                self.agent_id,
                "command_execution",
                {
                    "command": command,
                    "duration": duration,
                    "success": success,
                    "output": result.stdout[:500] if result.stdout else None,
                    "error": result.stderr[:500] if result.stderr else None
                }
            )
            
            if success:
                logging.debug(f"SUCCESS: {command} (duration: {duration:.2f}s)")
            else:
                logging.warning(f"COMMAND FAILED: {command} - {result.stderr}")
        except Exception as e:
            duration = time.time() - start_time
            logging.error(f"ERROR: {command} (duration: {duration:.2f}s) - {e}")
            
            # Обновляем статистику heartbeat
            self.heartbeat_manager.update_statistics('command_executed', {'success': False})
            
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
        self.last_activity_time = time.time()
        
        # Обновляем статистику heartbeat
        self.heartbeat_manager.update_statistics('app_opened', {'application': app_name})
        
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
            if not self.running:  # Проверяем флаг остановки
                break
            self.run_command(cmd)
            time.sleep(random.uniform(1, 3))
        
        self.last_activity_time = time.time()
        
        # Обновляем статистику heartbeat
        self.heartbeat_manager.update_statistics('activity_performed', {
            'application': app_name,
            'activity': activity_name
        })
        
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
    
    def is_break_time(self):
        """Проверяет, время ли перерыва"""
        current_time = datetime.now().time()
        schedule = self.config.get('work_schedule', {})
        breaks = schedule.get('breaks', [])
        
        for break_info in breaks:
            break_start = datetime.strptime(break_info['start'], '%H:%M').time()
            break_duration = break_info.get('duration_minutes', 60)
            break_end = (datetime.combine(datetime.today(), break_start) + 
                        timedelta(minutes=break_duration)).time()
            
            if break_start <= current_time <= break_end:
                return True
        
        return False
    
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
    
    def simulate_inactive_period(self):
        """Симулирует период неактивности"""
        if not self.in_inactive_period:
            # Начинаем период неактивности
            self.in_inactive_period = True
            self.inactive_start_time = time.time()
            inactive_duration = random.randint(
                MAIN_LOOP_CONFIG["inactive_period_min"],
                MAIN_LOOP_CONFIG["inactive_period_max"]
            )
            
            logging.info(f"Starting inactive period for {inactive_duration} seconds")
            
            # Закрываем текущее приложение
            if self.current_app:
                self.close_application(self.current_app)
            
            self.current_status = "inactive"
            self.db_manager.update_agent_status(self.agent_id, "inactive", "Inactive period")
            
            # Логируем начало периода неактивности
            self.db_manager.log_agent_activity(
                self.agent_id,
                "inactive_period_started",
                {
                    "planned_duration": inactive_duration,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Ждем с возможностью прерывания
            wait_start = time.time()
            while self.running and (time.time() - wait_start) < inactive_duration:
                time.sleep(1)
                
                # Проверяем обновления во время ожидания
                if self.loop_iterations % 60 == 0:  # Каждую минуту
                    if self.update_manager.check_for_updates_sync():
                        logging.info("Update available during inactive period")
                        self.update_manager._initiate_update()
            
            # Завершаем период неактивности
            actual_duration = time.time() - self.inactive_start_time
            self.in_inactive_period = False
            self.inactive_start_time = None
            
            # Обновляем статистику
            self.heartbeat_manager.update_statistics('inactive_period', {'duration': actual_duration})
            
            # Логируем завершение периода неактивности
            self.db_manager.log_agent_activity(
                self.agent_id,
                "inactive_period_ended",
                {
                    "actual_duration": actual_duration,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logging.info(f"Inactive period ended after {actual_duration:.1f} seconds")
    
    def get_heartbeat_status(self) -> Dict[str, Any]:
        """Возвращает статус heartbeat'ов"""
        if hasattr(self, 'heartbeat_manager'):
            return self.heartbeat_manager.get_last_heartbeat_info()
        return {"enabled": False, "error": "Heartbeat manager not initialized"}
    
    def force_heartbeat(self) -> bool:
        """Принудительно отправляет heartbeat"""
        if hasattr(self, 'heartbeat_manager'):
            return self.heartbeat_manager.force_heartbeat()
        return False
    
    def shutdown(self):
        """Корректное завершение работы агента"""
        logging.info("Shutting down agent...")
        self.running = False
        
        # Останавливаем мониторинг обновлений
        if hasattr(self, 'update_manager'):
            self.update_manager.stop_update_monitoring()
        
        # Останавливаем heartbeat
        if hasattr(self, 'heartbeat_manager'):
            self.heartbeat_manager.force_heartbeat()  # Финальный heartbeat
            self.heartbeat_manager.stop()
        
        # Закрываем текущее приложение
        if self.current_app:
            self.close_application(self.current_app)
        
        # Освобождаем мьютекс
        if hasattr(self, 'mutex_manager'):
            self.mutex_manager.release_mutex()
        
        # Обновляем статус в БД
        if hasattr(self, 'db_manager'):
            self.db_manager.update_agent_status(self.agent_id, "stopped", "Agent shutdown")
            self.db_manager.disconnect()
    
    def run(self):
        """Основной цикл работы агента - WHILE TRUE версия"""
        logging.info(f"Starting Enhanced Database Activity Agent in WHILE TRUE mode")
        logging.info(f"Agent ID: {self.agent_id}")
        logging.info(f"Template ID: {self.template_id}")
        logging.info(f"User ID: {self.config.get('user_id', 'Unknown')}")
        logging.info(f"User: {self.config.get('full_name', 'Unknown')}")
        logging.info(f"Role: {self.config.get('role', 'Unknown')}")
        logging.info(f"Operating System: {self.config.get('operating_system', 'Unknown')}")
        logging.info(f"Department: {self.config.get('department', 'Unknown')}")
        logging.info(f"Location: {self.config.get('location', 'Unknown')}")
        logging.info(f"Running Mode: WHILE TRUE with update support")
        logging.info(f"Heartbeat enabled: {self.heartbeat_manager.enabled}")
        logging.info(f"Heartbeat URL: {self.heartbeat_manager.backend_url}")
        logging.info(f"Update monitoring enabled: True")
        logging.info(f"Mutex directory: {self.mutex_manager.mutex_dir}")
        
        available_apps = self.get_available_applications()
        logging.info(f"Available applications: {list(available_apps.keys())}")
        
        if self.plugin_manager.enabled:
            logging.info(f"Plugin support enabled, loaded plugins: {list(self.plugin_manager.loaded_plugins.keys())}")
        
        # Отправляем первый heartbeat сразу при запуске
        if self.heartbeat_manager.enabled:
            first_heartbeat = self.heartbeat_manager.force_heartbeat()
            logging.info(f"Initial heartbeat sent: {first_heartbeat}")
        
        # Обновляем статус
        self.current_status = "running"
        self.db_manager.update_agent_status(self.agent_id, "running", "Agent started in while true mode")
        
        # Счетчик для периодических неактивных периодов
        activity_counter = 0
        inactive_period_frequency = random.randint(10, 20)  # Каждые 10-20 активностей
        
        try:
            # ОСНОВНОЙ ЦИКЛ WHILE TRUE
            while self.running:
                self.loop_iterations += 1
                
                # Проверка обновлений каждые N итераций
                if self.loop_iterations % 300 == 0:  # Примерно каждые 5 минут
                    if self.update_manager.check_for_updates_sync():
                        logging.info("Update available, will be installed by update manager")
                
                # Проверяем рабочее время
                if not self.is_work_time():
                    if self.current_app:
                        logging.info("Work time ended, closing current application")
                        self.close_application(self.current_app)
                    
                    self.current_status = "idle"
                    self.db_manager.update_agent_status(self.agent_id, "idle", "Outside work hours")
                    logging.debug("Outside work hours, sleeping...")
                    
                    # Спим с возможностью прерывания
                    wait_time = MAIN_LOOP_CONFIG["non_work_check_interval"]
                    for _ in range(wait_time):
                        if not self.running:
                            break
                        time.sleep(1)
                    continue
                
                # Проверяем время перерыва
                if self.is_break_time():
                    if self.current_app:
                        logging.info("Break time, closing current application")
                        self.close_application(self.current_app)
                    
                    self.current_status = "break"
                    self.db_manager.update_agent_status(self.agent_id, "break", "On break")
                    logging.info("Break time, pausing activity...")
                    
                    # Спим во время перерыва с возможностью прерывания
                    wait_time = MAIN_LOOP_CONFIG["break_check_interval"]
                    for _ in range(wait_time):
                        if not self.running:
                            break
                        time.sleep(1)
                    continue
                
                # Периодические неактивные периоды
                activity_counter += 1
                if activity_counter >= inactive_period_frequency:
                    activity_counter = 0
                    inactive_period_frequency = random.randint(10, 20)
                    self.simulate_inactive_period()
                    
                    if not self.running:  # Проверяем после неактивного периода
                        break
                    
                    continue
                
                # Переключение приложений
                if self.should_switch_app():
                    if self.current_app:
                        self.close_application(self.current_app)
                    
                    # Пауза между приложениями
                    pause_time = random.randint(
                        MAIN_LOOP_CONFIG["app_switch_min_pause"],
                        MAIN_LOOP_CONFIG["app_switch_max_pause"]
                    )
                    logging.debug(f"Pausing for {pause_time} seconds between applications")
                    
                    # Спим с возможностью прерывания
                    for _ in range(pause_time):
                        if not self.running:
                            break
                        time.sleep(1)
                    
                    if not self.running:
                        break
                    
                    # Открываем новое приложение
                    next_app = self.get_next_app()
                    if next_app and self.open_application(next_app):
                        self.session_duration = random.randint(
                            MAIN_LOOP_CONFIG["app_session_min"],
                            MAIN_LOOP_CONFIG["app_session_max"]
                        )
                        self.current_status = "active"
                        time.sleep(5)  # Даем приложению время открыться
                
                # Эмулируем активность
                if self.current_app:
                    self.simulate_activity(self.current_app)
                    
                    if not self.running:  # Проверяем после активности
                        break
                    
                    # Пауза между активностями
                    activity_pause = random.randint(
                        MAIN_LOOP_CONFIG["activity_min_pause"],
                        MAIN_LOOP_CONFIG["activity_max_pause"]
                    )
                    
                    # Спим с возможностью прерывания
                    for _ in range(activity_pause):
                        if not self.running:
                            break
                        time.sleep(1)
                else:
                    # Если нет активного приложения, небольшая пауза
                    logging.debug("No active application, waiting...")
                    time.sleep(5)
                
                # Проверяем флаг остановки
                if self.shutdown_requested:
                    logging.info("Shutdown requested, exiting main loop")
                    break
                
        except KeyboardInterrupt:
            logging.info("Agent stopped by user (Ctrl+C)")
        except Exception as e:
            logging.error(f"Agent crashed: {e}")
            self.db_manager.update_agent_status(self.agent_id, "error", f"Agent crashed: {str(e)}")
            raise
        finally:
            self.shutdown()

def main():
    """Главная функция"""
    setup_logging()
    
    # Получаем template_id и user_id из аргументов командной строки
    if len(sys.argv) < 2:
        print("Usage: python agent.py <template_id> [user_id]")
        print("Example: python agent.py 1 USER_123")
        sys.exit(1)
    
    try:
        template_id = int(sys.argv[1])
    except ValueError:
        print("Error: template_id must be an integer")
        sys.exit(1)
    
    user_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Также можно получить из переменных окружения
    if not user_id:
        user_id = os.environ.get('AGENT_USER_ID')
    
    if not user_id:
        print("Error: user_id is required")
        print("Usage: python agent.py <template_id> <user_id>")
        print("Or set AGENT_USER_ID environment variable")
        sys.exit(1)
    
    try:
        # Создаем и запускаем агента
        agent = DatabaseActivityAgent(template_id, user_id)
        
        # Показываем информацию о heartbeat при запуске
        heartbeat_status = agent.get_heartbeat_status()
        if heartbeat_status.get('enabled'):
            logging.info(f"Heartbeat configuration:")
            logging.info(f"  Backend URL: {heartbeat_status.get('backend_url')}")
            logging.info(f"  Interval: {heartbeat_status.get('interval_hours')} hours")
        
        # Запускаем основной цикл while True
        agent.run()
        
    except Exception as e:
        logging.error(f"Failed to start agent: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
