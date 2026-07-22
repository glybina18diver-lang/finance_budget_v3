# core/repositories/transaction_repository.py
import logging
from typing import Optional, List, Dict, Any
from decimal import Decimal
from core.db import Database
from core.models import Transaction
from utils.validators import to_decimal

logger = logging.getLogger(__name__)


class TransactionRepository:
    """Репозиторий для операций с таблицей транзакций (только CRUD)."""

    def __init__(self, db: Database):
        """
        Инициализация репозитория.

        Args:
            db: экземпляр фасада Database для выполнения запросов
        """
        self.db = db

    def _row_to_transaction(self, row: Dict[str, Any]) -> Transaction:
        """
        Преобразует словарь из БД в объект транзакции.
        Числовые поля конвертируются из float (SQLite REAL) в Decimal.

        Args:
            row: словарь с данными строки из БД

        Returns:
            Инициализированный объект Transaction
        """
        return Transaction(
            id=row.get("id"),
            date=row.get("date", ""),
            amount=to_decimal(row.get("amount", 0.0)),
            trans_type=row.get("trans_type", "expense"),
            account_id=row.get("account_id", 0),
            category_id=row.get("category_id"),
            description=row.get("description", ""),
            quantity=to_decimal(row.get("quantity", 1.0)),
            unit_price=to_decimal(row.get("unit_price")) if row.get("unit_price") is not None else None,
            original_transaction_id=row.get("original_transaction_id"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at")
        )

    def create(self, transaction: Transaction) -> Transaction:
        """
        Сохраняет новую транзакцию в БД и возвращает объект с присвоенным ID.

        Args:
            transaction: объект Transaction для сохранения

        Returns:
            Обновлённый объект Transaction с заполненным полем id
        """
        try:
            query = """
                INSERT INTO transactions (
                    date, amount, trans_type, account_id, category_id,
                    description, quantity, original_transaction_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                transaction.date,
                float(transaction.amount),
                transaction.trans_type,
                transaction.account_id,
                transaction.category_id,
                transaction.description,
                float(transaction.quantity),
                transaction.original_transaction_id,
                transaction.created_at,
                transaction.updated_at
            )
            new_id = self.db.execute(query, params)
            transaction.id = new_id
            return transaction
        except Exception as e:
            logger.error("[TransactionRepository] Ошибка при создании транзакции: %s", e, exc_info=True)
            raise

    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """
        Возвращает транзакцию по уникальному идентификатору.

        Args:
            transaction_id: ID искомой транзакции

        Returns:
            Объект Transaction или None, если запись не найдена
        """
        try:
            query = "SELECT * FROM transactions WHERE id = ?"
            row = self.db.fetchone(query, (transaction_id,))
            return self._row_to_transaction(row) if row else None
        except Exception as e:
            logger.error("[TransactionRepository] Ошибка при получении транзакции по ID %s: %s", transaction_id, e, exc_info=True)
            raise

    def get_all(self, account_id: Optional[int] = None, limit: int = 200, offset: int = 0) -> List[Transaction]:
        """
        Возвращает список транзакций с опциональной фильтрацией по счёту и пагинацией.

        Args:
            account_id: фильтр по счёту (если None — возвращает все записи)
            limit: максимальное количество возвращаемых записей
            offset: смещение начала выборки (для пагинации)

        Returns:
            Список объектов Transaction, отсортированный по дате (новые первыми)
        """
        try:
            if account_id is not None:
                query = "SELECT * FROM transactions WHERE account_id = ? ORDER BY date DESC, created_at DESC LIMIT ? OFFSET ?"
                params = (account_id, limit, offset)
            else:
                query = "SELECT * FROM transactions ORDER BY date DESC, created_at DESC LIMIT ? OFFSET ?"
                params = (limit, offset)

            rows = self.db.fetchall(query, params)
            return [self._row_to_transaction(row) for row in rows]
        except Exception as e:
            logger.error("[TransactionRepository] Ошибка при получении списка транзакций: %s", e, exc_info=True)
            raise

    def delete(self, transaction_id: int) -> bool:
        """
        Удаляет транзакцию по уникальному идентификатору.

        Args:
            transaction_id: ID транзакции для удаления

        Returns:
            True если операция прошла успешно (ошибки БД пробрасываются выше)
        """
        try:
            query = "DELETE FROM transactions WHERE id = ?"
            self.db.execute(query, (transaction_id,))
            return True
        except Exception as e:
            logger.error("[TransactionRepository] Ошибка при удалении транзакции ID %s: %s", transaction_id, e, exc_info=True)
            raise

    def get_latest(self, limit: int = 300) -> List[Transaction]:
        """
        Возвращает последние N транзакций, отсортированные по дате (новые первыми).
        Используется для инициализации таблицы при открытии диалога.

        Args:
            limit: максимальное количество записей (по умолчанию 300)

        Returns:
            Список объектов Transaction, отсортированный по дате (новые первыми)
        """
        try:
            query = """
                SELECT * FROM transactions
                ORDER BY date DESC, created_at DESC
                LIMIT ?
            """
            rows = self.db.fetchall(query, (limit,))
            return [self._row_to_transaction(row) for row in rows]
        except Exception as e:
            logger.error("[TransactionRepository] Ошибка при получении последних транзакций: %s", e, exc_info=True)
            raise