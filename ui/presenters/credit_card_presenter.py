"""
Презентер для модуля кредитных карт (CreditCardPresenter).

Связующее звено между UI и бизнес-логикой (CreditCardService).
Отвечает за валидацию ввода, конвертацию типов и подготовку данных для UI.
"""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Optional

from core.models import CreditCard
from services.credit_card_service import CreditCardService
from services.account_service import AccountService

logger = logging.getLogger(__name__)


class CreditCardPresenter:
    """
    Презентер главного диалога кредитных карт.
    
    Инкапсулирует логику подготовки данных для UI и обработки пользовательских действий.
    """

    def __init__(
        self, 
        credit_card_service: CreditCardService, 
        account_service: AccountService
    ):
        """
        Инициализация презентера.
        
        Args:
            credit_card_service: экземпляр CreditCardService
            account_service: экземпляр AccountService (для получения списка счетов)
        """
        self.service = credit_card_service
        self.account_service = account_service

    # --- Загрузка данных для UI ---

    def get_cards_list(self) -> List[Dict[str, Any]]:
        """
        Получает список всех активных кредитных карт для ComboBox.
        
        Returns:
            Список словарей с базовой информацией о картах (id, account_name)
        """
        try:
            cards = self.service.get_all_cards()
            return [
                {
                    "id": card.id,
                    "account_name": card.account_name or f"Карта ID {card.id}",
                    "account_id": card.account_id
                }
                for card in cards
            ]
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация списка карт: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения списка карт: {e}", exc_info=True)
            raise

    def get_card_dashboard(self, card_id: int) -> Dict[str, Any]:
        """
        Собирает метрики для главного экрана (долг, лимит, % использования).
        
        Args:
            card_id: ID выбранной кредитной карты
            
        Returns:
            Словарь с метриками для UI
        """
        try:
            if not card_id:
                raise ValueError("Не выбрана кредитная карта")
                
            return self.service.get_card_dashboard(card_id)
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация дашборда: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка сбора данных дашборда: {e}", exc_info=True)
            raise

    def get_accounts_for_payment(self, exclude_account_id: int) -> List[Dict[str, Any]]:
        """
        Получает список активных счетов для внесения платежа.
        Исключает счёт самой кредитной карты и счета типа CreditCard.
        
        Args:
            exclude_account_id: ID счёта текущей кредитной карты (для исключения)
            
        Returns:
            Список словарей со счетами
        """
        try:
            accounts = self.account_service.get_all_active_accounts()
            return [
                {
                    "id": acc.id,
                    "name": acc.name,
                    "balance": acc.current_balance,
                    "type": acc.account_type
                }
                for acc in accounts
                if acc.id != exclude_account_id and acc.account_type != "CreditCard"
            ]
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация счетов для платежа: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения счетов для платежа: {e}", exc_info=True)
            raise

    # --- Обработка действий пользователя ---

    def make_payment(
        self, 
        card_id: int, 
        amount_str: str, 
        interest_str: str, 
        payment_date_str: str, 
        from_account_id: int
    ) -> Dict[str, Any]:
        """
        Вносит платёж по кредитной карте (разбивка на тело, проценты и комиссии).
        
        Args:
            card_id: ID кредитной карты
            amount_str: общая сумма платежа (строка из UI)
            interest_str: сумма на погашение процентов (строка из UI)
            payment_date_str: дата платежа в формате YYYY-MM-DD
            from_account_id: ID счёта-источника
            
        Returns:
            Словарь с детализацией распределения платежа
            
        Raises:
            ValueError: при невалидном вводе (суммы, дата)
        """
        try:
            if not card_id:
                raise ValueError("Не выбрана кредитная карта")
            if not from_account_id:
                raise ValueError("Не выбран счёт для списания")

            # Конвертация и валидация ввода
            amount = self._parse_decimal(amount_str, "Общая сумма платежа")
            interest = self._parse_decimal(interest_str or "0", "Сумма процентов")
            payment_date = self._parse_date(payment_date_str, "Дата платежа")

            # Вызов сервиса
            return self.service.make_payment(
                card_id=card_id,
                amount=amount,
                interest_amount=interest,
                payment_date=payment_date,
                from_account_id=from_account_id
            )
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация платежа: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка внесения платежа: {e}", exc_info=True)
            raise

    def create_card(self, card_data: Dict[str, Any]) -> int:
        """
        Создаёт новую кредитную карту.
        
        Args:
            card_data: словарь с полями карты из UI
            
        Returns:
            ID созданной карты
        """
        try:
            if not card_data.get("account_id"):
                raise ValueError("Не выбран счёт")

            card = CreditCard(
                account_id=card_data["account_id"],
                credit_limit=self._parse_decimal(card_data.get("credit_limit"), "Кредитный лимит") if card_data.get("credit_limit") else None,
                annual_rate=self._parse_decimal(card_data.get("annual_rate"), "Годовая ставка") if card_data.get("annual_rate") else None,
                grace_months=int(card_data["grace_months"]) if card_data.get("grace_months") else None,
                min_payment_percent=self._parse_decimal(card_data.get("min_payment_percent"), "Мин. платёж %") / Decimal("100") if card_data.get("min_payment_percent") else None,
                payment_day=int(card_data["payment_day"]) if card_data.get("payment_day") else None,
                statement_day=int(card_data["statement_day"]) if card_data.get("statement_day") else None
            )
            
            return self.service.create_card(card)
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация создания карты: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания карты: {e}", exc_info=True)
            raise

    def update_card(self, card_data: Dict[str, Any]):
        """
        Обновляет настройки кредитной карты.
        
        Args:
            card_data: словарь с полями карты из UI (все поля опциональные)
        """
        try:
            if "id" not in card_data or not card_data["id"]:
                raise ValueError("ID карты отсутствует")

            # Получаем существующую карту для сохранения account_id
            existing_card = self.service.card_repo.get_by_id(card_data["id"])
            if not existing_card:
                raise ValueError(f"Карта ID {card_data['id']} не найдена")

            card = CreditCard(
                id=card_data["id"],
                account_id=existing_card.account_id,  # Не меняем привязку к счёту
                credit_limit=self._parse_decimal(card_data.get("credit_limit"), "Кредитный лимит") if card_data.get("credit_limit") is not None else None,
                annual_rate=self._parse_decimal(card_data.get("annual_rate"), "Годовая ставка") if card_data.get("annual_rate") is not None else None,
                grace_months=int(card_data["grace_months"]) if card_data.get("grace_months") is not None else None,
                min_payment_percent=self._parse_decimal(card_data.get("min_payment_percent"), "Мин. платёж %") / Decimal("100") if card_data.get("min_payment_percent") is not None else None,
                payment_day=int(card_data["payment_day"]) if card_data.get("payment_day") is not None else None,
                statement_day=int(card_data["statement_day"]) if card_data.get("statement_day") is not None else None
            )
            self.service.update_card(card)
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация настроек: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обновления настроек: {e}", exc_info=True)
            raise

    def get_card_settings(self, card_id: int) -> Dict[str, Any]:
        """
        Получает текущие настройки кредитной карты для формы редактирования.
        
        Args:
            card_id: ID кредитной карты
            
        Returns:
            Словарь с настройками карты (все поля опциональные, могут быть None)
            
        Raises:
            ValueError: если карта не найдена
        """
        try:
            if not card_id:
                raise ValueError("Не выбрана карта")
                
            card = self.service.card_repo.get_by_id(card_id)
            if not card:
                raise ValueError(f"Карта ID {card_id} не найдена")

            return {
                "id": card.id,
                "account_id": card.account_id,
                "account_name": card.account_name,
                "credit_limit": card.credit_limit,
                "annual_rate": card.annual_rate,
                "grace_months": card.grace_months,
                "min_payment_percent": card.min_payment_percent * 100 if card.min_payment_percent is not None else None,
                "payment_day": card.payment_day,
                "statement_day": card.statement_day
            }
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация настроек: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения настроек: {e}", exc_info=True)
            raise

    

    def hide_card(self, card_id: int):
        """
        Скрывает кредитную карту (устанавливает is_active = 0).
        
        Args:
            card_id: ID кредитной карты для удаления
        """
        try:
            if not card_id:
                raise ValueError("Не выбрана карта для удаления")
                
            self.service.hide_card(card_id)
            logger.info(f"[{self.__class__.__name__}] Карта ID={card_id} успешно скрыта")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка скрытия карты: {e}", exc_info=True)
            raise

    # --- Приватные методы-хелперы ---

    def _parse_decimal(self, value: Any, field_name: str) -> Decimal:
        """
        Безопасно парсит строку/число в Decimal.
        
        Args:
            value: исходное значение
            field_name: название поля для сообщения об ошибке
            
        Returns:
            Объект Decimal
            
        Raises:
            ValueError: если значение некорректно
        """
        try:
            if value is None or str(value).strip() == "":
                raise ValueError(f"{field_name} не может быть пустым")
            return Decimal(str(value).replace(",", "."))
        except InvalidOperation:
            raise ValueError(f"{field_name} должна быть корректным числом")

    def _parse_date(self, value: str, field_name: str) -> date:
        """
        Безопасно парсит строку в объект date.
        
        Args:
            value: строка в формате YYYY-MM-DD
            field_name: название поля для сообщения об ошибке
            
        Returns:
            Объект date
            
        Raises:
            ValueError: если формат даты неверный
        """
        try:
            if not value:
                raise ValueError(f"{field_name} не может быть пустой")
            return date.fromisoformat(value)
        except ValueError:
            raise ValueError(f"{field_name} должна быть в формате ГГГГ-ММ-ДД")