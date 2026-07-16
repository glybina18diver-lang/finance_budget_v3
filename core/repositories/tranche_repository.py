"""Репозиторий для работы с траншами."""

import logging
from datetime import date
from typing import List, Optional
from decimal import Decimal


from core.models import Tranche
from core.db import Database

logger = logging.getLogger(__name__)


class TrancheRepository:
    """CRUD-операции для траншей."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def create(self, tranche: Tranche) -> int:
        """
        Создаёт новый транш.
        
        Returns:
            ID созданного транша
        """
        try:
            query = """
                INSERT INTO tranches (
                    card_id, tranche_type, original_amount, remaining_amount,
                    commission, transaction_date, grace_end_date, status,
                    is_retroactive_triggered, linked_transaction_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                tranche.card_id,
                tranche.tranche_type,
                float(tranche.original_amount),
                float(tranche.remaining_amount),
                float(tranche.commission),
                tranche.transaction_date.isoformat(),
                tranche.grace_end_date.isoformat() if tranche.grace_end_date else None,
                tranche.status,
                1 if tranche.is_retroactive_triggered else 0,
                tranche.linked_transaction_id
            )
            new_id = self.db.execute(query, params)
            tranche.id = new_id
            return new_id
        except Exception as e:
            logger.error(f"[TrancheRepository] Ошибка создания транша: {e}", exc_info=True)
            raise
    
    def get_by_id(self, tranche_id: int) -> Optional[Tranche]:
        """Получает транш по ID."""
        try:
            query = "SELECT * FROM tranches WHERE id = ?"
            row = self.db.fetch_one(query, (tranche_id,))
            return self._row_to_tranche(row) if row else None
        except Exception as e:
            logger.error(f"[TrancheRepository] Ошибка получения транша {tranche_id}: {e}", exc_info=True)
            raise
    
    def get_by_card(self, card_id: int) -> List[Tranche]:
        """Получает все транши карты."""
        try:
            query = "SELECT * FROM tranches WHERE card_id = ? ORDER BY transaction_date"
            rows = self.db.fetch_all(query, (card_id,))
            return [self._row_to_tranche(row) for row in rows]
        except Exception as e:
            logger.error(f"[TrancheRepository] Ошибка получения траншей карты {card_id}: {e}", exc_info=True)
            raise
    
    def get_active_by_card(self, card_id: int) -> List[Tranche]:
        """Получает активные транши (не погашенные)."""
        try:
            query = """
                SELECT * FROM tranches 
                WHERE card_id = ? AND status != 'paid'
                ORDER BY transaction_date
            """
            rows = self.db.fetch_all(query, (card_id,))
            return [self._row_to_tranche(row) for row in rows]
        except Exception as e:
            logger.error(f"[TrancheRepository] Ошибка получения активных траншей: {e}", exc_info=True)
            raise
    
    def get_by_month(self, card_id: int, year: int, month: int) -> List[Tranche]:
        """Получает транши за конкретный месяц."""
        try:
            query = """
                SELECT * FROM tranches 
                WHERE card_id = ? 
                AND strftime('%Y', transaction_date) = ?
                AND strftime('%m', transaction_date) = ?
                ORDER BY transaction_date
            """
            rows = self.db.fetch_all(query, (card_id, str(year), str(month).zfill(2)))
            return [self._row_to_tranche(row) for row in rows]
        except Exception as e:
            logger.error(f"[TrancheRepository] Ошибка получения траншей за {year}-{month}: {e}", exc_info=True)
            raise
    
    def update(self, tranche: Tranche):
        """Обновляет транш."""
        try:
            query = """
                UPDATE tranches SET
                    remaining_amount = ?,
                    status = ?,
                    is_retroactive_triggered = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            self.db.execute(query, (
                float(tranche.remaining_amount),
                tranche.status,
                1 if tranche.is_retroactive_triggered else 0,
                tranche.id
            ))
        except Exception as e:
            logger.error(f"[TrancheRepository] Ошибка обновления транша {tranche.id}: {e}", exc_info=True)
            raise
    
    def delete(self, tranche_id: int):
        """Удаляет транш."""
        try:
            query = "DELETE FROM tranches WHERE id = ?"
            self.db.execute(query, (tranche_id,))
        except Exception as e:
            logger.error(f"[TrancheRepository] Ошибка удаления транша {tranche_id}: {e}", exc_info=True)
            raise
    
    def _row_to_tranche(self, row: dict) -> Tranche:
        """Конвертирует строку БД в объект Tranche."""
        from datetime import datetime
        return Tranche(
            id=row["id"],
            card_id=row["card_id"],
            tranche_type=row["tranche_type"],
            original_amount=Decimal(str(row["original_amount"])),
            remaining_amount=Decimal(str(row["remaining_amount"])),
            commission=Decimal(str(row["commission"])),
            transaction_date=datetime.fromisoformat(row["transaction_date"]).date(),
            grace_end_date=datetime.fromisoformat(row["grace_end_date"]).date() if row["grace_end_date"] else None,
            status=row["status"],
            is_retroactive_triggered=bool(row["is_retroactive_triggered"]),
            linked_transaction_id=row["linked_transaction_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"])
        )