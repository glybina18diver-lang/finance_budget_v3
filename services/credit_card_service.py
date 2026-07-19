"""
Главный сервис для модуля кредитных карт (CreditCardService).

Отвечает за CRUD операций с настройками карт и внесение платежей.
Платеж разбивается на: перевод (тело долга)  + расход (проценты).
"""

import logging
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any

from core.models import CreditCard
from core.repositories.credit_card_repository import CreditCardRepository
from core.repositories.category_repository import CategoryRepository
from services.transfer_service import TransferService
from services.transaction_service import TransactionService
from core.repositories.account_repository import AccountRepository


logger = logging.getLogger(__name__)


class CreditCardService:
    """
    Сервис для управления кредитными картами.
    
    Координирует CRUD операций с настройками карт и внесение платежей.
    """

    def __init__(
        self,
        card_repo: CreditCardRepository,
        category_repo: CategoryRepository,
        transfer_service: TransferService,
        transaction_service: TransactionService,
        account_repo: AccountRepository
    ):
        """
        Инициализация сервиса.
        
        Args:
            card_repo: репозиторий кредитных карт
            category_repo: репозиторий категорий (для получения ID системных категорий)
            transfer_service: сервис переводов (для погашения тела долга)
            transaction_service: сервис транзакций (для записи процентов)
        """
        self.card_repo = card_repo
        self.category_repo = category_repo
        self.transfer_service = transfer_service
        self.transaction_service = transaction_service
        self.account_repo = account_repo

    # --- CRUD Карты ---

    def create_card(self, card: CreditCard) -> int:
        """
        Создаёт новую кредитную карту.
        
        Args:
            card: объект CreditCard (account_id обязателен, остальные поля опциональны)
            
        Returns:
            ID созданной карты
            
        Raises:
            ValueError: если не передан account_id
            Exception: при ошибке БД
        """
        try:
            if not card.account_id:
                raise ValueError("account_id обязателен для создания карты")
            
            card_id = self.card_repo.create(card)
            logger.info(f"[{self.__class__.__name__}] Создана карта ID={card_id}")
            return card_id
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при создании карты: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания карты: {e}", exc_info=True)
            raise

    def update_card(self, card: CreditCard):
        """
        Обновляет настройки кредитной карты.
        
        Args:
            card: объект CreditCard с обновлёнными полями (id обязателен)
            
        Raises:
            ValueError: если не передан id
            Exception: при ошибке БД
        """
        try:
            if not card.id:
                raise ValueError("id карты обязателен для обновления")
            
            self.card_repo.update(card)
            logger.info(f"[{self.__class__.__name__}] Обновлена карта ID={card.id}")
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при обновлении карты: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обновления карты: {e}", exc_info=True)
            raise

    def hide_card(self, card_id: int):
        """
        Скрывает кредитную карту (is_active = 0).
        
        Args:
            card_id: ID кредитной карты
        """
        try:
            self.card_repo.hide(card_id)
            logger.info(f"[{self.__class__.__name__}] Скрыта карта ID={card_id}")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка скрытия карты: {e}", exc_info=True)
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

    def get_all_cards(self) -> List[CreditCard]:
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

    def get_card_dashboard(self, card_id: int) -> Dict[str, Any]:
        """
        Получает сводку по кредитной карте для отображения в UI.
        
        Args:
            card_id: ID кредитной карты
            
        Returns:
            Словарь с данными: debt, limit, usage_percent, account_name
            
        Raises:
            ValueError: если карта не найдена
        """
        try:
            card = self.card_repo.get_by_id(card_id)
            if not card:
                raise ValueError(f"Карта ID {card_id} не найдена")
            
            # Получаем баланс счёта (долг)
            account = self._get_account_by_id(card.account_id)
            
            # Конвертируем float в Decimal для точных вычислений
            balance = Decimal(str(account.current_balance))
            debt = abs(balance) if balance < 0 else Decimal("0.00")
            
            # Вычисляем процент использования лимита
            usage_percent = Decimal("0.00")
            if card.credit_limit and card.credit_limit > 0:
                usage_percent = (debt / card.credit_limit * 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            
            return {
                "card_id": card.id,
                "account_name": card.account_name or "Неизвестно",
                "debt": float(debt),
                "credit_limit": float(card.credit_limit) if card.credit_limit else 0.0,
                "usage_percent": float(usage_percent),
                "annual_rate": float(card.annual_rate) if card.annual_rate else 0.0,
                "payment_day": card.payment_day,
                "statement_day": card.statement_day
            }
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация дашборда: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения дашборда: {e}", exc_info=True)
            raise

    # --- Внесение платежа ---

    def make_payment(
        self,
        card_id: int,
        amount: Decimal,
        interest_amount: Decimal,
        payment_date: date,
        from_account_id: int
    ) -> Dict[str, Any]:
        """
        Вносит платёж по кредитной карте.
        
        Разбивает платёж на три операции:
        1. Перевод (тело долга) - уменьшает долг по кредитке
        3. Расход (проценты) - записывается в категорию "Проценты по кредитным картам"
        
        Args:
            card_id: ID кредитной карты
            amount: общая сумма платежа
            interest_amount: сумма на погашение процентов (может быть 0)
            payment_date: дата платежа
            from_account_id: ID счёта-источника
            
        Returns:
            Словарь с детализацией: principal_amount, interest_amount
            
        Raises:
            ValueError: при невалидных данных (сумма <= 0, проценты > суммы и т.д.)
            Exception: при ошибке БД или сервиса
        """
        try:
            # Валидация
            if amount <= 0:
                raise ValueError("Сумма платежа должна быть положительной")
            if interest_amount < 0:
                raise ValueError("Сумма процентов не может быть отрицательной")
            if interest_amount > amount:
                raise ValueError("Сумма процентов не может превышать общую сумму платежа")
            
            # Получаем карту
            card = self.card_repo.get_by_id(card_id)
            if not card:
                raise ValueError(f"Карта ID {card_id} не найдена")
            
            # Вычисляем сумму на погашение тела долга
            principal_amount = (amount - interest_amount).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            
            # Получаем ID системных категорий
            interest_category_id = self._get_system_category_id("Проценты по кредитным картам")
            
            # 1. Перевод (тело долга)
            if principal_amount > 0:
                data = {
                    "from_account_id": from_account_id,
                    "to_account_id": card.account_id,
                    "type": "internal",
                    "date": payment_date.isoformat(),
                    "amount": float(principal_amount),
                    "description": (f"Погашение долга по {card.account_name}")
                }
                self.transfer_service.create_transfer(data)
                logger.info(
                    f"[{self.__class__.__name__}] Создан перевод на {principal_amount} ₽ "
                    f"для погашения тела долга"
                )

            # 2. Расход (проценты)
            if interest_amount > 0:
                if not interest_category_id:
                    raise ValueError("Системная категория 'Проценты по кредитным картам' не найдена")
                
                self.transaction_service.create_transaction(
                    account_id=from_account_id,
                    raw_amount=str(interest_amount),
                    trans_type="expense",
                    category_id=interest_category_id,
                    date_str=str(payment_date.isoformat()),
                    description=f"Проценты по {card.account_name}"
                )
                logger.info(
                    f"[{self.__class__.__name__}] Записан расход на проценты {interest_amount} ₽"
                )
            
            result = {
                "principal_amount": float(principal_amount),
                "interest_amount": float(interest_amount),
                "total_amount": float(amount)
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

    # --- Приватные методы ---

    def _get_system_category_id(self, category_name: str) -> Optional[int]:
        """
        Получает ID системной категории по названию.
        
        Args:
            category_name: название системной категории
            
        Returns:
            ID категории или None, если не найдена
        """
        try:
            category = self.category_repo.get_by_name(category_name)
            return category.id if category else None
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка получения категории '{category_name}': {e}",
                exc_info=True
            )
            return None

    def _get_account_by_id(self, account_id: int):
        """
        Получает счёт по ID (вспомогательный метод).
        
        Args:
            account_id: ID счёта
            
        Returns:
            Объект Account
        """
        return self.account_repo.get_by_id(account_id)