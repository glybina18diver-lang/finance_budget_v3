import sys
import logging
from PySide6.QtWidgets import QApplication, QMessageBox

from config import APP_NAME, DB_PATH
from core.db import Database
from ui.main_window import MainWindow

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # 1. Инициализация БД
    try:
        db = Database(str(DB_PATH))
        # Проверим подключение
        db.fetchall("SELECT 1") 
    except Exception as e:
        QMessageBox.critical(None, "Ошибка БД", f"Не удалось открыть базу данных:\n{e}")
        sys.exit(1)

    # 2. Запуск UI
    window = MainWindow(db)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()