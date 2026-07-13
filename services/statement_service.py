"""
Сервис управления выписками и минимальными платежами (StatementService).

Отвечает за генерацию биллинговых циклов и расчёт обязательных платежей.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from core.models import Statement, CreditCard
from core.repositories.statement_repository import StatementRepository
from core.repositories.tranche_repository import TrancheRepository
from core.repositories.interest_accrual_repository import InterestAccrualRepository
from core.repositories.credit_card_repository import CreditCardRepository

logger = logging.getLogger(__name__)


class StatementService:
    """Бизнес-логика формирования выписок и расчёта минимального платежа."""

    def __init__(
        self,
        statement_repo: StatementRepository,
        tranche_repo: TrancheRepository,
        accrual_repo: InterestAccrualRepository,
        card_repo: CreditCardRepository
    ):
        self.statement_repo = statement_repo
        self.tranche_repo = tranche_repo
        self.accrual_repo = accrual_repo
        self.card_repo = card_repo

    def generate_statement(self, card_id: int, year: int, month: int) -> Statement:
        """
        Генерирует выписку за указанный месяц.
        
        Выписка формируется 1-го числа. Дата обязательного платежа — конец месяца.
        
        Args:
            card_id: ID кредитной карты
            year: год выписки
            month: месяц выписки (1-12)
            
        Returns:
            Созданный объект Statement
            
        Raises:
            ValueError: если выписка за этот месяц уже существует
        """
        try:
            # 1. Проверка на дубликат
            existing = self.statement_repo.get_by_month(card_id, year, month)
            if existing:
                raise ValueError(f"Выписка за {year}-{month} уже существует (ID={existing.id})")

            # 2. Даты выписки
            statement_date = date(year, month, 1)
            # Последний день месяца
            if month == 12:
                due_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                due_date = date(year, month + 1, 1) - timedelta(days=1)

            # 3. Расчёт баланса на начало периода (берём из предыдущей выписки или 0)
            prev_statement = self._get_previous_statement(card_id, year, month)
            opening_balance = prev_statement.closing_balance if prev_statement else Decimal("0.00")

            # 4. Новые начисления за период (упрощённо: сумма траншей + проценты)
            # В реальном проекте здесь будут сложные SQL-агрегации по датам
            new_charges = self._calculate_new_charges(card_id, year, month)
            interest_charged = self._calculate_interest_charged(card_id, year, month)
            payments_received = self._calculate_payments_received(card_id, year, month)

            # 5. Баланс на конец периода
            closing_balance = (opening_balance + new_charges + interest_charged - payments_received).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # 6. Расчёт минимального платежа
            card = self.card_repo.get_by_id(card_id)
            if not card:
                raise ValueError(f"Карта ID {card_id} не найдена")
            
            min_payment = self.calculate_min_payment(closing_balance, interest_charged, card.min_payment_percent)

            # 7. Создание и сохранение
            statement = Statement(
                card_id=card_id,
                statement_date=statement_date,
                due_date=due_date,
                opening_balance=opening_balance,
                new_charges=new_charges,
                payments_received=payments_received,
                interest_charged=interest_charged,
                closing_balance=closing_balance,
                min_payment_required=min_payment,
                status="open"
            )

            stmt_id = self.statement_repo.create(statement)
            statement.id = stmt_id

            logger.info(
                f"[{self.__class__.__name__}] Сгенерирована выписка ID={stmt_id} "
                f"за {year}-{month}. Мин. платёж: {min_payment} ₽"
            )
            return statement

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при генерации выписки: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка генерации выписки: {e}", exc_info=True)
            raise

    def calculate_min_payment(
        self, 
        debt_amount: Decimal, 
        interest_amount: Decimal, 
        min_percent: Decimal
    ) -> Decimal:
        """
        Рассчитывает минимальный обязательный платёж.
        
        Формула: (Тело долга × min_percent) + Проценты.
        (Комиссии добавляются аналогично процентам, если они есть).
        
        Args:
            debt_amount: сумма основного долга на дату выписки
            interest_amount: сумма начисленных процентов
            min_percent: процент минимального платежа (например, 0.02)
            
        Returns:
            Сумма минимального платежа, округлённая до копеек
        """
        try:
            if debt_amount < 0:
                raise ValueError("Сумма долга не может быть отрицательной")
            if not (0 <= min_percent <= 1):
                raise ValueError("min_percent должен быть от 0 до 1")

            principal_part = (debt_amount * min_percent).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            total_min = principal_part + interest_amount
            
            return total_min.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация расчёта мин. платежа: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка расчёта мин. платежа: {e}", exc_info=True)
            raise

    # --- Приватные методы для агрегации данных (заглушки для SQL) ---

    def _get_previous_statement(self, card_id: int, year: int, month: int) -> Optional[Statement]:
        """Получает выписку за предыдущий месяц."""
        # Упрощённая логика: если месяц 1, то предыдущий 12 прошлого года
        prev_month = month - 1
        prev_year = year
        if prev_month == 0:
            prev_month = 12
            prev_year -= 1
        return self.statement_repo.get_by_month(card_id, prev_year, prev_month)

    def _calculate_new_charges(self, card_id: int, year: int, month: int) -> Decimal:
        """Сумма новых траншей (покупок/переводов) за период."""
        # TODO: Реализовать SQL-запрос с SUM(original_amount) WHERE transaction_date IN (year, month)
        return Decimal("0.00")

    def _calculate_interest_charged(self, card_id: int, year: int, month: int) -> Decimal:
        """Сумма начисленных процентов за период."""
        # TODO: Реализовать SQL-запрос с SUM(amount) из interest_accruals
        return Decimal("0.00")

    def _calculate_payments_received(self, card_id: int, year: int, month: int) -> Decimal:
        """Сумма внесённых платежей за период."""
        # TODO: Реализовать SQL-запрос с SUM(amount) из credit_card_payments
        return Decimal("0.00")