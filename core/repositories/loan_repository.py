# core/repositories/loan_repository.py
"""
Репозиторий для управления займами.
Отвечает за CRUD-операции с таблицей loans и получение истории платежей из transfers.
"""
from typing import List, Optional, Dict, Any
from core.models import Loan


class LoanRepository:
    """Репозиторий займов."""

    def __init__(self, db):
        """
        Инициализация репозитория.
        
        Args:
            db: экземпляр подключения к базе данных
        """
        self.db = db

    def get_all_with_details(self, filters: Optional[Dict[str, Any]] = None) -> List[dict]:
        """
        Возвращает список займов для отображения в UI.
        
        Args:
            filters: словарь с фильтрами (status, loan_type, contact_name)
            
        Returns:
            Список словарей с данными займов
        """
        query = """
            SELECT
                id, contact_name, loan_type as type, loan_amount, remaining,
                status, issue_date, due_date, description
            FROM loans
            WHERE 1=1
        """
        params = []

        if filters:
            if filters.get("status"):
                query += " AND status = ?"
                params.append(filters["status"])
            
            if filters.get("loan_type"):
                query += " AND loan_type = ?"
                params.append(filters["loan_type"])
                
            if filters.get("contact_name"):
                query += " AND contact_name LIKE ?"
                params.append(f"%{filters['contact_name']}%")

        query += " ORDER BY status, issue_date DESC"

        return self.db.fetchall(query, params)

    def get_by_id(self, loan_id: int) -> Optional[Loan]:
        """
        Возвращает объект займа по ID.
        
        Args:
            loan_id: ID займа
            
        Returns:
            Объект Loan или None
        """
        query = "SELECT * FROM loans WHERE id = ?"
        row = self.db.fetchone(query, (loan_id,))
        return self._row_to_loan(row) if row else None

    def create(self, loan: Loan) -> int:
        """
        Создает новую запись займа.
        
        Args:
            loan: объект Loan
            
        Returns:
            ID созданной записи
        """
        query = """
            INSERT INTO loans (
                contact_name, loan_type, loan_amount, remaining,
                status, issue_date, due_date, description,
                account_id, counterparty_account_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            loan.contact_name,
            loan.loan_type,
            loan.loan_amount,
            loan.remaining,
            loan.status,
            loan.issue_date,
            loan.due_date,
            loan.description,
            loan.account_id,                  
            loan.counterparty_account_id
        )
        new_id = self.db.execute(query, params)
        loan.id = new_id
        return new_id

    def update(self, loan: Loan) -> bool:
        """
        Обновляет данные займа (обычно остаток и статус).
        
        Args:
            loan: объект Loan с обновленными полями
            
        Returns:
            True если успешно
        """
        query = """
            UPDATE loans SET
                remaining = ?,
                status = ?,
                description = ?
            WHERE id = ?
        """
        params = (
            loan.remaining,
            loan.status,
            loan.description,
            loan.id
        )
        self.db.execute(query, params)
        return True

    def delete(self, loan_id: int) -> bool:
        """
        Удаляет заём по ID.
        
        Args:
            loan_id: ID удаляемого займа
            
        Returns:
            True если успешно
        """
        query = "DELETE FROM loans WHERE id = ?"
        self.db.execute(query, (loan_id,))
        return True

    def get_payments_history(self, loan_id: int) -> List[dict]:
        """
        Возвращает историю платежей по займу из таблицы transfers.
        Используется для диалога "Детали займа".
        
        Args:
            loan_id: ID займа
            
        Returns:
            Список словарей с историей платежей
        """
        query = """
            SELECT 
                t.id, t.date, t.amount, t.description,
                a.name as account_name
            FROM transfers t
            LEFT JOIN accounts a ON t.from_account_id = a.id
            WHERE t.loan_id = ? AND t.is_system = 1
            ORDER BY t.date DESC
        """
        return self.db.fetchall(query, (loan_id,))

    def _row_to_loan(self, row) -> Loan:
        """
        Преобразует строку БД в объект Loan.
        
        Args:
            row: строка с данными
            
        Returns:
            Объект Loan
        """
        return Loan(
            id=row["id"],
            contact_name=row["contact_name"],
            loan_type=row["loan_type"],
            loan_amount=row["loan_amount"],
            remaining=row["remaining"],
            status=row["status"],
            issue_date=row["issue_date"],
            due_date=row.get("due_date"),
            description=row.get("description")
        )