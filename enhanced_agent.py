#!/usr/bin/env python3
"""
Enhanced Unified Linux Activity Agent with Plugin Support
Поддерживает загрузку и выполнение плагинов приложений
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
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем путь к плагинам в sys.path
PLUGIN_DIR = "/opt/linux_agent/plugins"
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

try:
    from plugin_manager import PluginManager, ApplicationPlugin
except ImportError:
    logging.error("Plugin manager not found. Please ensure plugin_manager.py is in the plugins directory.")
    PluginManager = None
    ApplicationPlugin = None

# Пути для конфигурационных файлов
DEFAULT_CONFIG_DIR = "/opt/linux_agent/configs"
USER_CONFIG_DIR = os.path.expanduser("~/.config/activity_agent")
SYSTEM_CONFIG_DIR = "/etc/activity_agent"

# Дефолтная конфигурация пользователя
DEFAULT_USER_CONFIG = {
    "user_id": "USR0012345",
    "username": "john_doe",
    "full_name": "John Doe", 
    "role": "Junior Developer",
    "work_schedule": {
        "start_time": "09:00",
        "end_time": "18:00",
        "breaks": [
            {
                "start": "13:00",
                "duration_minutes": 60
            }
        ]
    },
    "operating_system": "Linux Ubuntu 22.04",
    "applications_used": [
        "Visual Studio Code",
        "Google Chrome", 
        "Slack",
        "Docker Desktop"
    ],
    "activity_pattern": "Regular office hours with lunch break",
    "department": "Development",
    "location": "Headquarters",
    "plugin_support": {
        "enabled": True,
        "plugins_directory": "/opt/linux_agent/plugins",
        "auto_load": True,
        "fallback_to_builtin": True
    }
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

class ConfigManager:
    """Менеджер конфигураций для работы с внешними файлами"""
    
    def __init__(self):
        self.config_paths = [
            DEFAULT_CONFIG_DIR,
            SYSTEM_CONFIG_DIR,
            USER_CONFIG_DIR
        ]
        self.ensure_config_dirs()
    
    def ensure_config_dirs(self):
        """Создает необходимые директории для конфигураций"""
        for path in self.config_paths:
            try:
                os.makedirs(path, exist_ok=True)
            except PermissionError:
                logging.warning(f"Cannot create config directory: {path}")
    
    def find_config_file(self, config_name):
        """Ищет файл конфигурации в доступных директориях"""
        possible_names = [
            f"{config_name}.json",
            f"{config_name}_config.json",
            f"user_{config_name}.json"
        ]
        
        for config_dir in self.config_paths:
            for name in possible_names:
                config_path = os.path.join(config_dir, name)
                if os.path.exists(config_path):
                    logging.info(f"Found config file: {config_path}")
                    return config_path
        
        return None
    
    def load_config(self, config_name=None):
        """Загружает конфигурацию из файла или возвращает дефолтную"""
        if config_name:
            config_file = self.find_config_file(config_name)
            if config_file:
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                    logging.info(f"Loaded config from: {config_file}")
                    return self.validate_config(config)
                except Exception as e:
                    logging.error(f"Failed to load config {config_file}: {e}")
                    return None
        
        # Пытаемся найти любой доступный конфигурационный файл
        for config_dir in self.config_paths:
            if os.path.exists(config_dir):
                for file in os.listdir(config_dir):
                    if file.endswith('.json') and not file.startswith('plugin_'):
                        config_path = os.path.join(config_dir, file)
                        try:
                            with open(config_path, 'r', encoding='utf-8') as f:
                                config = json.load(f)
                            logging.info(f"Auto-loaded config from: {config_path}")
                            return self.validate_config(config)
                        except Exception as e:
                            logging.warning(f"Failed to load {config_path}: {e}")
                            continue
        
        # Если ничего не найдено, используем дефолтную конфигурацию
        logging.info("Using default configuration")
        return DEFAULT_USER_CONFIG
    
    def validate_config(self, config):
        """Валидация конфигурации и добавление недостающих полей"""
        validated_config = DEFAULT_USER_CONFIG.copy()
        validated_config.update(config)
        
        # Проверяем обязательные поля
        required_fields = ['username', 'work_schedule', 'applications_used']
        for field in required_fields:
            if field not in validated_config:
                logging.warning(f"Missing required field '{field}' in config, using default")
        
        return validated_config

class ActivityUtils:
    """Утилиты для работы с активностью"""
    
    @staticmethod
    def get_application_commands(app_name, custom_commands=None):
        """Возвращает команды для работы с приложением (legacy support)"""
        # Сначала проверяем кастомные команды из конфигурации
        if custom_commands and app_name in custom_commands:
            return custom_commands[app_name]
        
        # Затем используем встроенные команды для обратной совместимости
        app_configs = {
            "Visual Studio Code": {
                "open": "code",
                "close": "pkill -f code",
                "activities": [
                    {
                        "description": "Opening a file",
                        "commands": [
                            "xdotool key ctrl+o",
                            "sleep 2",
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
            "Slack": {
                "open": "slack",
                "close": "pkill -f slack",
                "activities": [
                    {
                        "description": "Checking messages",
                        "commands": [
                            "xdotool key ctrl+k",
                            "sleep 1",
                            "xdotool type 'general'",
                            "xdotool key Return"
                        ]
                    }
                ]
            },
            "Google Chrome": {
                "open": "google-chrome",
                "close": "pkill -f chrome",
                "activities": [
                    {
                        "description": "Browsing documentation",
                        "commands": [
                            "xdotool key ctrl+l",
                            "xdotool type 'https://docs.python.org'",
                            "xdotool key Return"
                        ]
                    }
                ]
            }
        }
        return app_configs.get(app_name, {})
    
    @staticmethod
    def is_work_time(current_time, work_schedule):
        """Проверяет, находится ли текущее время в рабочих часах"""
        current_time_only = current_time.time()
        
        start_time = datetime.strptime(work_schedule['start_time'], '%H:%M').time()
        end_time = datetime.strptime(work_schedule['end_time'], '%H:%M').time()
        
        return start_time <= current_time_only <= end_time
    
    @staticmethod
    def is_break_time(current_time, work_schedule):
        """Проверяет, находится ли текущее время в обеденном перерыве"""
        current_time_only = current_time.time()
        
        breaks = work_schedule.get('breaks', [])
        for break_info in breaks:
            break_start = datetime.strptime(break_info['start'], '%H:%M').time()
            break_duration = break_info['duration_minutes']
            
            # Вычисляем время окончания перерыва
            break_start_dt = datetime.combine(current_time.date(), break_start)
            break_end_dt = break_start_dt + timedelta(minutes=break_duration)
            break_end = break_end_dt.time()
            
            if break_start <= current_time_only <= break_end:
                return True
        
        return False
    
    @staticmethod
    def get_break_end_time(current_time, work_schedule):
        """Возвращает время окончания текущего перерыва"""
        current_time_only = current_time.time()
        
        breaks = work_schedule.get('breaks', [])
        for break_info in breaks:
            break_start = datetime.strptime(break_info['start'], '%H:%M').time()
            break_duration = break_info['duration_minutes']
            
            # Вычисляем время окончания перерыва
            break_start_dt = datetime.combine(current_time.date(), break_start)
            break_end_dt = break_start_dt + timedelta(minutes=break_duration)
            break_end = break_end_dt.time()
            
            # Проверяем, находимся ли мы в этом перерыве
            if break_start <= current_time_only <= break_end:
                return break_end_dt
        
        return None

class EnhancedActivityAgent:
    """Улучшенный агент активности с поддержкой плагинов"""
    
    def __init__(self, config):
        self.config = config
        self.current_app = None
        self.current_plugin = None
        self.app_start_time = None
        self.session_duration = random.randint(300, 900)
        self.utils = ActivityUtils()
        self.custom_commands = config.get('custom_commands', {})
        
        # Инициализация менеджера плагинов
        self.plugin_manager = None
        self.plugins_enabled = config.get('plugin_support', {}).get('enabled', True)
        
        if self.plugins_enabled and PluginManager:
            plugins_dir = config.get('plugin_support', {}).get('plugins_directory', PLUGIN_DIR)
            self.plugin_manager = PluginManager(plugins_dir)
            self.plugin_manager.scan_and_load_plugins()
            logging.info(f"Plugin manager initialized with {len(self.plugin_manager.get_all_plugins())} plugins")
        else:
            logging.info("Plugin support disabled or not available, using legacy mode")
    
    def run_command(self, command):
        """Выполняет команду и логирует результат"""
        start_time = time.time()
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            duration = time.time() - start_time
            if result.returncode == 0:
                logging.debug(f"SUCCESS: {command} (duration: {duration:.2f}s)")
            else:
                logging.warning(f"COMMAND FAILED: {command} - {result.stderr}")
        except Exception as e:
            duration = time.time() - start_time
            logging.error(f"ERROR: {command} (duration: {duration:.2f}s) - {e}")
    
    def get_available_applications(self):
        """Возвращает список доступных приложений (плагины + встроенные)"""
        apps = []
        
        # Добавляем приложения из плагинов
        if self.plugin_manager:
            apps.extend(self.plugin_manager.get_available_apps())
        
        # Добавляем встроенные приложения если включен fallback
        fallback_enabled = self.config.get('plugin_support', {}).get('fallback_to_builtin', True)
        if fallback_enabled:
            builtin_apps = self.config.get('applications_used', [])
            for app in builtin_apps:
                if app not in apps:
                    apps.append(app)
        
        return apps
    
    def open_application(self, app_name):
        """Открывает приложение (плагин или встроенное)"""
        # Сначала пытаемся использовать плагин
        if self.plugin_manager:
            plugin = self.plugin_manager.get_plugin(app_name)
            if plugin:
                logging.info(f"Opening {app_name} using plugin")
                success = plugin.open_application()
                if success:
                    self.current_app = app_name
                    self.current_plugin = plugin
                    self.app_start_time = time.time()
                    return True
        
        # Fallback к встроенному способу
        commands = self.utils.get_application_commands(app_name, self.custom_commands)
        if commands and 'open' in commands:
            logging.info(f"Opening {app_name} using legacy method")
            self.run_command(commands['open'])
            self.current_app = app_name
            self.current_plugin = None
            self.app_start_time = time.time()
            return True
        
        logging.warning(f"No way to open application: {app_name}")
        return False
    
    def close_application(self, app_name):
        """Закрывает приложение"""
        # Используем плагин если доступен
        if self.current_plugin:
            logging.info(f"Closing {app_name} using plugin")
            self.current_plugin.close_application()
        else:
            # Fallback к встроенному способу
            commands = self.utils.get_application_commands(app_name, self.custom_commands)
            if commands and 'close' in commands:
                logging.info(f"Closing {app_name} using legacy method")
                self.run_command(commands['close'])
        
        self.current_app = None
        self.current_plugin = None
        self.app_start_time = None
    
    def simulate_activity(self, app_name):
        """Эмулирует активность в приложении"""
        # Используем плагин если доступен
        if self.current_plugin:
            return self.current_plugin.execute_activity()
        
        # Fallback к встроенному способу
        commands = self.utils.get_application_commands(app_name, self.custom_commands)
        if commands and 'activities' in commands:
            activity = random.choice(commands['activities'])
            logging.info(f"Simulating legacy activity in {app_name}: {activity['description']}")
            
            for cmd in activity['commands']:
                self.run_command(cmd)
                time.sleep(random.uniform(1, 3))
            return True
        
        return False
    
    def should_switch_app(self):
        """Определяет, нужно ли переключиться на другое приложение"""
        if not self.current_app or not self.app_start_time:
            return True
        
        # Используем логику плагина если доступна
        if self.current_plugin:
            return not self.current_plugin.should_continue_session()
        
        # Fallback к базовой логике
        elapsed = time.time() - self.app_start_time
        return elapsed >= self.session_duration
    
    def get_next_app(self):
        """Выбирает следующее приложение для работы"""
        available_apps = self.get_available_applications()
        if not available_apps:
            return None
        
        # Фильтруем приложения по времени работы
        current_time = datetime.now()
        is_work_time = self.utils.is_work_time(current_time, self.config['work_schedule'])
        is_break_time = self.utils.is_break_time(current_time, self.config['work_schedule'])
        
        suitable_apps = []
        for app_name in available_apps:
            if app_name == self.current_app:
                continue  # Исключаем текущее приложение
            
            # Проверяем через плагин если доступен
            if self.plugin_manager:
                plugin = self.plugin_manager.get_plugin(app_name)
                if plugin:
                    # Проверяем настройки времени работы плагина
                    if is_work_time and plugin.can_use_during_work_hours():
                        suitable_apps.append((app_name, plugin.get_usage_probability()))
                    elif is_break_time and plugin.can_use_during_break():
                        suitable_apps.append((app_name, plugin.get_usage_probability()))
                    continue
            
            # Fallback: все приложения подходят
            suitable_apps.append((app_name, 0.5))
        
        if not suitable_apps:
            suitable_apps = [(app, 0.5) for app in available_apps if app != self.current_app]
        
        if not suitable_apps:
            return None
        
        # Выбираем с учетом вероятностей
        total_probability = sum(prob for _, prob in suitable_apps)
        if total_probability == 0:
            return random.choice([app for app, _ in suitable_apps])
        
        rand_val = random.random() * total_probability
        cumulative = 0
        for app_name, probability in suitable_apps:
            cumulative += probability
            if rand_val <= cumulative:
                return app_name
        
        return suitable_apps[-1][0]  # Fallback
    
    def get_system_statistics(self):
        """Возвращает статистику работы системы"""
        stats = {
            'agent_uptime': time.time() - getattr(self, 'start_time', time.time()),
            'current_app': self.current_app,
            'plugin_mode': self.current_plugin is not None,
            'total_plugins': len(self.plugin_manager.get_all_plugins()) if self.plugin_manager else 0,
            'available_apps': len(self.get_available_applications())
        }
        
        if self.current_plugin:
            plugin_stats = getattr(self.current_plugin, 'get_session_statistics', lambda: {})()
            stats.update({'current_plugin_stats': plugin_stats})
        
        return stats
    
    def run(self):
        """Основной цикл работы агента"""
        self.start_time = time.time()
        
        logging.info(f"Starting Enhanced Activity Agent for user: {self.config.get('username', 'unknown')}")
        logging.info(f"Role: {self.config.get('role', 'unknown')}")
        logging.info(f"Work schedule: {self.config.get('work_schedule', {})}")
        logging.info(f"Available applications: {self.get_available_applications()}")
        logging.info(f"Plugin support: {'enabled' if self.plugins_enabled else 'disabled'}")
        
        while True:
            current_time = datetime.now()
            
            # Проверяем, рабочее ли время
            if not self.utils.is_work_time(current_time, self.config['work_schedule']):
                if self.current_app:
                    logging.info("Work time ended, closing current application")
                    self.close_application(self.current_app)
                
                logging.info("Outside work hours, sleeping...")
                time.sleep(300)
                continue
            
            # Проверяем, не время ли перерыва
            if self.utils.is_break_time(current_time, self.config['work_schedule']):
                # Во время перерыва ВСЯ активность прекращается
                if self.current_app:
                    logging.info("Break time started, closing current application")
                    self.close_application(self.current_app)
                
                # Рассчитываем время окончания перерыва
                break_end_time = self.utils.get_break_end_time(current_time, self.config['work_schedule'])
                if break_end_time:
                    time_until_break_ends = (break_end_time - current_time).total_seconds()
                    if time_until_break_ends > 0:
                        logging.info(f"Break time - sleeping for {int(time_until_break_ends/60)} minutes until {break_end_time.strftime('%H:%M')}")
                        time.sleep(min(time_until_break_ends, 300))  # Максимум 5 минут за раз
                    continue
                else:
                    # Fallback: спим 5 минут если не удалось рассчитать
                    logging.info("Break time - no activity allowed, sleeping...")
                    time.sleep(300)
                    continue
            
            # Определяем, нужно ли переключить приложение
            if self.should_switch_app():
                # Закрываем текущее приложение
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
                    time.sleep(5)  # Даем время приложению запуститься
            
            # Эмулируем активность в текущем приложении
            if self.current_app:
                self.simulate_activity(self.current_app)
            
            # Пауза между активностями
            activity_pause = random.randint(10, 60)
            time.sleep(activity_pause)
            
            # Периодически выводим статистику
            if hasattr(self, 'last_stats_time'):
                if time.time() - self.last_stats_time > 3600:  # Каждый час
                    stats = self.get_system_statistics()
                    logging.info(f"System statistics: {stats}")
                    self.last_stats_time = time.time()
            else:
                self.last_stats_time = time.time()

def create_service_file():
    """Создает файл сервиса для systemd"""
    service_content = """[Unit]
Description=Enhanced Linux Activity Agent with Plugin Support
After=network.target graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/local/bin/activity_agent --daemon
WorkingDirectory=/opt/linux_agent
Restart=always
RestartSec=10
User=root
Group=root

# Переменные окружения для GUI приложений
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/user/.Xauthority
Environment=PYTHONPATH=/opt/linux_agent/plugins

# Логирование
StandardOutput=journal
StandardError=journal
SyslogIdentifier=activity-agent

# Ограничения ресурсов
MemoryMax=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
"""
    
    try:
        with open('/etc/systemd/system/activity-agent.service', 'w') as f:
            f.write(service_content)
        logging.info("Service file created successfully")
        return True
    except Exception as e:
        logging.error(f"Failed to create service file: {e}")
        return False

def install_plugin_system():
    """Устанавливает систему плагинов"""
    try:
        # Создаем структуру директорий для плагинов
        plugin_base_dir = Path("/opt/linux_agent/plugins")
        plugin_base_dir.mkdir(parents=True, exist_ok=True)
        
        configs_dir = plugin_base_dir / "configs"
        scripts_dir = plugin_base_dir / "scripts"
        configs_dir.mkdir(exist_ok=True)
        scripts_dir.mkdir(exist_ok=True)
        
        logging.info(f"Plugin directories created: {plugin_base_dir}")
        
        # Создаем файл __init__.py для Python пакета
        init_file = plugin_base_dir / "__init__.py"
        init_file.write_text("# Plugin package for Linux Activity Agent\n")
        
        # Копируем plugin_manager.py если он не существует
        plugin_manager_file = plugin_base_dir / "plugin_manager.py"
        if not plugin_manager_file.exists():
            # Здесь должен быть код для копирования plugin_manager.py
            logging.info("plugin_manager.py should be placed in the plugins directory")
        
        # Создаем пример конфигурации для VS Code
        vscode_config = {
            "app_info": {
                "name": "Visual Studio Code",
                "display_name": "VS Code",
                "category": "development",
                "description": "Visual Studio Code editor",
                "version": "1.0.0",
                "author": "System",
                "tags": ["editor", "development", "coding"]
            },
            "installation": {
                "check_command": "code --version",
                "install_commands": [
                    "wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg",
                    "sudo install -o root -g root -m 644 packages.microsoft.gpg /etc/apt/trusted.gpg.d/",
                    "sudo sh -c 'echo \"deb [arch=amd64,arm64,armhf signed-by=/etc/apt/trusted.gpg.d/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main\" > /etc/apt/sources.list.d/vscode.list'",
                    "sudo apt update",
                    "sudo apt install -y code"
                ]
            },
            "execution": {
                "open_command": "code",
                "close_command": "pkill -f code",
                "startup_delay": 3
            },
            "activities": [
                {
                    "id": "open_file",
                    "name": "Open File",
                    "description": "Opens a file in VS Code",
                    "weight": 30,
                    "commands": [
                        {"type": "key_combination", "keys": "ctrl+o", "delay": 1},
                        {"type": "type_text", "text": "main.py", "delay": 0.5},
                        {"type": "key", "key": "Return", "delay": 2}
                    ]
                },
                {
                    "id": "edit_code",
                    "name": "Edit Code",
                    "description": "Types some code",
                    "weight": 50,
                    "commands": [
                        {"type": "type_text", "text": "print('Hello, World!')", "delay": 1},
                        {"type": "key", "key": "Return", "delay": 0.5},
                        {"type": "key_combination", "keys": "ctrl+s", "delay": 0.5}
                    ]
                }
            ],
            "settings": {
                "session_duration": {"min": 300, "max": 1800},
                "usage_probability": 0.8
            }
        }
        
        vscode_config_file = configs_dir / "vscode.json"
        with open(vscode_config_file, 'w', encoding='utf-8') as f:
            json.dump(vscode_config, f, indent=2, ensure_ascii=False)
        
        logging.info("VS Code plugin configuration created")
        
        return True
        
    except Exception as e:
        logging.error(f"Failed to install plugin system: {e}")
        return False

def setup_autostart():
    """Настраивает автозапуск агента"""
    try:
        # Создаем рабочую директорию
        work_dir = '/opt/linux_agent'
        os.makedirs(work_dir, exist_ok=True)
        
        # Устанавливаем систему плагинов
        install_plugin_system()
        
        # Копируем исполняемый файл в системную директорию
        current_path = os.path.abspath(sys.argv[0])
        target_path = '/usr/local/bin/activity_agent'
        
        if current_path != target_path:
            shutil.copy2(current_path, target_path)
            os.chmod(target_path, 0o755)
            logging.info(f"Agent copied to {target_path}")
        
        # Также копируем в рабочую директорию
        work_agent_path = os.path.join(work_dir, 'activity_agent')
        if current_path != work_agent_path:
            shutil.copy2(current_path, work_agent_path)
            os.chmod(work_agent_path, 0o755)
            logging.info(f"Agent also copied to {work_agent_path}")
        
        # Создаем файл сервиса
        if create_service_file():
            # Перезагружаем systemd и включаем сервис
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            subprocess.run(['systemctl', 'enable', 'activity-agent.service'], check=True)
            logging.info("Service enabled for autostart")
            return True
        
    except Exception as e:
        logging.error(f"Failed to setup autostart: {e}")
        return False

def install_dependencies():
    """Устанавливает базовые зависимости"""
    dependencies = ["xdotool", "python3-pip"]
    
    try:
        # Обновляем пакеты
        subprocess.run(['apt', 'update'], check=True)
        
        # Устанавливаем зависимости
        for dep in dependencies:
            logging.info(f"Installing {dep}...")
            result = subprocess.run(['apt', 'install', '-y', dep], capture_output=True, text=True)
            if result.returncode != 0:
                logging.warning(f"Failed to install {dep}: {result.stderr}")
        
        logging.info("Dependencies installation completed")
        return True
        
    except Exception as e:
        logging.error(f"Failed to install dependencies: {e}")
        return False

def main():
    """Главная функция"""
    setup_logging()
    logging.info("Starting Enhanced Unified Linux Activity Agent")
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        if sys.argv[1] == '--install':
            # Режим установки
            logging.info("Installation mode activated")
            
            if os.geteuid() != 0:
                logging.error("Root privileges required for installation")
                sys.exit(1)
            
            # Устанавливаем зависимости
            install_dependencies()
            
            # Настраиваем автозапуск
            setup_autostart()
            
            logging.info("Installation completed. You can now:")
            logging.info("1. Add plugin configurations to /opt/linux_agent/plugins/configs/")
            logging.info("2. Start the agent: sudo systemctl start activity-agent")
            logging.info("3. Check status: sudo systemctl status activity-agent")
            return
            
        elif sys.argv[1] == '--daemon':
            # Режим демона
            logging.info("Daemon mode activated")
            
        elif sys.argv[1] == '--create-plugin':
            # Создание шаблона плагина
            if len(sys.argv) < 3:
                print("Usage: activity_agent --create-plugin <app_name>")
                sys.exit(1)
            
            app_name = sys.argv[2]
            if PluginManager:
                manager = PluginManager()
                template_path = manager.create_plugin_template(app_name)
                if template_path:
                    print(f"Plugin template created: {template_path}")
                    print("Edit the configuration file and restart the agent.")
                else:
                    print("Failed to create plugin template")
            return
            
        elif sys.argv[1] == '--list-plugins':
            # Список плагинов
            if PluginManager:
                manager = PluginManager()
                manager.scan_and_load_plugins()
                plugins = manager.get_all_plugins()
                if plugins:
                    print("Available plugins:")
                    for name, plugin in plugins.items():
                        print(f"  - {name}: {plugin.app_info.get('description', 'No description')}")
                else:
                    print("No plugins found")
            return
            
        elif sys.argv[1] == '--help':
            print("Enhanced Linux Activity Agent")
            print("Usage:")
            print("  activity_agent --install              Install the agent")
            print("  activity_agent --daemon               Run as daemon")
            print("  activity_agent --create-plugin <name> Create plugin template")
            print("  activity_agent --list-plugins         List available plugins")
            print("  activity_agent --help                 Show this help")
            return
    
    # Загружаем конфигурацию
    config_manager = ConfigManager()
    config = config_manager.load_config()
    
    # Создаем и запускаем агента
    agent = EnhancedActivityAgent(config)
    
    try:
        agent.run()
    except KeyboardInterrupt:
        logging.info("Agent stopped by user")
        if agent.current_app:
            agent.close_application(agent.current_app)
    except Exception as e:
        logging.error(f"Agent crashed: {e}")
        if agent.current_app:
            agent.close_application(agent.current_app)

if __name__ == "__main__":
    main()