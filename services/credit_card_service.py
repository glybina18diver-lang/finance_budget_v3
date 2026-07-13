"""
Главный сервис-фасад для модуля кредитных карт (CreditCardService).

Оркестрирует работу специализированных сервисов (Tranche, Interest, Waterfall, Forecast)
и предоставляет единый API для Презентера.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import List, Optional, Dict, Any

from core.models import CreditCard, Tranche
from core.repositories.credit_card_repository import CreditCardRepository
from core.repositories.tranche_repository import TrancheRepository
from services.tranche_service import TrancheService
from services.interest_engine import InterestEngine
from services.payment_waterfall import PaymentWaterfall, PaymentAllocation
from services.statement_service import StatementService
from services.forecast_service import ForecastService

logger = logging.getLogger(__name__)


class CreditCardService:
    """
    Фасад модуля кредитных карт.
    Координирует CRUD операции карты и сложные бизнес-процессы (платежи, прогнозы).
    """

    def __init__(
        self,
        card_repo: CreditCardRepository,
        tranche_repo: TrancheRepository,
        tranche_service: TrancheService,
        interest_engine: InterestEngine,
        payment_waterfall: PaymentWaterfall,
        statement_service: StatementService,
        forecast_service: ForecastService
    ):
        self.card_repo = card_repo
        self.tranche_repo = tranche_repo
        self.tranche_service = tranche_service
        self.interest_engine = interest_engine
        self.payment_waterfall = payment_waterfall
        self.statement_service = statement_service
        self.forecast_service = forecast_service

    # --- CRUD Карты ---

    def create_card(self, card: CreditCard) -> int:
        """
        Создаёт новую кредитную карту.
        
        Args:
            card: объект CreditCard с заполненными пользовательскими полями
            
        Returns:
            ID созданной карты
        """
        try:
            card_id = self.card_repo.create(card)
            logger.info(f"[{self.__class__.__name__}] Создана карта ID={card_id}")
            return card_id
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при создании карты: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания карты: {e}", exc_info=True)
            raise

    def update_card_settings(self, card: CreditCard):
        """
        Обновляет настройки кредитной карты.
        
        Args:
            card: объект CreditCard с обновлёнными полями (id обязателен)
        """
        try:
            if not card.id:
                raise ValueError("id карты обязателен для обновления")
            
            self.card_repo.update(card)
            logger.info(f"[{self.__class__.__name__}] Обновлены настройки карты ID={card.id}")
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при обновлении карты: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обновления карты: {e}", exc_info=True)
            raise

    def delete_card(self, card_id: int):
        """
        Мягко удаляет кредитную карту (is_active = 0).
        
        Args:
            card_id: ID кредитной карты
        """
        try:
            self.card_repo.delete(card_id)
            logger.info(f"[{self.__class__.__name__}] Мягко удалена карта ID={card_id}")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка удаления карты: {e}", exc_info=True)
            raise

    def get_card_by_account(self, account_id: int) -> Optional[CreditCard]:
        """
        Получает активную карту, привязанную к счёту.
        
        Args:
            account_id: ID счёта
            
        Returns:
            Объект CreditCard или None
        """
        try:
            return self.card_repo.get_by_account_id(account_id)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения карты по счёту: {e}", exc_info=True)
            raise

    def get_all_active_cards(self) -> List[CreditCard]:
        """
        Получает список всех активных кредитных карт.
        
        Returns:
            Список объектов CreditCard
        """
        try:
            return self.card_repo.get_all_active()
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения списка карт: {e}", exc_info=True)
            raise

    # --- Интеграция с обычными транзакциями ---

    def add_purchase_by_account(
        self, 
        account_id: int, 
        amount: Decimal, 
        transaction_date: date, 
        transaction_id: int
    ) -> Optional[Tranche]:
        """
        Точка интеграции: создаёт транш покупки для счёта кредитной карты.
        Вызывается из TransactionService.
        
        Args:
            account_id: ID счёта
            amount: сумма покупки (положительное число)
            transaction_date: дата покупки
            transaction_id: ID связанной транзакции
            
        Returns:
            Созданный транш или None, если карта не найдена
        """
        try:
            card = self.card_repo.get_by_account_id(account_id)
            if not card:
                logger.warning(
                    f"[{self.__class__.__name__}] Карта для счёта {account_id} не найдена. Транш не создан."
                )
                return None

            tranche = self.tranche_service.add_purchase(
                card_id=card.id,
                amount=amount,
                transaction_date=transaction_date,
                linked_transaction_id=transaction_id
            )
            return tranche
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при добавлении покупки: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка добавления покупки: {e}", exc_info=True)
            raise

    # --- Оркестрация Платежа ---

    def make_payment(
        self, 
        card_id: int, 
        amount: Decimal, 
        payment_date: date, 
        from_account_id: int
    ) -> Dict[str, Any]:
        """
        Полный цикл внесения платежа по кредитной карте.
        
        1. Пересчитывает проценты на дату платежа.
        2. Распределяет платёж по каскаду (Waterfall).
        3. Сохраняет результат.
        
        Args:
            card_id: ID кредитной карты
            amount: сумма платежа
            payment_date: дата платежа
            from_account_id: ID счёта, с которого списываются средства
            
        Returns:
            Словарь с детализацией распределения (allocation) для UI
        """
        try:
            if amount <= 0:
                raise ValueError("Сумма платежа должна быть положительной")

            card = self.card_repo.get_by_id(card_id)
            if not card:
                raise ValueError(f"Карта ID {card_id} не найдена")

            # Шаг 1: Пересчёт процентов на дату платежа
            self.interest_engine.recalculate_all_interests(
                card_id=card_id,
                annual_rate=card.annual_rate,
                as_of_date=payment_date
            )

            # Шаг 2: Каскадное распределение
            allocation: PaymentAllocation = self.payment_waterfall.distribute_payment(
                card_id=card_id,
                amount=amount,
                payment_date=payment_date
            )

            # Шаг 3: Формирование ответа для UI
            # (В будущем здесь будет вызов CreditCardPaymentRepository.create())
            result = {
                "payment_date": payment_date.isoformat(),
                "amount": float(amount),
                "from_account_id": from_account_id,
                "allocation": {
                    "commissions_paid": float(allocation.commissions_paid),
                    "interest_paid": float(allocation.interest_paid),
                    "principal_paid": float(allocation.principal_paid),
                    "remaining_amount": float(allocation.remaining_amount),
                    "tranches_affected": allocation.tranches_affected
                }
            }

            logger.info(
                f"[{self.__class__.__name__}] Платёж {amount} ₽ по карте {card_id} успешно обработан"
            )
            return result

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация платежа: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обработки платежа: {e}", exc_info=True)
            raise

    # --- Дашборд и Прогнозы ---

    def get_dashboard_data(self, card_id: int, as_of_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Собирает все данные для главного экрана диалога кредитной карты.
        
        Args:
            card_id: ID кредитной карты
            as_of_date: дата среза (по умолчанию сегодня)
            
        Returns:
            Словарь с данными для UI (карта, долги, алерты, прогнозы)
        """
        try:
            if as_of_date is None:
                as_of_date = date.today()

            card = self.card_repo.get_by_id(card_id)
            if not card:
                raise ValueError(f"Карта ID {card_id} не найдена")

            # 1. Базовые метрики
            active_tranches = self.tranche_repo.get_active_by_card(card_id)
            total_debt = sum(t.remaining_amount for t in active_tranches)
            available_limit = card.credit_limit - total_debt

            # 2. Прогнозы и инсайты
            burn_rate = self.forecast_service.calculate_burn_rate(card_id, as_of_date)
            grace_alerts = self.forecast_service.get_grace_saver_alerts(card_id, days_ahead=10, as_of_date=as_of_date)
            min_payment = self.forecast_service.forecast_min_payment(card_id, as_of_date)

            # 3. Формирование словаря для UI
            return {
                "card": {
                    "id": card.id,
                    "name": card.name,
                    "credit_limit": float(card.credit_limit),
                    "annual_rate": float(card.annual_rate),
                    "min_payment_percent": float(card.min_payment_percent)
                },
                "metrics": {
                    "total_debt": float(total_debt),
                    "available_limit": float(available_limit),
                    "burn_rate": float(burn_rate),
                    "min_payment": float(min_payment)
                },
                "grace_alerts": [
                    {
                        "tranche_id": alert.tranche_id,
                        "amount": float(alert.amount),
                        "days_left": alert.days_left,
                        "grace_end_date": alert.grace_end_date.isoformat(),
                        "retroactive_cost": float(alert.estimated_retroactive_cost)
                    }
                    for alert in grace_alerts
                ],
                "tranches_count": len(active_tranches)
            }

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация дашборда: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка сбора данных дашборда: {e}", exc_info=True)
            raise