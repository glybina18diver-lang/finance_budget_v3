# services/loan_service.py
"""
Сервис управления займами.
Корректно обрабатывает движение денег через системные переводы.
"""
from typing import List, Optional, Dict
from datetime import datetime, date
from core.models import Loan, Transfer
from core.repositories.loan_repository import LoanRepository
from core.repositories.transfer_repository import TransferRepository
from core.repositories.account_repository import AccountRepository


class LoanService:
    """Сервис для работы с займами и платежами."""

    def __init__(self, loan_repo: LoanRepository, 
                 transfer_repo: TransferRepository,
                 account_repo: AccountRepository):
        self.loan_repo = loan_repo
        self.transfer_repo = transfer_repo
        self.account_repo = account_repo
    
    def get_all_loans(self, filters: Optional[dict] = None) -> List[dict]:
        """
        Возвращает список займов для отображения в UI.
        
        Args:
            filters: словарь с фильтрами (status, contact_name и т.д.)
            
        Returns:
            Список словарей с данными займов
        """
        return self.loan_repo.get_all_with_details(filters)
    
    def get_loan_by_id(self, loan_id: int) -> Optional[Dict]:
        """Возвращает данные займа для редактирования."""
        loan = self.loan_repo.get_by_id(loan_id)
        if not loan:
            return None
        return {
            "id": loan.id,
            "contact_name": loan.contact_name,
            "loan_type": loan.loan_type,
            "loan_amount": loan.loan_amount,
            "remaining": loan.remaining,
            "issue_date": loan.issue_date,
            "due_date": loan.due_date,
            "description": loan.description
        }

    def get_all_accounts_active(self):
        return self.account_repo.get_all_active()

    def create_loan(self, loan_data: dict) -> int:
        """
        Создаёт новый заём и автоматически формирует перевод выдачи/получения денег.
        
        Args:
            loan_data: {
                'contact_name': str,
                'loan_type': 'issued' | 'received',
                'loan_amount': float,
                'account_id': int,  # Мой счёт
                'issue_date': str,
                'due_date': str (опционально),
                'description': str (опционально)
            }
            
        Returns:
            ID созданного займа
        """
        # 1. Валидация
        if not loan_data.get("contact_name"):
            raise ValueError("Укажите контактное лицо")
        if loan_data.get("loan_amount", 0) <= 0:
            raise ValueError("Сумма займа должна быть положительной")
        if not loan_data.get("account_id"):
            raise ValueError("Выберите счёт для операции")

        # 2. Получаем объекты счетов
        my_account = self.account_repo.get_by_id(loan_data["account_id"])
        if not my_account:
            raise ValueError(f"Счёт с ID {loan_data['account_id']} не найден")
        
        # Создаём/находим счёт контрагента (возвращает объект Account)
        counterparty_acc = self.account_repo.get_or_create_counterparty(
            loan_data["contact_name"]
        )

        # 3. Определяем направление движения денег и обновляем балансы
        amount = loan_data["loan_amount"]
        issue_date = loan_data.get("issue_date", datetime.now().strftime("%Y-%m-%d"))
        
        if loan_data["loan_type"] == "issued":
            # Я дал деньги: мой счёт → счёт контрагента
            from_acc_id = my_account.id
            to_acc_id = counterparty_acc.id
            description = f"Выдача займа: {loan_data['contact_name'].strip()}"
            
            # Обновляем балансы в объектах
            my_account.current_balance -= amount
            counterparty_acc.current_balance += amount
            
        else:  # loan_type == "received"
            # Мне дали деньги: счёт контрагента → мой счёт
            from_acc_id = counterparty_acc.id
            to_acc_id = my_account.id
            description = f"Получение займа: {loan_data['contact_name'].strip()}"
            
            # Обновляем балансы в объектах
            counterparty_acc.current_balance -= amount
            my_account.current_balance += amount

        # 4. Сохраняем изменения балансов через репозиторий
        self.account_repo.update(my_account)
        self.account_repo.update(counterparty_acc)

        # 5. Создаём объект займа (с уже заполненным counterparty_account_id)
        loan = Loan(
            contact_name=loan_data["contact_name"].strip(),
            loan_type=loan_data["loan_type"],
            loan_amount=amount,
            remaining=amount,  # Изначально весь долг
            status="active",
            issue_date=issue_date,
            due_date=loan_data.get("due_date"),
            description=loan_data.get("description", ""),
            account_id=my_account.id,
            counterparty_account_id=counterparty_acc.id  # ← Заполняем сразу!
        )
        
        loan_id = self.loan_repo.create(loan)

        # 6. Создаём системный перевод
        transfer = Transfer(
            date=issue_date,
            amount=amount,
            type="external",
            from_account_id=from_acc_id,
            to_account_id=to_acc_id,
            description=description,
            is_system=True,
            loan_id=loan_id
        )
        self.transfer_repo.create(transfer)
        
        return loan_id
    
    def add_payment_to_loan(self, loan_id: int, payment_data: dict) -> bool:
        """
        Добавляет платёж по займу (частичное или полное погашение).
        
        Args:
            loan_id: ID займа
            payment_data: {
                'amount': float,
                'date': str,
                'account_id': int,  # Счёт, с которого/на который идёт платёж
                'description': str (опционально)
            }
            
        Returns:
            True если успешно
        """
        # 1. Получаем заём
        loan = self.loan_repo.get_by_id(loan_id)
        if not loan:
            raise ValueError("Заём не найден")
        
        amount = float(payment_data["amount"])
        if amount <= 0:
            raise ValueError("Сумма платежа должна быть больше нуля")
        
        # 2. Обновляем остаток долга
        loan.remaining -= amount
        
        # 3. Определяем направление платежа и обновляем балансы
        counterparty_acc = self.account_repo.get_by_id(loan.counterparty_account_id)
        my_account = self.account_repo.get_by_id(payment_data["account_id"])
        
        if not counterparty_acc or not my_account:
            raise ValueError("Ошибка получения счетов")
        
        if loan.loan_type == "issued":
            # Возврат займа: контрагент → мой счёт
            from_acc_id = counterparty_acc.id
            to_acc_id = my_account.id
            description = f"Возврат займа: {loan.contact_name}"
            
            self.account_repo.update_balance(counterparty_acc.id, -amount)
            self.account_repo.update_balance(my_account.id, +amount)
            
        else:  # received
            # Я возвращаю: мой счёт → контрагент
            from_acc_id = my_account.id
            to_acc_id = counterparty_acc.id
            description = f"Платёж по займу: {loan.contact_name}"
            
            self.account_repo.update_balance(my_account.id, -amount)
            self.account_repo.update_balance(counterparty_acc.id, +amount)
        
        # 4. Обновляем статус
        if loan.remaining <= 0:
            loan.remaining = 0
            loan.status = "paid"
        elif loan.due_date:
            due_date = datetime.strptime(loan.due_date, "%Y-%m-%d").date()
            if due_date < date.today() and loan.remaining > 0:
                loan.status = "default"
            else:
                loan.status = "active"
        else:
            loan.status = "active"
        
        # 5. Создаём системный перевод платежа
        transfer = Transfer(
            date=payment_data.get("date", datetime.now().strftime("%Y-%m-%d")),
            amount=amount,
            type="external",
            from_account_id=from_acc_id,
            to_account_id=to_acc_id,
            description=payment_data.get("description", description),
            is_system=True,
            loan_id=loan_id
        )
        
        # 6. Сохраняем всё
        self.loan_repo.update(loan)
        self.transfer_repo.create(transfer)
        
        return True

    def get_loan_payments(self, loan_id: int) -> List[Dict]:
        """Возвращает историю платежей по займу из таблицы transfers."""
        return self.loan_repo.get_payments_history(loan_id)

    def delete_loan_payment(self, loan_id: int, payment_id: int) -> bool:
        """
        Удаляет платёж по займу и пересчитывает остаток.
        
        Args:
            loan_id: ID займа
            payment_id: ID платежа (записи в transfers)
            
        Returns:
            True если успешно
        """
        # 1. Получаем платёж
        payment = self.transfer_repo.get_by_id(payment_id)
        if not payment or payment.loan_id != loan_id:
            raise ValueError("Платёж не найден")
        
        # 2. Получаем заём
        loan = self.loan_repo.get_by_id(loan_id)
        if not loan:
            raise ValueError("Заём не найден")
        
        # 3. Возвращаем остаток (увеличиваем долг обратно)
        loan.remaining += payment.amount
        
        # 4. Если статус был "paid", возвращаем в "active"
        if loan.status == "paid":
            loan.status = "active"
        
        # 5. Откатываем балансы счетов
        self.account_repo.update_balance(payment.from_account_id, payment.amount)
        self.account_repo.update_balance(payment.to_account_id, -payment.amount)
        
        # 6. Удаляем перевод
        self.transfer_repo.delete(payment_id)
        
        # 7. Сохраняем обновлённый заём
        self.loan_repo.update(loan)
        
        return True

    def delete_loan(self, loan_id: int) -> bool:
        """Удаляет заём (только если нет платежей)."""
        loan = self.loan_repo.get_by_id(loan_id)
        if not loan:
            raise ValueError("Заём не найден")
        
        # Проверяем, есть ли платежи
        payments = self.loan_repo.get_payments_history(loan_id)
        if payments:
            raise ValueError("Нельзя удалить заём с историей платежей. Сначала удалите платежи.")
        
        return self.loan_repo.delete(loan_id)
    
    def update_loan(self, loan_id: int, update_data: dict) -> bool:
        """
        Обновляет редактируемые поля займа.
        
        Args:
            loan_id: ID займа
            update_data: словарь с новыми данными (contact_name, due_date, description)
            
        Returns:
            True если успешно
        """
        loan = self.loan_repo.get_by_id(loan_id)
        if not loan:
            raise ValueError("Заём не найден")
        
        # Обновляем только те поля, которые пришли из UI
        if "contact_name" in update_data:
            loan.contact_name = update_data["contact_name"].strip()
        if "due_date" in update_data:
            loan.due_date = update_data["due_date"]
        if "description" in update_data:
            loan.description = update_data["description"].strip()
        
        # Пересчитываем статус (если изменилась дата погашения)
        if loan.due_date and loan.remaining > 0:
            from datetime import datetime, date
            due = datetime.strptime(loan.due_date, "%Y-%m-%d").date()
            if due < date.today():
                loan.status = "default"
            else:
                loan.status = "active"
        
        return self.loan_repo.update(loan)

    def update_overdue_loans(self) -> int:
        """
        Обновляет статусы просроченных займов на 'default'.
        
        Returns:
            Количество обновлённых займов
        """
        today = date.today()
        loans = self.loan_repo.get_all_with_details({"status": "active"})
        
        updated_count = 0
        for loan_dict in loans:
            if loan_dict.get("due_date"):
                due_date = datetime.strptime(loan_dict["due_date"], "%Y-%m-%d").date()
                if due_date < today and loan_dict["remaining"] > 0:
                    loan = self.loan_repo.get_by_id(loan_dict["id"])
                    if loan:
                        loan.status = "default"
                        self.loan_repo.update(loan)
                        updated_count += 1
        
        return updated_count
        