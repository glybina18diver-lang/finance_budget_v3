"""
Репозиторий для работы с банковскими кредитами.

Работает только с записями в таблице loans, где source_type = 'bank'.
Займы у физических лиц (source_type = 'person') обрабатываются
отдельным репозиторием LoanRepository.
"""

from typing import Optional, Dict, Any, List
import logging

from core.db import Database
from core.models import Loan
from utils.validators import to_decimal

logger = logging.getLogger(__name__)


import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal

from core.db import Database
from core.models import Loan

logger = logging.getLogger(__name__)


class CreditRepository:
    """Репозиторий банковских кредитов."""

    def __init__(self, db: Database):
        """
        Инициализация репозитория.

        Args:
            db: экземпляр фасада Database для выполнения запросов
        """
        self.db = db

    def _row_to_loan(self, row: Dict[str, Any]) -> Loan:
        """
        Преобразует словарь из БД в объект кредита.

        Числовые поля (loan_amount, remaining, interest_rate)
        преобразуются из float в Decimal для точности вычислений.

        Args:
            row: словарь с данными строки из БД

        Returns:
            Инициализированный объект Loan
        """
        return Loan(
            id=row.get("id"),
            name=row.get("name", ""),
            source_type=row.get("source_type", "bank"),
            loan_type=row.get("loan_type", "received"),
            loan_purpose=row.get("loan_purpose"),
            loan_amount=to_decimal(row.get("loan_amount", 0.0)),
            remaining=to_decimal(row.get("remaining", 0.0)),
            interest_rate=to_decimal(row.get("interest_rate", 0.0)),
            term_months=row.get("term_months"),
            issue_date=row.get("issue_date", ""),
            due_date=row.get("due_date"),
            account_id=row.get("account_id", 0),
            counterparty_account_id=row.get("counterparty_account_id"),
            purchase_transaction_id=row.get("purchase_transaction_id"),
            contact_name=row.get("contact_name"),
            description=row.get("description", ""),
            status=row.get("status", "active"),
            created_at=row.get("created_at", ""),
        )

    def create(self, loan: Loan) -> Loan:
        """
        Создаёт банковский кредит в базе данных.

        Числовые поля (loan_amount, remaining, interest_rate)
        преобразуются из Decimal во float для записи в SQLite REAL.

        Args:
            loan: объект Loan с заполненными полями

        Returns:
            Объект Loan с присвоенным ID из базы данных

        Raises:
            ValueError: если source_type != 'bank'
            Exception: при ошибке базы данных
        """
        try:
            if loan.source_type != "bank":
                raise ValueError(
                    f"CreditRepository работает только с source_type='bank', "
                    f"получено: '{loan.source_type}'"
                )

            query = """
                INSERT INTO loans (
                    name, source_type, loan_type, loan_purpose,
                    loan_amount, remaining, interest_rate, term_months,
                    issue_date, due_date, account_id, counterparty_account_id,
                    purchase_transaction_id, contact_name, description, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                loan.name,
                loan.source_type,
                loan.loan_type,
                loan.loan_purpose,
                float(loan.loan_amount),
                float(loan.remaining),
                float(loan.interest_rate),
                loan.term_months,
                loan.issue_date,
                loan.due_date,
                loan.account_id,
                loan.counterparty_account_id,
                loan.purchase_transaction_id,
                loan.contact_name,
                loan.description,
                loan.status,
            )
            new_id = self.db.execute(query, params)
            loan.id = new_id

            logger.info(
                f"[CreditRepository] Создан кредит id={loan.id}, "
                f"name='{loan.name}', purpose={loan.loan_purpose}, "
                f"amount={loan.loan_amount}"
            )
            return loan

        except ValueError as e:
            logger.warning(f"[CreditRepository] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[CreditRepository] Ошибка создания кредита: {e}",
                exc_info=True,
            )
            raise

    def get_by_id(self, loan_id: int) -> Optional[Loan]:
        """
        Возвращает банковский кредит по ID.

        Args:
            loan_id: идентификатор кредита

        Returns:
            Объект Loan или None, если кредит не найден

        Raises:
            ValueError: если loan_id <= 0
            Exception: при ошибке базы данных
        """
        try:
            if loan_id <= 0:
                raise ValueError(f"Некорректный loan_id: {loan_id}")

            query = """
                SELECT * FROM loans
                WHERE id = ? AND source_type = 'bank'
            """
            row = self.db.fetch_one(query, (loan_id,))
            return self._row_to_loan(row) if row else None

        except ValueError as e:
            logger.warning(f"[CreditRepository] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[CreditRepository] Ошибка получения кредита #{loan_id}: {e}",
                exc_info=True,
            )
            raise

    def get_all(self) -> List[Loan]:
        """
        Возвращает список всех банковских кредитов.

        Returns:
            Список объектов Loan (может быть пустым)

        Raises:
            Exception: при ошибке базы данных
        """
        try:
            query = """
                SELECT * FROM loans
                WHERE source_type = 'bank'
                ORDER BY created_at DESC
            """
            rows = self.db.fetchall(query)
            return [self._row_to_loan(row) for row in rows]

        except Exception as e:
            logger.error(
                f"[CreditRepository] Ошибка получения списка кредитов: {e}",
                exc_info=True,
            )
            raise

    def get_active(self) -> List[Loan]:
        """
        Возвращает список активных (НЕ ПОГАШЕНЫХ) банковских кредитов.

        Returns:
            Список объектов Loan со статусом 'active'

        Raises:
            Exception: при ошибке базы данных
        """
        try:
            query = """
                SELECT * FROM loans
                WHERE source_type = 'bank' AND status = 'active'
                ORDER BY due_date ASC
            """
            rows = self.db.fetchall(query)
            return [self._row_to_loan(row) for row in rows]

        except Exception as e:
            logger.error(
                f"[CreditRepository] Ошибка получения активных кредитов: {e}",
                exc_info=True,
            )
            raise

    def get_remaining(self, loan_id: int) -> float:
        """
        Возвращает текущий остаток долга по кредиту.

        Args:
            loan_id: идентификатор кредита

        Returns:
            Текущий остаток долга

        Raises:
            ValueError: если кредит не найден
            Exception: при ошибке базы данных
        """
        try:
            query = """
                SELECT remaining FROM loans
                WHERE id = ? AND source_type = 'bank'
            """
            row = self.db.fetch_one(query, (loan_id,))

            if row is None:
                raise ValueError(f"Кредит #{loan_id} не найден")

            return to_decimal(row.get("remaining", 0.0))

        except ValueError as e:
            logger.warning(f"[CreditRepository] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[CreditRepository] Ошибка получения остатка: {e}",
                exc_info=True,
            )
            raise

    def update_remaining(self, loan_id: int, delta: Decimal ) -> None:
        """
        Изменяет остаток долга по кредиту.

        Args:
            loan_id: идентификатор кредита
            delta: изменение остатка (отрицательное — при погашении)

        Raises:
            ValueError: если кредит не найден или остаток уходит в минус
            Exception: при ошибке базы данных
        """
        try:
            current = self.get_remaining(loan_id)
            new_remaining = (current + delta).quantize(Decimal("0.01"))

            if new_remaining < 0:
                raise ValueError(
                    f"Остаток не может быть отрицательным: {new_remaining}"
                )

            new_status = "paid" if new_remaining == 0 else "active"

            query = """
                UPDATE loans
                SET remaining = ?, status = ?
                WHERE id = ?
            """
            self.db.execute(query, (float(new_remaining), new_status, loan_id))

            logger.info(
                f"[CreditRepository] Обновлён остаток кредита #{loan_id}: "
                f"{current} -> {new_remaining}"
            )

        except ValueError as e:
            logger.warning(f"[CreditRepository] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[CreditRepository] Ошибка обновления остатка: {e}",
                exc_info=True,
            )
            raise

    def update_purchase_transaction(self, loan_id: int, transaction_id: int) -> None:
        """
        Привязывает транзакцию покупки к POS-кредиту.

        Args:
            loan_id: идентификатор кредита
            transaction_id: идентификатор транзакции

        Raises:
            ValueError: если кредит не найден или не является POS-кредитом
            Exception: при ошибке базы данных
        """
        try:
            loan = self.get_by_id(loan_id)
            if loan is None:
                raise ValueError(f"Кредит #{loan_id} не найден")

            if loan.loan_purpose != "purchase":
                raise ValueError(
                    f"Кредит #{loan_id} не является POS-кредитом "
                    f"(purpose={loan.loan_purpose})"
                )

            query = """
                UPDATE loans
                SET purchase_transaction_id = ?
                WHERE id = ?
            """
            self.db.execute(query, (transaction_id, loan_id))

            logger.info(
                f"[CreditRepository] Привязана транзакция #{transaction_id} "
                f"к кредиту #{loan_id}"
            )

        except ValueError as e:
            logger.warning(f"[CreditRepository] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[CreditRepository] Ошибка привязки транзакции: {e}",
                exc_info=True,
            )
            raise

    def update(self, loan_id: int, data: Dict[str, Any]) -> None:
        """
        Обновляет поля банковского кредита.

        Args:
            loan_id: идентификатор кредита
            data: словарь с полями для обновления

        Raises:
            ValueError: если кредит не найден или переданы запрещённые поля
            Exception: при ошибке базы данных
        """
        try:
            if not data:
                return

            forbidden = {"id", "source_type", "account_id"}
            if forbidden & set(data.keys()):
                raise ValueError(
                    f"Поля {forbidden} нельзя изменять через update()"
                )

            existing = self.get_by_id(loan_id)
            if existing is None:
                raise ValueError(f"Кредит #{loan_id} не найден")

            set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
            params = tuple(data.values()) + (loan_id,)

            query = f"UPDATE loans SET {set_clause} WHERE id = ?"
            self.db.execute(query, params)

            logger.info(
                f"[CreditRepository] Обновлён кредит #{loan_id}, "
                f"поля: {list(data.keys())}"
            )

        except ValueError as e:
            logger.warning(f"[CreditRepository] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[CreditRepository] Ошибка обновления кредита: {e}",
                exc_info=True,
            )
            raise

    def delete(self, loan_id: int) -> bool:
        """
        Удаляет банковский кредит из базы данных.

        Args:
            loan_id: идентификатор кредита

        Returns:
            True если запись была найдена и удалена, False если не существовала

        Raises:
            Exception: при ошибке базы данных
        """
        try:
            query = """
                DELETE FROM loans
                WHERE id = ? AND source_type = 'bank'
            """
            result = self.db.execute(query, (loan_id,))

            if result == 0:
                return False

            logger.info(f"[CreditRepository] Удалён кредит #{loan_id}")
            return True

        except Exception as e:
            logger.error(
                f"[CreditRepository] Ошибка удаления кредита #{loan_id}: {e}",
                exc_info=True,
            )
            raise

    def get_loan_details(self, loan_id: int) -> Optional[Dict[str, Any]]:
        """
        Возвращает расширенную информацию о кредите с JOIN.

        Получает данные кредита вместе с названиями связанных счетов
        и информацией о покупке (для POS-кредитов).

        Args:
            loan_id: идентификатор кредита

        Returns:
            Словарь с расширенной информацией или None, если кредит не найден.
            Структура:
            {
                'loan': Loan,
                'account_name': str,
                'target_account_name': str|None,
                'purchase': {
                    'category_name': str,
                    'description': str,
                    'amount': float,
                    'date': str
                } | None
            }

        Raises:
            ValueError: если loan_id <= 0
            Exception: при ошибке базы данных
        """
        try:
            if loan_id <= 0:
                raise ValueError(f"Некорректный loan_id: {loan_id}")

            query = """
                SELECT
                    l.*,
                    a.name AS account_name,
                    ta.name AS target_account_name,
                    c.name AS purchase_category_name,
                    t.description AS purchase_description,
                    t.amount AS purchase_amount,
                    t.date AS purchase_date
                FROM loans l
                LEFT JOIN accounts a ON a.id = l.account_id
                LEFT JOIN accounts ta ON ta.id = l.counterparty_account_id
                LEFT JOIN transactions t ON t.id = l.purchase_transaction_id
                LEFT JOIN categories c ON c.id = t.category_id
                WHERE l.id = ? AND l.source_type = 'bank'
            """
            row = self.db.fetch_one(query, (loan_id,))

            if row is None:
                return None

            loan = self._row_to_loan(row)

            result = {
                "loan": loan,
                "account_name": row.get("account_name"),
                "target_account_name": row.get("target_account_name"),
                "purchase": None,
            }

            if loan.loan_purpose == "purchase" and row.get("purchase_category_name"):
                result["purchase"] = {
                    "category_name": row.get("purchase_category_name"),
                    "description": row.get("purchase_description", ""),
                    "amount": float(row.get("purchase_amount", 0.0)),
                    "date": row.get("purchase_date", ""),
                }

            return result

        except ValueError as e:
            logger.warning(f"[CreditRepository] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[CreditRepository] Ошибка получения деталей: {e}",
                exc_info=True,
            )
            raise