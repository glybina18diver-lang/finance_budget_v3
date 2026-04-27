import sys
import os
from pathlib import Path

# UI Настройки
APP_NAME = "Finance Budget (beta)"
APP_VERSION = "3.0.0"
WINDOW_TITLE = f"{APP_NAME} (PySide6 v{APP_VERSION}) - SQLite"

# Пути
#LOGS_DIR = BASE_DIR / "logs" #TODO также как и для БД та и для логов сделать верный путь

# ========== БАЗА ДАННЫХ ==========
DB_FILENAME = "budget.db"

def get_db_path() -> str:
    """
    Возвращает путь к БД.
    - В разработке: в корне проекта (ищет .git вверх по дереву)
    - В собранной версии: в системной папке пользователя (стандарт ОС)
    """
    is_compiled = getattr(sys, "frozen", False)
    
    # 1. Ищем маркер проекта (.git) в текущей папке или до 3 уровней выше
    project_root = Path(__file__).resolve().parent
    is_dev_mode = False
    for _ in range(4):
        if (project_root / ".git").exists():
            is_dev_mode = True
            break
        if project_root.parent == project_root:  # Достигли корня диска
            break
        project_root = project_root.parent

    # 2. Принудительное управление через переменные окружения
    if os.environ.get("FORCE_PROD_DB") == "1":
        is_dev_mode = False
    elif os.environ.get("FORCE_DEV_DB") == "1":
        is_dev_mode = True

    # 3. Возвращаем путь разработки, если не скомпилировано и режим dev активен
    if not is_compiled and is_dev_mode:
        dev_path = project_root / DB_FILENAME
        return str(dev_path)

    # 4. Системный путь для готовой сборки
    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:  # Linux
        base = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    data_dir = base / APP_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir / DB_FILENAME)
