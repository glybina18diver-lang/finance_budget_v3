"""
Репозиторий для работы с кредитными картами.
Инкапсулирует CRUD-операции для credit_cards, credit_card_periods, credit_card_payments.
"""
from typing import List, Optional
import logging
from core.models import CreditCard, CreditCardPeriod, CreditCardPayment

logger = logging.getLogger(__name__)


class CreditCardRepository:
    """Репозиторий кредитных карт."""

    def __init__(self, db):
        """
        Инициализация репозитория.

        Args:
            db: экземпляр подключения к базе данных
        """
        self.db = db

    # =================== CreditCard ===================

    def get_all_cards(self) -> List[CreditCard]:
        """Возвращает все кредитные карты."""
        try:
            query = "SELECT * FROM credit_cards"
            rows = self.db.fetchall(query)
            return [self._row_to_card(row) for row in rows]
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка получения всех карт: {e}", exc_info=True)
            raise

    def get_card_by_id(self, card_id: int) -> Optional[CreditCard]:
        """Возвращает карту по ID."""
        try:
            query = "SELECT * FROM credit_cards WHERE id = ?"
            row = self.db.fetchone(query, (card_id,))
            return self._row_to_card(row) if row else None
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка получения карты #{card_id}: {e}", exc_info=True)
            raise

    def get_card_by_account_id(self, account_id: int) -> Optional[CreditCard]:
        """Возвращает карту по ID связанного счёта."""
        try:
            query = "SELECT * FROM credit_cards WHERE account_id = ?"
            row = self.db.fetchone(query, (account_id,))
            return self._row_to_card(row) if row else None
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка получения карты по счёту #{account_id}: {e}", exc_info=True)
            raise

    def create_card(self, card: CreditCard) -> int:
        """Создаёт новую кредитную карту."""
        try:
            query = """
                INSERT INTO credit_cards (account_id, name, annual_rate, grace_months, 
                                          min_payment_percent, payment_day, statement_day, credit_limit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                card.account_id, card.name, card.annual_rate, card.grace_months,
                card.min_payment_percent, card.payment_day, card.statement_day, card.credit_limit
            )
            new_id = self.db.execute(query, params)
            card.id = new_id
            return new_id
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка создания карты: {e}", exc_info=True)
            raise

    def update_card(self, card: CreditCard) -> bool:
        """Обновляет данные кредитной карты."""
        try:
            query = """
                UPDATE credit_cards SET
                    account_id = ?, name = ?, annual_rate = ?,
                    grace_months = ?, min_payment_percent = ?,
                    payment_day = ?, statement_day = ?, credit_limit = ?
                WHERE id = ?
            """
            params = (
                card.account_id, card.name, card.annual_rate,
                card.grace_months, card.min_payment_percent,
                card.payment_day, card.statement_day, card.credit_limit,
                card.id
            )
            self.db.execute(query, params)
            return True
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка обновления карты #{card.id}: {e}", exc_info=True)
            raise

    def delete_card(self, card_id: int) -> bool:
        """Удаляет кредитную карту."""
        try:
            query = "DELETE FROM credit_cards WHERE id = ?"
            self.db.execute(query, (card_id,))
            return True
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка удаления карты #{card_id}: {e}", exc_info=True)
            raise

    def get_or_create_card_for_account(self, account_id: int) -> CreditCard:
        """
        Возвращает кредитную карту для счёта.
        Если записи нет — создаёт с дефолтными параметрами из модели.

        Args:
            account_id: ID счёта в таблице accounts

        Returns:
            Объект CreditCard
        """
        try:
            card = self.get_card_by_account_id(account_id)
            if card:
                return card

            # Используем только обязательные поля, остальное берётся из модели
            card = CreditCard(account_id=account_id)
            self.create_card(card)
            return card
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка создания/получения карты для счёта #{account_id}: {e}", exc_info=True)
            raise

    def get_all_cards_with_accounts(self) -> List[dict]:
        """
        Возвращает все кредитные карты вместе с данными счёта.
        Ищет по account_type = 'CreditCard' в accounts.

        Returns:
            Список словарей с данными карт и счетов
        """
        try:
            query = """
                SELECT
                    a.id AS account_id, a.name AS account_name,
                    a.current_balance,
                    cc.id AS card_id, cc.annual_rate, cc.grace_months, cc.min_payment_percent,
                    cc.credit_limit
                FROM accounts a
                LEFT JOIN credit_cards cc ON a.id = cc.account_id
                WHERE a.account_type = 'CreditCard' AND a.is_active = 1
                ORDER BY a.name
            """
            return self.db.fetchall(query)
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка получения карт со счетами: {e}", exc_info=True)
            raise

    # =================== CreditCardPeriod ===================

    def get_periods_by_card(self, card_id: int) -> List[CreditCardPeriod]:
        """Возвращает все периоды по карте, отсортированные по месяцу."""
        try:
            query = """
                SELECT * FROM credit_card_periods
                WHERE card_id = ?
                ORDER BY period_month DESC
            """
            rows = self.db.fetchall(query, (card_id,))
            return [self._row_to_period(row) for row in rows]
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка получения периодов карты #{card_id}: {e}", exc_info=True)
            raise

    def get_period(self, card_id: int, period_month: str) -> Optional[CreditCardPeriod]:
        """Возвращает период по карте и месяцу."""
        try:
            query = """
                SELECT * FROM credit_card_periods
                WHERE card_id = ? AND period_month = ?
            """
            row = self.db.fetchone(query, (card_id, period_month))
            return self._row_to_period(row) if row else None
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка получения периода {period_month} карты #{card_id}: {e}", exc_info=True)
            raise

    def create_period(self, period: CreditCardPeriod) -> int:
        """Создаёт новый период."""
        try:
            query = """
                INSERT INTO credit_card_periods (
                    card_id, period_month, total_purchases, total_transfers,
                    grace_period_end, is_paid, paid_amount,
                    interest_retroactive, interest_daily_accrued
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                period.card_id, period.period_month,
                period.total_purchases, period.total_transfers,
                period.grace_period_end,
                1 if period.is_paid else 0,
                period.paid_amount,
                period.interest_retroactive,
                period.interest_daily_accrued
            )
            new_id = self.db.execute(query, params)
            period.id = new_id
            return new_id
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка создания периода: {e}", exc_info=True)
            raise

    def update_period(self, period: CreditCardPeriod) -> bool:
        """
        Обновляет данные периода в БД.
        
        Args:
            period: объект CreditCardPeriod с обновлёнными полями
            
        Returns:
            True если успешно
        """
        try:
            query = """
                UPDATE credit_card_periods SET
                    total_purchases = ?, 
                    total_transfers = ?,
                    grace_period_end = ?, 
                    is_paid = ?,
                    paid_amount = ?, 
                    interest_retroactive = ?, 
                    interest_daily_accrued = ?
                WHERE id = ?
            """
            params = (
                period.total_purchases, 
                period.total_transfers,
                period.grace_period_end, 
                int(period.is_paid),  # SQLite требует 0 или 1 для boolean
                period.paid_amount, 
                period.interest_retroactive, 
                period.interest_daily_accrued,
                period.id
            )
            self.db.execute(query, params)
            return True
            
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка обновления периода #{period.id}: {e}", exc_info=True)
            raise

    def delete_period(self, period_id: int) -> bool:
        """Удаляет период."""
        try:
            query = "DELETE FROM credit_card_periods WHERE id = ?"
            self.db.execute(query, (period_id,))
            return True
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка удаления периода #{period_id}: {e}", exc_info=True)
            raise

    # =================== CreditCardPayment ===================

    def get_payments_by_card(self, card_id: int) -> List[CreditCardPayment]:
        """Возвращает все платежи по карте."""
        try:
            query = """
                SELECT * FROM credit_card_payments
                WHERE card_id = ?
                ORDER BY date DESC
            """
            rows = self.db.fetchall(query, (card_id,))
            return [self._row_to_payment(row) for row in rows]
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка получения платежей карты #{card_id}: {e}", exc_info=True)
            raise

    def create_payment(self, payment: CreditCardPayment) -> int:
        """Создаёт новый платёж."""
        try:
            query = """
                INSERT INTO credit_card_payments (
                    card_id, date, amount, from_account_id, allocation_json
                ) VALUES (?, ?, ?, ?, ?)
            """
            params = (
                payment.card_id, payment.date, payment.amount,
                payment.from_account_id, payment.allocation_json
            )
            new_id = self.db.execute(query, params)
            payment.id = new_id
            return new_id
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка создания платежа: {e}", exc_info=True)
            raise

    def delete_payment(self, payment_id: int) -> bool:
        """Удаляет платёж."""
        try:
            query = "DELETE FROM credit_card_payments WHERE id = ?"
            self.db.execute(query, (payment_id,))
            return True
        except Exception as e:
            logger.error(f"[CreditCardRepository] Ошибка удаления платежа #{payment_id}: {e}", exc_info=True)
            raise

    # =================== Маппинг ===================

    def _row_to_card(self, row) -> CreditCard:
        """Преобразует строку БД в объект CreditCard."""
        return CreditCard(
            id=row["id"],
            account_id=row["account_id"],
            name=row["name"],
            annual_rate=row["annual_rate"],
            grace_months=row["grace_months"],
            min_payment_percent=row["min_payment_percent"],
            payment_day=row.get("payment_day", 10),
            statement_day=row.get("statement_day", 1),
            credit_limit=row.get("credit_limit", 0.0)
        )

    def _row_to_period(self, row) -> CreditCardPeriod:
        """Преобразует строку БД в объект CreditCardPeriod."""
        return CreditCardPeriod(
            id=row["id"],
            card_id=row["card_id"],
            period_month=row["period_month"],
            total_purchases=row["total_purchases"],
            total_transfers=row["total_transfers"],
            grace_period_end=row.get("grace_period_end"),
            is_paid=bool(row["is_paid"]),
            paid_amount=row["paid_amount"],
            interest_retroactive=row["interest_retroactive"],
            interest_daily_accrued=row["interest_daily_accrued"]
        )

    def _row_to_payment(self, row) -> CreditCardPayment:
        """Преобразует строку БД в объект CreditCardPayment."""
        return CreditCardPayment(
            id=row["id"],
            card_id=row["card_id"],
            date=row["date"],
            amount=row["amount"],
            from_account_id=row["from_account_id"],
            allocation_json=row.get("allocation_json")
        )