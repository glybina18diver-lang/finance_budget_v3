"""
Репозиторий для работы с кредитными картами.
Инкапсулирует CRUD-операции для credit_cards, credit_card_periods, credit_card_payments.
"""
from typing import List, Optional
from core.models import CreditCard, CreditCardPeriod, CreditCardPayment


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
        query = "SELECT * FROM credit_cards"
        rows = self.db.fetchall(query)
        return [self._row_to_card(row) for row in rows]

    def get_card_by_id(self, card_id: int) -> Optional[CreditCard]:
        """Возвращает карту по ID."""
        query = "SELECT * FROM credit_cards WHERE id = ?"
        row = self.db.fetchone(query, (card_id,))
        return self._row_to_card(row) if row else None

    def get_card_by_account_id(self, account_id: int) -> Optional[CreditCard]:
        """Возвращает карту по ID связанного счёта."""
        query = "SELECT * FROM credit_cards WHERE account_id = ?"
        row = self.db.fetchone(query, (account_id,))
        return self._row_to_card(row) if row else None

    def create_card(self, card: CreditCard) -> int:
        """Создаёт новую кредитную карту."""
        query = """
            INSERT INTO credit_cards (account_id, name, annual_rate, grace_months, min_payment_percent)
            VALUES (?, ?, ?, ?, ?)
        """
        params = (
            card.account_id, card.name, card.annual_rate,
            card.grace_months, card.min_payment_percent
        )
        new_id = self.db.execute(query, params)
        card.id = new_id
        return new_id

    def update_card(self, card: CreditCard) -> bool:
        """Обновляет данные кредитной карты."""
        query = """
            UPDATE credit_cards SET
                account_id = ?, name = ?, annual_rate = ?,
                grace_months = ?, min_payment_percent = ?
            WHERE id = ?
        """
        params = (
            card.account_id, card.name, card.annual_rate,
            card.grace_months, card.min_payment_percent, card.id
        )
        self.db.execute(query, params)
        return True

    def delete_card(self, card_id: int) -> bool:
        """Удаляет кредитную карту."""
        query = "DELETE FROM credit_cards WHERE id = ?"
        self.db.execute(query, (card_id,))
        return True

    # =================== CreditCardPeriod ===================

    def get_periods_by_card(self, card_id: int) -> List[CreditCardPeriod]:
        """Возвращает все периоды по карте, отсортированные по месяцу."""
        query = """
            SELECT * FROM credit_card_periods
            WHERE card_id = ?
            ORDER BY period_month DESC
        """
        rows = self.db.fetchall(query, (card_id,))
        return [self._row_to_period(row) for row in rows]

    def get_period(self, card_id: int, period_month: str) -> Optional[CreditCardPeriod]:
        """Возвращает период по карте и месяцу."""
        query = """
            SELECT * FROM credit_card_periods
            WHERE card_id = ? AND period_month = ?
        """
        row = self.db.fetchone(query, (card_id, period_month))
        return self._row_to_period(row) if row else None

    def create_period(self, period: CreditCardPeriod) -> int:
        """Создаёт новый период."""
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

    def update_period(self, period: CreditCardPeriod) -> bool:
        """Обновляет период."""
        query = """
            UPDATE credit_card_periods SET
                total_purchases = ?, total_transfers = ?,
                grace_period_end = ?, is_paid = ?, paid_amount = ?,
                interest_retroactive = ?, interest_daily_accrued = ?
            WHERE id = ?
        """
        params = (
            period.total_purchases, period.total_transfers,
            period.grace_period_end,
            1 if period.is_paid else 0,
            period.paid_amount,
            period.interest_retroactive,
            period.interest_daily_accrued,
            period.id
        )
        self.db.execute(query, params)
        return True

    def delete_period(self, period_id: int) -> bool:
        """Удаляет период."""
        query = "DELETE FROM credit_card_periods WHERE id = ?"
        self.db.execute(query, (period_id,))
        return True

    # =================== CreditCardPayment ===================

    def get_payments_by_card(self, card_id: int) -> List[CreditCardPayment]:
        """Возвращает все платежи по карте."""
        query = """
            SELECT * FROM credit_card_payments
            WHERE card_id = ?
            ORDER BY date DESC
        """
        rows = self.db.fetchall(query, (card_id,))
        return [self._row_to_payment(row) for row in rows]

    def create_payment(self, payment: CreditCardPayment) -> int:
        """Создаёт новый платёж."""
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

    def delete_payment(self, payment_id: int) -> bool:
        """Удаляет платёж."""
        query = "DELETE FROM credit_card_payments WHERE id = ?"
        self.db.execute(query, (payment_id,))
        return True

    # =================== Маппинг ===================

    def _row_to_card(self, row) -> CreditCard:
        """Преобразует строку БД в объект CreditCard."""
        return CreditCard(
            id=row["id"],
            account_id=row["account_id"],
            name=row["name"],
            annual_rate=row["annual_rate"],
            grace_months=row["grace_months"],
            min_payment_percent=row["min_payment_percent"]
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