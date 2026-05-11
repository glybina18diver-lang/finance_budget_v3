"""
Репозиторий для работы с переводами в базе данных.
Инкапсулирует CRUD-операции и маппинг данных.
"""
from typing import List, Optional
from core.models import Transfer


class TransferRepository:
    """Репозиторий управления переводами между счетами."""

    def __init__(self, db):
        """
        Инициализация репозитория.
        
        Args:
            db: экземпляр подключения к базе данных
        """
        self.db = db

    def _row_to_transfer(self, row) -> Transfer:
        """
        Преобразует строку результата БД в объект Transfer.
        
        Args:
            row: строка с данными перевода
            
        Returns:
            Объект Transfer
        """
        return Transfer(
            id=row["id"],
            date=row["date"],
            amount=row["amount"],
            type=row["type"],
            from_account_id=row["from_account_id"],
            to_account_id=row["to_account_id"],
            description=row["description"]
        )

    def get_by_id(self, transfer_id: int) -> Optional[Transfer]:
        """
        Возвращает перевод по ID.
        
        Args:
            transfer_id: ID искомого перевода
            
        Returns:
            Объект Transfer или None, если не найден
        """
        query = "SELECT * FROM transfers WHERE id = ?"
        row = self.db.fetchone(query, (transfer_id,))
        return self._row_to_transfer(row) if row else None

    def get_all(self) -> List[Transfer]:
        """
        Возвращает все переводы, отсортированные по дате (новые сверху).
        
        Returns:
            Список объектов Transfer
        """
        query = "SELECT * FROM transfers ORDER BY date DESC"
        rows = self.db.fetchall(query)
        return [self._row_to_transfer(row) for row in rows]

    def get_all_with_details(self) -> List[dict]:
        """
        Возвращает переводы с подставленными именами счетов.
        Оптимизировано для отображения в UI (избегает N+1 запросов).
        
        Returns:
            Список словарей: {id, date, amount, type, from_account_name, to_account_name, description}
        """
        query = """
            SELECT t.id, t.date, t.amount, t.type, t.description,
                   a1.name as from_account_name,
                   a2.name as to_account_name
            FROM transfers t
            LEFT JOIN accounts a1 ON t.from_account_id = a1.id
            LEFT JOIN accounts a2 ON t.to_account_id = a2.id
            ORDER BY t.date DESC
        """
        return self.db.fetchall(query)

    def create(self, transfer: Transfer) -> int:
        """
        Создаёт новую запись перевода в БД.
        
        Args:
            transfer: объект Transfer с данными перевода
            
        Returns:
            ID созданной записи
        """
        query = """
            INSERT INTO transfers (
                date, 
                amount, 
                type, 
                from_account_id, 
                to_account_id, 
                description
            ) VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            transfer.date,
            transfer.amount,
            transfer.type,
            transfer.from_account_id,
            transfer.to_account_id,
            transfer.description
        )
        cursor = self.db.execute(query, params)
        return cursor.lastrowid

    def delete(self, transfer_id: int) -> bool:
        """
        Удаляет перевод по ID.
        
        Args:
            transfer_id: ID удаляемого перевода
            
        Returns:
            True если операция прошла успешно
        """
        query = "DELETE FROM transfers WHERE id = ?"
        self.db.execute(query, (transfer_id,))
        return True

    