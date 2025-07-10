#!/usr/bin/env python3
"""
Система сборки агентов с полной поддержкой шаблонов
Создает ELF файлы с помощью Nuitka с поддержкой плагинов и расширенных конфигураций
"""

import os
import sys
import json
import shutil
import tempfile
import subprocess
import logging
import psycopg2
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# Конфигурация базы данных
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

class EnhancedAgentBuilder:
    """Расширенный сборщик агентов с полной поддержкой шаблонов"""
    
    def __init__(self):
        self.db_connection = None
        self.build_dir = None
        self.template_dir = Path(__file__).parent
        
        # Создаем необходимые директории
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
            return []
    
    def get_behavior_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """Получение поведенческого шаблона"""
        query = """
        SELECT bt.*, r.name as role_name, r.category as role_category
        FROM behavior_templates bt
        LEFT JOIN roles r ON bt.role_id = r.id
        WHERE bt.id = %s AND bt.is_active = true
        """
        
        results = self.execute_query(query, (template_id,))
        return results[0] if results else None
    
    def get_application_templates(self, app_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Получение шаблонов приложений"""
        if not app_names:
            return {}
        
        placeholders = ','.join(['%s'] * len(app_names))
        query = f"""
        SELECT * FROM applications_template
        WHERE name IN ({placeholders}) AND is_active = true
        """
        
        results = self.execute_query(query, tuple(app_names))
        return {app['name']: app['template_config'] for app in results}
    
    def generate_agent_config(self, template_id: int) -> Optional[Dict[str, Any]]:
        """Генерация конфигурации агента из БД с полной поддержкой"""
        # Получаем поведенческий шаблон
        behavior_template = self.get_behavior_template(template_id)
        if not behavior_template:
            logging.error(f"Behavior template {template_id} not found")
            return None
        
        template_data = behavior_template['template_data']
        
        # Расширенная конфигурация с полной поддержкой шаблонов
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
    
    def generate_builtin_apps_code(self, used_apps: List[str]) -> str:
        """Генерирует код для встроенных приложений"""
        all_builtin_apps = {
            "Visual Studio Code": '''
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
                    "xdotool type 'print(\\"Hello World\\")'",
                    "xdotool key Return", 
                    "xdotool key ctrl+s"
                ]
            }
        ]
    }''',
            "leafpad": '''
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
            },
            {
                "description": "Набор текста",
                "commands": [
                    "xdotool type 'TODO список:'",
                    "xdotool key Return",
                    "xdotool type '- Проверить почту'",
                    "xdotool key Return",
                    "xdotool type '- Обновить документацию'",
                    "xdotool key ctrl+s"
                ]
            }
        ]
    }''',
            "Terminal": '''
    "Terminal": {
        "open": "gnome-terminal || xfce4-terminal || xterm",
        "close": "pkill -f 'gnome-terminal|xfce4-terminal|xterm'",
        "activities": [
            {
                "description": "System information check",
                "commands": [
                    "xdotool type 'uname -a'",
                    "xdotool key Return",
                    "sleep 2",
                    "xdotool type 'lsb_release -a'",
                    "xdotool key Return",
                    "sleep 2"
                ]
            },
            {
                "description": "Check disk usage",
                "commands": [
                    "xdotool type 'df -h'",
                    "xdotool key Return",
                    "sleep 2"
                ]
            }
        ]
    }'''
        }
        
        # Фильтруем только используемые приложения
        filtered_apps = []
        for app_name in used_apps:
            if app_name in all_builtin_apps:
                filtered_apps.append(all_builtin_apps[app_name])
        
        if not filtered_apps:
            return "{}"
        
        return "{\n" + ",\n".join(filtered_apps) + "\n}"
    
    def create_agent_source(self, config: Dict[str, Any], build_dir: Path) -> Path:
        """Создает исходный код агента с полной поддержкой конфигурации"""
        agent_file = build_dir / "compiled_agent.py"
        
        # Генерируем код встроенных приложений
        builtin_apps_code = self.generate_builtin_apps_code(config.get('applications_used', []))
        
        # Генерируем код кастомных приложений
        custom_apps = config.get('custom_applications', {})
        custom_apps_code = json.dumps(custom_apps, indent=2, ensure_ascii=False)
        
        # Создаем исходный код агента с полной поддержкой
        agent_source = f'''#!/usr/bin/env python3
"""
Enhanced Compiled Linux Activity Agent
Generated from template ID: {config.get('template_id', 'unknown')}
Build date: {datetime.now().isoformat()}
Full template compatibility with plugin support
"""

import os
import sys
import time
import json
import subprocess
import logging
import random
import socket
import platform
import importlib.util
from datetime import datetime, timedelta
from pathlib import Path

# Встроенная конфигурация (полная поддержка шаблонов)
AGENT_CONFIG = {json.dumps(config, indent=2, ensure_ascii=False)}

# Встроенные приложения
BUILTIN_APPLICATIONS = {builtin_apps_code}

# Кастомные приложения  
CUSTOM_APPLICATIONS = {custom_apps_code}

def setup_logging(log_level='INFO'):
    """Настраивает систему логирования"""
    log_dir = "/var/log/activity_agent"
    if not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except PermissionError:
            log_dir = "/tmp"
    
    log_file = os.path.join(log_dir, "compiled_agent.log")
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

class PluginManager:
    """Встроенный менеджер плагинов для скомпилированного агента"""
    
    def __init__(self, plugin_config):
        self.enabled = plugin_config.get('enabled', False)
        self.plugins_directory = plugin_config.get('plugins_directory', '/opt/linux_agent/plugins')
        self.auto_load = plugin_config.get('auto_load', True)
        self.fallback_to_builtin = plugin_config.get('fallback_to_builtin', True)
        self.loaded_plugins = {{}}
        
        if self.enabled and self.auto_load:
            self.load_plugins()
    
    def load_plugins(self):
        """Загружает плагины из директории"""
        if not os.path.exists(self.plugins_directory):
            logging.warning(f"Plugins directory {{self.plugins_directory}} not found")
            return
        
        for file_path in Path(self.plugins_directory).glob("*.py"):
            try:
                self.load_plugin(file_path)
            except Exception as e:
                logging.error(f"Failed to load plugin {{file_path}}: {{e}}")
    
    def load_plugin(self, plugin_path):
        """Загружает отдельный плагин"""
        plugin_name = plugin_path.stem
        
        spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, 'get_application_config'):
                self.loaded_plugins[plugin_name] = module
                logging.info(f"Plugin {{plugin_name}} loaded successfully")
    
    def get_plugin_applications(self):
        """Получает приложения от всех загруженных плагинов"""
        plugin_apps = {{}}
        
        for plugin_name, plugin_module in self.loaded_plugins.items():
            try:
                if hasattr(plugin_module, 'get_application_config'):
                    apps = plugin_module.get_application_config()
                    plugin_apps.update(apps)
            except Exception as e:
                logging.error(f"Error getting applications from plugin {{plugin_name}}: {{e}}")
        
        return plugin_apps

class CompiledActivityAgent:
    """Скомпилированный агент активности с полной поддержкой шаблонов"""
    
    def __init__(self):
        self.config = AGENT_CONFIG
        self.current_app = None
        self.app_start_time = None
        self.session_duration = random.randint(300, 900)
        self.start_time = time.time()
        
        # Инициализация менеджера плагинов
        self.plugin_manager = PluginManager(self.config.get('plugin_support', {{}}))
        
        logging.info(f"Enhanced compiled agent started")
        logging.info(f"User: {{self.config.get('full_name', 'unknown')}}")
        logging.info(f"User ID: {{self.config.get('user_id', 'unknown')}}")
        logging.info(f"Template ID: {{self.config.get('template_id', 'unknown')}}")
        logging.info(f"Operating System: {{self.config.get('operating_system', 'unknown')}}")
        logging.info(f"Department: {{self.config.get('department', 'unknown')}}")
        logging.info(f"Plugin support: {{self.plugin_manager.enabled}}")
        logging.info(f"Available applications: {{list(self.get_available_applications().keys())}}")
    
    def get_available_applications(self):
        """Возвращает доступные приложения (встроенные + кастомные + плагины)"""
        apps = {{}}
        
        # 1. Встроенные приложения
        for app_name in self.config.get('applications_used', []):
            if app_name in BUILTIN_APPLICATIONS:
                apps[app_name] = BUILTIN_APPLICATIONS[app_name]
        
        # 2. Кастомные приложения
        for app_name, app_config in CUSTOM_APPLICATIONS.items():
            apps[app_name] = self.convert_custom_app_config(app_config)
        
        # 3. Приложения из плагинов
        if self.plugin_manager.enabled:
            plugin_apps = self.plugin_manager.get_plugin_applications()
            apps.update(plugin_apps)
        
        return apps
    
    def convert_custom_app_config(self, db_config):
        """Конвертирует конфигурацию из БД в формат агента (расширенная версия)"""
        # Поддерживаем несколько форматов
        if 'execution' in db_config:
            execution = db_config['execution']
            activities_db = db_config.get('activities', [])
            
            activities = []
            for activity in activities_db:
                commands = []
                for cmd in activity.get('commands', []):
                    if cmd.get('type') == 'key_combination':
                        commands.append(f"xdotool key {{cmd.get('keys', '')}}")
                    elif cmd.get('type') == 'type_text':
                        text = cmd.get('text', '').replace("'", "\\\\'")
                        commands.append(f"xdotool type '{{text}}'")
                    elif cmd.get('type') == 'wait':
                        commands.append(f"sleep {{cmd.get('time', 1)}}")
                    elif cmd.get('type') == 'mouse_click':
                        x = cmd.get('x', 100)
                        y = cmd.get('y', 100)
                        button = cmd.get('button', 1)
                        commands.append(f"xdotool mousemove {{x}} {{y}} click {{button}}")
                    
                    if 'delay' in cmd and cmd['delay'] > 0:
                        commands.append(f"sleep {{cmd['delay']}}")
                
                activities.append({{
                    "description": activity.get('description', activity.get('name', 'Activity')),
                    "commands": commands
                }})
            
            return {{
                "open": execution.get('open_command', ''),
                "close": execution.get('close_command', ''),
                "activities": activities
            }}
        elif 'open' in db_config:
            return db_config
        else:
            return {{
                "open": db_config.get('open_command', ''),
                "close": db_config.get('close_command', ''),
                "activities": db_config.get('activities', [])
            }}
    
    def run_command(self, command):
        """Выполняет команду"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                logging.debug(f"SUCCESS: {{command}}")
            else:
                logging.warning(f"COMMAND FAILED: {{command}} - {{result.stderr}}")
        except Exception as e:
            logging.error(f"ERROR: {{command}} - {{e}}")
    
    def open_application(self, app_name):
        """Открывает приложение"""
        apps = self.get_available_applications()
        app_config = apps.get(app_name)
        
        if not app_config:
            return False
        
        open_cmd = app_config.get('open')
        if not open_cmd:
            return False
        
        logging.info(f"Opening {{app_name}}...")
        self.run_command(open_cmd)
        
        self.current_app = app_name
        self.app_start_time = time.time()
        
        return True
    
    def close_application(self, app_name):
        """Закрывает приложение"""
        apps = self.get_available_applications()
        app_config = apps.get(app_name)
        
        if app_config and 'close' in app_config:
            logging.info(f"Closing {{app_name}}")
            self.run_command(app_config['close'])
        
        self.current_app = None
        self.app_start_time = None
    
    def simulate_activity(self, app_name):
        """Эмулирует активность в приложении"""
        apps = self.get_available_applications()
        app_config = apps.get(app_name)
        
        if not app_config or 'activities' not in app_config:
            return False
        
        activities = app_config['activities']
        if not activities:
            return False
        
        activity = random.choice(activities)
        activity_name = activity.get('description', 'Unknown Activity')
        
        logging.info(f"Simulating activity in {{app_name}}: {{activity_name}}")
        
        for cmd in activity.get('commands', []):
            self.run_command(cmd)
            time.sleep(random.uniform(1, 3))
        
        return True
    
    def is_break_time(self):
        """Проверяет, время ли перерыва"""
        current_time = datetime.now().time()
        schedule = self.config.get('work_schedule', {{}})
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
        """Выбирает следующее приложение"""
        apps = list(self.get_available_applications().keys())
        if not apps:
            return None
        
        if self.current_app in apps:
            apps.remove(self.current_app)
        
        return random.choice(apps) if apps else None
    
    def is_work_time(self):
        """Проверяет рабочее время"""
        current_time = datetime.now().time()
        schedule = self.config.get('work_schedule', {{}})
        
        start_time = datetime.strptime(schedule.get('start_time', '09:00'), '%H:%M').time()
        end_time = datetime.strptime(schedule.get('end_time', '18:00'), '%H:%M').time()
        
        return start_time <= current_time <= end_time
    
    def run(self):
        """Основной цикл агента с поддержкой перерывов"""
        try:
            while True:
                if not self.is_work_time():
                    if self.current_app:
                        self.close_application(self.current_app)
                    time.sleep(300)
                    continue
                
                # Проверяем время перерыва
                if self.is_break_time():
                    if self.current_app:
                        logging.info("Break time, closing current application")
                        self.close_application(self.current_app)
                    
                    logging.info("Break time, pausing activity...")
                    time.sleep(180)
                    continue
                
                if self.should_switch_app():
                    if self.current_app:
                        self.close_application(self.current_app)
                    
                    time.sleep(random.randint(30, 120))
                    
                    next_app = self.get_next_app()
                    if next_app and self.open_application(next_app):
                        self.session_duration = random.randint(300, 900)
                        time.sleep(5)
                
                if self.current_app:
                    self.simulate_activity(self.current_app)
                
                time.sleep(random.randint(10, 60))
                
        except KeyboardInterrupt:
            logging.info("Agent stopped by user")
            if self.current_app:
                self.close_application(self.current_app)

def main():
    """Главная функция"""
    setup_logging()
    agent = CompiledActivityAgent()
    agent.run()

if __name__ == "__main__":
    main()
'''
        
        with open(agent_file, 'w', encoding='utf-8') as f:
            f.write(agent_source)
        
        logging.info(f"Enhanced agent source created: {agent_file}")
        return agent_file
    
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
            "--include-data-dir=/opt/linux_agent/plugins=plugins",  # Включаем плагины
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
    
    def update_build_record(self, template_id: int, build_status: str, binary_path: str = None, 
                          build_log: str = None, build_time: int = None):
        """Обновляет запись о сборке в БД"""
        agent_query = "SELECT id FROM agents WHERE template_id = %s LIMIT 1"
        agents = self.execute_query(agent_query, (template_id,))
        
        if not agents:
            logging.warning(f"No agent found for template {template_id}")
            return
        
        agent_id = agents[0]['id']
        
        insert_query = """
        INSERT INTO agent_builds (agent_id, build_config, build_status, binary_path, build_log, build_time, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        build_config = {"template_id": template_id, "build_date": datetime.now().isoformat()}
        
        self.execute_query(insert_query, (
            agent_id,
            json.dumps(build_config),
            build_status,
            binary_path,
            build_log,
            build_time,
            datetime.now()
        ))
    
    def build_agent(self, template_id: int, agent_name: str = None) -> Optional[Path]:
        """Полная сборка агента с расширенной поддержкой"""
        if not self.connect_db():
            return None
        
        try:
            build_start_time = time.time()
            
            if not agent_name:
                agent_name = f"enhanced_agent_template_{template_id}_{int(time.time())}"
            
            logging.info(f"Building enhanced agent for template {template_id}")
            
            self.build_dir = Path(tempfile.mkdtemp(prefix="agent_build_", dir=BUILD_CONFIG["temp_dir"]))
            logging.info(f"Build directory: {self.build_dir}")
            
            # Генерируем расширенную конфигурацию из БД
            config = self.generate_agent_config(template_id)
            if not config:
                self.update_build_record(template_id, "failed", build_log="Failed to generate config")
                return None
            
            # Создаем исходный код агента
            source_file = self.create_agent_source(config, self.build_dir)
            
            # Компилируем с Nuitka
            binary_path = self.compile_with_nuitka(source_file, agent_name)
            
            build_time = int(time.time() - build_start_time)
            
            if binary_path and binary_path.exists():
                os.chmod(binary_path, 0o755)
                
                logging.info(f"Enhanced agent built successfully: {binary_path}")
                self.update_build_record(
                    template_id, 
                    "completed", 
                    str(binary_path),
                    "Enhanced build completed successfully",
                    build_time
                )
                return binary_path
            else:
                self.update_build_record(template_id, "failed", build_log="Compilation failed", build_time=build_time)
                return None
                
        except Exception as e:
            logging.error(f"Enhanced build failed: {e}")
            self.update_build_record(template_id, "failed", build_log=str(e))
            return None
        finally:
            if self.build_dir and self.build_dir.exists():
                shutil.rmtree(self.build_dir)
            
            self.disconnect_db()

def main():
    """Главная функция сборщика"""
    if len(sys.argv) < 2:
        print("Usage: python enhanced_agent_builder.py <template_id> [agent_name]")
        sys.exit(1)
    
    try:
        template_id = int(sys.argv[1])
    except ValueError:
        print("Error: template_id must be an integer")
        sys.exit(1)
    
    agent_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    builder = EnhancedAgentBuilder()
    result = builder.build_agent(template_id, agent_name)
    
    if result:
        print(f"Enhanced agent built successfully: {result}")
        sys.exit(0)
    else:
        print("Enhanced agent build failed")
        sys.exit(1)

if __name__ == "__main__":
    main()