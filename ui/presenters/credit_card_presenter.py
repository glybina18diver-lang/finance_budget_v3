"""
Презентер для управления кредитной картой.
Координирует взаимодействие между UI и CreditCardService.
Архитектура MVP: вся бизнес-логика в сервисе, UI только отображает.
"""
from typing import List, Dict, Optional
from datetime import date

from services.credit_card_service import CreditCardService
from core.repositories.account_repository import AccountRepository


class CreditCardPresenter:
    """Презентер кредитной карты."""

    def __init__(self, service: CreditCardService, account_repo: AccountRepository):
        """
        Инициализация презентера.
        
        Args:
            service: экземпляр CreditCardService
            account_repo: репозиторий счетов (для выбора счёта при платеже)
        """
        self.service = service
        self.account_repo = account_repo
        self.view = None
        self.current_card_id: Optional[int] = None
        self.current_account_id: Optional[int] = None

    def set_view(self, view):
        """
        Устанавливает ссылку на UI и загружает начальные данные.
        
        Args:
            view: экземпляр CreditCardDialog
        """
        self.view = view
        self.load_initial_data()

    def set_current_card(self, card_id: int):
        """
        Устанавливает текущую карту для работы.
        
        Args:
            card_id: ID кредитной карты
        """
        self.current_card_id = card_id
        self.load_initial_data()

    # =================== Загрузка данных ===================

    def load_initial_data(self):
        """Загружает все данные для отображения в UI."""
        if not self.view or not self.current_card_id:
            return
        
        try:
            # 1. Загружаем информацию о карте
            card = self.service.repo.get_card_by_id(self.current_card_id)
            if not card:
                self.view.show_status("Карта не найдена", "error")
                return
            
            # 2. Загружаем периоды
            periods = self.service.get_periods(self.current_card_id)
            
            # 3. Рассчитываем задолженность на сегодня
            today = date.today().strftime("%Y-%m-%d")
            min_payment = self.service.calculate_minimum_payment(self.current_card_id, today)
            full_payoff = self.service.calculate_full_payoff(self.current_card_id, today)
            
            # 4. Загружаем список счетов для платежей
            accounts = self._get_active_accounts_as_dicts()
            
            # 5. Передаём всё в UI
            self.view.populate_card_info(self._card_to_dict(card))
            self.view.populate_periods(self._periods_to_dicts(periods))
            self.view.populate_debt_summary(min_payment, full_payoff)
            self.view.populate_accounts_for_payment(accounts)
            
        except Exception as e:
            self.view.show_status(f"Ошибка загрузки: {e}", "error")

    def load_data_for_payment_dialog(self, dialog):
        """
        Загружает данные для диалога внесения платежа.
        
        Args:
            dialog: экземпляр CreditCardPaymentDialog
        """
        try:
            # Рассчитываем минимальный платёж и полную задолженность
            today = date.today().strftime("%Y-%m-%d")
            min_payment = self.service.calculate_minimum_payment(self.current_card_id, today)
            full_payoff = self.service.calculate_full_payoff(self.current_card_id, today)
            
            # Загружаем счета
            accounts = self._get_active_accounts_as_dicts()
            
            # Передаём в диалог
            dialog.populate_payment_data(min_payment, full_payoff, accounts)
            
        except Exception as e:
            dialog.show_status(f"Ошибка загрузки: {e}", "error")

    def set_current_card(self, card_id: int, account_id: int):
        """
        Устанавливает текущую карту для работы.
        
        Args:
            card_id: ID из таблицы credit_cards
            account_id: ID счёта в таблице accounts
        """
        self.current_card_id = card_id
        self.current_account_id = account_id
        self.load_initial_data()

    def get_all_credit_cards(self) -> List[Dict]:
        """Возвращает список кредитных карт для UI выбора."""
        return self.service.get_all_credit_cards()

    # =================== Действия пользователя ===================

    def make_payment(self, payment_data: dict):
        """
        Обрабатывает внесение платежа.
        
        Args:
            payment_data: {date, amount, from_account_id}
        """
        try:
            # Валидация
            if not payment_data.get("amount") or payment_data["amount"] <= 0:
                self.view.show_status("Укажите сумму платежа", "error")
                return
            
            if not payment_data.get("from_account_id"):
                self.view.show_status("Выберите счёт для платежа", "error")
                return
            
            # Вносим платёж
            allocation = self.service.make_payment(self.current_card_id, payment_data)
            
            # Обновляем баланс счёта (с которого платим)
            from_account = self.account_repo.get_by_id(payment_data["from_account_id"])
            if from_account:
                from_account.current_balance -= payment_data["amount"]
                self.account_repo.update(from_account)
            
            self.view.show_status(
                f"Платёж {payment_data['amount']:,.2f} ₽ внесён успешно",
                "success"
            )
            
            # Перезагружаем данные
            self.load_initial_data()
            
            # Возвращаем распределение платежа для отображения
            return allocation
            
        except ValueError as e:
            self.view.show_status(str(e), "error")
        except Exception as e:
            self.view.show_status(f"Ошибка при внесении платежа: {e}", "error")

    def add_purchase(self, purchase_date: str, amount: float):
        """
        Добавляет покупку по кредитной карте.
        
        Args:
            purchase_date: дата покупки (YYYY-MM-DD)
            amount: сумма покупки
        """
        try:
            if amount <= 0:
                self.view.show_status("Сумма покупки должна быть положительной", "error")
                return
            
            period = self.service.add_purchase(self.current_card_id, purchase_date, amount)
            
            self.view.show_status(
                f"Покупка {amount:,.2f} ₽ добавлена в период {period.period_month}",
                "success"
            )
            
            self.load_initial_data()
            
        except Exception as e:
            self.view.show_status(f"Ошибка при добавлении покупки: {e}", "error")

    def add_transfer(self, transfer_date: str, amount: float) -> Optional[Dict]:
        """
        Добавляет перевод с кредитной карты.
        
        Args:
            transfer_date: дата перевода
            amount: сумма перевода
            
        Returns:
            Словарь {amount, commission, total} или None при ошибке
        """
        try:
            if amount <= 0:
                self.view.show_status("Сумма перевода должна быть положительной", "error")
                return None
            
            result = self.service.add_transfer(self.current_card_id, transfer_date, amount)
            
            self.view.show_status(
                f"Перевод {amount:,.2f} ₽ + комиссия {result['commission']:,.2f} ₽",
                "success"
            )
            
            self.load_initial_data()
            
            return result
            
        except Exception as e:
            self.view.show_status(f"Ошибка при добавлении перевода: {e}", "error")
            return None

    def refresh_calculations(self):
        """Пересчитывает проценты и обновляет UI."""
        try:
            today = date.today().strftime("%Y-%m-%d")
            min_payment = self.service.calculate_minimum_payment(self.current_card_id, today)
            full_payoff = self.service.calculate_full_payoff(self.current_card_id, today)
            
            self.view.populate_debt_summary(min_payment, full_payoff)
            
        except Exception as e:
            self.view.show_status(f"Ошибка пересчёта: {e}", "error")

    # =================== Конвертация данных ===================

    def _card_to_dict(self, card) -> Dict:
        """Конвертирует объект CreditCard в словарь для UI."""
        return {
            "id": card.id,
            "name": card.name,
            "annual_rate": card.annual_rate,
            "grace_months": card.grace_months,
            "min_payment_percent": card.min_payment_percent
        }

    def _periods_to_dicts(self, periods) -> List[Dict]:
        """Конвертирует список периодов в словари для UI."""
        result = []
        for period in periods:
            unpaid = period.total_purchases + period.total_transfers - period.paid_amount
            result.append({
                "id": period.id,
                "period_month": period.period_month,
                "total_purchases": period.total_purchases,
                "total_transfers": period.total_transfers,
                "grace_period_end": period.grace_period_end,
                "is_paid": period.is_paid,
                "paid_amount": period.paid_amount,
                "unpaid_amount": unpaid,
                "interest_retroactive": period.interest_retroactive,
                "interest_daily_accrued": period.interest_daily_accrued,
                "total_interest": period.interest_retroactive + period.interest_daily_accrued
            })
        return result

    def _get_active_accounts_as_dicts(self) -> List[Dict]:
        """Возвращает активные счета как словари (исключая саму кредитку)."""
        accounts = self.account_repo.get_all()
        result = []
        for acc in accounts:
            if acc.is_active and not acc.is_system and acc.id != self.current_card_id:
                result.append({
                    "id": acc.id,
                    "name": acc.name,
                    "current_balance": acc.current_balance
                })
        return result