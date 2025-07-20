#!/usr/bin/env python3
"""
Билдер для создания обновляемых агентов с поддержкой мьютексов
Версия для работы с агентом в режиме while True
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

# Конфигурация базы данных - получаем из переменных окружения или используем значения по умолчанию
DATABASE_CONFIG = {
    "host": os.environ.get("DB_HOST", "postgres"),
    "port": int(os.environ.get("DB_PORT", "5432")),
    "database": os.environ.get("DB_NAME", "lisa_dev"),
    "user": os.environ.get("DB_USER", "lisa"),
    "password": os.environ.get("DB_PASSWORD", "pass")
}

# Также поддерживаем DATABASE_URL
if "DATABASE_URL" in os.environ:
    # Парсим DATABASE_URL формата postgresql://user:pass@host:port/db
    import urllib.parse
    result = urllib.parse.urlparse(os.environ["DATABASE_URL"])
    DATABASE_CONFIG = {
        "host": result.hostname,
        "port": result.port or 5432,
        "database": result.path[1:],  # убираем первый слеш
        "user": result.username,
        "password": result.password
    }

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)

class UpdatableAgentBuilder:
    """Билдер для создания обновляемых агентов"""
    
    def __init__(self):
        self.db_connection = None
        
        # Логируем конфигурацию БД (без пароля)
        db_config_log = DATABASE_CONFIG.copy()
        db_config_log["password"] = "***"
        logging.info(f"Database config: {db_config_log}")
    
    def connect_db(self) -> bool:
        """Подключение к базе данных"""
        try:
            self.db_connection = psycopg2.connect(**DATABASE_CONFIG)
            logging.info("Connected to database")
            return True
        except Exception as e:
            logging.error(f"Database connection failed: {e}")
            logging.error(f"Trying to connect to: {DATABASE_CONFIG['host']}:{DATABASE_CONFIG['port']}")
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
        """Получение поведенческого шаблона из БД"""
        query = """
        SELECT bt.*, r.name as role_name, r.category as role_category
        FROM behavior_templates bt
        LEFT JOIN roles r ON bt.role_id = r.id
        WHERE bt.id = %s AND bt.is_active = true
        """
        
        results = self.execute_query(query, (template_id,))
        if results:
            template = results[0]
            if isinstance(template['template_data'], str):
                template['template_data'] = json.loads(template['template_data'])
            return template
        return None
    
    def get_agent_source_code(self) -> str:
        """Получает исходный код агента"""
        # Приоритеты поиска исходного файла:
        source_paths = [
            Path("modified_updatable_agent.py"),
            Path("complete_updatable_agent.py"),
            Path(__file__).parent / "modified_updatable_agent.py",
            Path(__file__).parent / "complete_updatable_agent.py",
            Path("/app/linux-agent/modified_updatable_agent.py"),
            Path("/app/linux-agent/complete_updatable_agent.py")
        ]
        
        source_found = None
        for source_path in source_paths:
            if source_path.exists():
                source_found = source_path
                logging.info(f"Found agent source at: {source_path}")
                break
        
        if not source_found:
            logging.error("Agent source file not found in any location")
            logging.error(f"Searched paths: {[str(p) for p in source_paths]}")
            raise Exception("Agent source file not found")
        
        # Читаем содержимое файла
        with open(source_found, 'r', encoding='utf-8') as f:
            return f.read()
    
    def compile_with_nuitka(self, source_code: str, output_name: str, build_dir: str) -> Optional[Path]:
        """Компилирует агент с помощью Nuitka - как в старом билдере"""
        
        # Создаем файл с исходным кодом в build_dir
        source_file_path = os.path.join(build_dir, "agent_source.py")
        with open(source_file_path, 'w', encoding='utf-8') as f:
            f.write(source_code)
        
        logging.info(f"Created source file: {source_file_path}")
        
        # Создаем команду для Nuitka - точно как в старом билдере
        nuitka_cmd = [
            "python", "-m", "nuitka", 
            "--standalone", 
            "--onefile",
            f"--output-filename={output_name}",
            f"--output-dir={build_dir}",
            "--remove-output", 
            "--assume-yes-for-downloads",
            source_file_path
        ]
        
        logging.info(f"Starting Nuitka compilation: {' '.join(nuitka_cmd)}")
        
        try:
            result = subprocess.run(
                nuitka_cmd, 
                capture_output=True, 
                text=True, 
                cwd=build_dir  # Запускаем из build_dir
            )
            
            if result.returncode != 0:
                logging.error(f"Nuitka compilation failed. Stderr: {result.stderr}")
                raise RuntimeError("Agent compilation failed.")
            
            logging.info("Agent binary compiled successfully.")
            
            # Ожидаемый путь к файлу
            output_path = os.path.join(build_dir, f"{output_name}.bin")
            
            if os.path.exists(output_path):
                return Path(output_path)
            else:
                logging.error(f"Expected output file not found: {output_path}")
                return None
                
        except subprocess.TimeoutExpired:
            logging.error("Compilation timed out")
            return None
        except Exception as e:
            logging.error(f"Compilation error: {e}")
            return None
    
    def get_agent_version_hash(self, source_code: str) -> str:
        """Получает хеш версии агента из исходного кода"""
        try:
            return hashlib.md5(source_code.encode('utf-8')).hexdigest()[:16]
        except Exception:
            return "unknown"
    
    def update_build_record(self, template_id: int, build_status: str, binary_path: str = None, 
                          build_log: str = None, build_time: int = None, version_hash: str = None):
        """Обновляет запись о сборке в БД"""
        try:
            # Проверяем/создаем агента
            agent_query = """
            SELECT id FROM agents WHERE template_id = %s 
            ORDER BY created_at DESC LIMIT 1
            """
            agents = self.execute_query(agent_query, (template_id,))
            
            if not agents:
                # Создаем агента если его нет
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
                "version": "2.1.0-updatable-while-true",
                "version_hash": version_hash,
                "running_mode": "while_true"
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
        except Exception as e:
            logging.error(f"Failed to update build record: {e}")

def get_db_connection():
    """
    Establishes a connection to the database using the DATABASE_URL environment variable.
    """
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logging.error("DATABASE_URL environment variable not set.")
        raise ValueError("DATABASE_URL is not set")

    try:
        conn = psycopg2.connect(database_url)
        logging.info("Successfully connected to the database.")
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Database connection failed: {e}")
        raise

def fetch_template_from_db(conn, template_id: int):
    """
    Fetches the agent source code or configuration from the database.
    """
    logging.info(f"Fetching agent template with ID: {template_id}")
    
    # Создаем билдер для получения шаблона
    builder = UpdatableAgentBuilder()
    builder.db_connection = conn
    
    template = builder.get_behavior_template(template_id)
    if not template:
        raise ValueError(f"Template with ID {template_id} not found.")
    
    # Получаем исходный код агента
    agent_source_code = builder.get_agent_source_code()
    
    return agent_source_code

def build_agent_binary(source_code: str, output_name: str, build_dir: str):
    """
    Compiles the Python source code into a standalone binary using Nuitka.
    """
    source_file_path = os.path.join(build_dir, "agent_source.py")
    with open(source_file_path, "w") as f:
        f.write(source_code)
    
    logging.info(f"Compiling agent binary '{output_name}'...")
    nuitka_cmd = [
        "python", "-m", "nuitka", "--standalone", "--onefile",
        f"--output-filename={output_name}", f"--output-dir={build_dir}",
        "--remove-output", "--assume-yes-for-downloads",
        source_file_path
    ]

    result = subprocess.run(nuitka_cmd, capture_output=True, text=True, cwd=build_dir)
    if result.returncode != 0:
        logging.error(f"Nuitka compilation failed. Stderr: {result.stderr}")
        raise RuntimeError("Agent compilation failed.")
    
    logging.info("Agent binary compiled successfully.")

def main():
    """
    Main execution flow of the builder - совместимый со старым интерфейсом.
    """
    if len(sys.argv) < 4 or sys.argv[1] != 'build':
        print("Usage: python fixed_updatable_agent_builder.py build <template_id> --name <output_name>")
        sys.exit(1)

    template_id = int(sys.argv[2])
    
    # Ищем --name параметр
    output_name = None
    for i, arg in enumerate(sys.argv):
        if arg == '--name' and i + 1 < len(sys.argv):
            output_name = sys.argv[i + 1]
            break
    
    if not output_name:
        print("Error: --name parameter is required")
        sys.exit(1)
    
    # Используем текущую директорию как build_dir (как в старом билдере)
    build_dir = os.getcwd() 

    conn = None
    try:
        # 1. Connect to the database using the environment variable
        conn = get_db_connection()
        
        # 2. Fetch the agent template code from the database
        agent_code = fetch_template_from_db(conn, template_id)
        
        # 3. Compile the code into a binary
        build_agent_binary(agent_code, output_name, build_dir)

        # 4. (Optional) Log success back to the database using builder
        builder = UpdatableAgentBuilder()
        builder.db_connection = conn
        version_hash = builder.get_agent_version_hash(agent_code)
        builder.update_build_record(template_id, "completed", 
                                   os.path.join(build_dir, f"{output_name}.bin"),
                                   "Agent compilation completed successfully",
                                   None, version_hash)

        logging.info("Agent build process completed successfully.")

    except Exception as e:
        logging.error(f"An error occurred during the build process: {e}")
        # (Optional) Log failure to the database
        if conn:
            try:
                builder = UpdatableAgentBuilder()
                builder.db_connection = conn
                builder.update_build_record(template_id, "failed", build_log=str(e))
            except:
                pass
        sys.exit(1) # Exit with a non-zero code to indicate failure
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()
