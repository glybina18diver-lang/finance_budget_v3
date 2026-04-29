# core/repositories/transaction_repository.py
from typing import Optional, List, Dict, Any
from core.db import Database
from core.models import Transaction

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
        
        Args:
            row: словарь с данными строки из БД
            
        Returns:
            Инициализированный объект Transaction
        """
        return Transaction(
            id=row.get("id"),
            date=row.get("date", ""),
            amount=row.get("amount", 0.0),
            trans_type=row.get("trans_type", "expense"),
            account_id=row.get("account_id", 0),
            category_id=row.get("category_id"),
            description=row.get("description", ""),
            quantity=row.get("quantity", 1.0),
            unit_price=row.get("unit_price"),
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
        query = """
            INSERT INTO transactions (
                date, amount, trans_type, account_id, category_id,
                description, quantity, original_transaction_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            transaction.date, transaction.amount, transaction.trans_type,
            transaction.account_id, transaction.category_id,
            transaction.description, transaction.quantity,
            transaction.original_transaction_id,
            transaction.created_at, transaction.updated_at
        )
        new_id = self.db.execute(query, params)
        transaction.id = new_id
        return transaction

    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """
        Возвращает транзакцию по уникальному идентификатору.
        
        Args:
            transaction_id: ID искомой транзакции
            
        Returns:
            Объект Transaction или None, если запись не найдена
        """
        query = "SELECT * FROM transactions WHERE id = ?"
        row = self.db.fetchone(query, (transaction_id,))
        return self._row_to_transaction(row) if row else None

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
        if account_id is not None:
            query = "SELECT * FROM transactions WHERE account_id = ? ORDER BY date DESC, created_at DESC LIMIT ? OFFSET ?"
            params = (account_id, limit, offset)
        else:
            query = "SELECT * FROM transactions ORDER BY date DESC, created_at DESC LIMIT ? OFFSET ?"
            params = (limit, offset)
            
        rows = self.db.fetchall(query, params)
        return [self._row_to_transaction(row) for row in rows]

    def delete(self, transaction_id: int) -> bool:
        """
        Удаляет транзакцию по уникальному идентификатору.
        
        Args:
            transaction_id: ID транзакции для удаления
            
        Returns:
            True если операция прошла успешно (ошибки БД пробрасываются выше)
        """
        query = "DELETE FROM transactions WHERE id = ?"
        self.db.execute(query, (transaction_id,))
        return True
    
    def get_latest(self, limit: int = 300) -> List[Transaction]:
        """
        Возвращает последние N транзакций, отсортированные по дате (новые первыми).
        Используется для инициализации таблицы при открытии диалога.
        
        Args:
            limit: максимальное количество записей (по умолчанию 300)
            
        Returns:
            Список объектов Transaction, отсортированный по дате (новые первыми)
        """
        query = """
            SELECT * FROM transactions 
            ORDER BY date DESC, created_at DESC 
            LIMIT ?
        """
        rows = self.db.fetchall(query, (limit,))
        return [self._row_to_transaction(row) for row in rows]