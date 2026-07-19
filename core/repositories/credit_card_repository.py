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
    Все параметры карты опциональны, кроме account_id.
    Название карты подтягивается из таблицы accounts через LEFT JOIN.
    """

    def __init__(self, db: Database):
        """
        Инициализация репозитория.
        
        Args:
            db: экземпляр Database (фасад SQLite)
        """
        self.db = db

    def create(self, card: CreditCard) -> int:
        """
        Создаёт новую запись кредитной карты.
        
        Вставляет только account_id и те поля, которые не равны None.
        
        Args:
            card: объект CreditCard (account_id обязателен, остальные поля опциональны)
            
        Returns:
            ID созданной записи
            
        Raises:
            ValueError: если не передан account_id
            Exception: при ошибке БД
        """
        try:
            if not card.account_id:
                raise ValueError("account_id обязателен для создания карты")

            # Динамически формируем список колонок и значений
            columns = ["account_id"]
            values = [card.account_id]
            placeholders = ["?"]

            optional_fields = [
                ("credit_limit", card.credit_limit),
                ("annual_rate", card.annual_rate),
                ("grace_months", card.grace_months),
                ("min_payment_percent", card.min_payment_percent),
                ("payment_day", card.payment_day),
                ("statement_day", card.statement_day),
            ]

            for col_name, value in optional_fields:
                if value is not None:
                    columns.append(col_name)
                    # Конвертируем Decimal в float для SQLite
                    if isinstance(value, Decimal):
                        values.append(float(value))
                    else:
                        values.append(value)
                    placeholders.append("?")

            columns_str = ", ".join(columns)
            placeholders_str = ", ".join(placeholders)

            query = f"""
                INSERT INTO credit_cards ({columns_str})
                VALUES ({placeholders_str})
            """
            card_id = self.db.execute(query, tuple(values))
            logger.info(
                f"[{self.__class__.__name__}] Создана карта ID={card_id}, account_id={card.account_id}"
            )
            return card_id
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при создании: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания карты: {e}", exc_info=True)
            raise

    def get_by_id(self, card_id: int) -> Optional[CreditCard]:
        """
        Получает карту по ID с именем счёта из таблицы accounts.
        
        Args:
            card_id: ID кредитной карты
            
        Returns:
            Объект CreditCard или None, если не найдена
        """
        try:
            query = """
                SELECT cc.*, a.name AS account_name
                FROM credit_cards cc
                LEFT JOIN accounts a ON cc.account_id = a.id
                WHERE cc.id = ? AND cc.is_active = 1
            """
            row = self.db.fetch_one(query, (card_id,))
            return self._row_to_credit_card(row) if row else None
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения карты {card_id}: {e}", exc_info=True)
            raise

    def get_by_account_id(self, account_id: int) -> Optional[CreditCard]:
        """
        Получает активную карту, привязанную к счёту.
        
        Args:
            account_id: ID счёта в таблице accounts
            
        Returns:
            Объект CreditCard или None
        """
        try:
            query = """
                SELECT cc.*, a.name AS account_name
                FROM credit_cards cc
                LEFT JOIN accounts a ON cc.account_id = a.id
                WHERE cc.account_id = ? AND cc.is_active = 1
            """
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
        Получает все активные кредитные карты с именами счетов.
        
        Returns:
            Список объектов CreditCard, отсортированный по имени счёта
        """
        try:
            query = """
                SELECT cc.*, a.name AS account_name
                FROM credit_cards cc
                LEFT JOIN accounts a ON cc.account_id = a.id
                WHERE cc.is_active = 1
                ORDER BY a.name
            """
            rows = self.db.fetch_all(query)
            return [self._row_to_credit_card(row) for row in rows]
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения активных карт: {e}", exc_info=True)
            raise

    def update(self, card: CreditCard):
        """
        Обновляет параметры кредитной карты.
        
        Обновляет только те поля, которые не равны None.
        account_id изменить нельзя (ограничение UNIQUE в БД).
        
        Args:
            card: объект CreditCard с обновлёнными полями (id обязателен)
            
        Raises:
            ValueError: если не передан id
            Exception: при ошибке БД
        """
        try:
            if not card.id:
                raise ValueError("id обязателен для обновления карты")

            # Динамически формируем SET-часть запроса
            set_parts = []
            values = []

            optional_fields = [
                ("credit_limit", card.credit_limit),
                ("annual_rate", card.annual_rate),
                ("grace_months", card.grace_months),
                ("min_payment_percent", card.min_payment_percent),
                ("payment_day", card.payment_day),
                ("statement_day", card.statement_day),
            ]

            for col_name, value in optional_fields:
                if value is not None:
                    set_parts.append(f"{col_name} = ?")
                    if isinstance(value, Decimal):
                        values.append(float(value))
                    else:
                        values.append(value)

            if not set_parts:
                logger.warning(
                    f"[{self.__class__.__name__}] Нет полей для обновления карты ID={card.id}"
                )
                return

            values.append(card.id)
            set_clause = ", ".join(set_parts)

            query = f"""
                UPDATE credit_cards
                SET {set_clause}
                WHERE id = ?
            """
            self.db.execute(query, tuple(values))
            logger.info(f"[{self.__class__.__name__}] Обновлена карта ID={card.id}")
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при обновлении: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обновления карты {card.id}: {e}", exc_info=True)
            raise

    def hide(self, card_id: int):
        """
        Скрывает карту (устанавливает is_active = 0).
        
        Args:
            card_id: ID кредитной карты
        """
        try:
            query = "UPDATE credit_cards SET is_active = 0 WHERE id = ?"
            self.db.execute(query, (card_id,))
            logger.info(f"[{self.__class__.__name__}] Карта ID={card_id} скрыта")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка скрытия карты {card_id}: {e}", exc_info=True)
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

    def _row_to_credit_card(self, row) -> CreditCard:
        """
        Маппит строку БД в объект CreditCard.
        
        Корректно обрабатывает NULL-значения для опциональных полей.
        Поле account_name приходит из LEFT JOIN с таблицей accounts.
        
        Args:
            row: строка из БД (dict или sqlite3.Row)
            
        Returns:
            Объект CreditCard
        """
        # Универсальная конвертация в dict (на случай sqlite3.Row)
        if not isinstance(row, dict):
            row = dict(row)
        
        def to_decimal(value) -> Optional[Decimal]:
            """Безопасная конвертация в Decimal."""
            if value is None:
                return None
            return Decimal(str(value))

        return CreditCard(
            id=row["id"],
            account_id=row["account_id"],
            credit_limit=to_decimal(row.get("credit_limit")),
            annual_rate=to_decimal(row.get("annual_rate")),
            grace_months=row.get("grace_months"),
            min_payment_percent=to_decimal(row.get("min_payment_percent")),
            payment_day=row.get("payment_day"),
            statement_day=row.get("statement_day"),
            is_active=bool(row.get("is_active", 1)),
            created_at=datetime.fromisoformat(row["created_at"]) if row.get("created_at") else datetime.now(),
            account_name=row.get("account_name")
        )