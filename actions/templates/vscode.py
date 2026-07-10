"""
actions/templates/vscode.py — Python code snippets for VS Code simulation
Mirrors Windows agent VSCODE_CODE_SNIPPETS exactly.
"""

import random

VSCODE_SNIPPETS = [
    "import os\n\ndef list_files(directory='.'):\n    for entry in os.scandir(directory):\n        print(entry.name, '[dir]' if entry.is_dir() else '[file]')\n\nif __name__ == '__main__':\n    list_files()\n",
    "import json\nimport datetime\n\ndef log_event(event_type, message):\n    entry = {'time': datetime.datetime.now().isoformat(), 'type': event_type, 'msg': message}\n    print(json.dumps(entry, indent=2))\n\nlog_event('INFO', 'System check completed')\n",
    "import socket\nimport platform\n\ndef system_info():\n    print('hostname:', socket.gethostname())\n    print('platform:', platform.system())\n    print('version:', platform.version())\n\nsystem_info()\n",
    "import hashlib\n\ndef hash_string(text):\n    return hashlib.sha256(text.encode()).hexdigest()\n\nsamples = ['admin', 'password123', 'server01']\nfor s in samples:\n    print(s, '->', hash_string(s)[:16])\n",
    "import re\n\ndef parse_log(line):\n    m = re.match(r'(\\d{4}-\\d{2}-\\d{2})\\s+(\\w+)\\s+(.+)', line)\n    return m.groups() if m else None\n\ntest = '2026-06-01 INFO Server started'\nprint(parse_log(test))\n",
    "def bubble_sort(arr):\n    n = len(arr)\n    for i in range(n):\n        for j in range(n - i - 1):\n            if arr[j] > arr[j+1]:\n                arr[j], arr[j+1] = arr[j+1], arr[j]\n    return arr\n\nprint(bubble_sort([64, 34, 25, 12, 22, 11, 90]))\n",
    "import subprocess\nimport sys\n\ndef run(cmd):\n    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)\n    print(r.stdout.strip())\n\nrun('whoami')\nrun('hostname')\n",
    "from pathlib import Path\nimport datetime\n\nreport = Path.home() / 'Documents' / f'report_{datetime.date.today()}.txt'\nlines = ['=== Daily Report ===', f'Date: {datetime.date.today()}', 'Status: Operational']\nreport.write_text('\\n'.join(lines))\nprint('Saved:', report)\n",
    "import time\nimport random\n\nfor i in range(1, 6):\n    time.sleep(random.uniform(0.05, 0.2))\n    print(f'Task {i}/5 complete')\nprint('Done.')\n",
    "import os\nimport sys\n\ninfo = {'python': sys.version.split()[0], 'cwd': os.getcwd(), 'user': os.environ.get('USER', 'unknown')}\nfor k, v in info.items():\n    print(f'{k}: {v}')\n",
]


def random_vscode_snippet():
    return random.choice(VSCODE_SNIPPETS)
