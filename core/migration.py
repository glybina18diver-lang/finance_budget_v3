# core/migration.py
import logging
from typing import Optional
import sqlite3

logger = logging.getLogger(__name__)


def migrate_schema(conn: Optional[sqlite3.Connection]) -> None:
    """Применяет миграции для совместимости с V3-моделями."""
    if not conn:
        return

    cursor = conn.cursor()

    # --- accounts: type → account_type ---
    cursor.execute("PRAGMA table_info(accounts)")
    cols = {row[1] for row in cursor.fetchall()}
    if "type" in cols and "account_type" not in cols:
        cursor.execute("ALTER TABLE accounts RENAME COLUMN type TO account_type")
        logger.info("Миграция: accounts.type → account_type")
    
    # --- accounts: нормализация значений account_type ---
    # Приводим все варианты написания к единому стилю PascalCase
    if "account_type" in cols or "account_type" in {row[1] for row in cursor.execute("PRAGMA table_info(accounts)").fetchall()}:
        # Маппинг: старое значение → новое значение
        type_normalization = {
            'Credit Card': 'CreditCard',
            'credit_card': 'CreditCard',
            'creditcard': 'CreditCard',
            'credit': 'CreditCard',
            
            'Bank Account': 'BankAccount',
            'bank_account': 'BankAccount',
            'bankaccount': 'BankAccount',
            'bank': 'BankAccount',
            
            'cash': 'Cash',
            'НАЛИЧНЫЕ': 'Cash',
            'Наличные': 'Cash',            
        }
        
        for old_type, new_type in type_normalization.items():
            cursor.execute(
                "UPDATE accounts SET account_type = ? WHERE account_type = ?",
                (new_type, old_type)
            )
            if cursor.rowcount > 0:
                logger.info(f"Миграция: account_type '{old_type}' → '{new_type}' ({cursor.rowcount} записей)")

    # --- categories: type → cat_type ---
    cursor.execute("PRAGMA table_info(categories)")
    cols = {row[1] for row in cursor.fetchall()}
    if "type" in cols and "cat_type" not in cols:
        cursor.execute("ALTER TABLE categories RENAME COLUMN type TO cat_type")
        logger.info("Миграция: categories.type → cat_type")

    # --- categories: добавление is_active и is_system (если отсутствуют) ---
    cursor.execute("PRAGMA table_info(categories)")
    cols = {row[1] for row in cursor.fetchall()}
    if "is_active" not in cols:
        cursor.execute("ALTER TABLE categories ADD COLUMN is_active INTEGER DEFAULT 1")
        logger.info("Миграция: добавлена колонка categories.is_active")
    if "is_system" not in cols:
        cursor.execute("ALTER TABLE categories ADD COLUMN is_system INTEGER DEFAULT 0")
        logger.info("Миграция: добавлена колонка categories.is_system")

    # --- transactions: type → trans_type ---
    cursor.execute("PRAGMA table_info(transactions)")
    cols = {row[1] for row in cursor.fetchall()}
    if "type" in cols and "trans_type" not in cols:
        cursor.execute("ALTER TABLE transactions RENAME COLUMN type TO trans_type")
        logger.info("Миграция: transactions.type → trans_type")

    # --- loans: outstanding_amount → remaining ---
    cursor.execute("PRAGMA table_info(loans)")
    cols = {row[1] for row in cursor.fetchall()}
    if "outstanding_amount" in cols and "remaining" not in cols:
        cursor.execute("ALTER TABLE loans RENAME COLUMN outstanding_amount TO remaining")
        logger.info("Миграция: loans.outstanding_amount → remaining")

    # --- transfers: добавление type, is_system, loan_id (если отсутствуют) ---
    cursor.execute("PRAGMA table_info(transfers)")
    cols = {row[1] for row in cursor.fetchall()}

    # миграция для таблиц кредитных карт
    # --- credit_cards: создание таблицы кредитных карт ---
    cursor.execute("PRAGMA table_info(credit_cards)")
    if not cursor.fetchall():
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credit_cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                name TEXT NOT NULL DEFAULT 'Сбер Молодёжная',
                annual_rate REAL NOT NULL DEFAULT 49.8,
                grace_months INTEGER NOT NULL DEFAULT 3,
                min_payment_percent REAL NOT NULL DEFAULT 0.02,
                payment_day INTEGER NOT NULL DEFAULT 10,
                statement_day INTEGER NOT NULL DEFAULT 1,
                credit_limit REAL NOT NULL DEFAULT 0.0,
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            )
        """)
        logger.info("Миграция: создана таблица credit_cards")

    # --- credit_card_periods: периоды покупок/переводов ---
    cursor.execute("PRAGMA table_info(credit_card_periods)")
    if not cursor.fetchall():
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credit_card_periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                period_month TEXT NOT NULL,
                total_purchases REAL DEFAULT 0,
                total_transfers REAL DEFAULT 0,
                grace_period_end TEXT,
                is_paid INTEGER DEFAULT 0,
                paid_amount REAL DEFAULT 0,
                interest_retroactive REAL DEFAULT 0,
                interest_daily_accrued REAL DEFAULT 0,
                FOREIGN KEY (card_id) REFERENCES credit_cards(id)
            )
        """)
        logger.info("Миграция: создана таблица credit_card_periods")

    # --- credit_card_payments: платежи по кредитной карте ---
    cursor.execute("PRAGMA table_info(credit_card_payments)")
    if not cursor.fetchall():
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credit_card_payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                from_account_id INTEGER NOT NULL,
                allocation_json TEXT,
                FOREIGN KEY (card_id) REFERENCES credit_cards(id),
                FOREIGN KEY (from_account_id) REFERENCES accounts(id)
            )
        """)
        logger.info("Миграция: создана таблица credit_card_payments")
    # конец миграции для кредитных карт

    if "type" not in cols:
        cursor.execute("ALTER TABLE transfers ADD COLUMN type TEXT DEFAULT 'internal'")
        logger.info("Миграция: добавлена колонка transfers.type")

    if "is_system" not in cols:
        cursor.execute("ALTER TABLE transfers ADD COLUMN is_system INTEGER DEFAULT 0")
        logger.info("Миграция: добавлена колонка transfers.is_system")

    if "loan_id" not in cols:
        cursor.execute("ALTER TABLE transfers ADD COLUMN loan_id INTEGER DEFAULT NULL")
        logger.info("Миграция: добавлена колонка transfers.loan_id")

    # --- accounts: удаление колонок кредитных карт (перенесены в credit_cards) ---
    # cursor.execute("PRAGMA table_info(accounts)")
    # cols = {row[1] for row in cursor.fetchall()}
    # if "credit_limit" in cols:
    #     logger.info("Миграция: удаление колонок credit_limit, payment_due_day, min_payment_percent, last_payment_date из accounts")
    #     cursor.execute("""
    #         CREATE TABLE accounts_new (
    #             id INTEGER PRIMARY KEY AUTOINCREMENT,
    #             name TEXT NOT NULL,
    #             account_type TEXT NOT NULL DEFAULT 'Cash',
    #             initial_balance REAL DEFAULT 0.0,
    #             current_balance REAL DEFAULT 0.0,
    #             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    #             is_active BOOLEAN DEFAULT 1,
    #             is_system BOOLEAN DEFAULT 0,
    #             currency TEXT DEFAULT 'RUB'
    #         )
    #     """)
    #     cursor.execute("""
    #         INSERT INTO accounts_new (id, name, account_type, initial_balance, current_balance,
    #                                   created_at, is_active, is_system, currency)
    #         SELECT id, name, account_type, initial_balance, current_balance,
    #                created_at, is_active, is_system, currency
    #         FROM accounts
    #     """)
    #     cursor.execute("DROP TABLE accounts")
    #     cursor.execute("ALTER TABLE accounts_new RENAME TO accounts")
    #     logger.info("Миграция: колонки кредитных карт успешно удалены из accounts")

    conn.commit()