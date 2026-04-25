import sys
import os
from pathlib import Path

# Пути
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "budget.db"
LOGS_DIR = BASE_DIR / "logs"

# ========== БАЗА ДАННЫХ ==========
DB_FILENAME = "budget.db"

def get_db_path() -> str:
    """
    Возвращает путь к БД.
    - В разработке: рядом с main.py (для удобства отладки и бэкапов)
    - В собранной версии: в системной папке пользователя (стандарт ОС)
    """
    # 1. Признак "сборки" (PyInstaller, cx_Freeze и т.д.)
    is_compiled = getattr(sys, "frozen", False)
    
    # 2. Режим разработки: если в папке проекта есть маркер (например, .git или requirements.txt)
    project_root = Path(__file__).parent
    is_dev_mode = not is_compiled and (project_root / ".git").exists()

    if is_dev_mode:
        # 🐍 Разработка: БД в корне проекта
        dev_path = project_root / DB_FILENAME
        # Можно принудительно включить режим пользователя через переменную окружения:
        # os.environ.get("USE_SYSTEM_DB") == "1"
        if dev_path.exists() or os.environ.get("FORCE_DEV_DB"):
            return str(dev_path)

    # 📦 Готовая версия: стандартный путь ОС
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    data_dir = base / APP_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / DB_FILENAME)


# UI Настройки
APP_NAME = "Finance Budget (beta)"
APP_VERSION = "3.0.0"
WINDOW_TITLE = f"{APP_NAME} (PySide6 v{APP_VERSION}) - SQLite"
