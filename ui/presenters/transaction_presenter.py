# ui/presenters/transaction_presenter.py
from typing import Optional
from typing import List
import logging
from services.transaction_service import TransactionService
from core.models import Transaction, Account, Category

logger = logging.getLogger(__name__)


class TransactionPresenter:
    """Презентер для координации UI, сервисов и отображения статуса."""

    def __init__(self, tx_service: TransactionService):
        """
        Инициализация презентера.

        Args:
            tx_service: экземпляр TransactionService для выполнения бизнес-операций
        """
        self.service = tx_service
        self.view = None  # Ссылка на UI-объект (устанавливается через set_view)

    def set_view(self, view):
        """
        Устанавливает ссылку на представление (диалог/окно).

        Args:
            view: объект с методами show_status, show_error, clear_form, refresh_transactions
        """
        self.view = view
        self.load_initial_data()

    # ================= Работа с транзакциями =================
    def add_transaction(self, raw_amount: str, trans_type: str, account_id: int,
                        category_id: Optional[int], description: str, date_str: str):
        """
        Обрабатывает добавление новой транзакции из UI.

        Args:
            raw_amount: строка суммы из поля ввода (например, "100*3")
            trans_type: тип операции ("income", "expense")
            account_id: ID выбранного счёта
            category_id: ID выбранной категории
            description: текст описания
            date_str: дата операции в формате YYYY-MM-DD
        """
        try:
            tx = self.service.create_transaction(
                raw_amount=raw_amount,
                trans_type=trans_type,
                account_id=account_id,
                category_id=category_id,
                description=description,
                date_str=date_str
            )
            if self.view:
                self.view.show_status(f"Транзакция ID{tx.id} добавлена")
                self.view.clear_form()
                self.view.refresh_transactions()
        except ValueError as e:
            if self.view:
                self.view.show_error(str(e))
        except Exception as e:
            logger.error(f"[TransactionPresenter] Ошибка добавления транзакции: {e}", exc_info=True)
            if self.view:
                self.view.show_error(f"Произошла ошибка: {e}")

    def delete_transaction(self, tx_id: int):
        """
        Обрабатывает удаление транзакции по ID.

        Args:
            tx_id: идентификатор транзакции для удаления
        """
        try:
            self.service.delete_transaction(tx_id)
            if self.view:
                self.view.show_status(f"Транзакция ID{tx_id} удалена")
                self.view.refresh_transactions()
        except ValueError as e:
            if self.view:
                self.view.show_error(str(e))
        except Exception as e:
            logger.error(f"[TransactionPresenter] Ошибка удаления транзакции #{tx_id}: {e}", exc_info=True)
            if self.view:
                self.view.show_error(f"Ошибка удаления: {e}")

    # ================= Работа с UI =================
    def refresh_data(self, current_type: str = "Расход"):
        """
        Обновляет данные в представлении (счета, категории, транзакции).
        используется при закрытии дочерних диалогов
        
        Args:
            current_type: текущий выбранный тип операции для сохранения состояния UI
        """
        if not self.view:
            return
        try:
            # 1. Загружаем актуальные списки счетов и категорий
            accounts = self.service.get_accounts_for_ui()
            self.all_categories = self.service.get_categories_for_ui()
            
            # 2. Обновляем кэши и комбобокс счетов
            self.create_caches(accounts, self.all_categories)
            self.view.load_accounts_combos(accounts)
            
            # 3. Обновляем комбобокс категорий с учётом текущего выбранного типа
            self.update_categories_for_type(current_type)
            
            # 4. Перезагружаем таблицу транзакций
            self.load_transactions(limit=300)
            
        except Exception as e:
            logger.error(f"[TransactionPresenter] Ошибка обновления данных: {e}", exc_info=True)
            if self.view:
                self.view.show_error(f"Ошибка обновления данных: {e}")

    def load_initial_data(self):
        """Загружает начальные данные при открытии диалога."""
        if not self.view:
            return

        try:
            # 1. Загружаем ВСЕ категории и счета (один раз)
            accounts = self.service.get_accounts_for_ui()
            self.all_categories = self.service.get_categories_for_ui()

            # 2. Создаём кэши в UI
            self.create_caches(accounts, self.all_categories)

            # 3. Загружаем категории для типа по умолчанию ("Расход") и счета (в комбокс)
            self.update_categories_for_type("Расход")
            self.view.load_accounts_combos(accounts)

            # 4. Загружаем таблицу транзакций
            self.load_transactions()
        except Exception as e:
            logger.error(f"[TransactionPresenter] Ошибка загрузки начальных данных: {e}", exc_info=True)
            if self.view:
                self.view.show_error(f"Ошибка загрузки данных: {e}")

    def update_categories_for_type(self, ui_type: str):
        """
        Фильтрует ВСЕ категории по типу (без запроса к БД).

        Args:
            ui_type: "Доход" или "Расход"
        """
        # Маппинг UI → БД
        db_type = "income" if ui_type == "Доход" else "expense"

        # Фильтруем ЛОКАЛЬНО (без запроса к БД)
        filtered = [cat for cat in self.all_categories if cat.cat_type == db_type]

        self.view.load_categories_combos(filtered)

    def create_caches(self, accounts: List[Account], categories: List[Category]):
        """
        Создаёт кэши для быстрого поиска счетов и категорий по ID.
        Передаёт кэши в представление (OperationDialog).

        Args:
            accounts: список объектов Account из сервиса
            categories: список объектов Category из сервиса
        """
        if not self.view:
            return

        # Сохраняем кэши в самом презентере (опционально, для внутренних нужд)
        self._account_cache = {acc.id: acc for acc in accounts}
        self._category_cache = {cat.id: cat for cat in categories}

        # Передаём кэши в UI для отрисовки таблицы и форматирования
        self.view.create_caches(accounts, categories)

    def load_transactions(self, limit: int = 300):
        """
        Загружает транзакции из БД и передает их в представление для отрисовки.

        Args:
            limit: количество записей для загрузки (по умолчанию 300)
        """
        try:
            transactions = self.service.get_latest_transactions(limit)
            if self.view:
                self.view.load_transactions(transactions)
        except Exception as e:
            logger.error(f"[TransactionPresenter] Ошибка загрузки транзакций: {e}", exc_info=True)
            if self.view:
                self.view.show_error(f"Ошибка загрузки транзакций: {e}")
