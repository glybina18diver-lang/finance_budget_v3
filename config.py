import sys
import os
from pathlib import Path

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def _find_project_root() -> tuple[Path, bool]:
    """
    Ищет корень проекта по наличию .git.
    
    Returns:
        tuple: (путь_к_корню, is_dev_mode)
    """
    project_root = Path(__file__).resolve().parent
    is_dev_mode = False
    
    for _ in range(4):
        if (project_root / ".git").exists():
            is_dev_mode = True
            break
        if project_root.parent == project_root:  # Достигли корня диска
            break
        project_root = project_root.parent

    # Принудительное управление через переменные окружения
    if os.environ.get("FORCE_PROD_DB") == "1":
        is_dev_mode = False
    elif os.environ.get("FORCE_DEV_DB") == "1":
        is_dev_mode = True

    return project_root, is_dev_mode

def _get_version() -> str:
    """Читает версию из файла VERSION в корне проекта."""
    project_root, is_dev_mode = _find_project_root()
    version_file = project_root / "VERSION"
    
    if is_dev_mode and version_file.exists():
        with open(version_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "dev"  # fallback

# ========== UI НАСТРОЙКИ ==========
APP_NAME = "Finance Budget V3 (beta)"
APP_VERSION = _get_version()
WINDOW_TITLE = f"{APP_NAME} (PySide6 v{APP_VERSION}) - SQLite"
ICON_DIR = './assets/icon.ico'

# ========== ПУТИ ==========
# LOGS_DIR = BASE_DIR / "logs"  # TODO: также как и для БД, сделать верный путь

# ========== БАЗА ДАННЫХ ==========
DB_FILENAME = "budget.db"

def get_db_path() -> str:
    """
    Возвращает путь к БД.
    - В разработке: в корне проекта (ищет .git вверх по дереву)
    - В собранной версии: в системной папке пользователя (стандарт ОС)
    """
    is_compiled = getattr(sys, "frozen", False)
    project_root, is_dev_mode = _find_project_root()

    # Возвращаем путь разработки, если не скомпилировано и режим dev активен
    if not is_compiled and is_dev_mode:
        dev_path = project_root / DB_FILENAME
        return str(dev_path)

    # Системный путь для готовой сборки
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    data_dir = base / APP_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / DB_FILENAME)

# ========== ЛОГИРОВАНИЕ ==========
LOGS_DIR_NAME = "logs" # Название директории с логами

def get_logs_dir() -> Path:
    """
    Возвращает путь к директории логов.
    - В разработке: logs/ в корне проекта (ищет .git вверх по дереву)
    - В собранной версии: logs/ в системной папке пользователя (рядом с БД)
    """
    is_compiled = getattr(sys, "frozen", False)
    project_root, is_dev_mode = _find_project_root()

    # Возвращаем путь разработки, если не скомпилировано и режим dev активен
    if not is_compiled and is_dev_mode:
        logs_path = project_root / LOGS_DIR_NAME
        logs_path.mkdir(exist_ok=True)
        return logs_path

    # Системный путь для готовой сборки
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    data_dir = base / APP_NAME
    logs_path = data_dir / LOGS_DIR_NAME
    logs_path.mkdir(parents=True, exist_ok=True)
    return logs_path

def get_log_file_path(filename: str = "app.log") -> Path:
    """
    Возвращает полный путь к файлу лога.
    
    Args:
        filename: имя файла лога (по умолчанию "app.log")
    """
    return get_logs_dir() / filename