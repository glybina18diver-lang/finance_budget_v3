# core/repositories/analytics_repository.py
"""Репозиторий для получения аналитических данных из БД."""

import logging
from datetime import datetime
from typing import Dict, List

from core.db import Database

logger = logging.getLogger(__name__)


class AnalyticsRepository:
    """Репозиторий для операций аналитики (только чтение агрегированных данных)."""

    def __init__(self, db: Database):
        """
        Инициализация репозитория.

        Args:
            db: экземпляр фасада Database для выполнения запросов
        """
        self.db = db

    def get_monthly_summary(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Получает помесячную сводку доходов/расходов за период.

        Args:
            start_date: начало периода в формате YYYY-MM-DD
            end_date: конец периода в формате YYYY-MM-DD

        Returns:
            Список словарей вида:
            [{'month': '2025-09', 'income': 62000.0, 'expense': 42300.0}, ...]

        Raises:
            ValueError: если даты некорректны
        """
        try:
            self._validate_date_range(start_date, end_date)

            sql = """
            SELECT
                strftime('%Y-%m', date) AS month,
                COALESCE(SUM(CASE WHEN trans_type = 'income'
                             THEN amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN trans_type = 'expense'
                             THEN ABS(amount) ELSE 0 END), 0) AS expense
            FROM transactions
            WHERE date BETWEEN ? AND ?
              AND trans_type IN ('income', 'expense')
            GROUP BY month
            ORDER BY month
            """

            rows = self.db.fetch_all(sql, (start_date, end_date))
            logger.info(
                f"[{self.__class__.__name__}] Получено {len(rows)} месяцев "
                f"за период {start_date} — {end_date}"
            )
            return rows
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def get_monthly_budget(self) -> float:
        """
        Возвращает общий месячный бюджет (Вариант B).

        Сумма budget_amount_monthly всех активных категорий расходов.
        Не зависит от периода — бюджет фиксирован на каждый месяц.

        Returns:
            Суммарный месячный бюджет (float)
        """
        try:
            sql = """
            SELECT COALESCE(SUM(budget_amount_monthly), 0) AS total_budget
            FROM categories
            WHERE cat_type = 'expense'
              AND budget_amount_monthly > 0
              AND is_active = 1
            """
            row = self.db.fetch_one(sql)
            budget = float(row['total_budget']) if row else 0.0
            logger.debug(
                f"[{self.__class__.__name__}] Общий месячный бюджет: {budget}"
            )
            return budget
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def get_balance_at_date(self, target_date: str) -> float:
        """
        Вычисляет суммарный баланс всех активных счетов на указанную дату.

        Формула: SUM(initial_balance) + SUM(все транзакции до target_date).
        Переводы не учитываются (не меняют общий капитал).

        Args:
            target_date: дата в формате YYYY-MM-DD

        Returns:
            Суммарный баланс на указанную дату

        Raises:
            ValueError: если дата не указана
        """
        try:
            if not target_date:
                raise ValueError("Дата не указана")

            # 1. Сумма начальных балансов активных счетов
            sql_initial = """
            SELECT COALESCE(SUM(initial_balance), 0) AS total
            FROM accounts
            WHERE is_active = 1
            """
            row_initial = self.db.fetch_one(sql_initial)
            initial = float(row_initial['total']) if row_initial else 0.0

            # 2. Все транзакции до target_date (включая refund и correct)
            sql_transactions = """
            SELECT COALESCE(SUM(amount), 0) AS total
            FROM transactions
            WHERE date < ?
            """
            row_trans = self.db.fetch_one(sql_transactions, (target_date,))
            transactions_sum = float(row_trans['total']) if row_trans else 0.0

            balance = initial + transactions_sum
            logger.debug(
                f"[{self.__class__.__name__}] Баланс на {target_date}: "
                f"{initial} (initial) + {transactions_sum} (транзакции) = {balance}"
            )
            return balance
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def get_category_breakdown(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Получает разбивку расходов по категориям за период.

        Args:
            start_date: начало периода в формате YYYY-MM-DD
            end_date: конец периода в формате YYYY-MM-DD

        Returns:
            Список словарей вида:
            [{'category': 'Продукты', 'amount': 15000.0, 'color': '#27AE60'}, ...]

        Raises:
            ValueError: если даты некорректны
        """
        try:
            self._validate_date_range(start_date, end_date)

            sql = """
            SELECT
                COALESCE(c.name, 'Без категории') AS category,
                SUM(ABS(t.amount)) AS amount,
                COALESCE(c.color, '#7F8C8D') AS color
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            WHERE t.date BETWEEN ? AND ?
              AND t.trans_type = 'expense'
            GROUP BY c.name, c.color
            ORDER BY amount DESC
            """

            rows = self.db.fetch_all(sql, (start_date, end_date))
            logger.info(
                f"[{self.__class__.__name__}] Получено {len(rows)} категорий "
                f"за период {start_date} — {end_date}"
            )
            return rows
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def _validate_date_range(self, start_date: str, end_date: str) -> None:
        """
        Проверяет корректность диапазона дат.

        Args:
            start_date: начало периода в формате YYYY-MM-DD
            end_date: конец периода в формате YYYY-MM-DD

        Raises:
            ValueError: если даты пустые, некорректные или start > end
        """
        if not start_date or not end_date:
            raise ValueError("Даты начала и конца периода обязательны")

        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            raise ValueError(
                f"Некорректный формат даты (ожидался YYYY-MM-DD): "
                f"start={start_date}, end={end_date}"
            )

        if start > end:
            raise ValueError(
                f"Дата начала ({start_date}) не может быть позже "
                f"даты конца ({end_date})"
            )