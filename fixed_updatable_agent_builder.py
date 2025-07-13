#!/usr/bin/env python3
"""
Билдер для создания обновляемых агентов с поддержкой мьютексов
Исправленная версия для работы с полным агентом
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
import logging
import psycopg2
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Конфигурация базы данных (совместимость с существующей БД)
DATABASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "lisa_dev",
    "user": "lisa",
    "password": "pass"
}

# Настройки сборки
BUILD_CONFIG = {
    "output_dir": "/opt/agent_builds",
    "temp_dir": "/tmp/agent_builds",
    "nuitka_path": "/usr/local/bin/python -m nuitka",
    "python_version": "3.8"
}

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

class UpdatableAgentBuilder:
    """Билдер для создания обновляемых агентов"""
    
    def __init__(self):
        self.db_connection = None
        self.build_dir = None
        
        os.makedirs(BUILD_CONFIG["output_dir"], exist_ok=True)
        os.makedirs(BUILD_CONFIG["temp_dir"], exist_ok=True)
    
    def connect_db(self) -> bool:
        """Подключение к базе данных"""
        try:
            self.db_connection = psycopg2.connect(**DATABASE_CONFIG)
            logging.info("Connected to database")
            return True
        except Exception as e:
            logging.error(f"Database connection failed: {e}")
            return False
    
    def disconnect_db(self):
        """Отключение от базы данных"""
        if self.db_connection:
            self.db_connection.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Выполнение SQL запроса"""
        try:
            with self.db_connection.cursor() as cursor:
                cursor.execute(query, params)
                
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    self.db_connection.commit()
                    return []
        except Exception as e:
            logging.error(f"Database query failed: {e}")
            if self.db_connection:
                self.db_connection.rollback()
            return []
    
    def get_behavior_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """Получение поведенческого шаблона из существующей БД"""
        query = """
        SELECT bt.*, r.name as role_name, r.category as role_category
        FROM behavior_templates bt
        LEFT JOIN roles r ON bt.role_id = r.id
        WHERE bt.id = %s AND bt.is_active = true
        """
        
        results = self.execute_query(query, (template_id,))
        if results:
            template = results[0]
            # Совместимость с вашей схемой - template_data уже JSON
            if isinstance(template['template_data'], str):
                template['template_data'] = json.loads(template['template_data'])
            return template
        return None
    
    def get_application_templates(self, app_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Получение шаблонов приложений из вашей БД"""
        if not app_names:
            return {}
        
        placeholders = ','.join(['%s'] * len(app_names))
        query = f"""
        SELECT * FROM applications_template
        WHERE name IN ({placeholders}) AND is_active = true
        """
        
        results = self.execute_query(query, tuple(app_names))
        return_dict = {}
        for app in results:
            # Совместимость с вашей схемой
            config = app['template_config']
            if isinstance(config, str):
                config = json.loads(config)
            return_dict[app['name']] = config
        return return_dict
    
    def generate_agent_config(self, template_id: int) -> Optional[Dict[str, Any]]:
        """Генерация конфигурации агента из БД"""
        behavior_template = self.get_behavior_template(template_id)
        if not behavior_template:
            logging.error(f"Behavior template {template_id} not found")
            return None
        
        template_data = behavior_template['template_data']
        
        config = {
            "template_id": template_id,
            "user_id": template_data.get('user_id', str(template_id)),
            "username": template_data.get('username', 'agent_user'),
            "full_name": template_data.get('full_name', 'Agent User'),
            "role": behavior_template.get('role_name', template_data.get('role', 'User')),
            "role_category": behavior_template.get('role_category', 'General'),
            "work_schedule": template_data.get('work_schedule', {
                "start_time": "09:00",
                "end_time": "18:00",
                "breaks": [{"start": "12:00", "duration_minutes": 60}]
            }),
            "operating_system": template_data.get('operating_system', 
                                               behavior_template.get('os_type', 'Linux')),
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
        
        # Получаем кастомные приложения
        custom_apps = template_data.get('custom_applications', [])
        if custom_apps:
            app_configs = self.get_application_templates(custom_apps)
            config['custom_applications'] = app_configs
        
        return config
    
    def copy_agent_source(self, build_dir: Path) -> Path:
        """Копирует исходный код полного агента"""
        agent_file = build_dir / "complete_updatable_agent.py"
        
        # Путь к исходному файлу агента
        source_agent_path = Path("complete_updatable_agent.py")
        
        if not source_agent_path.exists():
            # Если файл не найден локально, создаем его из кода
            logging.warning("Agent source file not found locally, creating from embedded code")
            return self.create_agent_from_embedded(build_dir)
        
        # Копируем исходный файл
        shutil.copy2(source_agent_path, agent_file)
        
        logging.info(f"Agent source copied to: {agent_file}")
        return agent_file
    
    def create_agent_from_embedded(self, build_dir: Path) -> Path:
        """Создает файл агента если исходный не найден"""
        agent_file = build_dir / "complete_updatable_agent.py"
        
        # Здесь должен быть полный код вашего агента
        # Для краткости я не буду вставлять весь код, но в реальности нужно вставить весь код из complete_updatable_agent.py
        logging.error("Cannot create agent from embedded code - source file required")
        raise Exception("Agent source file not found")
    
    def compile_with_nuitka(self, source_file: Path, output_name: str) -> Optional[Path]:
        """Компилирует агент с помощью Nuitka"""
        output_path = Path(BUILD_CONFIG["output_dir"]) / f"{output_name}.bin"
        
        nuitka_cmd = [
            "python", "-m", "nuitka",
            "--standalone",
            "--onefile",
            f"--output-filename={output_name}.bin",
            f"--output-dir={BUILD_CONFIG['output_dir']}",
            "--remove-output",
            "--assume-yes-for-downloads",
            "--python-flag=no_site",
            "--python-flag=no_docstrings",
            "--include-module=psycopg2",
            "--include-module=psutil",
            "--include-module=fcntl",
            "--include-module=signal", 
            "--include-module=hashlib",
            "--include-module=urllib",
            "--include-module=urllib.request",
            "--include-module=urllib.parse",
            "--include-module=urllib.error",
            "--include-module=threading",
            "--include-module=importlib",
            "--include-module=importlib.util",
            str(source_file)
        ]
        
        logging.info(f"Starting Nuitka compilation: {' '.join(nuitka_cmd)}")
        
        try:
            result = subprocess.run(
                nuitka_cmd,
                capture_output=True,
                text=True,
                timeout=1800
            )
            
            if result.returncode == 0:
                logging.info(f"Compilation successful: {output_path}")
                return output_path
            else:
                logging.error(f"Compilation failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logging.error("Compilation timed out")
            return None
        except Exception as e:
            logging.error(f"Compilation error: {e}")
            return None
    
    def get_agent_version_hash(self, source_file: Path) -> str:
        """Получает хеш версии агента из исходного файла"""
        try:
            with open(source_file, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()[:16]
        except Exception:
            return "unknown"
    
    def update_build_record(self, template_id: int, build_status: str, binary_path: str = None, 
                          build_log: str = None, build_time: int = None, version_hash: str = None):
        """Обновляет запись о сборке в существующей БД"""
        # Совместимость с вашей схемой agents
        agent_query = """
        SELECT id FROM agents WHERE template_id = %s 
        ORDER BY created_at DESC LIMIT 1
        """
        agents = self.execute_query(agent_query, (template_id,))
        
        if not agents:
            # Создаем агента если его нет (совместимость с вашей схемой)
            create_agent_query = """
            INSERT INTO agents (agent_id, name, status, os_type, template_id, role_id)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """
            agent_id_str = f"TEMPLATE_{template_id}_{int(time.time())}"
            
            # Получаем role_id из шаблона
            template_query = "SELECT role_id FROM behavior_templates WHERE id = %s"
            template_result = self.execute_query(template_query, (template_id,))
            role_id = template_result[0]['role_id'] if template_result and template_result[0]['role_id'] else 1
            
            results = self.execute_query(create_agent_query, (
                agent_id_str, f"Agent for template {template_id}", "created", "Linux", template_id, role_id
            ))
            agent_id = results[0]['id'] if results else None
        else:
            agent_id = agents[0]['id']
        
        if not agent_id:
            logging.error("Failed to get or create agent ID")
            return
        
        # Проверяем, существует ли таблица agent_builds
        check_table_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'agent_builds'
        );
        """
        table_exists = self.execute_query(check_table_query)
        
        if not table_exists or not table_exists[0]['exists']:
            # Создаем таблицу если её нет
            create_table_query = """
            CREATE TABLE IF NOT EXISTS agent_builds (
                id SERIAL PRIMARY KEY,
                agent_id INTEGER REFERENCES agents(id),
                build_config JSONB,
                build_status VARCHAR(50),
                binary_path TEXT,
                build_log TEXT,
                build_time INTEGER,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
            """
            self.execute_query(create_table_query)
            logging.info("Created agent_builds table")
        
        insert_query = """
        INSERT INTO agent_builds (agent_id, build_config, build_status, binary_path, build_log, build_time, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        build_config = {
            "template_id": template_id, 
            "build_date": datetime.now().isoformat(),
            "updatable_agent": True,
            "mutex_support": True,
            "version": "2.1.0-updatable",
            "version_hash": version_hash
        }
        
        self.execute_query(insert_query, (
            agent_id,
            json.dumps(build_config),
            build_status,
            binary_path,
            build_log,
            build_time,
            datetime.now()
        ))
    
    def build_updatable_agent(self, template_id: int, agent_name: str = None) -> Optional[Path]:
        """Полная сборка обновляемого агента"""
        if not self.connect_db():
            return None
        
        try:
            build_start_time = time.time()
            
            if not agent_name:
                agent_name = f"updatable_agent_template_{template_id}_{int(time.time())}"
            
            logging.info(f"Building updatable agent for template {template_id}")
            
            self.build_dir = Path(tempfile.mkdtemp(prefix="updatable_agent_build_", dir=BUILD_CONFIG["temp_dir"]))
            logging.info(f"Build directory: {self.build_dir}")
            
            # Генерируем конфигурацию из БД
            config = self.generate_agent_config(template_id)
            if not config:
                self.update_build_record(template_id, "failed", build_log="Failed to generate config")
                return None
            
            # Копируем исходный код агента
            source_file = self.copy_agent_source(self.build_dir)
            
            # Получаем версию агента
            version_hash = self.get_agent_version_hash(source_file)
            
            # Компилируем с Nuitka
            binary_path = self.compile_with_nuitka(source_file, agent_name)
            
            build_time = int(time.time() - build_start_time)
            
            if binary_path and binary_path.exists():
                os.chmod(binary_path, 0o755)
                
                logging.info(f"Updatable agent built successfully: {binary_path}")
                self.update_build_record(
                    template_id, 
                    "completed", 
                    str(binary_path),
                    "Updatable agent build completed successfully",
                    build_time,
                    version_hash
                )
                return binary_path
            else:
                self.update_build_record(template_id, "failed", build_log="Compilation failed", build_time=build_time)
                return None
                
        except Exception as e:
            logging.error(f"Updatable agent build failed: {e}")
            self.update_build_record(template_id, "failed", build_log=str(e))
            return None
        finally:
            if self.build_dir and self.build_dir.exists():
                shutil.rmtree(self.build_dir)
            
            self.disconnect_db()

class AgentDeploymentManager:
    """Менеджер развертывания и управления агентами"""
    
    def __init__(self):
        self.db_connection = None
    
    def connect_db(self) -> bool:
        """Подключение к базе данных"""
        try:
            self.db_connection = psycopg2.connect(**DATABASE_CONFIG)
            return True
        except Exception as e:
            logging.error(f"Database connection failed: {e}")
            return False
    
    def disconnect_db(self):
        """Отключение от базы данных"""
        if self.db_connection:
            self.db_connection.close()
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Выполнение SQL запроса"""
        try:
            with self.db_connection.cursor() as cursor:
                cursor.execute(query, params)
                
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    self.db_connection.commit()
                    return []
        except Exception as e:
            logging.error(f"Database query failed: {e}")
            return []
    
    def list_available_builds(self, template_id: int = None) -> List[Dict[str, Any]]:
        """Список доступных сборок агентов"""
        if not self.connect_db():
            return []
        
        try:
            # Проверяем существование таблицы
            check_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'agent_builds'
            );
            """
            exists = self.execute_query(check_query)
            
            if not exists or not exists[0]['exists']:
                logging.info("Table agent_builds does not exist")
                return []
            
            if template_id:
                query = """
                SELECT ab.*, a.template_id, bt.name as template_name
                FROM agent_builds ab
                JOIN agents a ON ab.agent_id = a.id
                JOIN behavior_templates bt ON a.template_id = bt.id
                WHERE a.template_id = %s AND ab.build_status = 'completed'
                ORDER BY ab.created_at DESC
                """
                results = self.execute_query(query, (template_id,))
            else:
                query = """
                SELECT ab.*, a.template_id, bt.name as template_name
                FROM agent_builds ab
                JOIN agents a ON ab.agent_id = a.id
                JOIN behavior_templates bt ON a.template_id = bt.id
                WHERE ab.build_status = 'completed'
                ORDER BY ab.created_at DESC
                """
                results = self.execute_query(query)
            
            return results
        finally:
            self.disconnect_db()
    
    def deploy_agent(self, template_id: int, user_id: str, target_path: str = None) -> bool:
        """Развертывает агент на целевой системе"""
        if not self.connect_db():
            return False
        
        try:
            # Проверяем существование таблицы agent_builds
            check_query = """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'agent_builds'
            );
            """
            exists = self.execute_query(check_query)
            
            if not exists or not exists[0]['exists']:
                logging.error("Table agent_builds does not exist. Please build an agent first.")
                return False
            
            # Получаем последнюю успешную сборку
            query = """
            SELECT ab.binary_path, ab.build_config
            FROM agent_builds ab
            JOIN agents a ON ab.agent_id = a.id
            WHERE a.template_id = %s AND ab.build_status = 'completed'
            ORDER BY ab.created_at DESC
            LIMIT 1
            """
            
            results = self.execute_query(query, (template_id,))
            
            if not results:
                logging.error(f"No completed builds found for template {template_id}")
                return False
            
            binary_path = results[0]['binary_path']
            
            if not Path(binary_path).exists():
                logging.error(f"Binary file not found: {binary_path}")
                return False
            
            # Определяем целевой путь
            if not target_path:
                target_path = f"/opt/agents/agent_template_{template_id}_user_{user_id}.bin"
            
            # Создаем директорию если нужно
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            # Копируем бинарный файл
            shutil.copy2(binary_path, target_path)
            os.chmod(target_path, 0o755)
            
            logging.info(f"Agent deployed to: {target_path}")
            
            # Создаем systemd service файл
            self._create_systemd_service(template_id, user_id, target_path)
            
            return True
            
        except Exception as e:
            logging.error(f"Deployment failed: {e}")
            return False
        finally:
            self.disconnect_db()
    
    def _create_systemd_service(self, template_id: int, user_id: str, binary_path: str):
        """Создает systemd service для агента"""
        service_name = f"activity-agent-template-{template_id}-user-{user_id}"
        service_file = f"/etc/systemd/system/{service_name}.service"
        
        service_content = f"""[Unit]
Description=Activity Agent for Template {template_id} User {user_id}
After=network.target
Wants=network.target

[Service]
Type=simple
ExecStart={binary_path} {template_id} {user_id}
Restart=on-failure
RestartSec=10
User=root
Group=root
Environment=PYTHONUNBUFFERED=1
Environment=AGENT_USER_ID={user_id}

# Мьютекс директория
RuntimeDirectory=activity_agents
RuntimeDirectoryMode=0755

# Логи
StandardOutput=journal
StandardError=journal
SyslogIdentifier={service_name}

[Install]
WantedBy=multi-user.target
"""
        
        try:
            with open(service_file, 'w') as f:
                f.write(service_content)
            
            # Перезагружаем systemd
            subprocess.run(["systemctl", "daemon-reload"], check=True)
            
            logging.info(f"Systemd service created: {service_name}")
            print(f"Service created: {service_name}")
            print(f"To start: sudo systemctl start {service_name}")
            print(f"To enable: sudo systemctl enable {service_name}")
            print(f"To check status: sudo systemctl status {service_name}")
            
        except Exception as e:
            logging.warning(f"Failed to create systemd service: {e}")
    
    def start_agent(self, template_id: int, user_id: str) -> bool:
        """Запускает агент через systemd"""
        service_name = f"activity-agent-template-{template_id}-user-{user_id}"
        
        try:
            subprocess.run(["systemctl", "start", service_name], check=True)
            logging.info(f"Agent started: {service_name}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to start agent: {e}")
            return False
    
    def stop_agent(self, template_id: int, user_id: str) -> bool:
        """Останавливает агент через systemd"""
        service_name = f"activity-agent-template-{template_id}-user-{user_id}"
        
        try:
            subprocess.run(["systemctl", "stop", service_name], check=True)
            logging.info(f"Agent stopped: {service_name}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to stop agent: {e}")
            return False
    
    def get_running_agents(self) -> List[Dict[str, Any]]:
        """Получает список запущенных агентов"""
        try:
            import psutil
        except ImportError:
            logging.error("psutil not installed")
            return []
        
        agents = []
        
        # Проверяем основную директорию мьютексов
        mutex_dirs = [
            Path("/var/run/activity_agents"),
            Path("/tmp/activity_agents")
        ]
        
        for mutex_dir in mutex_dirs:
            if not mutex_dir.exists():
                continue
            
            for mutex_file in mutex_dir.glob("agent_user_*.lock"):
                try:
                    with open(mutex_file, 'r') as f:
                        mutex_info = json.load(f)
                        pid = mutex_info.get('pid')
                        
                        if pid and psutil.pid_exists(pid):
                            process = psutil.Process(pid)
                            mutex_info['process_info'] = {
                                'cpu_percent': process.cpu_percent(),
                                'memory_percent': process.memory_percent(),
                                'status': process.status()
                            }
                            agents.append(mutex_info)
                except Exception as e:
                    logging.warning(f"Error reading mutex file {mutex_file}: {e}")
        
        return agents

def main():
    """Главная функция"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Updatable Agent Builder and Deployment Manager')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Команда сборки
    build_parser = subparsers.add_parser('build', help='Build updatable agent')
    build_parser.add_argument('template_id', type=int, help='Template ID')
    build_parser.add_argument('--name', help='Agent name')
    build_parser.add_argument('--source', help='Path to agent source file', default='complete_updatable_agent.py')
    
    # Команда развертывания
    deploy_parser = subparsers.add_parser('deploy', help='Deploy agent')
    deploy_parser.add_argument('template_id', type=int, help='Template ID')
    deploy_parser.add_argument('user_id', help='User ID')
    deploy_parser.add_argument('--target', help='Target path')
    
    # Команды управления
    start_parser = subparsers.add_parser('start', help='Start agent')
    start_parser.add_argument('template_id', type=int, help='Template ID')
    start_parser.add_argument('user_id', help='User ID')
    
    stop_parser = subparsers.add_parser('stop', help='Stop agent')
    stop_parser.add_argument('template_id', type=int, help='Template ID')
    stop_parser.add_argument('user_id', help='User ID')
    
    # Команды информации
    list_builds_parser = subparsers.add_parser('list-builds', help='List available builds')
    list_builds_parser.add_argument('--template', type=int, help='Filter by template ID')
    
    subparsers.add_parser('list-running', help='List running agents')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'build':
        builder = UpdatableAgentBuilder()
        
        # Если указан путь к исходному файлу, копируем его
        if args.source and args.source != 'complete_updatable_agent.py':
            source_path = Path(args.source)
            if source_path.exists():
                target_path = Path('complete_updatable_agent.py')
                shutil.copy2(source_path, target_path)
                logging.info(f"Copied source from {source_path} to {target_path}")
        
        result = builder.build_updatable_agent(args.template_id, args.name)
        
        if result:
            print(f"✅ Updatable agent built successfully: {result}")
            print("Features:")
            print("  - Automatic updates via database")
            print("  - Mutex-based user isolation")
            print("  - Graceful shutdown and restart")
            print("  - Database configuration support")
            print("  - Heartbeat monitoring")
            print("  - Plugin system support")
            sys.exit(0)
        else:
            print("❌ Agent build failed")
            sys.exit(1)
    
    elif args.command == 'deploy':
        manager = AgentDeploymentManager()
        success = manager.deploy_agent(args.template_id, args.user_id, args.target)
        
        if success:
            print(f"✅ Agent deployed successfully")
            sys.exit(0)
        else:
            print("❌ Deployment failed")
            sys.exit(1)
    
    elif args.command == 'start':
        manager = AgentDeploymentManager()
        success = manager.start_agent(args.template_id, args.user_id)
        
        if success:
            print(f"✅ Agent started successfully")
        else:
            print("❌ Failed to start agent")
    
    elif args.command == 'stop':
        manager = AgentDeploymentManager()
        success = manager.stop_agent(args.template_id, args.user_id)
        
        if success:
            print(f"✅ Agent stopped successfully")
        else:
            print("❌ Failed to stop agent")
    
    elif args.command == 'list-builds':
        manager = AgentDeploymentManager()
        template_filter = getattr(args, 'template', None)
        builds = manager.list_available_builds(template_filter)
        
        if builds:
            print(f"\n📦 Available builds ({len(builds)}):")
            print("=" * 80)
            for build in builds:
                config = build.get('build_config', {})
                if isinstance(config, str):
                    config = json.loads(config)
                
                print(f"Template ID: {build['template_id']}")
                print(f"Template Name: {build['template_name']}")
                print(f"Binary Path: {build['binary_path']}")
                print(f"Version Hash: {config.get('version_hash', 'unknown')}")
                print(f"Build Date: {build['created_at']}")
                print(f"Build Time: {build.get('build_time', 'N/A')}s")
                print("-" * 40)
        else:
            print("📭 No builds found")
    
    elif args.command == 'list-running':
        manager = AgentDeploymentManager()
        agents = manager.get_running_agents()
        
        if agents:
            print(f"\n🤖 Running agents ({len(agents)}):")
            print("=" * 80)
            for agent in agents:
                process_info = agent.get('process_info', {})
                print(f"User ID: {agent['user_id']}")
                print(f"Template ID: {agent['template_id']}")
                print(f"PID: {agent['pid']}")
                print(f"Version: {agent.get('version', 'unknown')}")
                print(f"Started: {agent['started_at']}")
                print(f"CPU: {process_info.get('cpu_percent', 'N/A')}%")
                print(f"Memory: {process_info.get('memory_percent', 'N/A')}%")
                print(f"Status: {process_info.get('status', 'N/A')}")
                print("-" * 40)
        else:
            print("📭 No running agents found")

if __name__ == "__main__":
    main()
