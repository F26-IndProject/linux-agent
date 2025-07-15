-- =====================================================
-- СОЗДАНИЕ РОЛЕЙ
-- =====================================================

-- Базовые роли для разных типов пользователей
INSERT INTO roles (name, category) VALUES 
    ('Developer', 'IT'),
    ('QA Engineer', 'IT'),
    ('DevOps Engineer', 'IT'),
    ('System Administrator', 'IT'),
    ('Data Analyst', 'Analytics'),
    ('Manager', 'Management'),
    ('Designer', 'Creative'),
    ('Content Writer', 'Marketing'),
    ('Accountant', 'Finance'),
    ('HR Specialist', 'HR');

-- =====================================================
-- ШАБЛОНЫ ПОЛЬЗОВАТЕЛЕЙ (behavior_templates)
-- =====================================================

-- 1. Шаблон для разработчика Python
INSERT INTO behavior_templates (name, template_data, role_id, os_type) VALUES (
    'Python Developer Template',
    '{
        "user_id": "DEV_001",
        "username": "alex_python_dev",
        "full_name": "Alex Johnson",
        "role": "Python Developer",
        "department": "Backend Development",
        "location": "Remote",
        "work_schedule": {
            "start_time": "09:00",
            "end_time": "18:00",
            "breaks": [
                {"start": "12:00", "duration_minutes": 60},
                {"start": "15:30", "duration_minutes": 15}
            ]
        },
        "applications_used": [
            "Terminal",
            "Visual Studio Code",
            "Firefox",
            "PyCharm"
        ],
        "custom_applications": [
            "PyCharm",
            "Postman",
            "DBeaver"
        ],
        "activity_pattern": "Intensive coding with regular breaks",
        "plugin_support": {
            "enabled": true,
            "plugins_directory": "/opt/linux_agent/plugins",
            "auto_load": true,
            "fallback_to_builtin": true
        }
    }'::jsonb,
    (SELECT id FROM roles WHERE name = 'Developer'),
    'Linux'
);

-- 2. Шаблон для QA инженера
INSERT INTO behavior_templates (name, template_data, role_id, os_type) VALUES (
    'QA Engineer Template',
    '{
        "user_id": "QA_001",
        "username": "maria_qa",
        "full_name": "Maria Rodriguez",
        "role": "Senior QA Engineer",
        "department": "Quality Assurance",
        "location": "Office",
        "work_schedule": {
            "start_time": "10:00",
            "end_time": "19:00",
            "breaks": [
                {"start": "13:00", "duration_minutes": 45},
                {"start": "16:00", "duration_minutes": 15}
            ]
        },
        "applications_used": [
            "Terminal",
            "Firefox",
            "Chrome",
            "Jira"
        ],
        "custom_applications": [
            "Chrome",
            "Jira",
            "Selenium IDE",
            "Postman"
        ],
        "activity_pattern": "Testing cycles with documentation",
        "plugin_support": {
            "enabled": false,
            "plugins_directory": "/opt/linux_agent/plugins",
            "auto_load": false,
            "fallback_to_builtin": true
        }
    }'::jsonb,
    (SELECT id FROM roles WHERE name = 'QA Engineer'),
    'Linux'
);

-- 3. Шаблон для DevOps инженера
INSERT INTO behavior_templates (name, template_data, role_id, os_type) VALUES (
    'DevOps Engineer Template',
    '{
        "user_id": "DEVOPS_001",
        "username": "john_devops",
        "full_name": "John Smith",
        "role": "DevOps Engineer",
        "department": "Infrastructure",
        "location": "Office",
        "work_schedule": {
            "start_time": "08:00",
            "end_time": "17:00",
            "breaks": [
                {"start": "12:30", "duration_minutes": 45}
            ]
        },
        "applications_used": [
            "Terminal",
            "Visual Studio Code",
            "Firefox"
        ],
        "custom_applications": [
            "Kubernetes Dashboard",
            "AWS Console",
            "Docker Desktop",
            "Terraform"
        ],
        "activity_pattern": "Infrastructure monitoring and deployment",
        "plugin_support": {
            "enabled": true,
            "plugins_directory": "/opt/linux_agent/plugins",
            "auto_load": true,
            "fallback_to_builtin": true
        }
    }'::jsonb,
    (SELECT id FROM roles WHERE name = 'DevOps Engineer'),
    'Linux'
);

-- 4. Шаблон для менеджера
INSERT INTO behavior_templates (name, template_data, role_id, os_type) VALUES (
    'Project Manager Template',
    '{
        "user_id": "MGR_001",
        "username": "sarah_manager",
        "full_name": "Sarah Williams",
        "role": "Project Manager",
        "department": "Project Management",
        "location": "Office",
        "work_schedule": {
            "start_time": "09:00",
            "end_time": "18:00",
            "breaks": [
                {"start": "12:00", "duration_minutes": 60},
                {"start": "15:00", "duration_minutes": 10}
            ]
        },
        "applications_used": [
            "Firefox",
            "LibreOffice Writer"
        ],
        "custom_applications": [
            "Slack",
            "Zoom",
            "LibreOffice Calc",
            "LibreOffice Writer"
        ],
        "activity_pattern": "Meetings and documentation",
        "plugin_support": {
            "enabled": false,
            "plugins_directory": "/opt/linux_agent/plugins",
            "auto_load": false,
            "fallback_to_builtin": true
        }
    }'::jsonb,
    (SELECT id FROM roles WHERE name = 'Manager'),
    'Linux'
);

-- =====================================================
-- ШАБЛОНЫ ПРИЛОЖЕНИЙ (applications_template)
-- =====================================================

-- 1. PyCharm
INSERT INTO applications_template (name, template_config) VALUES (
    'PyCharm',
    '{
        "execution": {
            "open_command": "pycharm || /snap/bin/pycharm-community || /usr/local/bin/pycharm",
            "close_command": "pkill -f pycharm"
        },
        "activities": [
            {
                "name": "Creating new Python project",
                "description": "Create a new Python project",
                "commands": [
                    {
                        "type": "key_combination",
                        "keys": "ctrl+shift+n",
                        "delay": 2
                    },
                    {
                        "type": "type_text",
                        "text": "my_new_project",
                        "delay": 1
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return",
                        "delay": 3
                    }
                ]
            },
            {
                "name": "Writing Python code",
                "description": "Write Python code with imports and functions",
                "commands": [
                    {
                        "type": "type_text",
                        "text": "import pandas as pd",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return",
                        "delay": 0.5
                    },
                    {
                        "type": "type_text",
                        "text": "import numpy as np",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return Return",
                        "delay": 0.5
                    },
                    {
                        "type": "type_text",
                        "text": "def process_data(df):",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return",
                        "delay": 0.5
                    },
                    {
                        "type": "type_text",
                        "text": "    return df.dropna()",
                        "delay": 1
                    }
                ]
            },
            {
                "name": "Running tests",
                "description": "Run unit tests",
                "commands": [
                    {
                        "type": "key_combination",
                        "keys": "shift+F10",
                        "delay": 5
                    }
                ]
            },
            {
                "name": "Debugging code",
                "description": "Debug Python code",
                "commands": [
                    {
                        "type": "key_combination",
                        "keys": "shift+F9",
                        "delay": 3
                    },
                    {
                        "type": "key_combination",
                        "keys": "F8",
                        "delay": 2
                    },
                    {
                        "type": "key_combination",
                        "keys": "F8",
                        "delay": 2
                    }
                ]
            }
        ]
    }'::jsonb
);

-- 2. Chrome Browser
INSERT INTO applications_template (name, template_config) VALUES (
    'Chrome',
    '{
        "execution": {
            "open_command": "google-chrome || chromium-browser || chromium",
            "close_command": "pkill -f chrome"
        },
        "activities": [
            {
                "name": "Browse GitHub",
                "description": "Navigate to GitHub and browse repositories",
                "commands": [
                    {
                        "type": "key_combination",
                        "keys": "ctrl+l",
                        "delay": 1
                    },
                    {
                        "type": "type_text",
                        "text": "github.com",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return",
                        "delay": 3
                    },
                    {
                        "type": "key_combination",
                        "keys": "Tab Tab Tab",
                        "delay": 1
                    },
                    {
                        "type": "type_text",
                        "text": "python projects",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return",
                        "delay": 3
                    }
                ]
            },
            {
                "name": "Check email",
                "description": "Open Gmail and check emails",
                "commands": [
                    {
                        "type": "key_combination",
                        "keys": "ctrl+t",
                        "delay": 1
                    },
                    {
                        "type": "type_text",
                        "text": "gmail.com",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return",
                        "delay": 3
                    },
                    {
                        "type": "key_combination",
                        "keys": "j",
                        "delay": 1
                    },
                    {
                        "type": "key_combination",
                        "keys": "k",
                        "delay": 1
                    }
                ]
            },
            {
                "name": "Developer console",
                "description": "Open developer console and check network",
                "commands": [
                    {
                        "type": "key_combination",
                        "keys": "F12",
                        "delay": 2
                    },
                    {
                        "type": "mouse_click",
                        "x": 200,
                        "y": 150,
                        "button": 1,
                        "delay": 1
                    },
                    {
                        "type": "key_combination",
                        "keys": "ctrl+shift+e",
                        "delay": 2
                    }
                ]
            }
        ]
    }'::jsonb
);

-- 3. Slack Desktop
INSERT INTO applications_template (name, template_config) VALUES (
    'Slack',
    '{
        "execution": {
            "open_command": "slack || /usr/bin/slack || /snap/bin/slack",
            "close_command": "pkill -f slack"
        },
        "activities": [
            {
                "name": "Send message",
                "description": "Send a message in general channel",
                "commands": [
                    {
                        "type": "key_combination",
                        "keys": "ctrl+k",
                        "delay": 1
                    },
                    {
                        "type": "type_text",
                        "text": "general",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return",
                        "delay": 2
                    },
                    {
                        "type": "type_text",
                        "text": "Good morning team! Starting work on the new feature.",
                        "delay": 1
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return",
                        "delay": 1
                    }
                ]
            },
            {
                "name": "Check notifications",
                "description": "Check and respond to notifications",
                "commands": [
                    {
                        "type": "key_combination",
                        "keys": "ctrl+shift+a",
                        "delay": 2
                    },
                    {
                        "type": "key_combination",
                        "keys": "Down",
                        "delay": 1
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return",
                        "delay": 2
                    }
                ]
            }
        ]
    }'::jsonb
);

-- 4. Postman
INSERT INTO applications_template (name, template_config) VALUES (
    'Postman',
    '{
        "execution": {
            "open_command": "postman || /opt/Postman/Postman || /usr/bin/postman",
            "close_command": "pkill -f Postman"
        },
        "activities": [
            {
                "name": "Create API request",
                "description": "Create a new API request",
                "commands": [
                    {
                        "type": "key_combination",
                        "keys": "ctrl+n",
                        "delay": 2
                    },
                    {
                        "type": "type_text",
                        "text": "https://api.example.com/users",
                        "delay": 1
                    },
                    {
                        "type": "key_combination",
                        "keys": "Tab Tab",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return",
                        "delay": 3
                    }
                ]
            },
            {
                "name": "Test API endpoint",
                "description": "Test API endpoint with parameters",
                "commands": [
                    {
                        "type": "mouse_click",
                        "x": 400,
                        "y": 300,
                        "button": 1,
                        "delay": 1
                    },
                    {
                        "type": "type_text",
                        "text": "limit",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Tab",
                        "delay": 0.5
                    },
                    {
                        "type": "type_text",
                        "text": "10",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "ctrl+Return",
                        "delay": 3
                    }
                ]
            }
        ]
    }'::jsonb
);

-- 5. DBeaver
INSERT INTO applications_template (name, template_config) VALUES (
    'DBeaver',
    '{
        "execution": {
            "open_command": "dbeaver || /usr/bin/dbeaver || /opt/dbeaver/dbeaver",
            "close_command": "pkill -f dbeaver"
        },
        "activities": [
            {
                "name": "Execute SQL query",
                "description": "Write and execute SQL query",
                "commands": [
                    {
                        "type": "key_combination",
                        "keys": "ctrl+]",
                        "delay": 2
                    },
                    {
                        "type": "type_text",
                        "text": "SELECT * FROM users WHERE created_at > NOW() - INTERVAL ''7 days''",
                        "delay": 1
                    },
                    {
                        "type": "key_combination",
                        "keys": "ctrl+Return",
                        "delay": 3
                    }
                ]
            },
            {
                "name": "Browse database structure",
                "description": "Navigate through database tables",
                "commands": [
                    {
                        "type": "key_combination",
                        "keys": "alt+1",
                        "delay": 1
                    },
                    {
                        "type": "key_combination",
                        "keys": "Down Down",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Right",
                        "delay": 1
                    },
                    {
                        "type": "key_combination",
                        "keys": "Down",
                        "delay": 0.5
                    }
                ]
            }
        ]
    }'::jsonb
);

-- 6. LibreOffice Writer
INSERT INTO applications_template (name, template_config) VALUES (
    'LibreOffice Writer',
    '{
        "execution": {
            "open_command": "libreoffice --writer || lowriter",
            "close_command": "pkill -f libreoffice"
        },
        "activities": [
            {
                "name": "Create document",
                "description": "Create a new document and write content",
                "commands": [
                    {
                        "type": "type_text",
                        "text": "Project Status Report",
                        "delay": 1
                    },
                    {
                        "type": "key_combination",
                        "keys": "ctrl+Return",
                        "delay": 0.5
                    },
                    {
                        "type": "type_text",
                        "text": "Date: ",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "ctrl+semicolon",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return Return",
                        "delay": 0.5
                    },
                    {
                        "type": "type_text",
                        "text": "Summary: Development progress is on track.",
                        "delay": 1
                    }
                ]
            },
            {
                "name": "Format document",
                "description": "Apply formatting to document",
                "commands": [
                    {
                        "type": "key_combination",
                        "keys": "ctrl+a",
                        "delay": 1
                    },
                    {
                        "type": "key_combination",
                        "keys": "ctrl+e",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "ctrl+Home",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "shift+End",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "ctrl+b",
                        "delay": 0.5
                    }
                ]
            }
        ]
    }'::jsonb
);

-- 7. Jira (Web-based через Firefox)
INSERT INTO applications_template (name, template_config) VALUES (
    'Jira',
    '{
        "execution": {
            "open_command": "firefox https://jira.company.com || google-chrome https://jira.company.com",
            "close_command": "pkill -f \"firefox.*jira|chrome.*jira\""
        },
        "activities": [
            {
                "name": "Create issue",
                "description": "Create a new Jira issue",
                "commands": [
                    {
                        "type": "wait",
                        "time": 3
                    },
                    {
                        "type": "key_combination",
                        "keys": "c",
                        "delay": 2
                    },
                    {
                        "type": "type_text",
                        "text": "Fix login validation bug",
                        "delay": 1
                    },
                    {
                        "type": "key_combination",
                        "keys": "Tab",
                        "delay": 0.5
                    },
                    {
                        "type": "type_text",
                        "text": "Users report that special characters in passwords cause login failures",
                        "delay": 1
                    }
                ]
            },
            {
                "name": "Update issue status",
                "description": "Change issue status",
                "commands": [
                    {
                        "type": "key_combination",
                        "keys": "g g",
                        "delay": 1
                    },
                    {
                        "type": "type_text",
                        "text": "DEV-123",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return",
                        "delay": 3
                    },
                    {
                        "type": "key_combination",
                        "keys": ".",
                        "delay": 1
                    },
                    {
                        "type": "type_text",
                        "text": "In Progress",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return",
                        "delay": 1
                    }
                ]
            }
        ]
    }'::jsonb
);

-- 8. Docker Desktop
INSERT INTO applications_template (name, template_config) VALUES (
    'Docker Desktop',
    '{
        "execution": {
            "open_command": "systemctl --user start docker-desktop || docker-desktop",
            "close_command": "systemctl --user stop docker-desktop"
        },
        "activities": [
            {
                "name": "Terminal Docker commands",
                "description": "Run Docker commands in terminal",
                "commands": [
                    {
                        "type": "key_combination",
                        "keys": "ctrl+alt+t",
                        "delay": 2
                    },
                    {
                        "type": "type_text",
                        "text": "docker ps -a",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return",
                        "delay": 2
                    },
                    {
                        "type": "type_text",
                        "text": "docker images",
                        "delay": 0.5
                    },
                    {
                        "type": "key_combination",
                        "keys": "Return",
                        "delay": 2
                    }
                ]
            }
        ]
    }'::jsonb
);

-- =====================================================
-- ЗАПРОСЫ ДЛЯ ПРОВЕРКИ
-- =====================================================

-- Проверка вставленных ролей
SELECT * FROM roles ORDER BY id;

-- Проверка шаблонов пользователей
SELECT 
    bt.id,
    bt.name,
    r.name as role_name,
    bt.template_data->>'username' as username,
    bt.template_data->>'department' as department,
    bt.is_active
FROM behavior_templates bt
LEFT JOIN roles r ON bt.role_id = r.id
ORDER BY bt.id;

-- Проверка шаблонов приложений
SELECT 
    id,
    name,
    template_config->'execution'->>'open_command' as open_command,
    jsonb_array_length(template_config->'activities') as activities_count
FROM applications_template
ORDER BY id;

-- Детальная информация о конкретном шаблоне пользователя
SELECT * FROM behavior_templates WHERE id = 1;