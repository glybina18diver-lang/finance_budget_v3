"""
Централизованная система логирования с ротацией и разделением потоков.

Особенности:
- RotatingFileHandler для app.log (5MB, 3 backup) — все уровни INFO+
- RotatingFileHandler для errors.log (2MB, 3 backup) — только ERROR+
- StreamHandler для консоли (INFO+)
- Подавление логов сторонних библиотек (PySide6, matplotlib, urllib3)
- Защита от дублирования хендлеров при повторном вызове
"""
import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logger(log_level: str = "INFO") -> logging.Logger:
    """
    Настраивает глобальное логирование. Вызывается ОДИН РАЗ в main.py.
    Создаёт app.log (общий) и errors.log (только ошибки).

    Args:
        log_level: уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Настроенный root-логгер
    """
    # Импортируем здесь, чтобы избежать циклического импорта
    from config import get_log_file_path

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Защита от дублирования хендлеров
    if root_logger.handlers:
        return root_logger

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Консоль (DEBUG+ для отладки)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)  # ← ИСПРАВЛЕНО!
    console.setFormatter(formatter)
    root_logger.addHandler(console)

    # 2. Общий файл app.log (ротация 5МБ, 3 бэкапа)
    app_path = get_log_file_path("app.log")
    app_handler = RotatingFileHandler(
        app_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8'
    )
    app_handler.setLevel(logging.INFO)
    app_handler.setFormatter(formatter)
    root_logger.addHandler(app_handler)

    # 3. Файл ошибок errors.log (только ERROR+, ротация 2МБ)
    err_path = get_log_file_path("errors.log")
    err_handler = RotatingFileHandler(
        err_path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding='utf-8'
    )
    err_handler.setLevel(logging.ERROR)
    err_handler.setFormatter(formatter)
    root_logger.addHandler(err_handler)

    # 4. Настройка уровней для сторонних библиотек
    logging.getLogger("PySide6").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    return root_logger