# services/analytics_service.py
"""Сервис аналитики: подготовка данных для графиков из реальной БД."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

from core.repositories.analytics_repository import AnalyticsRepository

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Бизнес-логика аналитики: получение и валидация данных из БД."""

    def __init__(self, analytics_repo: AnalyticsRepository):
        """
        Инициализация сервиса.

        Args:
            analytics_repo: репозиторий для получения данных аналитики
        """
        self.repo = analytics_repo

    def get_analytics_data(self, start_date: str, end_date: str) -> Dict:
        """
        Получает полные данные аналитики за указанный период.

        Args:
            start_date: начало периода в формате YYYY-MM-DD
            end_date: конец периода в формате YYYY-MM-DD

        Returns:
            Словарь с ключами months, period_dates, incomes, expenses,
            budget, cumulative_balance

        Raises:
            ValueError: если данные не прошли валидацию
        """
        try:
            summary = self.repo.get_monthly_summary(start_date, end_date)
            monthly_budget = self.repo.get_monthly_budget()
            balance_at_start = self.repo.get_balance_at_date(start_date)

            data = self._build_analytics_dict(
                summary, monthly_budget, balance_at_start
            )
            self._validate_analytics(data)
            return data
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def get_default_period(self) -> tuple:
        """
        Возвращает период по умолчанию: последние 12 месяцев.

        Returns:
            Кортеж (start_date, end_date) в формате YYYY-MM-DD
        """
        today = datetime.now()
        end_date = today.strftime('%Y-%m-%d')
        start_date = (today - timedelta(days=365)).strftime('%Y-%m-%d')
        return start_date, end_date

    def _build_analytics_dict(
        self,
        summary: List[Dict],
        monthly_budget: float,
        balance_at_start: float
    ) -> Dict:
        """
        Собирает словарь данных из результатов запросов.

        Args:
            summary: список словарей с доходами/расходами по месяцам
            monthly_budget: фиксированный месячный бюджет (Вариант B)
            balance_at_start: баланс всех счетов на начало периода

        Returns:
            Словарь с ключами months, period_dates, incomes, expenses,
            budget, cumulative_balance
        """
        months = []
        period_dates = []
        incomes = []
        expenses = []
        budget = []
        cumulative_balance = []

        running_balance = balance_at_start

        for row in summary:
            month_str = row['month']  # '2025-09'
            income = float(row['income'])
            expense = float(row['expense'])

            # Метка месяца для отображения: 'Сен 25'
            try:
                dt = datetime.strptime(month_str, '%Y-%m')
                month_label = dt.strftime('%b %y')
            except ValueError:
                month_label = month_str

            months.append(month_label)
            period_dates.append(f"{month_str}-01")
            incomes.append(income)
            expenses.append(expense)
            budget.append(monthly_budget)  # Вариант B: одно число на каждый месяц

            running_balance += income - expense
            cumulative_balance.append(running_balance)

        return {
            "months": months,
            "period_dates": period_dates,
            "incomes": incomes,
            "expenses": expenses,
            "budget": budget,
            "cumulative_balance": cumulative_balance,
        }

    def _validate_analytics(self, data: Dict) -> None:
        """
        Проверяет целостность набора данных аналитики.

        Args:
            data: словарь с массивами months, period_dates, incomes,
                  expenses, budget, cumulative_balance

        Raises:
            ValueError: если массивы пустые или разной длины
        """
        required = ("months", "period_dates", "incomes", "expenses",
                    "budget", "cumulative_balance")
        for key in required:
            if not data.get(key):
                raise ValueError(f"Пустой массив данных: {key}")
        lengths = {len(data[key]) for key in required}
        if len(lengths) > 1:
            raise ValueError("Массивы данных имеют разную длину")

    def get_kpi_metrics(self, data: Dict) -> Dict:
        """
        Вычисляет KPI-метрики по данным аналитики.

        Args:
            data: словарь с ключами months, incomes, expenses, budget

        Returns:
            Словарь с ключами total_income, total_expense, net_flow,
            savings_rate, budget_execution

        Raises:
            ValueError: если данных недостаточно или деление на ноль
        """
        try:
            self._validate_analytics(data)
            total_income = sum(data["incomes"])
            total_expense = sum(data["expenses"])
            total_budget = sum(data["budget"])

            if total_income == 0:
                raise ValueError(
                    "Сумма доходов равна нулю — Savings Rate не вычислить"
                )
            if total_budget == 0:
                raise ValueError(
                    "Сумма бюджета равна нулю — исполнение не вычислить"
                )

            net_flow = total_income - total_expense
            savings_rate = net_flow / total_income * 100
            budget_execution = total_expense / total_budget * 100

            return {
                "total_income": total_income,
                "total_expense": total_expense,
                "net_flow": net_flow,
                "savings_rate": savings_rate,
                "budget_execution": budget_execution,
            }
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise