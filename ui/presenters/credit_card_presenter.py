"""
Презентер для модуля кредитных карт (CreditCardPresenter).

Связующее звено между UI (CreditCardDialog) и бизнес-логикой (CreditCardService).
Отвечает за валидацию ввода, конвертацию типов и подготовку данных для отображения.
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
            credit_card_service: экземпляр CreditCardService (Фасад)
            account_service: экземпляр AccountService (для получения списка счетов)
        """
        self.service = credit_card_service
        self.account_service = account_service

    # --- Загрузка данных для UI ---

    def get_cards_list(self) -> List[Dict[str, Any]]:
        """
        Получает список всех активных кредитных карт для ComboBox.
        
        Returns:
            Список словарей с базовой информацией о картах
        """
        try:
            cards = self.service.get_all_active_cards()
            return [
                {
                    "id": card.id,
                    "name": card.name,
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

    def get_dashboard_data(self, card_id: int) -> Dict[str, Any]:
        """
        Собирает все метрики для главного экрана (Дашборда).
        
        Args:
            card_id: ID выбранной кредитной карты
            
        Returns:
            Словарь с метриками, алертами и общей информацией
        """
        try:
            if not card_id:
                raise ValueError("Не выбрана кредитная карта")
                
            return self.service.get_dashboard_data(card_id)
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация дашборда: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка сбора данных дашборда: {e}", exc_info=True)
            raise

    def get_tranches(self, card_id: int) -> List[Dict[str, Any]]:
        """
        Получает список активных траншей для таблицы.
        
        Args:
            card_id: ID кредитной карты
            
        Returns:
            Список словарей с данными траншей
        """
        try:
            if not card_id:
                raise ValueError("Не выбрана кредитная карта")

            tranches = self.service.tranche_service.get_active_tranches(card_id)
            return [
                {
                    "id": t.id,
                    "type": t.tranche_type,
                    "original_amount": float(t.original_amount),
                    "remaining_amount": float(t.remaining_amount),
                    "commission": float(t.commission),
                    "transaction_date": t.transaction_date.isoformat(),
                    "grace_end_date": t.grace_end_date.isoformat() if t.grace_end_date else None,
                    "status": t.status,
                    "is_retroactive_triggered": t.is_retroactive_triggered
                }
                for t in tranches
            ]
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация траншей: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения траншей: {e}", exc_info=True)
            raise

    def get_statements(self, card_id: int) -> List[Dict[str, Any]]:
        """
        Получает историю выписок (биллинговых циклов).
        
        Args:
            card_id: ID кредитной карты
            
        Returns:
            Список словарей с данными выписок
        """
        try:
            if not card_id:
                raise ValueError("Не выбрана кредитная карта")

            statements = self.service.statement_service.statement_repo.get_by_card(card_id)
            return [
                {
                    "id": s.id,
                    "statement_date": s.statement_date.isoformat(),
                    "due_date": s.due_date.isoformat() if s.due_date else None,
                    "closing_balance": float(s.closing_balance),
                    "min_payment_required": float(s.min_payment_required),
                    "status": s.status
                }
                for s in statements
            ]
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация выписок: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения выписок: {e}", exc_info=True)
            raise

    def get_available_accounts(self) -> List[Dict[str, Any]]:
        """
        Получает список доступных счетов для внесения платежа (исключая саму кредитку).
        
        Returns:
            Список словарей со счетами
        """
        try:
            accounts = self.account_service.get_all_active_accounts()
            return [
                {
                    "id": acc.id,
                    "name": acc.name,
                    "balance": float(acc.current_balance),
                    "type": acc.account_type
                }
                for acc in accounts
                if acc.account_type != "CreditCard" # Нельзя платить с кредитки на кредитку в этом диалоге
            ]
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация счетов: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения счетов: {e}", exc_info=True)
            raise

    def get_available_accounts_for_card_creation(self) -> List[Dict[str, Any]]:
        """
        Получает список счетов типа CreditCard, к которым ещё не привязана карта.
        
        Returns:
            Список словарей со счетами
        """
        try:
            # Получаем все счета типа CreditCard
            all_credit_accounts = self.account_service.get_accounts_by_type("CreditCard")
            # Получаем ID счетов, которые уже имеют карту
            used_account_ids = self.service.card_repo.get_all_card_account_ids()
            
            # Фильтруем
            available_accounts = [
                acc for acc in all_credit_accounts if acc.id not in used_account_ids
            ]
            
            return [
                {
                    "id": acc.id,
                    "name": acc.name,
                    "balance": float(acc.current_balance)
                }
                for acc in available_accounts
            ]
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация счетов для карты: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения счетов для карты: {e}", exc_info=True)
            raise

    def create_card(self, card_data: Dict[str, Any]) -> int:
        """
        Создаёт новую кредитную карту.
        
        Args:
            card_data: словарь с полями карты из UI
            
        Returns:
            ID созданной карты
            
        Raises:
            ValueError: при невалидном вводе
        """
        try:
            if not card_data.get("account_id"):
                raise ValueError("Не выбран счёт")
            if not card_data.get("name", "").strip():
                raise ValueError("Название карты не может быть пустым")

            card = CreditCard(
                account_id=card_data["account_id"],
                name=card_data["name"].strip(),
                annual_rate=self._parse_decimal(card_data["annual_rate"], "Годовая ставка"),
                grace_months=int(card_data["grace_months"]),
                min_payment_percent=self._parse_decimal(card_data["min_payment_percent"], "Мин. платёж %") / Decimal("100"),
                payment_day=int(card_data["payment_day"]),
                statement_day=int(card_data["statement_day"]),
                credit_limit=self._parse_decimal(card_data["credit_limit"], "Кредитный лимит")
            )
            
            card_id = self.service.create_card(card)
            logger.info(f"[{self.__class__.__name__}] Создана карта ID={card_id}")
            return card_id
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация создания карты: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания карты: {e}", exc_info=True)
            raise

    # --- Обработка действий пользователя ---

    def make_payment(
        self, 
        card_id: int, 
        amount_str: str, 
        payment_date_str: str, 
        from_account_id: int
    ) -> Dict[str, Any]:
        """
        Вносит платёж по кредитной карте.
        
        Args:
            card_id: ID кредитной карты
            amount_str: сумма платежа (строка из UI)
            payment_date_str: дата платежа в формате YYYY-MM-DD
            from_account_id: ID счёта-источника
            
        Returns:
            Словарь с детализацией распределения платежа (allocation)
            
        Raises:
            ValueError: при невалидном вводе (сумма, дата)
        """
        try:
            if not card_id:
                raise ValueError("Не выбрана кредитная карта")
            if not from_account_id:
                raise ValueError("Не выбран счёт для списания")

            # Конвертация и валидация ввода
            amount = self._parse_decimal(amount_str, "Сумма платежа")
            payment_date = self._parse_date(payment_date_str, "Дата платежа")

            # Вызов сервиса
            return self.service.make_payment(
                card_id=card_id,
                amount=amount,
                payment_date=payment_date,
                from_account_id=from_account_id
            )
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация платежа: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка внесения платежа: {e}", exc_info=True)
            raise

    def recalculate_interest(self, card_id: int, as_of_date_str: str) -> Dict[int, float]:
        """
        Вручную пересчитывает проценты по кнопке в UI.
        
        Args:
            card_id: ID кредитной карты
            as_of_date_str: дата среза в формате YYYY-MM-DD
            
        Returns:
            Словарь {tranche_id: сумма неоплаченных процентов}
        """
        try:
            if not card_id:
                raise ValueError("Не выбрана кредитная карта")

            as_of_date = self._parse_date(as_of_date_str, "Дата пересчёта")
            card = self.service.card_repo.get_by_id(card_id)
            
            if not card:
                raise ValueError(f"Карта ID {card_id} не найдена")

            result = self.service.interest_engine.recalculate_all_interests(
                card_id=card_id,
                annual_rate=card.annual_rate,
                as_of_date=as_of_date
            )
            # Конвертируем Decimal в float для UI
            return {k: float(v) for k, v in result.items()}
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация пересчёта: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка пересчёта процентов: {e}", exc_info=True)
            raise

    def generate_statement(self, card_id: int, year: int, month: int) -> Dict[str, Any]:
        """
        Формирует выписку за указанный месяц.
        
        Args:
            card_id: ID кредитной карты
            year: год выписки
            month: месяц выписки (1-12)
            
        Returns:
            Словарь с данными созданной выписки
        """
        try:
            if not card_id:
                raise ValueError("Не выбрана кредитная карта")
            if not (1 <= month <= 12):
                raise ValueError("Месяц должен быть от 1 до 12")

            statement = self.service.statement_service.generate_statement(card_id, year, month)
            return {
                "id": statement.id,
                "statement_date": statement.statement_date.isoformat(),
                "due_date": statement.due_date.isoformat(),
                "closing_balance": float(statement.closing_balance),
                "min_payment_required": float(statement.min_payment_required),
                "status": statement.status
            }
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация выписки: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка генерации выписки: {e}", exc_info=True)
            raise

    def update_card_settings(self, card_data: Dict[str, Any]):
        """
        Обновляет настройки кредитной карты.
        
        Args:
            card_data: словарь с полями карты из UI
        """
        try:
            if "id" not in card_data or not card_data["id"]:
                raise ValueError("ID карты отсутствует")

            card = CreditCard(
                id=card_data["id"],
                account_id=card_data["account_id"],
                name=card_data["name"],
                annual_rate=self._parse_decimal(card_data["annual_rate"], "Годовая ставка"),
                grace_months=int(card_data["grace_months"]),
                min_payment_percent=self._parse_decimal(card_data["min_payment_percent"], "Мин. платёж %") / Decimal("100"),
                payment_day=int(card_data["payment_day"]),
                statement_day=int(card_data["statement_day"]),
                credit_limit=self._parse_decimal(card_data["credit_limit"], "Кредитный лимит")
            )
            self.service.update_card_settings(card)
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация настроек: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обновления настроек: {e}", exc_info=True)
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