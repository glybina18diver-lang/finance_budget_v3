"""
Сервис управления траншами кредитных карт (TrancheService).

Отвечает за создание траншей (покупки, переводы, возвраты)
и расчёт дат окончания льготного периода.
"""

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from core.models import Tranche, CreditCard
from core.repositories.tranche_repository import TrancheRepository
from core.repositories.credit_card_repository import CreditCardRepository

logger = logging.getLogger(__name__)


class TrancheService:
    """
    Бизнес-логика управления траншами кредитной карты.
    """

    def __init__(
        self, 
        tranche_repo: TrancheRepository, 
        card_repo: CreditCardRepository
    ):
        self.tranche_repo = tranche_repo
        self.card_repo = card_repo

    def calculate_grace_end_date(self, transaction_date: date, grace_months: int) -> date:
        """
        Рассчитывает дату окончания льготного периода.
        
        Логика: Покупки в месяце M имеют грейс до конца месяца M + grace_months.
        Пример: Покупка 15 марта, grace_months=3 -> Грейс до 30 июня.
        
        Args:
            transaction_date: дата операции
            grace_months: количество месяцев льготного периода
            
        Returns:
            Последний день месяца окончания льготного периода
            
        Raises:
            ValueError: если grace_months < 0
        """
        try:
            if grace_months < 0:
                raise ValueError("grace_months не может быть отрицательным")

            # Вычисляем месяц и год окончания грейса
            month = transaction_date.month + grace_months
            year = transaction_date.year + (month - 1) // 12
            month = (month - 1) % 12 + 1

            # Находим первый день следующего месяца
            if month == 12:
                next_month_first_day = date(year + 1, 1, 1)
            else:
                next_month_first_day = date(year, month + 1, 1)

            # Вычитаем один день, чтобы получить последний день текущего месяца
            last_day_of_grace_month = next_month_first_day - timedelta(days=1)
            
            return last_day_of_grace_month

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация расчёта грейса: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка расчёта даты конца грейса: {e}", exc_info=True)
            raise

    def add_purchase(
        self, 
        card_id: int, 
        amount: Decimal, 
        transaction_date: date, 
        linked_transaction_id: int = None
    ) -> Tranche:
        """
        Создаёт транш для обычной покупки.
        
        Args:
            card_id: ID кредитной карты
            amount: сумма покупки (положительное число)
            transaction_date: дата покупки
            linked_transaction_id: ID связанной транзакции в таблице transactions
            
        Returns:
            Созданный объект Tranche
            
        Raises:
            ValueError: если сумма <= 0 или карта не найдена
        """
        try:
            if amount <= 0:
                raise ValueError("Сумма покупки должна быть положительной")

            card = self.card_repo.get_by_id(card_id)
            if not card:
                raise ValueError(f"Кредитная карта с ID {card_id} не найдена")

            grace_end_date = self.calculate_grace_end_date(transaction_date, card.grace_months)

            tranche = Tranche(
                card_id=card_id,
                tranche_type="purchase",
                original_amount=amount,
                remaining_amount=amount,
                commission=Decimal("0.00"),
                transaction_date=transaction_date,
                grace_end_date=grace_end_date,
                status="in_grace",
                is_retroactive_triggered=False,
                linked_transaction_id=linked_transaction_id
            )

            tranche_id = self.tranche_repo.create(tranche)
            tranche.id = tranche_id

            logger.info(
                f"[{self.__class__.__name__}] Создан транш покупки ID={tranche_id} "
                f"на сумму {amount} ₽, грейс до {grace_end_date}"
            )
            return tranche

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при добавлении покупки: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка добавления транша покупки: {e}", exc_info=True)
            raise

    def add_transfer(
        self, 
        card_id: int, 
        amount: Decimal, 
        commission: Decimal, 
        transaction_date: date
    ) -> Tranche:
        """
        Создаёт транш для перевода (сразу вне льготного периода).
        
        Args:
            card_id: ID кредитной карты
            amount: сумма перевода
            commission: сумма комиссии
            transaction_date: дата перевода
            
        Returns:
            Созданный объект Tranche
        """
        try:
            if amount <= 0:
                raise ValueError("Сумма перевода должна быть положительной")
            if commission < 0:
                raise ValueError("Комиссия не может быть отрицательной")

            card = self.card_repo.get_by_id(card_id)
            if not card:
                raise ValueError(f"Кредитная карта с ID {card_id} не найдена")

            # Для переводов грейс не действует, но для консистентности ставим дату
            grace_end_date = self.calculate_grace_end_date(transaction_date, card.grace_months)

            total_debt = amount + commission

            tranche = Tranche(
                card_id=card_id,
                tranche_type="transfer",
                original_amount=total_debt,
                remaining_amount=total_debt,
                commission=commission,
                transaction_date=transaction_date,
                grace_end_date=grace_end_date, # Формально есть, но статус сразу grace_expired
                status="grace_expired", 
                is_retroactive_triggered=False, # Проценты капнут сразу, триггер не нужен
                linked_transaction_id=None
            )

            tranche_id = self.tranche_repo.create(tranche)
            tranche.id = tranche_id

            logger.info(
                f"[{self.__class__.__name__}] Создан транш перевода ID={tranche_id} "
                f"на сумму {total_debt} ₽ (вкл. комиссию {commission} ₽)"
            )
            return tranche

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при добавлении перевода: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка добавления транша перевода: {e}", exc_info=True)
            raise

    def add_refund(
        self, 
        card_id: int, 
        amount: Decimal, 
        transaction_date: date,
        linked_transaction_id: Optional[int] = None
    ) -> Tranche:
        """
        Создаёт транш для возврата средств от магазина.
        
        Args:
            card_id: ID кредитной карты
            amount: сумма возврата (положительное число)
            transaction_date: дата возврата
            linked_transaction_id: ID связанной транзакции
            
        Returns:
            Созданный объект Tranche
        """
        try:
            if amount <= 0:
                raise ValueError("Сумма возврата должна быть положительной")

            tranche = Tranche(
                card_id=card_id,
                tranche_type="refund",
                original_amount=amount,
                remaining_amount=amount,
                commission=Decimal("0.00"),
                transaction_date=transaction_date,
                grace_end_date=None, # У возвратов нет грейса, они сразу идут в каскад
                status="in_grace", # Условно, чтобы не гасился процентами
                is_retroactive_triggered=False,
                linked_transaction_id=linked_transaction_id
            )

            tranche_id = self.tranche_repo.create(tranche)
            tranche.id = tranche_id

            logger.info(
                f"[{self.__class__.__name__}] Создан транш возврата ID={tranche_id} "
                f"на сумму {amount} ₽"
            )
            return tranche

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при добавлении возврата: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка добавления транша возврата: {e}", exc_info=True)
            raise

    def get_active_tranches(self, card_id: int) -> List[Tranche]:
        """
        Получает все активные (непогашенные) транши карты.
        
        Args:
            card_id: ID кредитной карты
            
        Returns:
            Список объектов Tranche
        """
        try:
            tranches = self.tranche_repo.get_active_by_card(card_id)
            logger.debug(
                f"[{self.__class__.__name__}] Получено {len(tranches)} активных траншей для карты {card_id}"
            )
            return tranches
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения активных траншей: {e}", exc_info=True)
            raise