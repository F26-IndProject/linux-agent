# -*- mode: python ; coding: utf-8 -*-
# PyInstaller specification file for Enhanced Linux Activity Agent

block_cipher = None

a = Analysis(
    ['enhanced_agent.py'],  # ИСПРАВЛЕНО: правильный главный файл
    pathex=[],
    binaries=[
        # Добавляем системные утилиты если нужно
        # ('/usr/bin/xdotool', 'bin/'),
    ],
    datas=[
        ('plugin_manager.py', '.'),  # ДОБАВЛЕНО: включаем менеджер плагинов
    ],
    hiddenimports=[
        # Стандартные модули Python
        'subprocess',
        'logging',
        'json',
        'datetime',
        'random',
        'time',
        'os',
        'sys',
        'shutil',
        'urllib.request',
        'tempfile',
        'pathlib',
        'collections',
        'threading',
        'signal',
        'functools',
        'itertools',
        'socket',
        'platform',
        
        # Для динамической загрузки плагинов
        'importlib.util',
        'importlib',
        'types',
        
        # Для работы с JSON и файлами
        'codecs',
        'encodings',
        'encodings.utf_8',
        
        # Для системной интеграции
        'pwd',
        'grp',
        'stat'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Исключаем ненужные GUI библиотеки
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'PIL',
        'PyQt5',
        'PySide2',
        'wx',
        
        # Исключаем ненужные модули для уменьшения размера
        'pytest',
        'setuptools',
        'distutils',
        'email',
        'http',
        'urllib3',
        'requests'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Фильтруем бинарные файлы для уменьшения размера
a.binaries = [x for x in a.binaries if not any([
    x[0].startswith('lib'),
    x[0].startswith('_'),
    'test' in x[0].lower(),
    'debug' in x[0].lower()
])]

# Фильтруем данные для уменьшения размера
a.datas = [x for x in a.datas if not any([
    'test' in x[0].lower(),
    'example' in x[0].lower(),
    x[0].endswith('.pyc'),
    x[0].endswith('.pyo')
])]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='activity_agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Сжатие UPX для уменьшения размера
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None  # Можно добавить иконку если нужно
)