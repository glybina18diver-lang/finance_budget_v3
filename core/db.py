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
        try:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            raise

    def _init_tables(self):
        """Создание всех таблиц согласно схеме V2."""
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

        # 7. Budgets (Бюджеты)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                month_year TEXT NOT NULL,
                planned_amount REAL NOT NULL,
                actual_amount REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category_id, month_year),
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        """)

        self._conn.commit()
        logger.info("Все таблицы схемы V2 успешно созданы/проверены")

    # --- Методы доступа к данным ---

    def execute(self, query: str, params: tuple = ()) -> int:
        if not self._conn:
            raise RuntimeError("Нет подключения к БД")
        cursor = self._conn.cursor()
        cursor.execute(query, params)
        self._conn.commit()
        return cursor.lastrowid

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
        if self._conn:
            self._conn.close()
            self._conn = None