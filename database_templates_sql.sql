-- =====================================================
-- ROLES
-- =====================================================

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
    ('HR Specialist', 'HR')
ON CONFLICT (name) DO NOTHING;

-- =====================================================
-- BEHAVIOR TEMPLATES
-- Fixed: added version column (was missing, caused NOT NULL error)
-- Fixed: removed ::jsonb cast (column is JSON not JSONB)
-- =====================================================

INSERT INTO behavior_templates (name, description, os_type, template_data, is_active, role_id, version) VALUES (
    'Python Developer Template',
    'Linux developer role',
    'Linux',
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
        "applications_used": ["Terminal", "Visual Studio Code", "Firefox", "PyCharm"],
        "custom_applications": ["PyCharm", "Postman", "DBeaver"],
        "activity_pattern": "Intensive coding with regular breaks",
        "plugin_support": {
            "enabled": true,
            "plugins_directory": "/opt/linux_agent/plugins",
            "auto_load": true,
            "fallback_to_builtin": true
        }
    }',
    true,
    (SELECT id FROM roles WHERE name = 'Developer'),
    '1.0'
);

INSERT INTO behavior_templates (name, description, os_type, template_data, is_active, role_id, version) VALUES (
    'QA Engineer Template',
    'QA Engineer role',
    'Linux',
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
        "applications_used": ["Terminal", "Firefox", "Chrome", "Jira"],
        "custom_applications": ["Chrome", "Jira", "Selenium IDE", "Postman"],
        "activity_pattern": "Testing cycles with documentation",
        "plugin_support": {
            "enabled": false,
            "plugins_directory": "/opt/linux_agent/plugins",
            "auto_load": false,
            "fallback_to_builtin": true
        }
    }',
    true,
    (SELECT id FROM roles WHERE name = 'QA Engineer'),
    '1.0'
);

INSERT INTO behavior_templates (name, description, os_type, template_data, is_active, role_id, version) VALUES (
    'DevOps Engineer Template',
    'DevOps Engineer role',
    'Linux',
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
        "applications_used": ["Terminal", "Visual Studio Code", "Firefox"],
        "custom_applications": ["Kubernetes Dashboard", "Docker Desktop", "Terraform"],
        "activity_pattern": "Infrastructure monitoring and deployment",
        "plugin_support": {
            "enabled": true,
            "plugins_directory": "/opt/linux_agent/plugins",
            "auto_load": true,
            "fallback_to_builtin": true
        }
    }',
    true,
    (SELECT id FROM roles WHERE name = 'DevOps Engineer'),
    '1.0'
);

INSERT INTO behavior_templates (name, description, os_type, template_data, is_active, role_id, version) VALUES (
    'Project Manager Template',
    'Project Manager role',
    'Linux',
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
        "applications_used": ["Firefox", "LibreOffice Writer"],
        "custom_applications": ["Slack", "LibreOffice Calc", "LibreOffice Writer"],
        "activity_pattern": "Meetings and documentation",
        "plugin_support": {
            "enabled": false,
            "plugins_directory": "/opt/linux_agent/plugins",
            "auto_load": false,
            "fallback_to_builtin": true
        }
    }',
    true,
    (SELECT id FROM roles WHERE name = 'Manager'),
    '1.0'
);

INSERT INTO behavior_templates (name, description, os_type, template_data, is_active, role_id, version) VALUES (
    'System Administrator Template',
    'System Administrator role',
    'Linux',
    '{
        "user_id": "ADMIN_001",
        "username": "admin_user",
        "full_name": "Admin User",
        "role": "System Administrator",
        "department": "IT",
        "location": "Office",
        "work_schedule": {
            "start_time": "08:00",
            "end_time": "17:00",
            "breaks": [
                {"start": "12:00", "duration_minutes": 60}
            ]
        },
        "applications_used": ["Terminal", "Firefox"],
        "custom_applications": ["Terminal"],
        "activity_pattern": "System monitoring and maintenance",
        "plugin_support": {
            "enabled": true,
            "plugins_directory": "/opt/linux_agent/plugins",
            "auto_load": true,
            "fallback_to_builtin": true
        }
    }',
    true,
    (SELECT id FROM roles WHERE name = 'System Administrator'),
    '1.0'
);

-- =====================================================
-- APPLICATION TEMPLATES
-- Fixed: added os_type column (was missing, caused NOT NULL error)
-- Fixed: removed ::jsonb cast (column is JSON not JSONB)
-- =====================================================

INSERT INTO applications_template (name, os_type, template_config) VALUES (
    'PyCharm',
    'Linux',
    '{
        "execution": {
            "open_command": "pycharm || /snap/bin/pycharm-community || /usr/local/bin/pycharm",
            "close_command": "pkill -f pycharm"
        },
        "activities": [
            {
                "name": "Writing Python code",
                "description": "Write Python code with imports and functions",
                "commands": [
                    {"type": "type_text", "text": "import pandas as pd", "delay": 0.5},
                    {"type": "key_combination", "keys": "Return", "delay": 0.5},
                    {"type": "type_text", "text": "import numpy as np", "delay": 0.5},
                    {"type": "key_combination", "keys": "Return Return", "delay": 0.5},
                    {"type": "type_text", "text": "def process_data(df):", "delay": 0.5},
                    {"type": "key_combination", "keys": "Return", "delay": 0.5},
                    {"type": "type_text", "text": "    return df.dropna()", "delay": 1}
                ]
            },
            {
                "name": "Running tests",
                "description": "Run unit tests",
                "commands": [
                    {"type": "key_combination", "keys": "shift+F10", "delay": 5}
                ]
            }
        ]
    }'
);

INSERT INTO applications_template (name, os_type, template_config) VALUES (
    'Chrome',
    'Linux',
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
                    {"type": "key_combination", "keys": "ctrl+l", "delay": 1},
                    {"type": "type_text", "text": "github.com", "delay": 0.5},
                    {"type": "key_combination", "keys": "Return", "delay": 3}
                ]
            },
            {
                "name": "Check email",
                "description": "Open Gmail and check emails",
                "commands": [
                    {"type": "key_combination", "keys": "ctrl+t", "delay": 1},
                    {"type": "type_text", "text": "gmail.com", "delay": 0.5},
                    {"type": "key_combination", "keys": "Return", "delay": 3}
                ]
            }
        ]
    }'
);

INSERT INTO applications_template (name, os_type, template_config) VALUES (
    'Slack',
    'Linux',
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
                    {"type": "key_combination", "keys": "ctrl+k", "delay": 1},
                    {"type": "type_text", "text": "general", "delay": 0.5},
                    {"type": "key_combination", "keys": "Return", "delay": 2},
                    {"type": "type_text", "text": "Good morning team! Starting work on the new feature.", "delay": 1},
                    {"type": "key_combination", "keys": "Return", "delay": 1}
                ]
            }
        ]
    }'
);

INSERT INTO applications_template (name, os_type, template_config) VALUES (
    'Postman',
    'Linux',
    '{
        "execution": {
            "open_command": "postman || /opt/Postman/Postman || /usr/bin/postman",
            "close_command": "pkill -f Postman"
        },
        "activities": [
            {
                "name": "Test API endpoint",
                "description": "Test API endpoint with parameters",
                "commands": [
                    {"type": "key_combination", "keys": "ctrl+n", "delay": 2},
                    {"type": "type_text", "text": "https://api.example.com/users", "delay": 1},
                    {"type": "key_combination", "keys": "Return", "delay": 3}
                ]
            }
        ]
    }'
);

INSERT INTO applications_template (name, os_type, template_config) VALUES (
    'DBeaver',
    'Linux',
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
                    {"type": "type_text", "text": "SELECT * FROM users LIMIT 100", "delay": 1},
                    {"type": "key_combination", "keys": "ctrl+Return", "delay": 3}
                ]
            }
        ]
    }'
);

INSERT INTO applications_template (name, os_type, template_config) VALUES (
    'LibreOffice Writer',
    'Linux',
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
                    {"type": "type_text", "text": "Project Status Report", "delay": 1},
                    {"type": "key_combination", "keys": "Return Return", "delay": 0.5},
                    {"type": "type_text", "text": "Summary: Development progress is on track.", "delay": 1},
                    {"type": "key_combination", "keys": "ctrl+s", "delay": 2}
                ]
            }
        ]
    }'
);

INSERT INTO applications_template (name, os_type, template_config) VALUES (
    'Docker Desktop',
    'Linux',
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
                    {"type": "key_combination", "keys": "ctrl+alt+t", "delay": 2},
                    {"type": "type_text", "text": "docker ps -a", "delay": 0.5},
                    {"type": "key_combination", "keys": "Return", "delay": 2},
                    {"type": "type_text", "text": "docker images", "delay": 0.5},
                    {"type": "key_combination", "keys": "Return", "delay": 2}
                ]
            }
        ]
    }'
);

-- =====================================================
-- VERIFY
-- =====================================================

SELECT id, name, category FROM roles ORDER BY id;

SELECT id, name, os_type, version FROM behavior_templates ORDER BY id;

SELECT id, name, os_type FROM applications_template ORDER BY id;
