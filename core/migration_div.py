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

    # --- categories: добавление системных категорий (если отсутствуют) ---
    system_categories = [
        ('Проценты по кредитным картам', 'expense')
    ]
    
    for name, cat_type in system_categories:
        cursor.execute("SELECT id FROM categories WHERE name = ? AND is_system = 1", (name,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO categories (name, cat_type, is_system, is_active) VALUES (?, ?, 1, 1)",
                (name, cat_type)
            )
            logger.info(f"Миграция: добавлена системная категория '{name}'")
            
    conn.commit()

    

    conn.commit()