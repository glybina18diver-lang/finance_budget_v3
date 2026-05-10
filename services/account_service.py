# services/account_service.py
"""
Сервис управления счетами.
Инкапсулирует бизнес-логику: валидацию данных, CRUD-операции и проверку ограничений.
"""
from typing import Dict, Optional, List
from core.repositories.account_repository import AccountRepository
from core.models import Account


class AccountService:
    """Сервис для управления счетами: валидация, CRUD, бизнес-логика."""

    def __init__(self, acc_repo: AccountRepository):
        """
        Инициализация сервиса.
        
        Args:
            acc_repo: репозиторий для работы с БД
        """
        self.acc_repo = acc_repo

    def create_account(self, account_data: Dict) -> Account:
        """
        Создаёт новый счёт после валидации.
        
        Args:
            account_data: словарь с данными счёта
            
        Returns:
            Созданный объект Account
            
        Raises:
            ValueError: если данные некорректны
        """
        existing = self.acc_repo.get_by_name(account_data["name"])
        if existing:
            raise ValueError(f"Счёт с именем '{account_data['name']}' уже существует")
        
        self._validate_account_data(account_data)
        account = Account(**account_data)
        return self.acc_repo.create(account)

    def update_account(self, account_id: int, account_data: Dict) -> bool:
        """
        Обновляет существующий счёт.
        
        Args:
            account_id: ID обновляемого счёта
            account_data: словарь с новыми данными
            
        Returns:
            True если обновление успешно
            
        Raises:
            ValueError: если счёт не найден или данные некорректны
        """
        self._validate_account_data(account_data)
        account = self.acc_repo.get_by_id(account_id)
        if not account:
            raise ValueError("Счёт не найден")
            
        for key, value in account_data.items():
            if hasattr(account, key):
                setattr(account, key, value)
                
        return self.acc_repo.update(account)

    def delete_account(self, account_id: int) -> bool:
        """
        Удаляет счёт с проверкой на системность, баланс и связанные операции.
        
        Args:
            account_id: ID удаляемого счёта
            
        Returns:
            True если удаление успешно
            
        Raises:
            ValueError: если счёт не найден, системный, имеет ненулевой баланс или к нему привязаны операции
        """
        account = self.acc_repo.get_by_id(account_id)
        if not account:
            raise ValueError("Счёт не найден")
        if account.is_system:
            raise ValueError("Системные счета нельзя удалить")

        # Проверка на наличие связанных транзакций
        if self._has_transactions(account_id):
            raise ValueError("Невозможно удалить: у счёта есть связанные операции")
            
        return self.acc_repo.delete(account_id)

    def _has_transactions(self, account_id: int) -> bool:
        """
        Проверяет наличие транзакций, связанных со счётом.
        
        Returns:
            True если к счёту привязаны операции
        """
        query = "SELECT COUNT(*) AS cnt FROM transactions WHERE account_id = ?"
        result = self.acc_repo.db.fetchone(query, (account_id,))
        return result["cnt"] > 0 if result else False
    
    def _get_transaction_count(self, account_id: int) -> int:
        """
        Вспомогательный метод для получения количества операций по счёту.
        
        Args:
            account_id: ID счёта
            
        Returns:
            Количество связанных транзакций
        """
        query = "SELECT COUNT(*) AS cnt FROM transactions WHERE account_id = ?"
        result = self.acc_repo.db.fetchone(query, (account_id,))
        return result["cnt"] if result else 0

    def get_all_accounts(self) -> List[Account]:
        """
        Возвращает список всех активных счетов.
        
        Returns:
            Список объектов Account
        """
        return self.acc_repo.get_all_active()

    def get_account(self, account_id: int) -> Optional[Account]:
        """
        Возвращает счёт по ID.
        
        Args:
            account_id: ID счёта
            
        Returns:
            Объект Account или None
        """
        return self.acc_repo.get_by_id(account_id)

    def _validate_account_data(self, account_data: Dict) -> None:
        """
        Валидирует входящие данные счёта.
        
        Args:
            account_data: проверяемые данные
            
        Raises:
            ValueError: если валидация не пройдена
        """
        if not account_data.get("name", "").strip():
            raise ValueError("Название счёта не может быть пустым")
        if account_data.get("initial_balance", 0) < 0:
            raise ValueError("Начальный баланс не может быть отрицательным")
        if account_data.get("account_type") == "Credit Card":
            if not (1 <= account_data.get("payment_due_day", 0) <= 31):
                raise ValueError("День платежа должен быть от 1 до 31")