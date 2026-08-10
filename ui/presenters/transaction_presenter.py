# ui/presenters/transaction_presenter.py
from typing import Optional
from typing import List, Dict
import logging
from services.transaction_service import TransactionService
from core.models import Transaction, Account, Category
from utils.validators import to_decimal


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
                self.view.show_status(f"Транзакция создана. ID: {tx.id}, Сумма: {tx.amount}", message_type="success")
                self.view.clear_form()
                self.view.refresh_transactions()
                self.view.amount_input.setFocus()
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
                self.view.show_status(f"Транзакция ID: {tx_id} - удалена", message_type="success")
                self.view.refresh_transactions()
        except ValueError as e:
            if self.view:
                self.view.show_error(str(e))
        except Exception as e:
            logger.error(f"[TransactionPresenter] Ошибка удаления транзакции #{tx_id}: {e}", exc_info=True)
            if self.view:
                self.view.show_error(f"Ошибка удаления: {e}")

    def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """
        Возвращает транзакцию по ID.
        
        Args:
            transaction_id: идентификатор транзакции
        
        Returns:
            Объект Transaction или None, если не найдена
        
        Raises:
            ValueError: если ID некорректен
        """
        try:
            if not isinstance(transaction_id, int) or transaction_id <= 0:
                raise ValueError(f"Некорректный ID транзакции: {transaction_id}")
            
            return self.service.get_by_id(transaction_id)
        
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения транзакции: {e}", exc_info=True)
            raise
    
    def update_transaction(
        self,
        transaction_id: int,
        raw_amount: str,
        trans_type: str,
        account_id: int,
        category_id: Optional[int],
        description: str,
        date_str: str
    ):
        """
        Обновляет транзакцию через сервис и инициирует обновление View.

        Args:
            transaction_id: ID транзакции
            raw_amount: строка суммы (например, "100*3")
            trans_type: тип операции ('income', 'expense', 'correct')
            account_id: ID счёта
            category_id: ID категории (None для корректировки)
            description: описание
            date_str: дата (yyyy-MM-dd)

        Raises:
            ValueError: при некорректных данных
            Exception: при системной ошибке
        """
        try:
            # Если это корректировка и категория не передана, можно подставить системную или None
            # (зависит от вашей бизнес-логики, здесь оставляем как есть)
            
            self.service.update_transaction(
                transaction_id=transaction_id,
                raw_amount=raw_amount,
                trans_type=trans_type,
                account_id=account_id,
                category_id=category_id,
                description=description,
                date_str=date_str
            )

            # Сообщаем View, что нужно перезагрузить данные
            if self.view:
                # Предполагается, что во View есть метод refresh_transactions
                self.view.refresh_transactions()

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обновления: {e}", exc_info=True)
            raise

    # возврат транзакции
    def get_refund_info(self, original_transaction_id: int) -> dict:
        """
        Возвращает информацию о доступной сумме возврата по оригинальной транзакции.

        Args:
            original_transaction_id: ID оригинальной транзакции

        Returns:
            Словарь:
            - max_refundable: Decimal, доступная сумма для возврата
            - already_refunded: Decimal, уже возвращённая сумма
            - original_amount: Decimal, абсолютная сумма оригинала

        Raises:
            ValueError: если оригинальная транзакция не найдена
            Exception: при системной ошибке
        """
        try:
            if not isinstance(original_transaction_id, int) or original_transaction_id <= 0:
                raise ValueError(f"Некорректный ID транзакции: {original_transaction_id}")

            original = self.service.get_by_id(original_transaction_id)
            if not original:
                raise ValueError(f"Транзакция ID={original_transaction_id} не найдена")

            if original.trans_type not in ["income", "expense"]:
                raise ValueError(
                    "Возврат можно создать только для операции типа Доход или Расход"
                )

            # Получаем все существующие возвраты
            refunds = self.service.get_refunds_for_transaction(original_transaction_id)

            original_amount = abs(original.amount)
            already_refunded = sum(abs(r.amount) for r in refunds)
            max_refundable = original_amount - already_refunded

            return {
                "max_refundable": max_refundable,
                "already_refunded": already_refunded,
                "original_amount": original_amount,
            }

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка получения информации о возврате: {e}",
                exc_info=True,
            )
            raise


    def create_refund(self, original_transaction_id: int, data: dict) -> Transaction:
        """
        Создаёт возврат по оригинальной транзакции.

        Знак суммы определяется автоматически:
        - Если оригинал был Расход (amount < 0) → возврат положительный (+X)
        - Если оригинал был Доход (amount > 0) → возврат отрицательный (-X)

        Args:
            original_transaction_id: ID оригинальной транзакции
            data: словарь с параметрами возврата:
                - date: str, формат yyyy-MM-dd
                - amount: float, положительная сумма возврата
                - description: str, описание возврата

        Returns:
            Созданный объект Transaction с trans_type='refund'

        Raises:
            ValueError: если оригинал не найден, данные некорректны или сумма превышает доступную
            Exception: при системной ошибке
        """
        try:
            if not isinstance(original_transaction_id, int) or original_transaction_id <= 0:
                raise ValueError(f"Некорректный ID транзакции: {original_transaction_id}")

            if not isinstance(data, dict):
                raise ValueError("Параметр data должен быть словарём")

            # Валидация обязательных ключей
            required_keys = {"date", "amount", "description"}
            missing_keys = required_keys - set(data.keys())
            if missing_keys:
                raise ValueError(f"В data отсутствуют ключи: {missing_keys}")

            # Получаем оригинальную транзакцию
            original = self.service.get_by_id(original_transaction_id)
            if not original:
                raise ValueError(f"Оригинальная транзакция ID={original_transaction_id} не найдена")

            if original.trans_type not in ["income", "expense"]:
                raise ValueError("Возврат можно создать только для операции типа Доход или Расход")

            # Проверяем доступную сумму
            refund_info = self.get_refund_info(original_transaction_id)
            amount = to_decimal(data["amount"])

            if amount <= 0:
                raise ValueError("Сумма возврата должна быть больше нуля")

            if amount > refund_info["max_refundable"]:
                raise ValueError(
                    f"Сумма возврата ({amount}) превышает доступную "
                    f"({refund_info['max_refundable']})"
                )

            # Определяем знак: инвертируем знак оригинала
            # Расход (отрицательный) → возврат положительный
            # Доход (положительный) → возврат отрицательный
            signed_amount = -amount if original.trans_type == "income" else amount

            # Сохраняем в БД
            saved_tx = self.service.create_transaction(
                raw_amount=str(signed_amount),
                trans_type="refund",
                account_id=original.account_id,
                category_id=original.category_id,
                description=str(data["description"].strip()),
                date_str=str(data["date"]),
                original_transaction_id=original_transaction_id,
                )
            logger.debug(f"[{self.__class__.__name__}] Создан возврат ID={saved_tx.id}")

            # Обновляем баланс счёта
            # self.account_service.update_balance(original.account_id, signed_amount)
            logger.debug(
                f"[{self.__class__.__name__}] Баланс счёта {original.account_id} "
                f"обновлён на {signed_amount}"
            )

            logger.info(
                f"[{self.__class__.__name__}] Возврат ID={saved_tx.id} создан "
                f"для транзакции ID={original_transaction_id}, сумма={signed_amount}"
            )
            return saved_tx

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация возврата: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка создания возврата: {e}",
                exc_info=True,
            )
            raise

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

    def load_with_filters(self, filters: Optional[Dict] = None):
        """
        Загружает транзакции с учётом фильтров и передаёт их в View.

        Координирует вызов сервиса и обновление таблицы.
        При ошибке показывает сообщение пользователю через View.

        Args:
            filters: словарь с параметрами фильтрации. Если None — загружает последние 300 записей.

        Raises:
            ValueError: при некорректных параметрах
            Exception: при системной ошибке
        """
        try:
            if filters:
                transactions = self.service.get_filtered_transactions(filters=filters, limit=300)
                logger.debug(f"[{self.__class__.__name__}] Загружено {len(transactions)} транзакций с фильтрами")
            else:
                transactions = self.service.get_filtered_transactions(filters=None, limit=300)
                logger.debug(f"[{self.__class__.__name__}] Загружено {len(transactions)} транзакций без фильтров")

            if self.view:
                self.view.load_transactions(transactions)

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация загрузки: {e}")
            if self.view:
                self.view.show_status(str(e), message_type="error")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка загрузки транзакций: {e}", exc_info=True)
            if self.view:
                self.view.show_status("Произошла ошибка при загрузке операций", message_type="error")
            raise

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
