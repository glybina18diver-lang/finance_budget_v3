"""Репозиторий для работы с кредитными картами (CRUD)."""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from core.db import Database
from core.models import CreditCard

logger = logging.getLogger(__name__)


class CreditCardRepository:
    """
    Инкапсулирует CRUD-операции для таблицы credit_cards.
    
    Не содержит бизнес-логики. Только SQL и маппинг dict ↔ CreditCard.
    """

    def __init__(self, db: Database):
        self.db = db

    def create(self, card: CreditCard) -> int:
        """
        Создаёт новую кредитную карту.
        
        Args:
            card: объект CreditCard со всеми обязательными полями
            
        Returns:
            ID созданной карты
            
        Raises:
            ValueError: если не передан account_id или name
            Exception: при ошибке БД
        """
        try:
            if not card.account_id:
                raise ValueError("account_id обязателен для создания карты")
            if not card.name:
                raise ValueError("name обязателен для создания карты")

            query = """
                INSERT INTO credit_cards (
                    account_id, name, annual_rate, grace_months,
                    min_payment_percent, payment_day, statement_day,
                    credit_limit, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                card.account_id,
                card.name,
                float(card.annual_rate),
                card.grace_months,
                float(card.min_payment_percent),
                card.payment_day,
                card.statement_day,
                float(card.credit_limit),
                1 if card.is_active else 0
            )
            new_id = self.db.execute(query, params)
            card.id = new_id
            logger.info(
                f"[{self.__class__.__name__}] Создана карта ID={new_id}, "
                f"name='{card.name}', account_id={card.account_id}"
            )
            return new_id
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при создании: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания карты: {e}", exc_info=True)
            raise

    def get_by_id(self, card_id: int) -> Optional[CreditCard]:
        """
        Получает карту по ID.
        
        Args:
            card_id: ID кредитной карты
            
        Returns:
            Объект CreditCard или None, если не найдена
        """
        try:
            query = "SELECT * FROM credit_cards WHERE id = ?"
            row = self.db.fetch_one(query, (card_id,))
            return self._row_to_credit_card(row) if row else None
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения карты {card_id}: {e}", exc_info=True)
            raise

    def get_by_account_id(self, account_id: int) -> Optional[CreditCard]:
        """
        Получает карту, привязанную к счёту.
        
        Args:
            account_id: ID счёта в таблице accounts
            
        Returns:
            Объект CreditCard или None
        """
        try:
            query = "SELECT * FROM credit_cards WHERE account_id = ? AND is_active = 1"
            row = self.db.fetch_one(query, (account_id,))
            return self._row_to_credit_card(row) if row else None
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка получения карты по account_id={account_id}: {e}",
                exc_info=True
            )
            raise

    def get_all_active(self) -> List[CreditCard]:
        """
        Получает все активные кредитные карты.
        
        Returns:
            Список объектов CreditCard
        """
        try:
            query = "SELECT * FROM credit_cards WHERE is_active = 1 ORDER BY name"
            rows = self.db.fetch_all(query)
            return [self._row_to_credit_card(row) for row in rows]
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения активных карт: {e}", exc_info=True)
            raise

    def get_all_card_account_ids(self) -> List[int]:
        """
        Получает ID всех счетов, к которым привязаны активные карты.
        
        Используется для фильтрации доступных счетов при создании новой карты.
        
        Returns:
            Список account_id
        """
        try:
            query = "SELECT account_id FROM credit_cards WHERE is_active = 1"
            rows = self.db.fetch_all(query)
            return [row["account_id"] for row in rows]
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения ID счетов карт: {e}", exc_info=True)
            raise

    def update(self, card: CreditCard):
        """
        Обновляет настройки кредитной карты.
        account_id не обновляется, так как привязка к счёту неизменна.
        
        Args:
            card: объект CreditCard с обновлёнными полями (id обязателен)
            
        Raises:
            ValueError: если не передан id
            Exception: при ошибке БД
        """
        try:
            if not card.id:
                raise ValueError("id обязателен для обновления карты")

            query = """
                UPDATE credit_cards SET
                    name = ?,
                    annual_rate = ?,
                    grace_months = ?,
                    min_payment_percent = ?,
                    payment_day = ?,
                    statement_day = ?,
                    credit_limit = ?,
                    is_active = ?
                WHERE id = ?
            """
            params = (
                card.name,
                float(card.annual_rate),
                card.grace_months,
                float(card.min_payment_percent),
                card.payment_day,
                card.statement_day,
                float(card.credit_limit),
                1 if card.is_active else 0,
                card.id
            )
            self.db.execute(query, params)
            logger.info(f"[{self.__class__.__name__}] Обновлена карта ID={card.id}, name='{card.name}'")
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при обновлении: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обновления карты {card.id}: {e}", exc_info=True)
            raise

    def delete(self, card_id: int):
        """
        Мягко удаляет карту (устанавливает is_active = 0).
        
        Args:
            card_id: ID кредитной карты
        """
        try:
            query = "UPDATE credit_cards SET is_active = 0 WHERE id = ?"
            self.db.execute(query, (card_id,))
            logger.info(f"[{self.__class__.__name__}] Мягко удалена карта ID={card_id}")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка удаления карты {card_id}: {e}", exc_info=True)
            raise

    def hard_delete(self, card_id: int):
        """
        Физически удаляет карту из БД.
        
        Используется только при каскадном удалении вместе со счётом.
        
        Args:
            card_id: ID кредитной карты
        """
        try:
            query = "DELETE FROM credit_cards WHERE id = ?"
            self.db.execute(query, (card_id,))
            logger.info(f"[{self.__class__.__name__}] Физически удалена карта ID={card_id}")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка физического удаления карты {card_id}: {e}", exc_info=True)
            raise

    def _row_to_credit_card(self, row: dict) -> CreditCard:
        """
        Маппит строку БД в объект CreditCard.
        
        Преобразует float → Decimal для денежных полей.
        
        Args:
            row: словарь со строкой из БД
            
        Returns:
            Объект CreditCard
        """
        return CreditCard(
            id=row["id"],
            account_id=row["account_id"],
            name=row["name"],
            annual_rate=Decimal(str(row["annual_rate"])),
            grace_months=row["grace_months"],
            min_payment_percent=Decimal(str(row["min_payment_percent"])),
            payment_day=row["payment_day"],
            statement_day=row["statement_day"],
            credit_limit=Decimal(str(row["credit_limit"])),
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else datetime.now()
        )