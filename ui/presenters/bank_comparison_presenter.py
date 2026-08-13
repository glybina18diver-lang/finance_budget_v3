import logging
import traceback
from datetime import datetime
from services.transaction_service import TransactionService


logger = logging.getLogger(__name__)

class BankComparisonPresenter:
    """Презентер для окна сверки с банковским приложением."""

    def __init__(self, transaction_service: TransactionService):
        """
        Инициализация презентера.
        
        Args:
            view: Экземпляр диалогового окна.
            transaction_service: Сервис для работы с транзакциями.
        """
        self.view = None
        self.tr_service = transaction_service

    def set_view(self, view):
        """                             
        Устанавливает ссылку на представление (диалог/окно).

        Args:
            view: объект с методами show_status, show_error, clear_form, refresh_transactions
        """ 
        self.view = view
        self.load_initial_data()

    def load_summary(self, start_date: datetime, end_date: datetime, account_id: int):
        """
        Загружает и передает в UI сводку за период.
        
        Args:
            start_date: Начало периода.
            end_date: Конец периода.
            account_id: ID счета для фильтрации.
            
        Raises:
            ValueError: Если даты некорректны.
        """
        try:
            if start_date > end_date:
                raise ValueError("Дата начала периода не может быть позже даты окончания.")
                
            # Обращение к сервису для получения агрегированных данных
            summary = self.tr_service.get_bank_comparison_summary(start_date, end_date, account_id)
            self.view.update_summary(summary)
            
        except ValueError as e:
            # Ожидаемые ошибки валидации
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            # Системные ошибки
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def load_initial_data(self):
        """Загружает начальные данные при открытии диалога."""
        if not self.view:
            return

        try:
            # 1. Загружаем ВСЕ категории и счета (один раз)
            accounts = self.tr_service.get_accounts_for_ui()
            self.all_categories = self.tr_service.get_categories_for_ui()

            self.view.load_accounts_combos(accounts)

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка загрузки начальных данных: {e}", exc_info=True)
            if self.view:
                self.view.show_error(f"Ошибка загрузки данных: {e}")