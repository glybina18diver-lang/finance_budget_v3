"""
Репозиторий для работы с переводами в базе данных.
Инкапсулирует CRUD-операции и маппинг данных.
"""
import logging
from typing import List, Optional
from core.models import Transfer

logger = logging.getLogger(__name__)


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
        try:
            query = "SELECT * FROM transfers WHERE id = ?"
            row = self.db.fetchone(query, (transfer_id,))
            return self._row_to_transfer(row) if row else None
        except Exception as e:
            logger.error("[TransferRepository] Ошибка при получении перевода по ID %s: %s", transfer_id, e, exc_info=True)
            raise

    def get_all(self) -> List[Transfer]:
        """
        Возвращает все переводы, отсортированные по дате (новые сверху).
        
        Returns:
            Список объектов Transfer
        """
        try:
            query = "SELECT * FROM transfers ORDER BY date DESC"
            rows = self.db.fetchall(query)
            return [self._row_to_transfer(row) for row in rows]
        except Exception as e:
            logger.error("[TransferRepository] Ошибка при получении списка переводов: %s", e, exc_info=True)
            raise

    def get_all_with_details(self) -> List[dict]:
        """
        Возвращает пользовательские переводы с именами счетов и контрагентов.
        
        Returns:
            Список словарей с данными для UI
        """
        try:
            query = """
                SELECT
                    t.id, t.date, t.amount, t.type, t.description, t.is_system,
                    a1.name AS from_account_name,
                    a2.name AS to_account_name,
                    -- Определяем имя контрагента для внешних переводов
                    CASE
                        WHEN t.type = 'external' AND a1.account_type = 'Counterparty' THEN a1.name
                        WHEN t.type = 'external' AND a2.account_type = 'Counterparty' THEN a2.name
                        ELSE ''
                    END AS counterparty_name
                FROM transfers t
                LEFT JOIN accounts a1 ON t.from_account_id = a1.id
                LEFT JOIN accounts a2 ON t.to_account_id = a2.id
                WHERE t.is_system = 0  -- Фильтруем системные переводы на уровне БД
                ORDER BY t.date DESC
            """
            return self.db.fetchall(query)
        except Exception as e:
            logger.error("[TransferRepository] Ошибка при получении переводов с деталями: %s", e, exc_info=True)
            raise

    def create(self, transfer: Transfer) -> int:
        try:
            query = """
                INSERT INTO transfers (
                    date, amount, type,
                    from_account_id, to_account_id,
                    description, is_system, loan_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                transfer.date,
                transfer.amount,
                transfer.type,
                transfer.from_account_id,
                transfer.to_account_id,
                transfer.description,
                1 if transfer.is_system else 0,
                transfer.loan_id
            )
            transfer.id = self.db.execute(query, params)
            return transfer
        except Exception as e:
            logger.error("[TransferRepository] Ошибка при создании перевода: %s", e, exc_info=True)
            raise

    def delete(self, transfer_id: int) -> bool:
        """
        Удаляет перевод по ID.
        
        Args:
            transfer_id: ID удаляемого перевода
            
        Returns:
            True если операция прошла успешно
        """
        try:
            query = "DELETE FROM transfers WHERE id = ?"
            self.db.execute(query, (transfer_id,))
            return True
        except Exception as e:
            logger.error("[TransferRepository] Ошибка при удалении перевода ID %s: %s", transfer_id, e, exc_info=True)
            raise

    