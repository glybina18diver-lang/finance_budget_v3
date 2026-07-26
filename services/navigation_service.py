# services/navigation_service.py
"""
Сервис навигации между диалогами.
Центр управления открытием окон с правильным внедрением зависимостей.
"""
from typing import Optional
import logging
from PySide6.QtWidgets import QWidget, QMessageBox, QInputDialog
from PySide6.QtCore import Qt

from core.db import Database

# Диалоги
from ui.dialogs.operation_dialog import OperationDialog
from ui.dialogs.account_dialog import AccountDialog
from ui.dialogs.category_dialog import CategoryDialog
from ui.dialogs.transfer_dialog import TransferDialog
from ui.dialogs.loan_dialog import LoanDialog
from ui.dialogs.credit_card_dialog import CreditCardDialog
from ui.dialogs.credit_create_dialog import CreditCreateDialog
from ui.dialogs.credit_payment_dialog import CreditPaymentDialog


# Презентеры
from ui.presenters.transaction_presenter import TransactionPresenter
from ui.presenters.account_presenter import AccountPresenter
from ui.presenters.category_presenter import CategoryPresenter
from ui.presenters.transfer_presenter import TransferPresenter
from ui.presenters.loan_presenter import LoanPresenter
from ui.presenters.credit_card_presenter import CreditCardPresenter
from ui.presenters.credit_presenter import CreditPresenter




# Сервисы
from services.transaction_service import TransactionService
from services.account_service import AccountService
from services.category_service import CategoryService
from services.transfer_service import TransferService
from services.loan_service import LoanService
from services.credit_card_service import CreditCardService
from services.credit_service import CreditService
# from services.tranche_service import TrancheService
# from services.interest_engine import InterestEngine
# from services.payment_waterfall import PaymentWaterfall, PaymentAllocation
# from services.statement_service import StatementService
# from services.forecast_service import ForecastService


# Репозитории
from core.repositories.account_repository import AccountRepository
from core.repositories.transaction_repository import TransactionRepository
from core.repositories.category_repository import CategoryRepository
from core.repositories.transfer_repository import TransferRepository
from core.repositories.loan_repository import LoanRepository
from core.repositories.credit_card_repository import CreditCardRepository
from core.repositories.credit_repository import CreditRepository
# from core.repositories.tranche_repository import TrancheRepository
# from core.repositories.interest_accrual_repository import InterestAccrualRepository
# from core.repositories.statement_repository import StatementRepository



logger = logging.getLogger(__name__)


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
        """Инициализирует репозитории и сервисы, общие для всех диалогов."""
        try:
            # Создаем репозитории
            self.acc_repo = AccountRepository(self.db)
            self.tx_repo = TransactionRepository(self.db)
            self.cat_repo = CategoryRepository(self.db)
            self.tr_repo = TransferRepository(self.db)
            self.loan_repo = LoanRepository(self.db)
            self.credit_card_repo = CreditCardRepository(self.db)
            self.credit_repo = CreditRepository(self.db)
            # self.tranche_repo = TrancheRepository(self.db)
            # self.accrual_repo = InterestAccrualRepository(self.db)
            # self.statement_repo = StatementRepository(self.db)

            # self.interest_engine = InterestEngine(self.tranche_repo, self.accrual_repo)
            # self.payment_waterfall = PaymentWaterfall(self.tranche_repo, self.accrual_repo)
            # self.statement_service = StatementService(self.statement_repo, self.tranche_repo, self.accrual_repo, self.credit_card_repo)
            # self.forecast_service = ForecastService(self.tranche_repo, self.accrual_repo, self.credit_card_repo)
            # self.tranche_service = TrancheService(self.tranche_repo, self.credit_card_repo)

            # Создаем сервисы
            self.acc_service = AccountService(self.acc_repo, self.credit_card_repo)
            self.tr_service = TransferService(self.tr_repo, self.acc_repo)
            self.tx_service = TransactionService(
                tx_repo=self.tx_repo,
                acc_repo=self.acc_repo,
                cat_repo=self.cat_repo
                # credit_card_service=.credit_card_service
            )
            self.credit_card_service = CreditCardService(
                self.credit_card_repo, 
                self.cat_repo,
                self.tr_service,
                self.tx_service,
                self.acc_repo
                )
            self.cat_service = CategoryService(cat_repo=self.cat_repo)
            self.credit_service = CreditService(
                self.credit_repo,
                self.acc_repo,
                self.tr_service,
                self.tx_service,
                self.cat_service
            )

            # Создаем презентеры
            self.credit_presenter = CreditPresenter(self.credit_service, self.acc_repo, self.cat_service)
            
        except Exception as e:
            logger.error(f"[NavigationService] Ошибка инициализации репозиториев: {e}", exc_info=True)
            raise

    def open_operation_dialog(self, parent: QWidget) -> Optional[OperationDialog]:
        """
        Открывает диалог операций (не модальный).

        Args:
            parent: родительское окно (обычно MainWindow)

        Returns:
            Экземпляр OperationDialog
        """
        try:
                        # Создаём презентер
            presenter = TransactionPresenter(tx_service=self.tx_service)
            # Создаём и показываем диалог
            dialog = OperationDialog(parent=parent, presenter=presenter, navigation_service=self)
            dialog.show()  # Не modal!
            return dialog
        except Exception as e:
            logger.error(f"[NavigationService] Ошибка открытия диалога операций: {e}", exc_info=True)
            raise

    def open_account_dialog(self, parent: QWidget) -> Optional[AccountDialog]:
        """
        Открывает диалог управления счетами (модальный).

        Args:
            parent: родительское окно (обычно MainWindow)

        Returns:
            Экземпляр AccountDialog
        """
        try:
            # Создаём презентер
            presenter = AccountPresenter(service=self.acc_service)
            # Создаём и показываем диалог
            dialog = AccountDialog(parent=parent, presenter=presenter)
            dialog.show()
            return dialog
        except Exception as e:
            logger.error(f"[NavigationService] Ошибка открытия диалога счетов: {e}", exc_info=True)
            raise

    def open_category_dialog(self, parent: QWidget) -> Optional[CategoryDialog]:
        """
        Открывает диалог управления категориями (немодальный).

        Args:
            parent: родительское окно (обычно MainWindow)

        Returns:
            Экземпляр CategoryDialog
        """
        try:
            # 2. Создаём презентер для КАТЕГОРИЙ
            presenter = CategoryPresenter(service=self.cat_service)

            # 3. Создаём и показываем диалог
            dialog = CategoryDialog(parent=parent, presenter=presenter)
            dialog.show()  # Немодальный

            return dialog
        except Exception as e:
            logger.error(f"[NavigationService] Ошибка открытия диалога категорий: {e}", exc_info=True)
            raise

    def open_transfer_dialog(self, parent: QWidget) -> Optional[TransferDialog]:
        """
        Открывает диалог переводов (немодальный).

        Args:
            parent: родительское окно (обычно MainWindow)

        Returns:
            Объект TransferDialog
        """
        try:
            presenter = TransferPresenter(self.tr_service)
            dialog = TransferDialog(parent=parent, presenter=presenter)
            dialog.show()
            return dialog
        except Exception as e:
            logger.error(f"[NavigationService] Ошибка открытия диалога переводов: {e}", exc_info=True)
            raise

    def open_loan_dialog(self, parent: QWidget) -> Optional[LoanDialog]:
        """
        Открывает диалог управления займами (немодальный).

        Args:
            parent: родительское окно (обычно MainWindow)

        Returns:
            Объект LoanDialog
        """
        try:
            # 2. Создаем сервис
            service = LoanService(self.loan_repo, self.tr_repo, self.acc_repo)

            # 3. Создаем презентер
            presenter = LoanPresenter(service, self.credit_service)

            # 4. Создаем и показываем диалог
            dialog = LoanDialog(parent=parent, presenter=presenter, navigation_service=self)
            dialog.show()
            return dialog
        except Exception as e:
            logger.error(f"[NavigationService] Ошибка открытия диалога займов: {e}", exc_info=True)
            raise

    def open_credit_card_dialog(self, parent: QWidget) -> Optional[LoanDialog]:
        """
        Открывает диалог управления кредитной картой.

        Args:
            parent: родительское окно
        """
        try:
            
            # Создаём презентер и открываем диалог
            presenter = CreditCardPresenter(self.credit_card_service, self.acc_service)
            dialog = CreditCardDialog(
                parent=parent,
                presenter=presenter,
            )
            dialog.show()
            return dialog
        except Exception as e:
            logger.error(f"[NavigationService] Ошибка открытия диалога кредитных карт: {e}", exc_info=True)
            raise

    def open_credit_create_dialog(self, parent: QWidget) -> Optional[LoanDialog]:
        """
        Открывает диалог создания кредита.

        Args:
            parent: родительское окно
        """
        try:
            
            # Создаём презентер и открываем диалог
            dialog = CreditCreateDialog(
                parent=parent,
                presenter=self.credit_presenter,
            )
            dialog.show()
            return dialog
        except Exception as e:
            logger.error(f"[NavigationService] Ошибка открытия диалога rhtlbnjd: {e}", exc_info=True)
            raise

    def open_credit_payment_dialog(self, parent: QWidget, credit_id) -> Optional[LoanDialog]:
            """
            Открывает диалог внесения платежа по кредиту.
    
            Args:
                parent: родительское окно
                credit_id: ID кредита
            """
            try:
                
                # Создаём презентер и открываем диалог
                dialog = CreditPaymentDialog(
                    parent=parent,
                    presenter=self.credit_presenter,
                    loan_id = credit_id
                )
                dialog.exec()
                return dialog
            except Exception as e:
                logger.error(f"[NavigationService] Ошибка открытия диалога: {e}", exc_info=True)
                raise