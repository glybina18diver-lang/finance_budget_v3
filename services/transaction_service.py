# services/transaction_service.py
import logging
from core.repositories.transaction_repository import TransactionRepository
from core.repositories.account_repository import AccountRepository
from core.repositories.category_repository import CategoryRepository
from core.repositories.credit_card_repository import CreditCardRepository
from services.credit_card_service import CreditCardService

from services.tranche_service import TrancheService
from core.models import Transaction, Account, Category
from typing import Tuple, List
from datetime import date, datetime
from decimal import Decimal
import re

logger = logging.getLogger(__name__)


class TransactionService:
    """Сервис управления транзакциями: валидация, расчёты, обновление балансов."""

    def __init__(self, tx_repo: TransactionRepository, acc_repo: AccountRepository,
                 cat_repo: CategoryRepository, tranche_service=TrancheService, credit_card_service=CreditCardService):
        """
        Инициализация сервиса.

        Args:
            tx_repo: репозиторий транзакций для CRUD-операций
            acc_repo: репозиторий счетов для проверки и обновления баланса
        """
        self.tx_repo = tx_repo
        self.acc_repo = acc_repo
        self.cat_repo = cat_repo
        self.tranche_service = tranche_service
        self.credit_card_service = credit_card_service

    # ------Работа с транзакциями------
    def create_transaction(self, raw_amount: str, trans_type: str, account_id: int,
                           category_id: int, description: str, date_str: str) -> Transaction:
        """
        Создаёт транзакцию с парсингом суммы, валидацией и обновлением баланса счёта.

        Args:
            raw_amount: строка суммы из UI (например, "100*3" или "10,50")
            trans_type: тип операции ("income", "expense", "correct")
            account_id: ID счёта
            category_id: ID категории
            description: описание операции
            date_str: дата в формате YYYY-MM-DD

        Returns:
            Сохранённый объект Transaction с присвоенным ID

        Raises:
            ValueError: при некорректном формате суммы или данных
        """
        try:
            if not isinstance(account_id, int) or account_id <= 0:
                raise ValueError("Некорректный ID счёта")
            if not isinstance(category_id, int) or category_id <= 0:
                raise ValueError("Некорректный ID категории")

            # 1. Парсинг суммы и количества
            amount_positive, quantity = self._parse_amount(raw_amount)

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

            # 7. Обновление баланса счёта
            self._update_account_balance(account_id, signed_amount)
            
            # конвертируем перед вызовом
            amount_decimal = Decimal(str(amount_positive))
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

            # 6. ОБРАБОТКА КРЕДИТНОЙ КАРТЫ (если это расход с кредитки)
            if trans_type == "expense":
                self._handle_credit_card_expense(account_id, amount_decimal, date_obj, saved_tx.id)
            return saved_tx

        except ValueError as e:
            logger.warning(f"[TransactionService] Валидация: {e}")
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

    def _handle_credit_card_expense(
        self, 
        account_id: int, 
        amount: Decimal, 
        date: date, 
        transaction_id: int
    ):
        """
        Метод-посредник: если счёт — кредитная карта, создаёт транш покупки.
        Вызывается после создания расхода.

        Args:
            account_id: ID счёта
            amount: сумма расхода (положительное число, Decimal)
            date: дата транзакции (объект date)
            transaction_id: ID созданной транзакции (для связи)
            
        Raises:
            ValueError: при ошибках валидации данных транша
            Exception: при системных ошибках БД или сервиса
        """
        if not self.tranche_service:
            logger.debug("[TransactionService] TrancheService не подключён, пропускаем создание транша")
            return

        try:
            # Проверяем, является ли счёт кредитной картой
            account = self.acc_repo.get_by_id(account_id)
            if not account or account.account_type != 'CreditCard':
                logger.debug(f"[TransactionService] Счёт ID {account_id} не является CreditCard")
                return

            # Создаём транш покупки
            self.credit_card_service.add_purchase_by_account(
                account_id=account_id,
                amount=amount,
                transaction_date=date,
                transaction_id=transaction_id
            )

        except ValueError as e:
            logger.warning(f"[TransactionService] Ошибка валидации при создании транша: {e}")
            raise
        except Exception as e:
            logger.error(f"[TransactionService] Системная ошибка при создании транша: {e}", exc_info=True)
            raise

    # ------Проверки, валидация, преобразование------
    def _parse_amount(self, raw: str) -> Tuple[float, float]:
        """
        Разбирает строку суммы: поддерживает "100*3", "10,50", "1000".

        Args:
            raw: исходная строка из поля ввода

        Returns:
            Кортеж (общая_сумма, количество)

        Raises:
            ValueError: при недопустимом формате
        """
        normalized = raw.replace(",", ".").strip()

        # Формат "сумма*количество"
        if "*" in normalized:
            parts = normalized.split("*", maxsplit=1)
            if len(parts) != 2:
                raise ValueError("Некорректный формат умножения. Используйте: сумма*количество")
            unit_price = float(parts[0])
            quantity = float(parts[1])
            if quantity <= 0:
                raise ValueError("Количество должно быть больше 0")
            return round(unit_price * quantity, 2), quantity

        # Обычное число
        total = float(normalized)
        if total <= 0:
            raise ValueError("Сумма должна быть положительным числом")
        return total, 1.0

    def _validate_inputs(self, trans_type: str, account_id: int, category_id: int, amount: float):
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
    def _update_account_balance(self, account_id: int, amount: float):
        """
        Обновляет текущий баланс счёта на указанную сумму.

        Args:
            account_id: ID счёта для обновления
            amount: сумма с учётом знака (+ для дохода, - для расхода)
        """
        try:
            account = self.acc_repo.get_by_id(account_id)
            if account:
                account.current_balance = round(account.current_balance + amount, 2)
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