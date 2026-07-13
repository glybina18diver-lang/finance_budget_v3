"""Репозиторий для работы с выписками (биллинговыми циклами)."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from core.db import Database
from core.models import Statement

logger = logging.getLogger(__name__)


class StatementRepository:
    """CRUD-операции для выписок."""

    def __init__(self, db: Database):
        self.db = db

    def create(self, statement: Statement) -> int:
        """Создаёт новую выписку."""
        try:
            query = """
                INSERT INTO statements (
                    card_id, statement_date, due_date,
                    opening_balance, new_charges, payments_received,
                    interest_charged, closing_balance, min_payment_required,
                    status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor = self.db.execute(query, (
                statement.card_id,
                statement.statement_date.isoformat(),
                statement.due_date.isoformat() if statement.due_date else None,
                float(statement.opening_balance),
                float(statement.new_charges),
                float(statement.payments_received),
                float(statement.interest_charged),
                float(statement.closing_balance),
                float(statement.min_payment_required),
                statement.status
            ))
            logger.info(
                f"[{self.__class__.__name__}] Создана выписка ID={cursor.lastrowid} "
                f"для карты {statement.card_id} на {statement.statement_date}"
            )
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания выписки: {e}", exc_info=True)
            raise

    def get_by_card(self, card_id: int) -> List[Statement]:
        """Получает все выписки карты, отсортированные от новых к старым."""
        try:
            query = """
                SELECT * FROM statements 
                WHERE card_id = ? 
                ORDER BY statement_date DESC
            """
            rows = self.db.fetch_all(query, (card_id,))
            return [self._row_to_statement(row) for row in rows]
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения выписок карты {card_id}: {e}", exc_info=True)
            raise

    def get_by_month(self, card_id: int, year: int, month: int) -> Optional[Statement]:
        """Получает выписку за конкретный месяц."""
        try:
            query = """
                SELECT * FROM statements 
                WHERE card_id = ? 
                AND strftime('%Y', statement_date) = ?
                AND strftime('%m', statement_date) = ?
                LIMIT 1
            """
            row = self.db.fetch_one(query, (card_id, str(year), str(month).zfill(2)))
            return self._row_to_statement(row) if row else None
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения выписки за {year}-{month}: {e}", exc_info=True)
            raise

    def get_current(self, card_id: int) -> Optional[Statement]:
        """Получает последнюю (текущую) выписку карты."""
        try:
            query = """
                SELECT * FROM statements 
                WHERE card_id = ? 
                ORDER BY statement_date DESC 
                LIMIT 1
            """
            row = self.db.fetch_one(query, (card_id,))
            return self._row_to_statement(row) if row else None
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения текущей выписки: {e}", exc_info=True)
            raise

    def update(self, statement: Statement):
        """Обновляет данные выписки."""
        try:
            if not statement.id:
                raise ValueError("id обязателен для обновления выписки")

            query = """
                UPDATE statements SET
                    closing_balance = ?,
                    min_payment_required = ?,
                    status = ?
                WHERE id = ?
            """
            self.db.execute(query, (
                float(statement.closing_balance),
                float(statement.min_payment_required),
                statement.status,
                statement.id
            ))
            logger.info(f"[{self.__class__.__name__}] Обновлена выписка ID={statement.id}")
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при обновлении: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обновления выписки {statement.id}: {e}", exc_info=True)
            raise

    def _row_to_statement(self, row: dict) -> Statement:
        """Маппит строку БД в объект Statement."""
        return Statement(
            id=row["id"],
            card_id=row["card_id"],
            statement_date=datetime.fromisoformat(row["statement_date"]).date(),
            due_date=datetime.fromisoformat(row["due_date"]).date() if row["due_date"] else None,
            opening_balance=Decimal(str(row["opening_balance"])),
            new_charges=Decimal(str(row["new_charges"])),
            payments_received=Decimal(str(row["payments_received"])),
            interest_charged=Decimal(str(row["interest_charged"])),
            closing_balance=Decimal(str(row["closing_balance"])),
            min_payment_required=Decimal(str(row["min_payment_required"])),
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now()
        )