# services/transaction_service.py
import logging
from decimal import Decimal
from core.repositories.transaction_repository import TransactionRepository
from core.repositories.account_repository import AccountRepository
from core.repositories.category_repository import CategoryRepository
from core.repositories.transfer_repository import TransferRepository
from core.models import Transaction, Account, Category, Transfer
from typing import Tuple, List, Union, Optional, Dict
from datetime import date, datetime
from utils.validators import to_decimal

logger = logging.getLogger(__name__)


class TransactionService:
    """Сервис управления транзакциями: валидация, расчёты, обновление балансов."""

    def __init__(self, tx_repo: TransactionRepository, acc_repo: AccountRepository,
                 cat_repo: CategoryRepository, tr_repo: TransferRepository): 
        """
        Инициализация сервиса.

        Args:
            tx_repo: репозиторий транзакций для CRUD-операций
            acc_repo: репозиторий счетов для проверки и обновления баланса
        """
        self.tx_repo = tx_repo
        self.acc_repo = acc_repo
        self.cat_repo = cat_repo
        self.tr_repo = tr_repo

    # ------Работа с транзакциями------
    def create_transaction(
        self,
        raw_amount: Union[str, Decimal],
        trans_type: str,
        account_id: int,
        category_id: int,
        description: str,
        date_str: str,
        original_transaction_id: Optional[int] = None
    ) -> Transaction:
        """
        Создаёт транзакцию с парсингом суммы, валидацией и обновлением баланса счёта.

        Принимает сумму в двух форматах:
        - Decimal: прямое значение (например, из CreditService)
        - str: строка с возможностью выражения "сумма * количество"
            (например, "100 * 5" = 500, или "104883,10")

        Args:
            raw_amount: сумма транзакции (Decimal или строка суммы из UI, например, "100*3" или "10,50")
            trans_type: тип операции ("income", "expense", "refund", "correct")
            account_id: ID счёта
            category_id: ID категории
            description: описание операции/транзакции
            date_str: дата в формате YYYY-MM-DD
            original_transaction_id: ID оригинальной транзакции (для возвратов).
                                    Если None — транзакция не является возвратом.

        Returns:
            Созданный объект Transaction с заполненным полем id

        Raises:
            ValueError: если сумма некорректна или <= 0, или данные не валидны
            Exception: при системной ошибке
        """
        try:
            if not isinstance(account_id, int) or account_id <= 0:
                raise ValueError("Некорректный ID счёта")
            if not isinstance(category_id, int) or category_id <= 0:
                raise ValueError("Некорректный ID категории")
            
            # Валидация original_transaction_id, если передан
            if original_transaction_id is not None:
                if not isinstance(original_transaction_id, int) or original_transaction_id <= 0:
                    raise ValueError(f"Некорректный ID оригинальной транзакции: {original_transaction_id}")

            # 1. Парсинг суммы и количества (возвращает Decimal)
            amount_positive, quantity = self._parse_amount(raw_amount)

            # Считаем общую сумму
            amount_summ = amount_positive * quantity
            total_amount = to_decimal(amount_summ)

            if total_amount <= 0:
                raise ValueError(f"Сумма должна быть > 0, получено: {total_amount}")

            # 2. Бизнес-валидация
            self._validate_inputs(trans_type, account_id, category_id, total_amount)

            # 3. Применение знака по типу 
            # TODO: не забудь отипизировать применение знака
            # signed_amount = total_amount if trans_type == "income" else -total_amount            
            if  trans_type == "income":
                signed_amount = total_amount
            elif trans_type == "expense":
                signed_amount = -total_amount
            elif trans_type == "refund":
                signed_amount = to_decimal(raw_amount)
            else:
                raise ValueError(f"Некорректный тип транзакции: {trans_type}")      
            
            # 4. Сборка объекта
            transaction = Transaction(
                date=date_str,
                amount=signed_amount,
                trans_type=trans_type,
                account_id=account_id,
                category_id=category_id,
                description=description.strip(),
                quantity=quantity,
                original_transaction_id=original_transaction_id
            )

            # 5. Сохранение в БД
            saved_tx = self.tx_repo.create(transaction)

            logger.debug(f"[TransactionService] ID создаваемой транзакции = {saved_tx.id}")

            # 6. Обновление баланса счёта
            self._update_account_balance(account_id, signed_amount)

            return saved_tx

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[TransactionService] Критическая ошибка при создании транзакции: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise RuntimeError(f"Системная ошибка при создании транзакции: {e}") from e

    def delete_transaction(self, tx_id: int) -> bool:
        """
        Удаляет транзакцию с коррекцией баланса счёта.

        Args:
            tx_id: ID транзакции для удаления

        Returns:
            True при успешном удалении
        """
        try:
            # Получаем транзакцию, чтобы вернуть баланс на место
            tx = self.tx_repo.get_by_id(tx_id)
            if not tx:
                raise ValueError(f"Транзакция #{tx_id} не найдена")

            # Удаляем запись
            self.tx_repo.delete(tx_id)

            # Возвращаем баланс: вычитаем сумму (т.к. она уже со знаком)
            self._update_account_balance(tx.account_id, -tx.amount)
            return True

        except ValueError as e:
            logger.warning(f"[TransactionService] Валидация при удалении: {e}")
            raise
        except Exception as e:
            logger.error(f"[TransactionService] Критическая ошибка при удалении транзакции #{tx_id}: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise RuntimeError(f"Системная ошибка при удалении транзакции: {e}") from e

    def update_transaction(
        self,
        transaction_id: int,
        raw_amount: str,
        trans_type: str,
        account_id: int,
        category_id: Optional[int],
        description: str,
        date_str: str
    ) -> Transaction:
        """
        Обновляет существующую транзакцию с пересчётом баланса счёта.
        
        Алгоритм:
        1. Получает старую транзакцию.
        2. Откатывает её влияние на баланс старого счёта.
        3. Парсит и валидирует новые данные.
        4. Сохраняет обновлённую транзакцию.
        5. Применяет новое влияние на баланс (возможно, нового) счёта.

        Args:
            transaction_id: ID транзакции для обновления
            raw_amount: строка суммы (может содержать "*", например "100*2")
            trans_type: тип транзакции ('income', 'expense', 'correct')
            account_id: ID счёта
            category_id: ID категории (None для корректировки)
            description: описание транзакции
            date_str: дата в формате yyyy-MM-dd

        Returns:
            Обновлённый объект Transaction

        Raises:
            ValueError: если транзакция не найдена или данные некорректны
            Exception: при системной ошибке
        """
        try:
            # 1. Получаем старую транзакцию через существующий метод репозитория
            old_tx = self.tx_repo.get_by_id(transaction_id)
            if not old_tx:
                raise ValueError(f"Транзакция с ID {transaction_id} не найдена")

            # 2. Парсим новую сумму (используем ваш существующий метод парсинга)
            amount_positive, quantity = self._parse_amount(raw_amount)
            total_amount = to_decimal(amount_positive * quantity)

            # 3. Валидация новых данных
            if total_amount <= 0:
                raise ValueError(f"Сумма должна быть > 0, получено: {total_amount}")
            
            if trans_type not in ['income', 'expense', 'correct']:
                raise ValueError(f"Некорректный тип транзакции: {trans_type}")
            
            if trans_type != 'correct' and not category_id:
                raise ValueError("Для дохода или расхода обязательна категория")

            # 4. Применяем знак к новой сумме
            signed_amount = total_amount if trans_type == "income" else -total_amount

            # 5. Откатываем старую транзакцию с баланса старого счёта
            self._update_account_balance(old_tx.account_id, -old_tx.amount)
            logger.debug(
                f"[{self.__class__.__name__}] Откат баланса счёта {old_tx.account_id}: {-old_tx.amount}"
            )

            # 6. Собираем новый объект транзакции (сохраняем original_transaction_id, если был)
            updated_tx = Transaction(
                id=transaction_id,
                date=date_str,
                amount=signed_amount,
                trans_type=trans_type,
                account_id=account_id,
                category_id=category_id,
                description=description.strip(),
                quantity=quantity,
                original_transaction_id=old_tx.original_transaction_id
            )

            # 7. Сохраняем в репозитории
            self.tx_repo.update(updated_tx)
            logger.debug(f"[{self.__class__.__name__}] Транзакция ID={transaction_id} обновлена в БД")

            # 8. Применяем новую транзакцию к балансу (возможно, уже нового) счёта
            self._update_account_balance(account_id, signed_amount)
            logger.debug(
                f"[{self.__class__.__name__}] Применение к балансу счёта {account_id}: {signed_amount}"
            )

            logger.info(f"[{self.__class__.__name__}] Транзакция ID={transaction_id} успешно обновлена")
            return updated_tx

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация обновления: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обновления транзакции ID={transaction_id}: {e}", exc_info=True)
            raise
    # ------Проверки, валидация, преобразование------
    def _parse_amount(self, raw_amount: Union[str, Decimal]) -> Tuple[Decimal, Decimal]:
        """
        Парсит сумму транзакции из строки или Decimal.

        Поддерживает два формата:
        - Decimal: возвращается как есть, quantity = 1
        - str: может содержать выражение "сумма * количество"
               (например, "100 * 5" → amount=100, quantity=5)
               или просто число ("104883,10" → amount=104883.10, quantity=1)

        Args:
            raw_amount: сумма в виде Decimal или строки

        Returns:
            Кортеж (amount, quantity), где:
            - amount: Decimal, положительная сумма
            - quantity: Decimal, количество (по умолчанию 1)

        Raises:
            ValueError: если формат некорректен
        """
        try:
            # Если уже Decimal — просто возвращаем
            if isinstance(raw_amount, Decimal):
                if raw_amount < 0:
                    return abs(raw_amount), Decimal("1")
                return raw_amount, Decimal("1")

            # Если не строка — ошибка
            if not isinstance(raw_amount, str):
                raise ValueError(
                    f"Ожидается Decimal или str, получено: {type(raw_amount).__name__}"
                )

            # Парсим строку
            normalized = raw_amount.replace(" ", "").replace(",", ".")

            if not normalized:
                raise ValueError("Сумма не может быть пустой")

            # Проверяем наличие выражения "сумма * количество"
            if "*" in normalized:
                parts = normalized.split("*")
                if len(parts) != 2:
                    raise ValueError(
                        f"Некорректный формат выражения: '{raw_amount}'"
                    )

                amount = Decimal(parts[0].strip())
                quantity = Decimal(parts[1].strip())

                if quantity <= 0:
                    raise ValueError(
                        f"Количество должно быть > 0, получено: {quantity}"
                    )

                return amount, quantity

            # Простое число
            amount = Decimal(normalized)
            return amount, Decimal("1")

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация суммы: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка парсинга суммы: {e}",
                exc_info=True,
            )
            raise

    def _validate_inputs(self, trans_type: str, account_id: int, category_id: int, amount: Decimal):
        """
        Проверяет бизнес-правила перед сохранением транзакции.

        Args:
            trans_type: тип операции
            account_id: ID счёта
            category_id: ID категории
            amount: итоговая сумма операции
        """
        if trans_type not in ("income", "expense", "correct", "refund"):
            raise ValueError(f"Недопустимый тип транзакции: {trans_type}")

        if amount <= 0:
            raise ValueError("Сумма операции должна быть больше нуля")

        account = self.acc_repo.get_by_id(account_id)
        if not account:
            raise ValueError(f"Счёт #{account_id} не найден")
        if not account.is_active:
            raise ValueError(f"Счёт '{account.name}' деактивирован")

        # Корректировка может быть без категории, остальные требуют
        if trans_type != "correct" and not category_id:
            raise ValueError("Для доходов/расходов необходимо указать категорию")

    # ------Обработчики UI------
    def _update_account_balance(self, account_id: int, amount: Decimal):
        """
        Обновляет текущий баланс счёта на указанную сумму.

        Args:
            account_id: ID счёта для обновления
            amount: сумма с учётом знака (+ для дохода, - для расхода)
        """
        try:
            account = self.acc_repo.get_by_id(account_id)
            if account:
                account.current_balance = (account.current_balance + amount).quantize(Decimal("0.01"))
                self.acc_repo.update(account)
        except Exception as e:
            logger.error(f"[TransactionService] Ошибка обновления баланса счёта #{account_id}: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise

    def get_accounts_for_ui(self) -> List[Account]:
        """
        Возвращает список активных  счетов для заполнения комбобокса.

        Returns:
            Список объектов Account
        """
        try:
            return self.acc_repo.get_all_active()
        except Exception as e:
            logger.error(f"[TransactionService] Ошибка загрузки счетов: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise
    
    def get_categories_for_ui(self) -> List[Category]:
        """Возвращает список активные  категории для UI (комбоксов) (без фильтров)."""
        try:
            return self.cat_repo.get_all_active_categories()
        except Exception as e:
            logger.error(f"[TransactionService] Ошибка загрузки всех категорий: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise

    def get_categories_by_type(self, ui_type: str) -> List[Category]:
        """
        Возвращает категории для указанного типа операции из UI.

        Args:
            ui_type: строка из UI ("Доход" или "Расход")

        Returns:
            Список объектов Category
        """
        try:
            # Маппинг UI -> БД
            db_type = "income" if ui_type == "Доход" else "expense"
            return self.cat_repo.get_all_by_type(db_type)
        except Exception as e:
            logger.error(f"[TransactionService] Ошибка загрузки категорий: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise

    def get_latest_transactions(self, limit: int = 300) -> List[Transaction]:
        """
        Возвращает последние N транзакций для отображения в UI.

        Args:
            limit: максимальное количество записей (по умолчанию 300)

        Returns:
            Список объектов Transaction, отсортированный по дате (новые первыми)
        """
        try:
            return self.tx_repo.get_latest(limit)
        except Exception as e:
            logger.error(f"[TransactionService] Ошибка загрузки транзакций: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise

    def get_transactions_by_date(self, date: datetime.date) -> List[Transaction]:
        """
        ЗАГЛУШКА
        Возвращает транзакции за указанную дату для отображения в UI.

        Args:
            date: дата в формате datetime.date

        Returns:
            Список объектов Transaction, отсортированный по дате (новые первыми)
        """
        try:
            return #self.tx_repo.get_by_date(date)
        except Exception as e:
            logger.error(f"[TransactionService] Ошибка загрузки транзакций: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise

    def get_by_id(self, tx_id: int) -> Transaction:
        """
        Возвращает транзакцию по ID для отображения в UI.

        Args:
            tx_id: ID транзакции

        Returns:
            Объект Transaction
        """
        try:
            return self.tx_repo.get_by_id(tx_id)
        except Exception as e:
            logger.error(f"[TransactionService] Ошибка загрузки транзакции: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise

    def get_refunds_for_transaction(self, original_transaction_id: int) -> List[Transaction]:
        """
        Возвращает список всех возвратов для указанной оригинальной транзакции.

        Args:
            original_transaction_id: ID оригинальной транзакции

        Returns:
            Список объектов Transaction с trans_type='refund'
            Если не найдено, возвращается пустой список
        """
        try:
            return self.tx_repo.get_refunds_for_transaction(original_transaction_id)
        except Exception as e:
            logger.error(f"[TransactionService] Ошибка загрузки возвратов: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise

    def get_filtered_transactions(self, filters: Optional[Dict] = None, limit: int = 300) -> List[Transaction]:
        """
        Возвращает отфильтрованные транзакции через репозиторий.

        Тонкая прослойка — делегирует запрос в репозиторий.
        При необходимости сюда можно добавить дополнительную бизнес-валидацию.

        Args:
            filters: словарь с параметрами фильтрации (см. TransactionRepository.get_filtered)
            limit: максимальное количество записей (по умолчанию 300)

        Returns:
            Список объектов Transaction

        Raises:
            ValueError: если параметры некорректны
            Exception: при системной ошибке
        """
        try:
            return self.tx_repo.get_filtered(filters=filters, limit=limit)

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения отфильтрованных транзакций: {e}", exc_info=True)
            raise

    def get_bank_comparison_summary(self, start_date: datetime, end_date: datetime, account_id: int) -> dict:
        """
        Агрегирует транзакции и переводы за период для сверки с банковским приложением.

        Args:
            start_date: Начало периода (включительно).
            end_date: Конец периода (включительно).
            account_id: Идентификатор счета, по которому формируется сводка.

        Returns:
            dict: Словарь с агрегированными суммами:
                - income (float): Общие доходы.
                - expenses (float): Общие расходы.
                - transfers_in (float): Поступления от переводов.
                - transfers_out (float): Исходящие переводы.
                - refunds (float): Возвраты средств.
                - total_in (float): Все поступления за период.
                - total_out (float): Все списания за период.

        Raises:
            ValueError: Если start_date > end_date или account_id некорректен.
        """
        try:
            # 1. Валидация входных данных
            if start_date > end_date:
                raise ValueError(f"Дата начала ({start_date}) не может быть позже даты окончания ({end_date})")

            if not isinstance(account_id, int) or account_id <= 0:
                raise ValueError(f"Некорректный ID счета: {account_id}")

            # 2. Фильтры периода
            period_filters = {
                'account_id': account_id,
                'date_from': start_date,
                'date_to': end_date,
                'is_system': None # Указываем что нужный все переводы
            }

            # 3. Получение данных из репозиториев
            transactions = self.tx_repo.get_filtered(filters=period_filters)
            transfers = self.tr_repo.get_filtered(filters=period_filters)

            # 4. Счетчики в Decimal — точность денежных расчетов
            income = Decimal("0.00")
            expenses = Decimal("0.00")
            transfers_in = Decimal("0.00")
            transfers_out = Decimal("0.00")
            refunds = Decimal("0.00")
            total_in = Decimal("0.00")
            total_out = Decimal("0.00")

            # 5. Агрегация транзакций (по trans_type)
            for tx in transactions:
                amount = abs(tx.amount)

                if tx.trans_type == "refund":
                    # Возврат — поступление на счет
                    refunds += amount
                    total_in += amount

                elif tx.trans_type == "income":
                    # Доход — поступление 
                    income += amount
                    total_in += amount

                elif tx.trans_type == "expense":
                    # Расход — списание
                    expenses += amount
                    total_out += amount

            # 6. Агрегация переводов (направление по from/to счетам)
            for tr in transfers:
                amount = abs(tr.amount)

                if tr.to_account_id == account_id:
                    # Входящий перевод — поступление
                    transfers_in += amount
                    total_in += amount
                elif tr.from_account_id == account_id:
                    # Исходящий перевод — списание
                    transfers_out += amount
                    total_out += amount

            # 7. Формирование результата
            summary = {
                "income": round(float(income), 2),
                "expenses": round(float(expenses), 2),
                "transfers_in": round(float(transfers_in), 2),
                "transfers_out": round(float(transfers_out), 2),
                "refunds": round(float(refunds), 2),
                "total_in": round(float(total_in), 2),
                "total_out": round(float(total_out), 2)
            }

            logger.debug(f"[{self.__class__.__name__}] Сводка сформирована для счета {account_id}: {summary}")
            return summary

        except ValueError as e:
            # Ожидаемые ошибки валидации
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            # Системные ошибки
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise