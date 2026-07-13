"""Репозиторий для работы с начислениями процентов."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from core.db import Database
from core.models import InterestAccrual

logger = logging.getLogger(__name__)


class InterestAccrualRepository:
    """CRUD-операции для начислений процентов."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def create(self, accrual: InterestAccrual) -> int:
        """Создаёт запись о начислении процентов."""
        try:
            query = """
                INSERT INTO interest_accruals (
                    tranche_id, accrual_date, interest_type,
                    amount, paid_amount, is_paid
                ) VALUES (?, ?, ?, ?, ?, ?)
            """
            cursor = self.db.execute(query, (
                accrual.tranche_id,
                accrual.accrual_date.isoformat(),
                accrual.interest_type,
                float(accrual.amount),
                float(accrual.paid_amount),
                1 if accrual.is_paid else 0
            ))
            logger.info(
                f"[{self.__class__.__name__}] Создано начисление ID={cursor.lastrowid}, "
                f"tranche_id={accrual.tranche_id}, тип={accrual.interest_type}, сумма={accrual.amount}"
            )
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания начисления процентов: {e}", exc_info=True)
            raise
    
    def get_by_tranche(self, tranche_id: int) -> List[InterestAccrual]:
        """Получает все начисления по траншу."""
        try:
            query = """
                SELECT * FROM interest_accruals 
                WHERE tranche_id = ? 
                ORDER BY accrual_date
            """
            rows = self.db.fetch_all(query, (tranche_id,))
            return [self._row_to_accrual(row) for row in rows]
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения начислений транша {tranche_id}: {e}", exc_info=True)
            raise
    
    def get_unpaid_by_tranche(self, tranche_id: int) -> List[InterestAccrual]:
        """Получает неоплаченные начисления по траншу."""
        try:
            query = """
                SELECT * FROM interest_accruals 
                WHERE tranche_id = ? AND is_paid = 0
                ORDER BY accrual_date
            """
            rows = self.db.fetch_all(query, (tranche_id,))
            return [self._row_to_accrual(row) for row in rows]
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения неоплаченных начислений: {e}", exc_info=True)
            raise
    
    def get_unpaid_by_card(self, card_id: int) -> List[InterestAccrual]:
        """
        Получает все неоплаченные начисления процентов по всем траншам карты.
        
        Использует JOIN с таблицей tranches для фильтрации по card_id.
        Оптимизация: один запрос вместо N запросов в цикле.
        
        Args:
            card_id: ID кредитной карты
            
        Returns:
            Список неоплаченных начислений процентов
        """
        try:
            query = """
                SELECT ia.* 
                FROM interest_accruals ia
                INNER JOIN tranches t ON ia.tranche_id = t.id
                WHERE t.card_id = ? AND ia.is_paid = 0
                ORDER BY t.transaction_date, ia.accrual_date
            """
            rows = self.db.fetch_all(query, (card_id,))
            accruals = [self._row_to_accrual(row) for row in rows]
            logger.debug(
                f"[{self.__class__.__name__}] Получено {len(accruals)} неоплаченных начислений для карты {card_id}"
            )
            return accruals
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения неоплаченных начислений карты {card_id}: {e}", exc_info=True)
            raise
    
    def update_paid_amount(self, accrual_id: int, paid_amount: float):
        """Обновляет сумму погашения."""
        try:
            query = """
                UPDATE interest_accruals 
                SET paid_amount = ?, is_paid = 1
                WHERE id = ?
            """
            self.db.execute(query, (paid_amount, accrual_id))
            logger.debug(
                f"[{self.__class__.__name__}] Обновлено погашение accrual_id={accrual_id}, paid_amount={paid_amount}"
            )
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обновления погашения {accrual_id}: {e}", exc_info=True)
            raise
    
    def _row_to_accrual(self, row: dict) -> InterestAccrual:
        """Конвертирует строку БД в объект InterestAccrual."""
        return InterestAccrual(
            id=row["id"],
            tranche_id=row["tranche_id"],
            accrual_date=datetime.fromisoformat(row["accrual_date"]).date(),
            interest_type=row["interest_type"],
            amount=Decimal(str(row["amount"])),
            paid_amount=Decimal(str(row["paid_amount"])),
            is_paid=bool(row["is_paid"]),
            created_at=datetime.fromisoformat(row["created_at"])
        )