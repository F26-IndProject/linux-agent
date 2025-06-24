#!/usr/bin/env python3
"""
Plugin Manager для Linux Activity Agent
Управляет загрузкой и выполнением плагинов приложений
"""

import os
import sys
import json
import importlib.util
import logging
import subprocess
import time
import random
from pathlib import Path
from typing import Dict, List, Optional, Any

class ApplicationPlugin:
    """Базовый класс для плагинов приложений"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.app_info = config.get('app_info', {})
        self.installation = config.get('installation', {})
        self.execution = config.get('execution', {})
        self.activities = config.get('activities', [])
        self.settings = config.get('settings', {})
        self.custom_scripts = config.get('custom_scripts', {})
        
        self.is_running = False
        self.current_activity = None
        self.session_start_time = None
        self.last_activity_time = None
    
    def get_name(self) -> str:
        """Возвращает имя приложения"""
        return self.app_info.get('name', 'Unknown App')
    
    def get_display_name(self) -> str:
        """Возвращает отображаемое имя приложения"""
        return self.app_info.get('display_name', self.get_name())
    
    def is_installed(self) -> bool:
        """Проверяет, установлено ли приложение"""
        check_cmd = self.installation.get('check_command')
        if not check_cmd:
            return True
        
        try:
            result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logging.error(f"Failed to check if {self.get_name()} is installed: {e}")
            return False
    
    def install(self) -> bool:
        """Устанавливает приложение"""
        if self.is_installed():
            logging.info(f"{self.get_name()} is already installed")
            return True
        
        install_commands = self.installation.get('install_commands', [])
        if not install_commands:
            logging.warning(f"No installation commands for {self.get_name()}")
            return False
        
        logging.info(f"Installing {self.get_name()}...")
        
        for cmd in install_commands:
            logging.info(f"Executing: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                logging.error(f"Installation command failed: {cmd} - {result.stderr}")
                return False
            time.sleep(1)
        
        # Выполняем пост-установочные команды
        post_install_commands = self.installation.get('post_install_commands', [])
        for cmd in post_install_commands:
            subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        return self.is_installed()
    
    def run_command(self, command: str) -> bool:
        """Выполняет команду и возвращает результат"""
        try:
            # Устанавливаем переменные окружения если нужно
            env = os.environ.copy()
            env_vars = self.execution.get('environment_vars', {})
            env.update(env_vars)
            
            result = subprocess.run(command, shell=True, env=env, capture_output=True, text=True)
            if result.returncode == 0:
                logging.debug(f"Command executed successfully: {command}")
                return True
            else:
                logging.warning(f"Command failed: {command} - {result.stderr}")
                return False
        except Exception as e:
            logging.error(f"Error executing command: {command} - {e}")
            return False
    
    def execute_activity_command(self, cmd_config: Dict[str, Any]):
        """Выполняет команду активности"""
        cmd_type = cmd_config.get('type', 'command')
        delay = cmd_config.get('delay', 0)
        
        if cmd_type == 'key_combination':
            keys = cmd_config.get('keys', '')
            self.run_command(f"xdotool key {keys}")
        
        elif cmd_type == 'key':
            key = cmd_config.get('key', '')
            self.run_command(f"xdotool key {key}")
        
        elif cmd_type == 'type_text':
            text = cmd_config.get('text', '')
            self.run_command(f"xdotool type '{text}'")
        
        elif cmd_type == 'click':
            x = cmd_config.get('x', 0)
            y = cmd_config.get('y', 0)
            self.run_command(f"xdotool click --window $(xdotool getactivewindow) {x} {y}")
        
        elif cmd_type == 'command':
            command = cmd_config.get('command', '')
            self.run_command(command)
        
        elif cmd_type == 'wait':
            wait_time = cmd_config.get('time', 1)
            time.sleep(wait_time)
        
        if delay > 0:
            time.sleep(delay)
    
    def open_application(self) -> bool:
        """Открывает приложение"""
        if self.is_running:
            return True
        
        # Выполняем скрипты перед запуском
        before_start_scripts = self.custom_scripts.get('before_start', [])
        for script in before_start_scripts:
            self.run_command(script)
        
        open_cmd = self.execution.get('open_command')
        if not open_cmd:
            logging.error(f"No open command defined for {self.get_name()}")
            return False
        
        logging.info(f"Opening {self.get_name()}")
        success = self.run_command(open_cmd)
        
        if success:
            # Ждем запуска приложения
            startup_delay = self.execution.get('startup_delay', 3)
            time.sleep(startup_delay)
            
            self.is_running = True
            self.session_start_time = time.time()
            self.last_activity_time = time.time()
            
            logging.info(f"{self.get_name()} opened successfully")
            return True
        
        return False
    
    def close_application(self) -> bool:
        """Закрывает приложение"""
        if not self.is_running:
            return True
        
        close_cmd = self.execution.get('close_command')
        if close_cmd:
            logging.info(f"Closing {self.get_name()}")
            self.run_command(close_cmd)
        
        # Выполняем скрипты после закрытия
        after_close_scripts = self.custom_scripts.get('after_close', [])
        for script in after_close_scripts:
            self.run_command(script)
        
        self.is_running = False
        self.session_start_time = None
        self.last_activity_time = None
        self.current_activity = None
        
        return True
    
    def get_weighted_activity(self) -> Optional[Dict[str, Any]]:
        """Возвращает случайную активность с учетом весов"""
        if not self.activities:
            return None
        
        # Создаем список активностей с учетом весов
        weighted_activities = []
        for activity in self.activities:
            weight = activity.get('weight', 10)
            weighted_activities.extend([activity] * weight)
        
        return random.choice(weighted_activities) if weighted_activities else None
    
    def can_execute_activity(self, activity: Dict[str, Any]) -> bool:
        """Проверяет, можно ли выполнить активность"""
        conditions = activity.get('conditions', {})
        
        # Проверяем время дня
        time_of_day = conditions.get('time_of_day')
        if time_of_day:
            current_hour = time.localtime().tm_hour
            if current_hour < 12 and 'morning' not in time_of_day:
                return False
            elif 12 <= current_hour < 18 and 'afternoon' not in time_of_day:
                return False
            elif current_hour >= 18 and 'evening' not in time_of_day:
                return False
        
        # Проверяем наличие необходимых файлов
        required_files = conditions.get('required_files', [])
        for file_path in required_files:
            if not os.path.exists(file_path):
                return False
        
        return True
    
    def execute_activity(self) -> bool:
        """Выполняет случайную активность"""
        if not self.is_running:
            return False
        
        activity = self.get_weighted_activity()
        if not activity:
            return False
        
        if not self.can_execute_activity(activity):
            return False
        
        activity_name = activity.get('name', 'Unknown Activity')
        logging.info(f"Executing activity in {self.get_name()}: {activity_name}")
        
        self.current_activity = activity
        commands = activity.get('commands', [])
        
        for cmd_config in commands:
            self.execute_activity_command(cmd_config)
        
        self.last_activity_time = time.time()
        
        # Случайная пауза после активности (как в оригинальном коде)
        min_duration = activity.get('min_duration', 10)   # 10 секунд минимум
        max_duration = activity.get('max_duration', 60)   # 60 секунд максимум
        pause_time = random.randint(min_duration, max_duration)
        time.sleep(pause_time)
        
        return True
    
    def should_continue_session(self) -> bool:
        """Определяет, нужно ли продолжать сессию с приложением"""
        if not self.is_running or not self.session_start_time:
            return False
        
        session_duration = time.time() - self.session_start_time
        min_duration = self.settings.get('session_duration', {}).get('min', 300)  # 5 минут
        max_duration = self.settings.get('session_duration', {}).get('max', 900)  # 15 минут
        
        # Используем те же значения что и в оригинальном агенте
        target_duration = random.randint(min_duration, max_duration)
        
        return session_duration < target_duration
    
    def get_usage_probability(self) -> float:
        """Возвращает вероятность использования приложения"""
        return self.settings.get('usage_probability', 0.5)
    
    def can_use_during_work_hours(self) -> bool:
        """Проверяет, можно ли использовать приложение в рабочее время"""
        return self.settings.get('work_hours_only', True)


class PluginManager:
    """Менеджер плагинов приложений"""
    
    def __init__(self, plugins_dir: str = "/opt/linux_agent/plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.plugins: Dict[str, ApplicationPlugin] = {}
        self.ensure_plugins_dir()
    
    def ensure_plugins_dir(self):
        """Создает директорию для плагинов"""
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем поддиректории
        (self.plugins_dir / "configs").mkdir(exist_ok=True)
        (self.plugins_dir / "scripts").mkdir(exist_ok=True)
    
    def load_plugin_from_json(self, json_path: str) -> Optional[ApplicationPlugin]:
        """Загружает плагин из JSON файла"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Проверяем, есть ли связанный Python файл
            json_file = Path(json_path)
            py_file = json_file.with_suffix('.py')
            
            if py_file.exists():
                # Загружаем кастомный класс из Python файла
                return self.load_custom_plugin(str(py_file), config)
            else:
                # Используем базовый класс
                return ApplicationPlugin(config)
        
        except Exception as e:
            logging.error(f"Failed to load plugin from {json_path}: {e}")
            return None
    
    def load_custom_plugin(self, py_path: str, config: Dict[str, Any]) -> Optional[ApplicationPlugin]:
        """Загружает кастомный плагин из Python файла"""
        try:
            spec = importlib.util.spec_from_file_location("custom_plugin", py_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Ищем класс, наследующий от ApplicationPlugin
            for name in dir(module):
                obj = getattr(module, name)
                if (isinstance(obj, type) and 
                    issubclass(obj, ApplicationPlugin) and 
                    obj != ApplicationPlugin):
                    return obj(config)
            
            logging.warning(f"No ApplicationPlugin subclass found in {py_path}")
            return ApplicationPlugin(config)
        
        except Exception as e:
            logging.error(f"Failed to load custom plugin from {py_path}: {e}")
            return ApplicationPlugin(config)
    
    def scan_and_load_plugins(self):
        """Сканирует директорию и загружает все плагины"""
        configs_dir = self.plugins_dir / "configs"
        
        if not configs_dir.exists():
            logging.warning(f"Plugins configs directory not found: {configs_dir}")
            return
        
        for json_file in configs_dir.glob("*.json"):
            plugin = self.load_plugin_from_json(str(json_file))
            if plugin:
                app_name = plugin.get_name()
                self.plugins[app_name] = plugin
                logging.info(f"Loaded plugin: {app_name}")
    
    def get_plugin(self, app_name: str) -> Optional[ApplicationPlugin]:
        """Возвращает плагин по имени приложения"""
        return self.plugins.get(app_name)
    
    def get_all_plugins(self) -> Dict[str, ApplicationPlugin]:
        """Возвращает все загруженные плагины"""
        return self.plugins.copy()
    
    def get_available_apps(self) -> List[str]:
        """Возвращает список доступных приложений"""
        return list(self.plugins.keys())
    
    def install_plugin_dependencies(self, app_name: str) -> bool:
        """Устанавливает зависимости для плагина"""
        plugin = self.get_plugin(app_name)
        if not plugin:
            return False
        
        return plugin.install()
    
    def create_plugin_template(self, app_name: str) -> str:
        """Создает шаблон плагина для нового приложения"""
        template_path = self.plugins_dir / "configs" / f"{app_name.lower().replace(' ', '_')}.json"
        
        template = {
            "app_info": {
                "name": app_name,
                "display_name": app_name,
                "category": "custom",
                "description": f"Custom plugin for {app_name}",
                "version": "1.0.0",
                "author": "User",
                "tags": ["custom"]
            },
            "installation": {
                "check_command": f"{app_name.lower()} --version",
                "install_commands": [
                    f"echo 'Please configure installation commands for {app_name}'"
                ]
            },
            "execution": {
                "open_command": app_name.lower(),
                "close_command": f"pkill -f {app_name.lower()}",
                "startup_delay": 3
            },
            "activities": [
                {
                    "id": "basic_activity",
                    "name": "Basic Activity",
                    "description": f"Basic activity in {app_name}",
                    "weight": 10,
                    "commands": [
                        {
                            "type": "wait",
                            "time": 2
                        }
                    ]
                }
            ],
            "settings": {
                "session_duration": {"min": 300, "max": 900},
                "usage_probability": 0.5
            }
        }
        
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                json.dump(template, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Plugin template created: {template_path}")
            return str(template_path)
        
        except Exception as e:
            logging.error(f"Failed to create plugin template: {e}")
            return ""
    
    def reload_plugins(self):
        """Перезагружает все плагины"""
        self.plugins.clear()
        self.scan_and_load_plugins()
        logging.info("Plugins reloaded")
    
    def validate_plugin_config(self, config_path: str) -> List[str]:
        """Валидирует конфигурацию плагина и возвращает список ошибок"""
        errors = []
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Проверяем обязательные поля
            required_fields = {
                'app_info': ['name'],
                'execution': ['open_command'],
                'activities': []
            }
            
            for section, fields in required_fields.items():
                if section not in config:
                    errors.append(f"Missing required section: {section}")
                    continue
                
                for field in fields:
                    if field not in config[section]:
                        errors.append(f"Missing required field: {section}.{field}")
            
            # Проверяем активности
            activities = config.get('activities', [])
            if not activities:
                errors.append("No activities defined")
            else:
                for i, activity in enumerate(activities):
                    if 'commands' not in activity:
                        errors.append(f"Activity {i}: missing 'commands' field")
        
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON format: {e}")
        except Exception as e:
            errors.append(f"Error reading config file: {e}")
        
        return errors