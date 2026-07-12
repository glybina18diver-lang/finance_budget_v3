"""
Сервис кредитной карты "Сбер Молодёжная".
Инкапсулирует бизнес-логику: расчёт процентов, комиссий, минимального платежа.
"""
from typing import List, Optional, Dict
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import json
import logging

from core.models import CreditCard, CreditCardPeriod, CreditCardPayment
from core.repositories.credit_card_repository import CreditCardRepository
from core.repositories.account_repository import AccountRepository

logger = logging.getLogger(__name__)


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
        try:
            return self.repo.get_all_cards()
        except Exception as e:
            logger.error(f"[CreditCardService] Ошибка загрузки карт: {e}", exc_info=True)
            raise

    def create_card(self, account_id: int) -> int:
        """
        Создаёт новую кредитную карту.
        Имя карты по умолчанию берется из названия привязанного счета.

        Args:
            account_id: ID счёта карты

        Returns:
            ID созданной карты
        """
        try:
            # Получаем счет, чтобы узнать его имя
            account = self.account_repo.get_by_id(account_id)
            default_name = account.name if account else "Кредитная карта"

            card = CreditCard(
                account_id=account_id,
                name=default_name,  # <-- Подхватываем имя счета
                annual_rate=49.8,
                grace_months=3,
                min_payment_percent=0.02,
                payment_day=1,
                statement_day=1,
                credit_limit=10000
            )
            return self.repo.create_card(card)
        except Exception as e:
            logger.error(f"[CreditCardService] Ошибка создания карты: {e}", exc_info=True)
            raise

    def update_card_settings(self, card_id: int, settings_data: dict) -> bool:
        """
        Обновляет настройки кредитной карты.

        Args:
            card_id: ID карты
            settings_data: словарь с новыми настройками

        Returns:
            True если успешно
        """
        try:
            card = self.repo.get_card_by_id(card_id)
            if not card:
                raise ValueError("Карта не найдена")

            # Обновляем поля, если они есть в словаре
            if "name" in settings_data:
                card.name = settings_data["name"].strip()
            if "annual_rate" in settings_data:
                card.annual_rate = float(settings_data["annual_rate"])
            if "grace_months" in settings_data:
                card.grace_months = int(settings_data["grace_months"])
            if "min_payment_percent" in settings_data:
                card.min_payment_percent = float(settings_data["min_payment_percent"])
            if "payment_day" in settings_data:
                card.payment_day = int(settings_data["payment_day"])
            if "statement_day" in settings_data:
                card.statement_day = int(settings_data["statement_day"])
            if "credit_limit" in settings_data:
                card.credit_limit = float(settings_data["credit_limit"])

            return self.repo.update_card(card)

        except ValueError as e:
            logger.warning(f"[CreditCardService] Валидация настроек: {e}")
            raise
        except Exception as e:
            logger.error(f"[CreditCardService] Ошибка обновления настроек карты #{card_id}: {e}", exc_info=True)
            raise RuntimeError(f"Системная ошибка при обновлении карты: {e}") from e

    def delete_card(self, card_id: int) -> bool:
        """
        Удаляет кредитную карту.
        Проверяет наличие операций перед удалением.

        Args:
            card_id: ID карты из таблицы credit_cards

        Returns:
            True если удалена успешно

        Raises:
            ValueError: если есть операции по карте
        """
        try:
            # Проверяем наличие операций
            periods = self.repo.get_periods_by_card(card_id)
            payments = self.repo.get_payments_by_card(card_id)

            if periods or payments:
                raise ValueError(
                    f"Невозможно удалить карту: есть операции.\n"
                    f"Периодов: {len(periods)}, Платежей: {len(payments)}\n\n"
                    f"Сначала удалите все периоды и платежи."
                )

            # Удаляем карту
            return self.repo.delete_card(card_id)

        except ValueError as e:
            logger.warning(f"[CreditCardService] Валидация удаления: {e}")
            raise
        except Exception as e:
            logger.error(f"[CreditCardService] Ошибка удаления карты #{card_id}: {e}", exc_info=True)
            raise RuntimeError(f"Системная ошибка при удалении карты: {e}") from e

    def get_all_credit_cards(self) -> List[Dict]:
        """
        Возвращает список кредитных карт (счетов типа CreditCard) для UI.
        Автоматически создаёт запись в credit_cards, если её нет.

        Returns:
            Список словарей с данными карт
        """
        try:
            cards_with_accounts = self.repo.get_all_cards_with_accounts()

            result = []
            for row in cards_with_accounts:
                # Если записи в credit_cards нет — создаём автоматически
                if not row["card_id"]:
                    card = self.repo.get_or_create_card_for_account(row["account_id"])
                    row["card_id"] = card.id
                    row["annual_rate"] = card.annual_rate
                    row["grace_months"] = card.grace_months
                    row["min_payment_percent"] = card.min_payment_percent

                result.append({
                    "card_id": row["card_id"],
                    "account_id": row["account_id"],
                    "name": row["account_name"],
                    "current_balance": row["current_balance"],
                    "credit_limit": row.get("credit_limit", 0),
                    "annual_rate": row["annual_rate"],
                    "grace_months": row["grace_months"],
                    "min_payment_percent": row["min_payment_percent"]
                })

            return result
        except Exception as e:
            logger.error(f"[CreditCardService] Ошибка загрузки кредитных карт: {e}", exc_info=True)
            raise

    # =================== Периоды ===================
    def add_purchase_by_account(self, account_id: int, purchase_date: str, amount: float):
        """
        Добавляет покупку, находя карту по ID счёта.
        Метод-обёртка для использования из других сервисов.

        Args:
            account_id: ID счёта типа CreditCard
            purchase_date: дата покупки
            amount: сумма покупки (положительная)

        Returns:
            Обновлённый объект периода или None, если счёт не кредитка
        """
        try:
            # Используем готовый метод из репозитория
            card = self.repo.get_or_create_card_for_account(account_id)

            if not card:
                logger.error(f"[CreditCardService] Не удалось получить/создать карту для счета ID: {account_id}")
                return None

            return self.add_purchase(card.id, purchase_date, amount)
        except Exception as e:
            logger.error(f"[CreditCardService] Ошибка добавления покупки по счёту #{account_id}: {e}", exc_info=True)
            raise

    def get_periods(self, card_id: int) -> List[CreditCardPeriod]:
        """Возвращает все периоды по карте."""
        try:
            return self.repo.get_periods_by_card(card_id)
        except Exception as e:
            logger.error(f"[CreditCardService] Ошибка загрузки периодов карты #{card_id}: {e}", exc_info=True)
            raise

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
        try:
            period_month = self._get_period_month(purchase_date)
            period = self.repo.get_period(card_id, period_month)

            if not period:
                # Создаём новый период
                grace_end = self._calculate_grace_period_end(purchase_date, card_id)
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
        except Exception as e:
            logger.error(f"[CreditCardService] Ошибка добавления покупки к карте #{card_id}: {e}", exc_info=True)
            raise

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
        try:
            commission = self.calculate_transfer_commission(amount)
            period_month = self._get_period_month(transfer_date)
            period = self.repo.get_period(card_id, period_month)

            if not period:
                grace_end = self._calculate_grace_period_end(transfer_date, card_id)
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
        except Exception as e:
            logger.error(f"[CreditCardService] Ошибка добавления перевода по карте #{card_id}: {e}", exc_info=True)
            raise

    # =================== Платежи ===================

    def make_payment(self, card_id: int, payment_data: dict) -> Dict:
        """
        Вносит платёж по кредитной карте с автораспределением.
        """
        try:
            amount = float(payment_data["amount"])
            payment_date = payment_data["date"]
            from_account_id = payment_data["from_account_id"]

            periods = sorted(
                self.repo.get_periods_by_card(card_id),
                key=lambda p: p.period_month
            )

            self._recalculate_interest(periods, payment_date)

            allocation = {
                "interest_paid": 0.0,
                "principal_paid": 0.0,
                "periods_updated": []
            }

            remaining = amount

            # === 1. Гасим проценты ===
            for period in periods:
                if remaining <= 0:
                    break

                period_changed = False

                # Гасим ретроактивные проценты
                if period.interest_retroactive > 0:
                    to_pay = min(remaining, period.interest_retroactive)
                    period.interest_retroactive -= to_pay
                    remaining -= to_pay
                    allocation["interest_paid"] += to_pay
                    period_changed = True

                # Гасим ежедневные проценты
                if period.interest_daily_accrued > 0:
                    to_pay = min(remaining, period.interest_daily_accrued)
                    period.interest_daily_accrued -= to_pay
                    remaining -= to_pay
                    allocation["interest_paid"] += to_pay
                    period_changed = True

                # ✅ СОХРАНЯЕМ изменения в БД
                if period_changed:
                    self.repo.update_period(period)
                    if period.period_month not in [p["period_month"] for p in allocation["periods_updated"]]:
                        allocation["periods_updated"].append({
                            "period_month": period.period_month,
                            "paid": allocation["interest_paid"]
                        })

            # === 2. Гасим тело долга (FIFO) ===
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

                # ✅ СОХРАНЯЕМ изменения в БД
                self.repo.update_period(period)
                
                existing = next(
                    (p for p in allocation["periods_updated"] if p["period_month"] == period.period_month),
                    None
                )
                if existing:
                    existing["paid"] += to_pay
                else:
                    allocation["periods_updated"].append({
                        "period_month": period.period_month,
                        "paid": to_pay
                    })

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

        except Exception as e:
            logger.error(f"[CreditCardService] Ошибка внесения платежа по карте #{card_id}: {e}", exc_info=True)
            raise
        
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
        try:
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
        except Exception as e:
            logger.error(f"[CreditCardService] Ошибка расчёта минимального платежа: {e}", exc_info=True)
            raise

    def calculate_full_payoff(self, card_id: int, as_of_date: Optional[str] = None) -> Dict:
        """
        Рассчитывает сумму для полного погашения.

        Args:
            card_id: ID карты
            as_of_date: дата расчёта

        Returns:
            Словарь с разбивкой задолженности
        """
        try:
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
        except Exception as e:
            logger.error(f"[CreditCardService] Ошибка расчёта полного погашения: {e}", exc_info=True)
            raise

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

    def _calculate_grace_period_end(self, purchase_date: str, card_id: int) -> str:
        """
        Рассчитывает конец льготного периода.
        Логика: конец месяца покупки + grace_months месяцев.

        Пример: покупка 15.03.2025, grace_months=3 → льгота до 30.06.2025

        Args:
            purchase_date: дата покупки (YYYY-MM-DD)
            card_id: ID кредитной карты (для получения настроек)

        Returns:
            Дата конца льготного периода (YYYY-MM-DD)
        """
        dt = datetime.strptime(purchase_date, "%Y-%m-%d")

        # 1. Находим конец месяца покупки
        end_of_month = dt.replace(day=1) + relativedelta(months=1, days=-1)

        # 2. Добавляем grace_months из настроек карты
        grace_months = self._get_card_grace_months(card_id)
        grace_end = end_of_month + relativedelta(months=grace_months)

        return grace_end.strftime("%Y-%m-%d")

    def _get_card_grace_months(self, card_id: int) -> int:
        """
        Возвращает количество месяцев льготного периода из настроек карты.

        Args:
            card_id: ID кредитной карты

        Returns:
            Количество месяцев льготного периода (по умолчанию 0, если карта не найдена)
        """
        card = self.repo.get_card_by_id(card_id)
        if card and card.grace_months:
            return card.grace_months
        return 0  # Значение по умолчанию, если карта не найдена

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
        try:
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
        except Exception as e:
            logger.error(f"[CreditCardService] Ошибка пересчёта процентов: {e}", exc_info=True)
            raise