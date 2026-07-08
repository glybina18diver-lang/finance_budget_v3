"""
Сервис кредитной карты "Сбер Молодёжная".
Инкапсулирует бизнес-логику: расчёт процентов, комиссий, минимального платежа.
"""
from typing import List, Optional, Dict
import calendar
from datetime import datetime, date
#from dateutil.relativedelta import relativedelta
import json

from core.models import CreditCard, CreditCardPeriod, CreditCardPayment
from core.repositories.credit_card_repository import CreditCardRepository
from core.repositories.account_repository import AccountRepository


class CreditCardService:
    """Сервис управления кредитной картой."""

    # Комиссия за перевод: 5.9% + 590 ₽
    TRANSFER_FEE_PERCENT = 0.059
    TRANSFER_FEE_FIXED = 590.0

    def __init__(self, repo: CreditCardRepository, account_repo: AccountRepository):
        """
        Инициализация сервиса.
        
        Args:
            repo: репозиторий кредитных карт
            account_repo: репозиторий счетов
        """
        self.repo = repo
        self.account_repo = account_repo

    # =================== Карты ===================

    def get_all_cards(self) -> List[CreditCard]:
        """Возвращает все кредитные карты."""
        return self.repo.get_all_cards()

    def create_card(self, account_id: int, name: str = "Сбер Молодёжная") -> int:
        """
        Создаёт новую кредитную карту.
        
        Args:
            account_id: ID счёта карты
            name: название карты
            
        Returns:
            ID созданной карты
        """
        card = CreditCard(
            account_id=account_id,
            name=name,
            annual_rate=49.8,
            grace_months=3,
            min_payment_percent=0.02
        )
        return self.repo.create_card(card)

    # =================== Периоды ===================

    def get_periods(self, card_id: int) -> List[CreditCardPeriod]:
        """Возвращает все периоды по карте."""
        return self.repo.get_periods_by_card(card_id)

    def add_purchase(self, card_id: int, purchase_date: str, amount: float) -> CreditCardPeriod:
        """
        Добавляет покупку в соответствующий период.
        Создаёт период, если его ещё нет.
        
        Args:
            card_id: ID карты
            purchase_date: дата покупки (YYYY-MM-DD)
            amount: сумма покупки
            
        Returns:
            Обновлённый объект периода
        """
        period_month = self._get_period_month(purchase_date)
        period = self.repo.get_period(card_id, period_month)
        
        if not period:
            # Создаём новый период
            grace_end = self._calculate_grace_period_end(purchase_date)
            period = CreditCardPeriod(
                card_id=card_id,
                period_month=period_month,
                total_purchases=0.0,
                total_transfers=0.0,
                grace_period_end=grace_end,
                is_paid=False,
                paid_amount=0.0,
                interest_retroactive=0.0,
                interest_daily_accrued=0.0
            )
            self.repo.create_period(period)
        
        # Увеличиваем сумму покупок
        period.total_purchases += amount
        self.repo.update_period(period)
        
        return period

    def add_transfer(self, card_id: int, transfer_date: str, amount: float) -> Dict:
        """
        Добавляет перевод с кредитной карты.
        Возвращает сумму перевода + комиссию.
        
        Args:
            card_id: ID карты
            transfer_date: дата перевода
            amount: сумма перевода
            
        Returns:
            Словарь {amount, commission, total}
        """
        commission = self.calculate_transfer_commission(amount)
        period_month = self._get_period_month(transfer_date)
        period = self.repo.get_period(card_id, period_month)
        
        if not period:
            grace_end = self._calculate_grace_period_end(transfer_date)
            period = CreditCardPeriod(
                card_id=card_id,
                period_month=period_month,
                total_purchases=0.0,
                total_transfers=0.0,
                grace_period_end=grace_end,
                is_paid=False,
                paid_amount=0.0,
                interest_retroactive=0.0,
                interest_daily_accrued=0.0
            )
            self.repo.create_period(period)
        
        period.total_transfers += amount
        self.repo.update_period(period)
        
        return {
            "amount": amount,
            "commission": commission,
            "total": amount + commission
        }

    # =================== Платежи ===================

    def make_payment(self, card_id: int, payment_data: dict) -> Dict:
        """
        Вносит платёж по кредитной карте с автораспределением.
        
        Логика распределения:
        1. Проценты (ретроактивные + ежедневные до конца предыдущего месяца)
        2. Тело долга (FIFO — от старых периодов к новым)
        
        Args:
            card_id: ID карты
            payment_data: {date, amount, from_account_id}
            
        Returns:
            Словарь с распределением платежа
        """
        amount = float(payment_data["amount"])
        payment_date = payment_data["date"]
        from_account_id = payment_data["from_account_id"]
        
        # Получаем все периоды (от старых к новым)
        periods = sorted(
            self.repo.get_periods_by_card(card_id),
            key=lambda p: p.period_month
        )
        
        # Рассчитываем проценты на текущий момент
        self._recalculate_interest(periods, payment_date)
        
        # Распределение платежа
        allocation = {
            "interest_paid": 0.0,
            "principal_paid": 0.0,
            "periods_updated": []
        }
        
        remaining = amount
        
        # 1. Гасим проценты (сначала ретроактивные, потом ежедневные)
        for period in periods:
            if remaining <= 0:
                break
            
            # Гасим ретроактивные проценты
            if period.interest_retroactive > 0:
                to_pay = min(remaining, period.interest_retroactive)
                period.interest_retroactive -= to_pay
                remaining -= to_pay
                allocation["interest_paid"] += to_pay
            
            # Гасим ежедневные проценты (только до конца предыдущего месяца)
            if period.interest_daily_accrued > 0:
                # Процент с 1 июля не гасится, пока не закончится тело долга
                # Гасим только начисленные до конца grace_period_end
                to_pay = min(remaining, period.interest_daily_accrued)
                period.interest_daily_accrued -= to_pay
                remaining -= to_pay
                allocation["interest_paid"] += to_pay
        
        # 2. Гасим тело долга (FIFO)
        for period in periods:
            if remaining <= 0:
                break
            
            unpaid = period.total_purchases + period.total_transfers - period.paid_amount
            if unpaid <= 0:
                continue
            
            to_pay = min(remaining, unpaid)
            period.paid_amount += to_pay
            remaining -= to_pay
            allocation["principal_paid"] += to_pay
            
            # Проверяем полное погашение
            if period.paid_amount >= period.total_purchases + period.total_transfers:
                period.is_paid = True
                period.paid_amount = period.total_purchases + period.total_transfers
            
            allocation["periods_updated"].append({
                "period_month": period.period_month,
                "paid": to_pay
            })
            
            self.repo.update_period(period)
        
        # Создаём запись платежа
        payment = CreditCardPayment(
            card_id=card_id,
            date=payment_date,
            amount=amount,
            from_account_id=from_account_id,
            allocation_json=json.dumps(allocation, ensure_ascii=False)
        )
        self.repo.create_payment(payment)
        
        return allocation

    # =================== Расчёты ===================

    def calculate_transfer_commission(self, amount: float) -> float:
        """
        Рассчитывает комиссию за перевод с кредитной карты.
        Формула: сумма × 5.9% + 590 ₽
        
        Args:
            amount: сумма перевода
            
        Returns:
            Сумма комиссии
        """
        return amount * self.TRANSFER_FEE_PERCENT + self.TRANSFER_FEE_FIXED

    def calculate_minimum_payment(self, card_id: int, as_of_date: Optional[str] = None) -> Dict:
        """
        Рассчитывает минимальный платёж.
        Формула: 2% от тела долга + все начисленные проценты
        
        Args:
            card_id: ID карты
            as_of_date: дата расчёта (по умолчанию — сегодня)
            
        Returns:
            Словарь {min_payment, principal_part, interest_part, total_debt}
        """
        periods = self.repo.get_periods_by_card(card_id)
        as_of = as_of_date or date.today().strftime("%Y-%m-%d")
        
        self._recalculate_interest(periods, as_of)
        
        total_principal = 0.0
        total_interest = 0.0
        
        for period in periods:
            unpaid = period.total_purchases + period.total_transfers - period.paid_amount
            if unpaid > 0:
                total_principal += unpaid
            total_interest += period.interest_retroactive + period.interest_daily_accrued
        
        principal_part = total_principal * 0.02
        min_payment = principal_part + total_interest
        
        return {
            "min_payment": min_payment,
            "principal_part": principal_part,
            "interest_part": total_interest,
            "total_debt": total_principal + total_interest,
            "total_principal": total_principal,
            "total_interest": total_interest
        }

    def calculate_full_payoff(self, card_id: int, as_of_date: Optional[str] = None) -> Dict:
        """
        Рассчитывает сумму для полного погашения.
        
        Args:
            card_id: ID карты
            as_of_date: дата расчёта
            
        Returns:
            Словарь с разбивкой задолженности
        """
        periods = self.repo.get_periods_by_card(card_id)
        as_of = as_of_date or date.today().strftime("%Y-%m-%d")
        
        self._recalculate_interest(periods, as_of)
        
        total_principal = 0.0
        total_retro = 0.0
        total_daily = 0.0
        
        for period in periods:
            unpaid = period.total_purchases + period.total_transfers - period.paid_amount
            if unpaid > 0:
                total_principal += unpaid
            total_retro += period.interest_retroactive
            total_daily += period.interest_daily_accrued
        
        return {
            "total": total_principal + total_retro + total_daily,
            "principal": total_principal,
            "interest_retroactive": total_retro,
            "interest_daily": total_daily
        }

    # =================== Внутренние методы ===================

    def _get_period_month(self, purchase_date: str) -> str:
        """
        Определяет месяц периода по дате покупки.
        
        Args:
            purchase_date: дата в формате YYYY-MM-DD
            
        Returns:
            Строка в формате YYYY-MM
        """
        dt = datetime.strptime(purchase_date, "%Y-%m-%d")
        return dt.strftime("%Y-%m")

    def _calculate_grace_period_end(self, purchase_date: str) -> str:
        """
        Рассчитывает конец льготного периода.
        Логика: месяц покупки + grace_months месяцев → последний день того месяца.
        
        Пример: покупка 15.03.2025, grace_months=3 → льгота до 30.06.2025
        """
        dt = datetime.strptime(purchase_date, "%Y-%m-%d").date()
        
        # Вычисляем целевой год и месяц (добавляем grace_months)
        month = dt.month - 1 + self._get_card_grace_months()
        year = dt.year + month // 12
        month = month % 12 + 1
        
        # Находим последний день этого месяца
        last_day = calendar.monthrange(year, month)[1]
        
        grace_end = date(year, month, last_day)
        return grace_end.strftime("%Y-%m-%d")

    def _get_card_grace_months(self) -> int:
        """Возвращает количество месяцев льготного периода (по умолчанию 3)."""
        # TODO: брать из настроек карты, пока хардкод
        return 3

    def _recalculate_interest(self, periods: List[CreditCardPeriod], as_of_date: str):
        """
        Пересчитывает проценты для всех периодов на указанную дату.
        
        Логика:
        - Если период НЕ погашен и grace_period_end < as_of_date → 
          ретроактивные проценты на ВСЮ сумму покупок с даты каждой покупки
          + ежедневные проценты после grace_period_end
        - Если период погашен → проценты = 0
        
        Args:
            periods: список периодов
            as_of_date: дата расчёта (YYYY-MM-DD)
        """
        as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        daily_rate = 0.498 / 365  # 49.8% годовых
        
        for period in periods:
            if period.is_paid:
                period.interest_retroactive = 0.0
                period.interest_daily_accrued = 0.0
                continue
            
            if not period.grace_period_end:
                continue
            
            grace_end = datetime.strptime(period.grace_period_end, "%Y-%m-%d").date()
            
            if as_of <= grace_end:
                # Льготный период ещё не закончился → процентов нет
                period.interest_retroactive = 0.0
                period.interest_daily_accrued = 0.0
            else:
                # Льготный период закончился → ретроактивные проценты
                # На ВСЮ сумму покупок за период (упрощённо — считаем от середины месяца)
                # Для точности нужно хранить даты каждой покупки, но пока используем приближение
                
                # Приближение: считаем от середины месяца периода до grace_period_end
                year, month = map(int, period.period_month.split("-"))
                mid_month = date(year, month, 15)
                days_to_grace = (grace_end - mid_month).days
                
                if days_to_grace > 0:
                    period.interest_retroactive = (
                        period.total_purchases * daily_rate * days_to_grace
                    )
                
                # Ежедневные проценты после grace_period_end
                days_after_grace = (as_of - grace_end).days
                if days_after_grace > 0:
                    unpaid = period.total_purchases + period.total_transfers - period.paid_amount
                    period.interest_daily_accrued = (
                        unpaid * daily_rate * days_after_grace
                    )
            
            self.repo.update_period(period)