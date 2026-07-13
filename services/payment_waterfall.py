"""
Каскадная модель списания платежей (Payment Waterfall).

Распределяет внесённую сумму по строгому приоритету:
1. Комиссии и штрафы
2. Накопленные проценты
3. Тело долга вне льготного периода (FIFO)
4. Тело долга в льготном периоде (FIFO)
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any

from core.models import Tranche, InterestAccrual
from core.repositories.tranche_repository import TrancheRepository
from core.repositories.interest_accrual_repository import InterestAccrualRepository

logger = logging.getLogger(__name__)


@dataclass
class PaymentAllocation:
    """Детализация распределения платежа по уровням каскада."""
    commissions_paid: Decimal = Decimal('0.00')
    interest_paid: Decimal = Decimal('0.00')
    principal_paid: Decimal = Decimal('0.00')
    remaining_amount: Decimal = Decimal('0.00')
    tranches_affected: List[Dict[str, Any]] = field(default_factory=list)


class PaymentWaterfall:
    """
    Реализует банковскую логику распределения платежа по кредитной карте.
    """

    def __init__(self, tranche_repo: TrancheRepository, accrual_repo: InterestAccrualRepository):
        self.tranche_repo = tranche_repo
        self.accrual_repo = accrual_repo

    def distribute_payment(self, card_id: int, amount: Decimal, payment_date: date) -> PaymentAllocation:
        """
        Распределяет платёж по 4 уровням приоритета.
        
        Args:
            card_id: ID кредитной карты
            amount: сумма платежа
            payment_date: дата внесения платежа
            
        Returns:
            PaymentAllocation: объект с детализацией распределения
            
        Raises:
            ValueError: если сумма платежа <= 0
        """
        try:
            if amount <= 0:
                raise ValueError("Сумма платежа должна быть положительной")

            allocation = PaymentAllocation()
            remaining = amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            # Получаем все активные транши карты
            tranches = self.tranche_repo.get_active_by_card(card_id)
            
            # Уровень 1: Комиссии (по переводам)
            remaining = self._apply_level_1_commissions(tranches, remaining, allocation)

            # Уровень 2: Накопленные проценты
            remaining = self._apply_level_2_interest(card_id, remaining, allocation)

            # Уровень 3: Тело долга вне льготного периода (FIFO)
            remaining = self._apply_level_3_principal_outside_grace(tranches, remaining, payment_date, allocation)

            # Уровень 4: Тело долга в льготном периоде (FIFO)
            remaining = self._apply_level_4_principal_inside_grace(
                tranches, remaining, payment_date, allocation
            )

            allocation.remaining_amount = remaining

            logger.info(
                f"[{self.__class__.__name__}] Платёж {amount} ₽ распределён: "
                f"комиссии={allocation.commissions_paid}, "
                f"проценты={allocation.interest_paid}, "
                f"тело={allocation.principal_paid}"
            )
            return allocation

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация платежа: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка распределения платежа: {e}", exc_info=True)
            raise

    def _apply_level_1_commissions(
        self, tranches: List[Tranche], remaining: Decimal, allocation: PaymentAllocation
    ) -> Decimal:
        """
        Уровень 1: Погашение комиссий за переводы.
        """
        try:
            for tranche in tranches:
                if tranche.tranche_type == 'transfer' and tranche.commission > 0:
                    # Комиссия "зашита" в remaining_amount, но имеет приоритет
                    to_pay = min(remaining, tranche.commission)
                    if to_pay > 0:
                        tranche.remaining_amount -= to_pay
                        tranche.commission -= to_pay
                        self.tranche_repo.update(tranche)
                        
                        remaining -= to_pay
                        allocation.commissions_paid += to_pay
                        allocation.tranches_affected.append({
                            "tranche_id": tranche.id, 
                            "amount": to_pay, 
                            "type": "commission"
                        })
                        
                        if remaining <= 0:
                            break
            return remaining
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка на Уровне 1 (Комиссии): {e}", exc_info=True)
            raise

    def _apply_level_2_interest(self, card_id: int, remaining: Decimal, allocation: PaymentAllocation) -> Decimal:
        """
        Уровень 2: Погашение накопленных процентов.
        Сначала проценты по переводам, затем ретроактивные по покупкам.
        """
        try:
            # Получаем все неоплаченные начисления процентов по карте одним запросом
            accruals = self.accrual_repo.get_unpaid_by_card(card_id)
            
            # Сортируем: сначала переводы (tranche_type='transfer'), потом покупки
            # Для этого нужно получить типы траншей
            tranche_types = {}
            tranches = self.tranche_repo.get_active_by_card(card_id)
            for t in tranches:
                tranche_types[t.id] = t.tranche_type
            
            # Сортировка: переводы (0) перед покупками (1), внутри группы - по дате транша
            accruals.sort(key=lambda a: (
                0 if tranche_types.get(a.tranche_id) == 'transfer' else 1,
                a.accrual_date
            ))

            for accrual in accruals:
                unpaid_interest = accrual.amount - accrual.paid_amount
                if unpaid_interest <= 0:
                    continue
                    
                to_pay = min(remaining, unpaid_interest)
                if to_pay > 0:
                    accrual.paid_amount += to_pay
                    if accrual.paid_amount >= accrual.amount:
                        accrual.is_paid = True
                    self.accrual_repo.update_paid_amount(accrual.id, float(accrual.paid_amount))
                    
                    remaining -= to_pay
                    allocation.interest_paid += to_pay
                    
                    if remaining <= 0:
                        break
            
            return remaining
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка на Уровне 2 (Проценты): {e}", exc_info=True)
            raise

    def _apply_level_3_principal_outside_grace(
        self, tranches: List[Tranche], remaining: Decimal, payment_date: date, allocation: PaymentAllocation
    ) -> Decimal:
        """
        Уровень 3: Тело долга вне льготного периода (FIFO).
        """
        try:
            # Фильтруем транши, у которых грейс закончился на дату платежа
            expired_tranches = [
                t for t in tranches 
                if t.grace_end_date and t.grace_end_date < payment_date and t.remaining_amount > 0
            ]
            # Сортируем от старых к новым (FIFO)
            expired_tranches.sort(key=lambda t: t.transaction_date)

            for tranche in expired_tranches:
                to_pay = min(remaining, tranche.remaining_amount)
                if to_pay > 0:
                    tranche.remaining_amount -= to_pay
                    if tranche.remaining_amount <= 0:
                        tranche.status = 'paid'
                    else:
                        tranche.status = 'partial'
                    self.tranche_repo.update(tranche)
                    
                    remaining -= to_pay
                    allocation.principal_paid += to_pay
                    allocation.tranches_affected.append({
                        "tranche_id": tranche.id, 
                        "amount": to_pay, 
                        "type": "principal_outside_grace"
                    })
                    
                    if remaining <= 0:
                        break
            return remaining
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка на Уровне 3 (Тело вне грейса): {e}", exc_info=True)
            raise

    def _apply_level_4_principal_inside_grace(
        self, tranches: List[Tranche], remaining: Decimal, payment_date: date, allocation: PaymentAllocation
    ) -> Decimal:
        """
        Уровень 4: Тело долга в льготном периоде (FIFO).
        """
        try:
            # Фильтруем транши, у которых грейс ещё действует
            active_tranches = [
                t for t in tranches 
                if (t.grace_end_date is None or t.grace_end_date >= payment_date) 
                and t.remaining_amount > 0
            ]
            # Сортируем от старых к новым (FIFO)
            active_tranches.sort(key=lambda t: t.transaction_date)

            for tranche in active_tranches:
                to_pay = min(remaining, tranche.remaining_amount)
                if to_pay > 0:
                    tranche.remaining_amount -= to_pay
                    if tranche.remaining_amount <= 0:
                        tranche.status = 'paid'
                    else:
                        tranche.status = 'partial'
                    self.tranche_repo.update(tranche)
                    
                    remaining -= to_pay
                    allocation.principal_paid += to_pay
                    allocation.tranches_affected.append({
                        "tranche_id": tranche.id, 
                        "amount": to_pay, 
                        "type": "principal_inside_grace"
                    })
                    
                    if remaining <= 0:
                        break
            return remaining
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка на Уровне 4 (Тело в грейсе): {e}", exc_info=True)
            raise