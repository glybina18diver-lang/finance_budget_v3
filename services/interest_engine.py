"""Движок начисления процентов по кредитным картам (Interest Engine)."""

import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional

from core.models import Tranche, InterestAccrual, CreditCard
from core.repositories.tranche_repository import TrancheRepository
from core.repositories.interest_accrual_repository import InterestAccrualRepository

logger = logging.getLogger(__name__)


class InterestEngine:
    """
    Рассчитывает проценты по траншам кредитной карты.
    
    Реализует бизнес-правила:
    1. Ежедневное начисление (Daily Burn Rate).
    2. Триггер ретроактивности при выходе из льготного периода.
    3. Пересчёт всех начислений на заданную дату.
    """

    def __init__(self, tranche_repo: TrancheRepository, accrual_repo: InterestAccrualRepository):
        self.tranche_repo = tranche_repo
        self.accrual_repo = accrual_repo

    def calculate_daily_interest(self, amount: Decimal, annual_rate: Decimal, days: int) -> Decimal:
        """
        Рассчитывает ежедневные проценты за указанный период.
        
        Args:
            amount: сумма долга
            annual_rate: годовая ставка в процентах (например, 49.8)
            days: количество дней
            
        Returns:
            Сумма процентов, округлённая до копеек
        """
        try:
            if days <= 0 or amount <= 0:
                return Decimal("0.00")
            
            daily_rate = annual_rate / Decimal("100") / Decimal("365")
            interest = amount * daily_rate * days
            
            return interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка расчёта ежедневных процентов: {e}", exc_info=True)
            raise

    def trigger_retroactive(self, tranche: Tranche, annual_rate: Decimal) -> InterestAccrual:
        """
        Активирует триггер ретроактивности для транша покупок.
        
        Начисляет проценты задним числом за весь льготный период 
        (от даты покупки до конца льготного периода).
        
        Args:
            tranche: транш, у которого закончился грейс
            annual_rate: годовая ставка карты
            
        Returns:
            Объект InterestAccrual с ретроактивными процентами
            
        Raises:
            ValueError: если транш уже был триггернут или это не покупка
        """
        try:
            if tranche.tranche_type != "purchase":
                raise ValueError(f"Ретроактивность применяется только к покупкам, тип: {tranche.tranche_type}")
            
            if tranche.is_retroactive_triggered:
                raise ValueError(f"Транш {tranche.id} уже имеет сработавший ретроактивный триггер")
            
            if not tranche.grace_end_date or not tranche.transaction_date:
                raise ValueError("У транша не указаны даты для расчёта ретроактивности")

            # Считаем дни льготного периода
            grace_days = (tranche.grace_end_date - tranche.transaction_date).days
            if grace_days <= 0:
                grace_days = 1  # Защита от деления на 0 или отрицательных значений

            # Рассчитываем ретроактивные проценты
            retro_amount = self.calculate_daily_interest(tranche.original_amount, annual_rate, grace_days)

            # Создаём запись о начислении
            accrual = InterestAccrual(
                tranche_id=tranche.id,
                accrual_date=tranche.grace_end_date,
                interest_type="retroactive",
                amount=retro_amount,
                paid_amount=Decimal("0.00"),
                is_paid=False
            )
            accrual_id = self.accrual_repo.create(accrual)
            accrual.id = accrual_id

            # Обновляем статус транша
            tranche.is_retroactive_triggered = True
            tranche.status = "grace_expired"
            self.tranche_repo.update(tranche)

            logger.info(
                f"[{self.__class__.__name__}] Сработал ретроактивный триггер для транша {tranche.id}. "
                f"Начислено: {retro_amount} ₽ за {grace_days} дн."
            )
            return accrual

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация ретроактивности: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка триггера ретроактивности: {e}", exc_info=True)
            raise

    def recalculate_all_interests(self, card_id: int, annual_rate: Decimal, as_of_date: Optional[date] = None
    ) -> Dict[int, Decimal]:
        """
        Пересчитывает все проценты по карте на заданную дату.
        
        Вызывается вручную по кнопке "Пересчитать проценты" в UI.
        
        Алгоритм:
        1. Получает все активные транши карты.
        2. Для каждого транша проверяет статус грейса.
        3. Если грейс закончился и триггер не сработал — запускает trigger_retroactive.
        4. Рассчитывает ежедневные проценты за период после окончания грейса 
           (или с даты перевода) до as_of_date.
        5. Сохраняет новые записи InterestAccrual.
        
        Args:
            card_id: ID кредитной карты
            annual_rate: годовая ставка карты
            as_of_date: дата, на которую делается срез (по умолчанию — сегодня)
            
        Returns:
            Словарь {tranche_id: total_unpaid_interest}
        """
        try:
            if as_of_date is None:
                as_of_date = date.today()

            tranches = self.tranche_repo.get_active_by_card(card_id)
            result = {}

            for tranche in tranches:
                total_interest = Decimal("0.00")

                # 1. Обработка ретроактивности (только для покупок)
                if tranche.tranche_type == "purchase" and not tranche.is_retroactive_triggered:
                    if as_of_date > tranche.grace_end_date:
                        try:
                            self.trigger_retroactive(tranche, annual_rate)
                        except ValueError:
                            pass  # Уже триггернут или невалиден, игнорируем

                # 2. Расчёт ежедневных процентов
                # Определяем дату начала начисления ежедневных процентов
                if tranche.tranche_type == "transfer":
                    # Для переводов проценты капляют сразу с даты операции
                    start_date = tranche.transaction_date
                else:
                    # Для покупок — только после окончания льготного периода
                    start_date = tranche.grace_end_date if tranche.grace_end_date else tranche.transaction_date

                # Получаем уже существующие начисления, чтобы не дублировать
                existing_accruals = self.accrual_repo.get_by_tranche(tranche.id)
                last_accrual_date = max(
                    [a.accrual_date for a in existing_accruals], 
                    default=start_date
                )
                
                # Если последнее начисление уже позже as_of_date, пропускаем
                if last_accrual_date >= as_of_date:
                    result[tranche.id] = self._get_unpaid_interest(tranche.id)
                    continue

                days_to_charge = (as_of_date - last_accrual_date).days
                if days_to_charge > 0:
                    daily_interest = self.calculate_daily_interest(
                        tranche.remaining_amount, annual_rate, days_to_charge
                    )
                    
                    if daily_interest > 0:
                        accrual = InterestAccrual(
                            tranche_id=tranche.id,
                            accrual_date=as_of_date,
                            interest_type="daily",
                            amount=daily_interest,
                            paid_amount=Decimal("0.00"),
                            is_paid=False
                        )
                        self.accrual_repo.create(accrual)

                # Считаем общую неоплаченную задолженность по траншу
                result[tranche.id] = self._get_unpaid_interest(tranche.id)

            logger.info(
                f"[{self.__class__.__name__}] Пересчёт процентов для карты {card_id} "
                f"на {as_of_date} завершён. Обработано траншей: {len(tranches)}"
            )
            return result

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка массового пересчёта процентов: {e}", exc_info=True)
            raise

    def _get_unpaid_interest(self, tranche_id: int) -> Decimal:
        """Суммирует неоплаченные проценты по траншу."""
        try:
            accruals = self.accrual_repo.get_unpaid_by_tranche(tranche_id)
            total = sum((a.amount - a.paid_amount) for a in accruals)
            return total
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка подсчёта неоплаченных процентов: {e}", exc_info=True)
            raise