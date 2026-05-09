import sys
import logging
from PySide6.QtWidgets import QApplication, QMessageBox

from config import APP_NAME, get_db_path  # ← используем функцию, а не константу
from core.db import Database
from ui.main_window import MainWindow
from services.navigation_service import NavigationService

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # 1. Инициализация фасада БД
    try:
        db = Database(get_db_path())
        # Простая проверка подключения
        db.fetchone("SELECT 1")
        logging.info(f"База данных успешно подключена: {get_db_path()}")
    except Exception as e:
        QMessageBox.critical(None, "Ошибка БД", f"Не удалось открыть базу данных:\n{e}")
        sys.exit(1)

    # 2. Создаём навигационный сервис
    nav_service = NavigationService(db=db)
    
    # 3. Передаём его в главное окно
    main_window = MainWindow(navigation_service=nav_service)
    main_window.show()

    # 4. Корректное завершение
    exit_code = app.exec()
    db.close()  # ← закрываем соединение при выходе
    sys.exit(exit_code)

if __name__ == "__main__":
    main()