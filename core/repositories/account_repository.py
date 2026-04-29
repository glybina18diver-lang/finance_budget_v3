# core/repositories/account_repository.py
from typing import Optional, Dict, Any, List
from core.db import Database
from core.models import Account

class AccountRepository:
    """Репозиторий для работы со счетами (только чтение и обновление)."""

    def __init__(self, db: Database):
        """
        Инициализация репозитория.
        
        Args:
            db: экземпляр фасада Database для выполнения запросов
        """
        self.db = db

    def _row_to_account(self, row: Dict[str, Any]) -> Account:
        """
        Преобразует словарь из БД в объект счёта.
        
        Args:
            row: словарь с данными строки из БД
            
        Returns:
            Инициализированный объект Account
        """
        return Account(
            id=row.get("id"),
            name=row.get("name", ""),
            account_type=row.get("account_type", "Cash"),
            initial_balance=row.get("initial_balance", 0.0),
            current_balance=row.get("current_balance", 0.0),
            credit_limit=row.get("credit_limit", 0.0),
            payment_due_day=row.get("payment_due_day", 1),
            min_payment_percent=row.get("min_payment_percent", 5.0),
            last_payment_date=row.get("last_payment_date"),
            is_active=bool(row.get("is_active", 1)),
            is_system=bool(row.get("is_system", 0)),
            currency=row.get("currency", "RUB")
        )

    def get_by_id(self, account_id: int) -> Optional[Account]:
        """
        Возвращает счёт по уникальному идентификатору.
        
        Args:
            account_id: ID искомого счёта
            
        Returns:
            Объект Account или None, если запись не найдена
        """
        query = "SELECT * FROM accounts WHERE id = ?"
        row = self.db.fetchone(query, (account_id,))
        return self._row_to_account(row) if row else None

    def update(self, account: Account) -> bool:
        """
        Обновляет существующий счёт в БД.
        
        Args:
            account: объект Account с изменёнными полями
            
        Returns:
            True если операция прошла успешно
        """
        query = """
            UPDATE accounts SET 
                name = ?, account_type = ?, initial_balance = ?, current_balance = ?,
                credit_limit = ?, payment_due_day = ?, min_payment_percent = ?,
                last_payment_date = ?, is_active = ?, is_system = ?, currency = ?
            WHERE id = ?
        """
        params = (
            account.name, account.account_type, account.initial_balance, account.current_balance,
            account.credit_limit, account.payment_due_day, account.min_payment_percent,
            account.last_payment_date, account.is_active, account.is_system, account.currency,
            account.id
        )
        self.db.execute(query, params)
        return True
    
    def get_all_active(self) -> List[Account]:
        """
        Возвращает список всех активных счетов, отсортированных по имени.
        
        Returns:
            Список объектов Account
        """
        query = """
            SELECT * FROM accounts 
            WHERE is_active = 1 
            ORDER BY name
        """
        rows = self.db.fetchall(query)
        return [self._row_to_account(row) for row in rows]