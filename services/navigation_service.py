# ui/services/navigation_service.py
"""
Сервис навигации между диалогами.
Центр управления открытием окон с правильным внедрением зависимостей.
"""
from typing import Optional
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt

from core.db import Database

# Диалоги
from ui.dialogs.operation_dialog import OperationDialog
from ui.dialogs.account_dialog import AccountDialog
from ui.dialogs.category_dialog import CategoryDialog

# Презентеры
from ui.presenters.transaction_presenter import TransactionPresenter
from ui.presenters.account_presenter import AccountPresenter
from ui.presenters.category_presenter import CategoryPresenter


# Сервисы
from services.transaction_service import TransactionService
from services.account_service import AccountService
from services.category_service import CategoryService

# Репозитории
from core.repositories.account_repository import AccountRepository
from core.repositories.transaction_repository import TransactionRepository
from core.repositories.category_repository import CategoryRepository


class NavigationService:
    """Сервис навигации между диалогами приложения."""

    def __init__(self, db: Database):
        """
        Инициализация сервиса навигации.
        
        Args:
            db: экземпляр подключения к базе данных
        """
        self.db = db
        # Создаём общие репозитории один раз для всего приложения
        self._init_shared_repositories()

    def _init_shared_repositories(self):
        """Инициализирует репозитории, общие для всех диалогов."""
        self.acc_repo = AccountRepository(self.db)
        self.tx_repo = TransactionRepository(self.db)
        self.cat_repo = CategoryRepository(self.db)

    def open_operation_dialog(self, parent: QWidget) -> None:
        """
        Открывает диалог операций (не модальный).
        
        Args:
            parent: родительское окно (обычно MainWindow)
        """
        # Создаём сервис с нужными репозиториями
        tx_service = TransactionService(
            tx_repo=self.tx_repo,
            acc_repo=self.acc_repo,
            cat_repo=self.cat_repo
        )
        # Создаём презентер
        presenter = TransactionPresenter(tx_service=tx_service)
        # Создаём и показываем диалог
        dialog = OperationDialog(parent=parent, presenter=presenter)
        dialog.show()  # Не modal!
        return dialog # Возвращаем диалог

    def open_account_dialog(self, parent: QWidget) -> None:
        """
        Открывает диалог управления счетами (модальный).
        
        Args:
            parent: родительское окно (обычно MainWindow)
        """
        # Создаём сервис для счетов
        acc_service = AccountService(acc_repo=self.acc_repo)
        # Создаём презентер
        presenter = AccountPresenter(service=acc_service)
        # Создаём и показываем диалог
        dialog = AccountDialog(parent=parent, presenter=presenter)
        dialog.exec()  # Modal
        return dialog # Возвращаем диалог
    
    def open_category_dialog(self, parent: QWidget) -> CategoryDialog:
        """
        Открывает диалог управления категориями (немодальный).
        
        Args:
            parent: родительское окно (обычно MainWindow)
            
        Returns:
            Экземпляр CategoryDialog
        """
        # 1. Создаём сервис для КАТЕГОРИЙ (не счетов!)
        cat_service = CategoryService(cat_repo=self.cat_repo)
        
        # 2. Создаём презентер для КАТЕГОРИЙ
        presenter = CategoryPresenter(service=cat_service)
        
        # 3. Создаём и показываем диалог
        dialog = CategoryDialog(parent=parent, presenter=presenter)
        dialog.show()  # Немодальный
        
        return dialog