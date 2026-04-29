import sys
import logging
from PySide6.QtWidgets import QApplication, QMessageBox

from config import APP_NAME, get_db_path  # ← используем функцию, а не константу
from core.db import Database
from ui.main_window import MainWindow
from core.repositories.transaction_repository import TransactionRepository
from core.repositories.account_repository import AccountRepository
from core.repositories.category_repository import CategoryRepository
from services.transaction_service import TransactionService
from ui.presenters.transaction_presenter import TransactionPresenter


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)

    # 1. Получаем корректный путь к БД (с учётом режима разработки/сборки)
    db_path = get_db_path()
    
    # 2. Инициализация фасада БД
    try:
        db = Database(db_path)
        # Простая проверка подключения
        db.fetchone("SELECT 1")
        logging.info(f"База данных успешно подключена: {db_path}")
    except Exception as e:
        QMessageBox.critical(None, "Ошибка БД", f"Не удалось открыть базу данных:\n{e}")
        sys.exit(1)

    # Создаём репозитории
    tx_repo = TransactionRepository(db)
    acc_repo = AccountRepository(db)
    cat_repo = CategoryRepository(db)

    # Создаём сервис
    tx_service = TransactionService(tx_repo, acc_repo, cat_repo)

    # Создаём презентер с готовым сервисом
    tx_presenter = TransactionPresenter(tx_service)

    # 3. Передаём только фасад БД в главное окно
    window = MainWindow(database=db, tx_presenter=tx_presenter)  # ← явная инъекция зависимости
    window.show()

    # 4. Корректное завершение
    exit_code = app.exec()
    db.close()  # ← закрываем соединение при выходе
    sys.exit(exit_code)

if __name__ == "__main__":
    main()