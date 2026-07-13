"""
Сервис прогнозов и финансовых инсайтов (ForecastService). (Прототип)

Отвечает за расчёт Burn Rate, алертов о спасении грейс-периода 
и прогнозирование минимальных платежей. 
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from core.models import Tranche, CreditCard
from core.repositories.tranche_repository import TrancheRepository
from core.repositories.interest_accrual_repository import InterestAccrualRepository
from core.repositories.credit_card_repository import CreditCardRepository

logger = logging.getLogger(__name__)


@dataclass
class GraceSaverAlert:
    """
    Алерт о скором окончании льготного периода по конкретному траншу.
    """
    tranche_id: int
    tranche_type: str
    amount: Decimal
    days_left: int
    grace_end_date: date
    estimated_retroactive_cost: Decimal  # Сколько процентов спишут, если не погасить


class ForecastService:
    """
    Бизнес-логика расчёта прогнозов и инсайтов по кредитным картам.
    """

    def __init__(
        self,
        tranche_repo: TrancheRepository,
        accrual_repo: InterestAccrualRepository,
        card_repo: CreditCardRepository
    ):
        self.tranche_repo = tranche_repo
        self.accrual_repo = accrual_repo
        self.card_repo = card_repo

    def calculate_burn_rate(self, card_id: int, as_of_date: Optional[date] = None) -> Decimal:
        """
        Рассчитывает «Стоимость дня» (Burn Rate) — сколько рублей в день 
        обходится текущий долг по карте.
        
        Считает только транши, по которым уже капляют проценты 
        (переводы и покупки вне льготного периода).
        
        Args:
            card_id: ID кредитной карты
            as_of_date: дата расчёта (по умолчанию сегодня)
            
        Returns:
            Сумма ежедневных процентов, округлённая до копеек
        """
        try:
            if as_of_date is None:
                as_of_date = date.today()

            card = self.card_repo.get_by_id(card_id)
            if not card:
                raise ValueError(f"Карта ID {card_id} не найдена")

            tranches = self.tranche_repo.get_active_by_card(card_id)
            
            daily_rate = (card.annual_rate / Decimal("100") / Decimal("365")).quantize(
                Decimal("0.00000001"), rounding=ROUND_HALF_UP
            )

            total_burn_rate = Decimal("0.00")
            for tranche in tranches:
                # Проценты каплют, если это перевод или если грейс уже закончился
                is_accruing = (
                    tranche.tranche_type == "transfer" or 
                    (tranche.grace_end_date and tranche.grace_end_date < as_of_date)
                )
                
                if is_accruing and tranche.remaining_amount > 0:
                    total_burn_rate += tranche.remaining_amount * daily_rate

            result = total_burn_rate.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            logger.debug(
                f"[{self.__class__.__name__}] Burn Rate для карты {card_id} на {as_of_date}: {result} ₽"
            )
            return result

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация расчёта Burn Rate: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка расчёта Burn Rate: {e}", exc_info=True)
            raise

    def get_grace_saver_alerts(
        self, 
        card_id: int, 
        days_ahead: int = 10, 
        as_of_date: Optional[date] = None
    ) -> List[GraceSaverAlert]:
        """
        Сканирует транши и находит те, у которых льготный период 
        заканчивается в ближайшие N дней.
        
        Args:
            card_id: ID кредитной карты
            days_ahead: горизонт предупреждения (по умолчанию 10 дней)
            as_of_date: дата отсчёта (по умолчанию сегодня)
            
        Returns:
            Список объектов GraceSaverAlert
        """
        try:
            if as_of_date is None:
                as_of_date = date.today()

            card = self.card_repo.get_by_id(card_id)
            if not card:
                raise ValueError(f"Карта ID {card_id} не найдена")

            tranches = self.tranche_repo.get_active_by_card(card_id)
            alerts = []

            daily_rate = card.annual_rate / Decimal("100") / Decimal("365")

            for tranche in tranches:
                if tranche.tranche_type != "purchase" or not tranche.grace_end_date:
                    continue

                days_left = (tranche.grace_end_date - as_of_date).days

                # Если грейс заканчивается в заданный горизонт и ещё не закончился
                if 0 <= days_left <= days_ahead:
                    # Оцениваем стоимость ретроактивных процентов
                    grace_days = (tranche.grace_end_date - tranche.transaction_date).days
                    if grace_days > 0:
                        retro_cost = (tranche.remaining_amount * daily_rate * grace_days).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                    else:
                        retro_cost = Decimal("0.00")

                    alerts.append(GraceSaverAlert(
                        tranche_id=tranche.id,
                        tranche_type=tranche.tranche_type,
                        amount=tranche.remaining_amount,
                        days_left=days_left,
                        grace_end_date=tranche.grace_end_date,
                        estimated_retroactive_cost=retro_cost
                    ))

            # Сортируем от самых срочных к менее срочным
            alerts.sort(key=lambda a: a.days_left)

            logger.info(
                f"[{self.__class__.__name__}] Найдено {len(alerts)} алертов Grace Saver для карты {card_id}"
            )
            return alerts

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация Grace Saver: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка расчёта Grace Saver: {e}", exc_info=True)
            raise

    def forecast_min_payment(self, card_id: int, as_of_date: Optional[date] = None) -> Decimal:
        """
        Прогнозирует текущий минимальный обязательный платёж.
        
        Формула: (Общий остаток тела долга × min_payment_percent) + Все неоплаченные проценты.
        
        Args:
            card_id: ID кредитной карты
            as_of_date: дата прогноза (по умолчанию сегодня)
            
        Returns:
            Сумма прогнозируемого минимального платежа
        """
        try:
            if as_of_date is None:
                as_of_date = date.today()

            card = self.card_repo.get_by_id(card_id)
            if not card:
                raise ValueError(f"Карта ID {card_id} не найдена")

            # 1. Считаем общий остаток тела долга по всем активным траншам
            tranches = self.tranche_repo.get_active_by_card(card_id)
            total_principal_debt = sum(t.remaining_amount for t in tranches)

            # 2. Считаем все неоплаченные проценты
            unpaid_accruals = self.accrual_repo.get_unpaid_by_card(card_id)
            total_unpaid_interest = sum(
                (a.amount - a.paid_amount) for a in unpaid_accruals
            )

            # 3. Применяем формулу
            principal_part = (total_principal_debt * card.min_payment_percent).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            min_payment = (principal_part + total_unpaid_interest).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            logger.debug(
                f"[{self.__class__.__name__}] Прогноз мин. платежа для карты {card_id}: {min_payment} ₽"
            )
            return min_payment

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация прогноза мин. платежа: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка прогноза мин. платежа: {e}", exc_info=True)
            raise