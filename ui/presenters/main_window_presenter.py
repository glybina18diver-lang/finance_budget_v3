"""
Презентер для работы с банковскими кредитами.

Отвечает за:
- Валидацию входных данных из UI
- Конвертацию типов (str → Decimal, str → int)
- Делегирование бизнес-логики в CreditService
- Возврат данных в читаемом виде для UI

Не содержит бизнес-логики и прямых обращений к БД.
"""

import logging
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from datetime import datetime
from decimal import Decimal

from core.models import Account, CreditCard
from services.account_service import AccountService
from services.main_window_service import MainWindowService
from services.credit_card_service import CreditCardService

if TYPE_CHECKING:
    from ui.main_window import MainWindow 

from utils.validators import parse_float, parse_int, to_decimal


logger = logging.getLogger(__name__)


import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow  # Только для IDE и type checker'ов

logger = logging.getLogger(__name__)

class MainWindowPresenter:
    """Презентер главного окна."""

    def __init__(
        self,
        service: MainWindowService,
        credit_card_service: CreditCardService,
        db
    ):
        """
        Инициализация презентера.
        
        Args:
            service: сервис главного окна
            credit_card_service: сервис кредитных карт
        """
        try:
            self.service = service
            self.credit_card_service = credit_card_service
            self.db_manager = db
            self.view: 'MainWindow' = None  # ← Forward reference как строка
            logger.debug(f"[{self.__class__.__name__}] Презентер инициализирован")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка инициализации: {e}", exc_info=True)
            raise

    def set_view(self, view: 'MainWindow'):  # ← Тоже строковая аннотация
        """
        Устанавливает ссылку на UI и загружает начальные данные.
        
        Args:
            view: экземпляр MainWindow
        """
        try:
            self.view = view
            self._load_accounts()
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка установки View: {e}", exc_info=True)
            raise

    def _load_accounts(self) -> List[Dict[str, Any]]:
        """
        Загружает список счетов.

        Returns:
            Список счетов в формате, пригодном для отображения в UI.
        """
        try:
            # Получаем все пользовательские счета
            regular_accounts, credit_accounts = self.service._load_accounts()
            self.view._load_accounts(regular_accounts, credit_accounts)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка загрузки счетов: {e}", exc_info=True)
            self.view.show_error(f"Ошибка загрузки счетов: {e}")
        return 

    def get_credit_cards_info(self, credit_cards_id: int) ->  Optional[CreditCard]:
        """
        Получает информацию о кредитных картах.

        Args:
            account_id: ID счёта в таблице accounts

        Returns:
            Список кредитных карт в формате, пригодном для отображения в UI.
        """
        try:
            credit_card = self.credit_card_service.get_by_account_id(credit_cards_id)

            return credit_card
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения информации о кредитных картах: {e}", exc_info=True)
            self.view.show_error(f"Ошибка получения информации о кредитных картах: {e}")

    # --- импорт в начале файла ---
    

    # --- в __init__ после инициализации остальных сервисов ---
    # Замени self.view на тот атрибут, которым у тебя зовётся главное окно
    

    # --- новый метод класса MainPresenter ---
    def open_analytics_window(self) -> None:
        """Открывает тестовое окно аналитики.

        Raises:
            ValueError: если данные аналитики не прошли валидацию
        """
        from ui.presenters.analytics_presenter import AnalyticsPresenter
        try:
            self.analytics_presenter = AnalyticsPresenter(parent_window=self.view, db_manager=self.db_manager)
            self.analytics_presenter.open_analytics_window()
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise
           