"""Фасад для работы с SQLite (полная схема как в V2, обновлено до V3)."""

import sqlite3
import logging
from typing import Optional, Dict, Any, List

from core.migration_div import migrate_schema
# from core.migration import migrate_database

logger = logging.getLogger(__name__)


class Database:
    """Фасад для работы с SQLite."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()
        # new_db = "new_budget.db"
        # migrate_database(db_path, new_db)
        # migrate_schema(self._conn)  # ← миграция сразу после создания таблиц (для старых БД)
        self._init_tables()

    def _connect(self):
        """Устанавливает соединение с БД."""
        try:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            logger.info(f"[Database] Подключение к БД: {self.db_path}")
        except Exception as e:
            logger.error(f"[Database] Ошибка подключения к БД: {e}", exc_info=True)
            raise

    # Это временный метод только для того чтобы по быстрому подключть минималный график в гл. окне
    def get_yearly_summary(self, year: int) -> Dict[str, Dict]:
        """
        Получает сводку доходов/расходов по месяцам за год для графика.
        
        Args:
            year: год для получения данных (например, 2026)
            
        Returns:
            Словарь вида {'2026-01': {'income': 1000.0, 'expense': 800.0, 'balance': 200.0}, ...}
            Всегда возвращает данные за все 12 месяцев (даже если по ним нет транзакций).
            
        Raises:
            ValueError: если год некорректен
            RuntimeError: при ошибке работы с БД
        """
        try:
            # Валидация входных данных
            if not isinstance(year, int):
                raise ValueError(f"Год должен быть целым числом, получено: {type(year).__name__}")
            if year < 1900 or year > 2100:
                raise ValueError(f"Год вне допустимого диапазона: {year}")
            
            sql = '''
                SELECT 
                    strftime('%Y-%m', date) AS month_year,
                    COALESCE(SUM(CASE WHEN trans_type = 'income' THEN amount ELSE 0 END), 0) AS income,
                    COALESCE(SUM(CASE WHEN trans_type = 'expense' THEN ABS(amount) ELSE 0 END), 0) AS expense,
                    COALESCE(SUM(amount), 0) AS balance
                FROM transactions
                WHERE strftime('%Y', date) = ?
                    AND trans_type IN ('income', 'expense')
                GROUP BY month_year
                ORDER BY month_year
            '''
            
            cursor = self._conn.cursor()
            cursor.execute(sql, (str(year),))
            results = cursor.fetchall()
            
            # Инициализируем структуру для всех 12 месяцев (нулевые значения)
            monthly_data = {}
            for month in range(1, 13):
                month_key = f"{year}-{month:02d}"
                monthly_data[month_key] = {
                    'income': 0.0,
                    'expense': 0.0,
                    'balance': 0.0
                }
            
            # Заполняем данные из БД
            for row in results:
                month_key = row[0]
                if month_key in monthly_data:
                    monthly_data[month_key] = {
                        'income': float(row[1] or 0.0),
                        'expense': float(row[2] or 0.0),
                        'balance': float(row[3] or 0.0)
                    }
            
            logger.info(f"[{self.__class__.__name__}] Получена сводка за {year} год: "
                        f"{len([m for m in monthly_data.values() if m['income'] or m['expense']])} "
                        f"месяцев с данными")
            return monthly_data
            
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация года: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения сводки за {year}: {e}", 
                        exc_info=True)
            raise RuntimeError(f"Не удалось получить сводку за {year} год") from e
        
    
    def _init_tables(self):
        """Создание всех таблиц согласно актуальной схеме V3."""
        if not self._conn:
            return
        cursor = self._conn.cursor()

        # 1. Accounts (Счета)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                account_type TEXT NOT NULL CHECK(account_type IN (
                    'Cash', 'BankAccount', 'CreditCard', 'Counterparty', 'Credit'
                )),
                initial_balance REAL DEFAULT 0.0,
                current_balance REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                is_system BOOLEAN DEFAULT 0,
                currency TEXT DEFAULT 'RUB'
            )
        """)

        # 2. Categories (Категории)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                cat_type TEXT NOT NULL CHECK(cat_type IN ('income', 'expense')),
                budget_amount_monthly REAL DEFAULT 0.0,
                parent_id INTEGER DEFAULT NULL,
                color TEXT DEFAULT '#3498db',
                icon TEXT DEFAULT '',
                is_active INTEGER DEFAULT 1,
                is_system BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        """)

        # 3. Transactions (Транзакции)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                trans_type TEXT NOT NULL CHECK (trans_type IN ('income', 'expense', 'refund', 'correct')),
                category_id INTEGER,
                description TEXT,
                account_id INTEGER NOT NULL,
                original_transaction_id INTEGER DEFAULT NULL,
                quantity REAL DEFAULT 1.0,
                unit_price REAL GENERATED ALWAYS AS (
                    CASE WHEN quantity != 0 THEN amount / quantity ELSE NULL END
                ) STORED,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE RESTRICT,
                FOREIGN KEY (original_transaction_id) REFERENCES transactions(id) ON DELETE SET NULL,
                CHECK (
                    (trans_type IN ('income', 'expense', 'refund') AND category_id IS NOT NULL) OR 
                    (trans_type = 'correct' AND category_id IS NULL)
                ),
                CHECK (
                    (trans_type != 'refund') OR 
                    (trans_type = 'refund' AND original_transaction_id IS NOT NULL)
                )
            )
        """)

        # 4. Transfers (Переводы)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                from_account_id INTEGER NOT NULL,
                to_account_id INTEGER NOT NULL,
                description TEXT,
                type TEXT DEFAULT 'internal',
                is_system INTEGER DEFAULT 0,
                loan_id INTEGER DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_account_id) REFERENCES accounts(id),
                FOREIGN KEY (to_account_id) REFERENCES accounts(id),
                FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE SET NULL,
                CHECK (from_account_id != to_account_id)
            )
        """)

        # 5. Loans (Займы и Кредиты)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                
                -- Разделение сущностей
                source_type TEXT NOT NULL CHECK(source_type IN ('bank', 'person')),
                loan_type TEXT NOT NULL CHECK(loan_type IN ('issued', 'received')),
                loan_purpose TEXT CHECK(loan_purpose IN ('consumer', 'purchase')),
                
                -- Суммы
                loan_amount REAL NOT NULL,
                remaining REAL NOT NULL,
                interest_rate REAL DEFAULT 0.0,
                term_months INTEGER,
                
                -- Даты
                issue_date TEXT NOT NULL,
                due_date TEXT,
                
                -- Связи со счетами
                account_id INTEGER NOT NULL,
                counterparty_account_id INTEGER,
                
                -- Специфичные поля для POS-кредита (purchase)
                purchase_transaction_id INTEGER,
                
                -- Специфичные поля для займов у людей
                contact_name TEXT,
                
                -- Общее
                description TEXT,
                status TEXT DEFAULT 'active' CHECK(status IN ('active', 'paid', 'default')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (counterparty_account_id) REFERENCES accounts(id) ON DELETE SET NULL,
                FOREIGN KEY (purchase_transaction_id) REFERENCES transactions(id) ON DELETE SET NULL
            )
        """)

        # 6. Loan Payments (Платежи по займам)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loan_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_id INTEGER NOT NULL,
                payment_date TEXT NOT NULL,
                payment_amount REAL NOT NULL,
                interest_amount REAL DEFAULT 0.0,
                principal_amount REAL DEFAULT 0.0,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (loan_id) REFERENCES loans(id) ON DELETE CASCADE
            )
        """)

        # 10. Credit Cards (Кредитные карты)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credit_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL UNIQUE,
                
                -- Опциональные параметры (NULL по умолчанию)
                credit_limit REAL,
                annual_rate REAL,
                grace_months INTEGER,
                min_payment_percent REAL,
                payment_day INTEGER,
                statement_day INTEGER,
                
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )
        """)

        # Инициализация системных категорий и индексов
        self._init_system_parameters(cursor)
        # self.index_tables()

        self._conn.commit()
        logger.info("[Database] Все таблицы схемы V3 успешно созданы/проверены")

    def index_tables(self):
        """Создание индексов для таблиц."""
        try:
            cursor = self._conn.cursor()
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tranches_card_id ON tranches(card_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tranches_status ON tranches(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_tranches_grace_end ON tranches(grace_end_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interest_accruals_tranche_id ON interest_accruals(tranche_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interest_accruals_date ON interest_accruals(accrual_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_statements_card_id ON statements(card_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_statements_date ON statements(statement_date)")
            self._conn.commit()
            logger.info("[Database] Индексы для таблиц tranches, interest_accruals, statements созданы/проверены")
        except Exception as e:
            logger.error(f"[Database] Ошибка создания индексов: {e}", exc_info=True)
            raise

    def _init_system_parameters(self, cursor):
        """
        Создаёт системные категории, счетов если их ещё нет в БД.
        
        Логирует создание только при реальной вставке (rowcount > 0).
        
        Args:
            cursor: активный курсор SQLite
        """
        try:
            system_categories = [
                ("Проценты по кредитным картам", "expense"),
                ("Проценты по кредитам", "expense")
            ]
            pre_installed_acc = [
                ("Наличка", "Cash")
            ]
            
            for name, cat_type in system_categories:
                cursor.execute("""
                    INSERT INTO categories (name, cat_type, is_system, is_active)
                    SELECT ?, ?, 1, 1
                    WHERE NOT EXISTS (SELECT 1 FROM categories WHERE name = ? AND is_system = 1)
                """, (name, cat_type, name))
                
                # Логируем только если реально была вставка
                if cursor.rowcount > 0:
                    logger.info(f"Создана системная категория '{name}'")

            for name, account_type in pre_installed_acc:
                cursor.execute("""
                    INSERT INTO accounts (name, account_type, is_active)
                    SELECT ?, ?, 1
                    WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE name = ?)
                """, (name, account_type, name))
                
                # Логируем только если реально была вставка
                if cursor.rowcount > 0:
                    logger.info(f"Создан pre-installed счет '{name}'")
                    
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания системных параметров: {e}", exc_info=True)
            raise

    # --- Методы доступа к данным ---

    def execute(self, query: str, params: tuple = ()) -> int:
        """Выполняет SQL-запрос и возвращает lastrowid для INSERT."""
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            self._conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка выполнения запроса: {e}", exc_info=True)
            raise

    def fetch_all(self, query: str, params: tuple = ()) -> list:
        """Выполняет SELECT и возвращает все строки как список словарей."""
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]  # ← конвертация в dict
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка выборки данных: {e}", exc_info=True)
            raise

    def fetch_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Выполняет SELECT и возвращает одну строку."""
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка выборки одной записи: {e}", exc_info=True)
            raise

    def fetchall(self, query: str, params: tuple = ()) -> list:
        """Выполняет SELECT и возвращает все строки (альтернативный метод)."""
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка выборки данных: {e}", exc_info=True)
            raise

    def fetchone(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Выполняет SELECT и возвращает одну строку (альтернативный метод)."""
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка выборки одной записи: {e}", exc_info=True)
            raise

    def close(self):
        """Закрывает соединение с БД."""
        try:
            if self._conn:
                self._conn.close()
                logger.info("[Database] Соединение с БД закрыто")
        except Exception as e:
            logger.error(f"[Database] Ошибка закрытия соединения: {e}", exc_info=True)
            raise