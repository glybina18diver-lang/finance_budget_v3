"""
Репозиторий для работы со счетами.

Поддерживает следующие типы счетов:
- Cash: наличные
- BankAccount: банковский счёт
- CreditCard: кредитная карта
- Counterparty: контрагент (системный, для займов)
- Credit: кредит (системный, для банковских кредитов)
"""

from typing import Optional, Dict, Any, List
from decimal import Decimal
import logging

from core.db import Database
from core.models import Account
from utils.validators import to_decimal

logger = logging.getLogger(__name__)


class AccountRepository:
    """Репозиторий для работы со счетами."""

    def __init__(self, db: Database):
        """
        Инициализация репозитория.

        Args:
            db: экземпляр фасада Database для выполнения запросов
        """
        self.db = db

    def _row_to_account(self, row: Dict[str, Any]) -> Account:
        """
        Преобразует словарь из БД в объект счёта.
        Числовые поля конвертируются из float (SQLite REAL) в Decimal.

        Args:
            row: словарь с данными строки из БД

        Returns:
            Инициализированный объект Account
        """
        return Account(
            id=row.get("id"),
            name=row.get("name", ""),
            account_type=row.get("account_type", "Cash"),
            initial_balance=to_decimal(row.get("initial_balance", 0.0)),
            current_balance=to_decimal(row.get("current_balance", 0.0)),
            is_active=bool(row.get("is_active", 1)),
            is_system=bool(row.get("is_system", 0)),
            currency=row.get("currency", "RUB"),
        )

    def get_by_id(self, account_id: int) -> Optional[Account]:
        """
        Возвращает счёт по уникальному идентификатору.

        Args:
            account_id: ID искомого счёта

        Returns:
            Объект Account или None, если запись не найдена
        """
        try:
            query = "SELECT * FROM accounts WHERE id = ?"
            row = self.db.fetchone(query, (account_id,))
            return self._row_to_account(row) if row else None
        except Exception as e:
            logger.error(
                f"[AccountRepository] Ошибка получения счёта #{account_id}: {e}",
                exc_info=True,
            )
            raise

    def get_all_active(self) -> List[Account]:
        """
        Возвращает список всех активных счетов, отсортированных по имени.

        Returns:
            Список объектов Account
        """
        try:
            query = """
                SELECT * FROM accounts 
                WHERE is_active = 1 
                ORDER BY name
            """
            rows = self.db.fetchall(query)
            return [self._row_to_account(row) for row in rows]
        except Exception as e:
            logger.error(
                f"[AccountRepository] Ошибка получения активных счетов: {e}",
                exc_info=True,
            )
            raise

    def get_user_accounts(self) -> List[Account]:
        """
        Возвращает список пользовательских счетов для UI.

        Исключает системные счета типов 'Counterparty' и 'Credit',
        которые используются только для внутренней логики.

        Returns:
            Список объектов Account (Cash, BankAccount, CreditCard)
        """
        try:
            query = """
                SELECT * FROM accounts 
                WHERE is_active = 1 
                  AND is_system = 0
                ORDER BY name
            """
            rows = self.db.fetchall(query)
            return [self._row_to_account(row) for row in rows]
        except Exception as e:
            logger.error(
                f"[AccountRepository] Ошибка получения пользовательских счетов: {e}", exc_info=True)
            raise

    def get_by_name(self, name: str) -> Optional[Account]:
        """
        Возвращает счёт по имени.

        Args:
            name: имя счёта

        Returns:
            Объект Account или None
        """
        try:
            query = "SELECT * FROM accounts WHERE name = ?"
            row = self.db.fetchone(query, (name,))
            return self._row_to_account(row) if row else None
        except Exception as e:
            logger.error(
                f"[AccountRepository] Ошибка получения счёта по имени '{name}': {e}",
                exc_info=True,
            )
            raise

    def create(self, account: Account) -> Account:
        """
        Создаёт новую запись счёта в базе данных.

        Args:
            account: объект Account с данными для создания

        Returns:
            Объект Account с присвоенным ID из базы данных
        """
        try:
            query = """
                INSERT INTO accounts (
                    name, account_type, initial_balance, current_balance,
                    currency, is_active, is_system
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                account.name,
                account.account_type,
                float(account.initial_balance),
                float(account.current_balance),
                account.currency or "RUB",
                1 if account.is_active else 0,
                1 if account.is_system else 0,
            )
            new_id = self.db.execute(query, params)
            account.id = new_id
            return account
        except Exception as e:
            logger.error(
                f"[AccountRepository] Ошибка создания счёта '{account.name}': {e}",
                exc_info=True,
            )
            raise

    def delete(self, account_id: int) -> bool:
        """
        Удаляет счёт из базы данных по ID.

        Args:
            account_id: ID удаляемого счёта

        Returns:
            True если запись была найдена и удалена, False если счёт не существовал
        """
        try:
            if not self.get_by_id(account_id):
                return False
            query = "DELETE FROM accounts WHERE id = ?"
            self.db.execute(query, (account_id,))
            return True
        except Exception as e:
            logger.error(
                f"[AccountRepository] Ошибка удаления счёта #{account_id}: {e}",
                exc_info=True,
            )
            raise

    def update(self, account: Account) -> bool:
        """
        Обновляет существующий счёт в БД.

        Args:
            account: объект Account с изменёнными полями

        Returns:
            True если операция прошла успешно
        """
        try:
            query = """
                UPDATE accounts SET 
                    name = ?, account_type = ?, initial_balance = ?, current_balance = ?,
                    is_active = ?, is_system = ?, currency = ?
                WHERE id = ?
            """
            params = (
                account.name,
                account.account_type,
                float(account.initial_balance),
                float(account.current_balance),
                account.is_active,
                account.is_system,
                account.currency,
                account.id,
            )
            self.db.execute(query, params)
            return True
        except Exception as e:
            logger.error(
                f"[AccountRepository] Ошибка обновления счёта #{account.id}: {e}",
                exc_info=True,
            )
            raise

    def get_or_create_counterparty(self, name: str) -> Account:
        """
        Ищет счет контрагента по имени. Если не найден — создает новый системный счет.

        Args:
            name: имя контрагента

        Returns:
            Объект Account созданного или найденного контрагента
        """
        try:
            normalized_name = name.strip().lower()

            # 1. Проверяем существование
            query = "SELECT * FROM accounts WHERE LOWER(name) = ? AND account_type = 'Counterparty'"
            row = self.db.fetchone(query, (normalized_name,))
            if row:
                return self._row_to_account(row)

            # 2. Создаем новый объект Account
            new_account = Account(
                name=name.strip(),
                account_type="Counterparty",
                initial_balance=Decimal("0.00"),
                current_balance=Decimal("0.00"),
                currency="RUB",
                is_active=True,
                is_system=True,
            )

            # 3. Сохраняем в БД
            insert_query = """
                INSERT INTO accounts (
                    name, account_type, initial_balance, current_balance, 
                    currency, is_active, is_system
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                new_account.name,
                new_account.account_type,
                float(new_account.initial_balance),
                float(new_account.current_balance),
                new_account.currency,
                1 if new_account.is_active else 0,
                1 if new_account.is_system else 0,
            )
            new_id = self.db.execute(insert_query, params)
            new_account.id = new_id
            return new_account
        except Exception as e:
            logger.error(
                f"[AccountRepository] Ошибка создания/получения контрагента '{name}': {e}",
                exc_info=True,
            )
            raise

    def get_or_create_credit_account(self, name: str) -> Account:
        """
        Создаёт системный счёт типа 'Credit' для банковского кредита.

        В отличие от контрагентов, счета кредитов всегда создаются новые
        (каждый кредит имеет свой уникальный счёт).

        Args:
            name: название счёта (обычно "Кредит: {название кредита}")

        Returns:
            Объект Account созданного счёта кредита

        Raises:
            Exception: при ошибке базы данных
        """
        try:
            new_account = Account(
                name=name.strip(),
                account_type="Credit",
                initial_balance=Decimal("0.00"),
                current_balance=Decimal("0.00"),
                currency="RUB",
                is_active=True,
                is_system=True,
            )

            insert_query = """
                INSERT INTO accounts (
                    name, account_type, initial_balance, current_balance, 
                    currency, is_active, is_system
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                new_account.name,
                new_account.account_type,
                float(new_account.initial_balance),
                float(new_account.current_balance),
                new_account.currency,
                1 if new_account.is_active else 0,
                1 if new_account.is_system else 0,
            )
            new_id = self.db.execute(insert_query, params)
            new_account.id = new_id

            logger.info(
                f"[AccountRepository] Создан системный счёт кредита "
                f"id={new_account.id}, name='{new_account.name}'"
            )
            return new_account
        except Exception as e:
            logger.error(
                f"[AccountRepository] Ошибка создания счёта кредита '{name}': {e}",
                exc_info=True,
            )
            raise

    def get_credit_account_by_loan_id(self, loan_id: int) -> Optional[Account]:
        """
        Возвращает системный счёт кредита по ID займа.

        Args:
            loan_id: ID кредита в таблице loans

        Returns:
            Объект Account счёта кредита или None, если не найден
        """
        try:
            query = """
                SELECT a.* FROM accounts a
                INNER JOIN loans l ON l.account_id = a.id
                WHERE l.id = ? AND l.source_type = 'bank'
            """
            row = self.db.fetchone(query, (loan_id,))
            return self._row_to_account(row) if row else None
        except Exception as e:
            logger.error(
                f"[AccountRepository] Ошибка получения счёта кредита "
                f"для loan_id={loan_id}: {e}",
                exc_info=True,
            )
            raise

    def update_balance_delta(self, account_id: int, delta: Decimal) -> bool:
        """
        Изменяет текущий баланс счёта на указанную дельту.

        Args:
            account_id: ID счёта
            delta: Изменение баланса (может быть отрицательным)

        Returns:
            True если операция прошла успешно

        Raises:
            ValueError: если счёт не найден
        """
        try:
            account = self.get_by_id(account_id)
            if not account:
                raise ValueError(f"Счёт #{account_id} не найден")

            new_balance = (account.current_balance + delta).quantize(Decimal("0.01"))

            query = "UPDATE accounts SET current_balance = ? WHERE id = ?"
            self.db.execute(query, (float(new_balance), account_id))

            logger.info(
                f"[AccountRepository] Обновлён баланс счёта #{account_id}: "
                f"{account.current_balance} -> {new_balance}"
            )
            return True
        except ValueError as e:
            logger.warning(f"[AccountRepository] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[AccountRepository] Ошибка обновления баланса счёта #{account_id}: {e}",
                exc_info=True,
            )
            raise