import sys
import logging
from PySide6.QtWidgets import QApplication, QMessageBox

from config import APP_NAME, get_db_path  # ← используем функцию, а не константу
from core.db import Database
from core.logger import setup_logger
from ui.main_window import MainWindow
from services.navigation_service import NavigationService
from ui.presenters.main_window_presenter import MainWindowPresenter

logger = logging.getLogger(__name__)


def main():
    # Инициализация системы логирования (до всех импортов UI)
    setup_logger("DEBUG")
    # setup_logger("INFO")
    logger.info(f"Запуск {APP_NAME}")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # 1. Инициализация фасада БД
    try:
        db = Database(get_db_path())
        # Простая проверка подключения
        db.fetchone("SELECT 1")
        logger.info(f"База данных успешно подключена: {get_db_path()}")
    except Exception as e:
        logger.critical(f"Не удалось подключиться к БД: {e}", exc_info=True)
        QMessageBox.critical(None, "Ошибка БД", f"Не удалось открыть базу данных:\n{e}")
        sys.exit(1)

    # 2. Создаём навигационный сервис и главное окно
    nav_service = NavigationService(db=db)

    # Создаём презентер, получая сервисы ИЗ навигации
    presenter = MainWindowPresenter(
        service=nav_service.main_window_service,
        credit_card_service=nav_service.credit_card_service
    )

    # 3. Передаём его в главное окно
    main_window = MainWindow(presenter, navigation_service=nav_service)
    main_window.show()

    # 4. Корректное завершение
    exit_code = app.exec()
    db.close()  # ← закрываем соединение при выходе
    logger.info(f"Завершение {APP_NAME} с кодом {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()