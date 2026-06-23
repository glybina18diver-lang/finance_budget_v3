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
from ui.dialogs.transfer_dialog import TransferDialog
from ui.dialogs.loan_dialog import LoanDialog

# Презентеры
from ui.presenters.transaction_presenter import TransactionPresenter
from ui.presenters.account_presenter import AccountPresenter
from ui.presenters.category_presenter import CategoryPresenter
from ui.presenters.transfer_presenter import TransferPresenter
from ui.presenters.loan_presenter import LoanPresenter


# Сервисы
from services.transaction_service import TransactionService
from services.account_service import AccountService
from services.category_service import CategoryService
from services.transfer_service import TransferService
from services.loan_service import LoanService

# Репозитории
from core.repositories.account_repository import AccountRepository
from core.repositories.transaction_repository import TransactionRepository
from core.repositories.category_repository import CategoryRepository
from core.repositories.transfer_repository import TransferRepository
from core.repositories.loan_repository import LoanRepository


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
        self.tr_repo = TransferRepository(self.db)
        self.loan_repo = LoanRepository(self.db)

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
        # 1. Создаём сервис для КАТЕГОРИЙ
        cat_service = CategoryService(cat_repo=self.cat_repo)
        
        # 2. Создаём презентер для КАТЕГОРИЙ
        presenter = CategoryPresenter(service=cat_service)
        
        # 3. Создаём и показываем диалог
        dialog = CategoryDialog(parent=parent, presenter=presenter)
        dialog.show()  # Немодальный
        
        return dialog
    
    def open_transfer_dialog(self, parent: QWidget) -> TransferDialog:
        """
        Открывает диалог переводов (немодальный).
        
        Args:
            parent: родительское окно (обычно MainWindow)
            
        Returns:
            Объект TransferDialog
        """
        tr_service = TransferService(self.tr_repo, self.acc_repo)
        presenter = TransferPresenter(tr_service)
        dialog = TransferDialog(parent=parent, presenter=presenter)
        dialog.show()
        return dialog
    
    def open_loan_dialog(self, parent: QWidget) -> LoanDialog:
        """
        Открывает диалог управления займами (немодальный).
        
        Args:
            parent: родительское окно (обычно MainWindow)
            
        Returns:
            Объект LoanDialog
        """
        # 2. Создаем сервис
        service = LoanService(self.loan_repo, self.tr_repo, self.acc_repo)
        
        # 3. Создаем презентер
        presenter = LoanPresenter(service)
        
        # 4. Создаем и показываем диалог
        dialog = LoanDialog(parent=parent, presenter=presenter)
        dialog.show()
        return dialog