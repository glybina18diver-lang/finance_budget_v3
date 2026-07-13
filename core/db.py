# core/db.py
import sqlite3
import logging
from typing import List, Dict, Any, Optional

from core.migration import migrate_schema

logger = logging.getLogger(__name__)


class Database:
    """Фасад для работы с SQLite (полная схема как в V2)."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._connect()
        self._init_tables()
        migrate_schema(self._conn)  # ← миграция сразу после создания таблиц

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

    def _init_tables(self):
        """Создание всех таблиц согласно схеме V2, но обновлено до V3."""
        if not self._conn:
            return

        cursor = self._conn.cursor()

        # 1. Accounts (Счета)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                account_type TEXT NOT NULL CHECK(account_type IN ('Cash', 'BankAccount', 'CreditCard', 'Counterparty')),
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (from_account_id) REFERENCES accounts(id),
                FOREIGN KEY (to_account_id) REFERENCES accounts(id),
                CHECK (from_account_id != to_account_id)
            )
        """)

        # 5. Loans (Займы)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                counterparty_account_id INTEGER NOT NULL,
                contact_name TEXT NOT NULL,
                loan_type TEXT NOT NULL CHECK (loan_type IN ('issued', 'received')),
                loan_amount REAL NOT NULL,
                outstanding_amount REAL NOT NULL,
                interest_rate REAL DEFAULT 0.0,
                issue_date TEXT NOT NULL,
                due_date TEXT,
                description TEXT,
                status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paid', 'default')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                FOREIGN KEY (counterparty_account_id) REFERENCES accounts(id) ON DELETE CASCADE
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

        # Таблица 7: tranches (Транш)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tranches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                tranche_type TEXT NOT NULL DEFAULT 'purchase',
                original_amount REAL NOT NULL DEFAULT 0.0,
                remaining_amount REAL NOT NULL DEFAULT 0.0,
                commission REAL NOT NULL DEFAULT 0.0,
                transaction_date DATE NOT NULL,
                grace_end_date DATE,
                status TEXT NOT NULL DEFAULT 'in_grace',
                is_retroactive_triggered INTEGER NOT NULL DEFAULT 0,
                linked_transaction_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (card_id) REFERENCES credit_cards(id) ON DELETE CASCADE
            )
        """)
        
        # Таблица 8: interest_accruals (Проценты на дату)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interest_accruals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tranche_id INTEGER NOT NULL,
                accrual_date DATE NOT NULL,
                interest_type TEXT NOT NULL DEFAULT 'daily',
                amount REAL NOT NULL DEFAULT 0.0,
                paid_amount REAL NOT NULL DEFAULT 0.0,
                is_paid INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tranche_id) REFERENCES tranches(id) ON DELETE CASCADE
            )
        """)
        
        # Таблица 9: statements (Биллинговый цикл (выписка))
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS statements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                statement_date DATE NOT NULL,
                due_date DATE,
                opening_balance REAL NOT NULL DEFAULT 0.0,
                new_charges REAL NOT NULL DEFAULT 0.0,
                payments_received REAL NOT NULL DEFAULT 0.0,
                interest_charged REAL NOT NULL DEFAULT 0.0,
                closing_balance REAL NOT NULL DEFAULT 0.0,
                min_payment_required REAL NOT NULL DEFAULT 0.0,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (card_id) REFERENCES credit_cards(id) ON DELETE CASCADE
            )
        """)

        # 10. credit_cards (Кредитная карта)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credit_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            annual_rate REAL NOT NULL,
            grace_months INTEGER NOT NULL,
            min_payment_percent REAL NOT NULL,
            payment_day INTEGER NOT NULL,
            statement_day INTEGER NOT NULL,
            credit_limit REAL NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            )
        """)

        # 7. Budgets (Бюджеты)
        # пока не создаем так как это не исползкется 
        # cursor.execute("""
        #     CREATE TABLE IF NOT EXISTS budgets (
        #         id INTEGER PRIMARY KEY AUTOINCREMENT,
        #         category_id INTEGER NOT NULL,
        #         month_year TEXT NOT NULL,
        #         planned_amount REAL NOT NULL,
        #         actual_amount REAL DEFAULT 0.0,
        #         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        #         UNIQUE(category_id, month_year),
        #         FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        #     )
        # """)

        self._conn.commit()
        logger.info("Все таблицы схемы V2 успешно созданы/проверены")

    def index_tables(self):
        """Создание индексов для таблиц"""
        cursor = self._conn.cursor()
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tranches_card_id ON tranches(card_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tranches_status ON tranches(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tranches_grace_end ON tranches(grace_end_date)")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interest_accruals_tranche_id ON interest_accruals(tranche_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_interest_accruals_date ON interest_accruals(accrual_date)")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_statements_card_id ON statements(card_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_statements_date ON statements(statement_date)")
        
        self._conn.commit()
        
        logger.info("[Database] Таблицы tranches, interest_accruals, statements созданы/проверены")

    # --- Методы доступа к данным ---

    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Выполняет SQL-запрос с автокоммитом."""
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            self._conn.commit()
            return cursor
        except Exception as e:
            logger.error(f"[Database] Ошибка выполнения запроса: {e}", exc_info=True)
            raise

    def fetch_all(self, query: str, params: tuple = ()) -> list:
        """Выполняет SELECT и возвращает все строки."""
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"[Database] Ошибка выборки данных: {e}", exc_info=True)
            raise
    
    def fetch_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Выполняет SELECT и возвращает одну строку."""
        try:
            cursor = self._conn.cursor()
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"[Database] Ошибка выборки одной записи: {e}", exc_info=True)
            raise

    def fetchall(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        if not self._conn:
            raise RuntimeError("Нет подключения к БД")
        cursor = self._conn.cursor()
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        if not self._conn:
            raise RuntimeError("Нет подключения к БД")
        cursor = self._conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None

    def close(self):
        """Закрывает соединение с БД."""
        if self._conn:
            self._conn.close()
            logger.info("[Database] Соединение с БД закрыто")