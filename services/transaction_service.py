# services/transaction_service.py
import logging
from decimal import Decimal
from core.repositories.transaction_repository import TransactionRepository
from core.repositories.account_repository import AccountRepository
from core.repositories.category_repository import CategoryRepository
from core.models import Transaction, Account, Category
from typing import Tuple, List, Union
from datetime import date, datetime
from utils.validators import to_decimal

logger = logging.getLogger(__name__)


class TransactionService:
    """Сервис управления транзакциями: валидация, расчёты, обновление балансов."""

    def __init__(self, tx_repo: TransactionRepository, acc_repo: AccountRepository,
                 cat_repo: CategoryRepository):
        """
        Инициализация сервиса.

        Args:
            tx_repo: репозиторий транзакций для CRUD-операций
            acc_repo: репозиторий счетов для проверки и обновления баланса
        """
        self.tx_repo = tx_repo
        self.acc_repo = acc_repo
        self.cat_repo = cat_repo

    # ------Работа с транзакциями------
    def create_transaction(self, raw_amount: Union[str, Decimal], trans_type: str, account_id: int,
                           category_id: int, description: str, date_str: str) -> Transaction:
        """
        Создаёт транзакцию, с парсингом суммы, валидацией и обновлением баланса счёта.

        Принимает сумму в двух форматах:
        - Decimal: прямое значение (например, из CreditService)
        - str: строка с возможностью выражения "сумма * количество"
               (например, "100 * 5" = 500, или "104883,10")

        Args:
            raw_amount: сумма транзакции (Decimal или строка суммы из UI (например, "100*3" или "10,50")
            trans_type: тип операции ("income", "expense", "correct")
            account_id: ID счёта
            category_id: ID категории
            description: описание операции/транзакции
            date_str: дата в формате YYYY-MM-DD

        Returns:
            Созданный объект Transaction

        Raises:
            ValueError: если сумма некорректна или <= 0 или данных
            Exception: при системной ошибке
        """
        try:
            if not isinstance(account_id, int) or account_id <= 0:
                raise ValueError("Некорректный ID счёта")
            if not isinstance(category_id, int) or category_id <= 0:
                raise ValueError("Некорректный ID категории")
            
            # 1. Парсинг суммы и количества (возвращает Decimal)
            amount_positive, quantity = self._parse_amount(raw_amount)

            if amount_positive <= 0:
                raise ValueError(f"Сумма должна быть > 0, получено: {amount_positive}")

            # 2. Бизнес-валидация
            self._validate_inputs(trans_type, account_id, category_id, amount_positive)

            # 3. Применение знака по типу
            signed_amount = amount_positive if trans_type == "income" else -amount_positive

            # 4. Сборка объекта
            transaction = Transaction(
                date=date_str,
                amount=signed_amount,
                trans_type=trans_type,
                account_id=account_id,
                category_id=category_id,
                description=description.strip(),
                quantity=quantity
            )

            # 5. Сохранение в БД
            saved_tx = self.tx_repo.create(transaction)

            logger.debug(f"[TransactionService] ID создаваемой транзакции = {saved_tx.id}")

            # 6. Обновление баланса счёта
            self._update_account_balance(account_id, signed_amount)

            return saved_tx

            # вариант исполнгния логики
            # # Бизнес-логика создания транзакции
            # transaction = self.transaction_repo.create(
            #     account_id=account_id,
            #     category_id=category_id,
            #     amount=amount_positive,
            #     quantity=quantity,
            #     date=date,
            #     type=type,
            #     description=description,
            # )

            # # Обновляем баланс счёта
            # delta = amount_positive if type == "income" else -amount_positive
            # self.account_repo.update_balance(account_id, delta)

            # logger.info(
            #     f"[{self.__class__.__name__}] Создана транзакция "
            #     f"id={transaction.id}, type={type}, amount={amount_positive}"
            # )
            # return transaction

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
        if trans_type not in ("income", "expense", "correct"):
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
        Возвращает список активных счетов для заполнения комбобокса.

        Returns:
            Список объектов Account
        """
        try:
            return self.acc_repo.get_all_active()
        except Exception as e:
            logger.error(f"[TransactionService] Ошибка загрузки счетов: {e}")
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

    def get_all_categories(self) -> List[Category]:
        """Возвращает все категории для UI (без фильтрации)."""
        try:
            return self.cat_repo.get_all_categories()
        except Exception as e:
            logger.error(f"[TransactionService] Ошибка загрузки всех категорий: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise