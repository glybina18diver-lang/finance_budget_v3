# services/transaction_service.py
from core.repositories.transaction_repository import TransactionRepository
from core.repositories.account_repository import AccountRepository
from core.models import Transaction, Account
from typing import Tuple
import re

class TransactionService:
    """Сервис управления транзакциями: валидация, расчёты, обновление балансов."""

    def __init__(self, tx_repo: TransactionRepository, acc_repo: AccountRepository):
        """
        Инициализация сервиса.
        
        Args:
            tx_repo: репозиторий транзакций для CRUD-операций
            acc_repo: репозиторий счетов для проверки и обновления баланса
        """
        self.tx_repo = tx_repo
        self.acc_repo = acc_repo

    def create_transaction(self, raw_amount: str, trans_type: str, account_id: int, 
                           category_id: int, description: str, date_str: str) -> Transaction:
        """
        Создаёт транзакцию с парсингом суммы, валидацией и обновлением баланса счёта.
        
        Args:
            raw_amount: строка суммы из UI (например, "100*3" или "10,50")
            trans_type: тип операции ("income", "expense", "correct")
            account_id: ID счёта
            category_id: ID категории
            description: описание операции
            date_str: дата в формате YYYY-MM-DD
            
        Returns:
            Сохранённый объект Transaction с присвоенным ID
            
        Raises:
            ValueError: при некорректном формате суммы или данных
        """
        # 1. Парсинг суммы и количества
        amount_positive, quantity = self._parse_amount(raw_amount)
        
        # 2. Бизнес-валидация
        self._validate_inputs(trans_type, account_id, category_id, amount_positive)
        
        # 3. Применение знака по типу
        signed_amount = amount_positive if trans_type == "income" else -amount_positive
        
        # 4. Сборка объекта
        transaction = Transaction(
            date=date_str,
            amount=signed_amount,
            trans_type=trans_type,
            account_id=account_id,
            category_id=category_id,
            description=description.strip(),
            quantity=quantity
        )
        
        # 5. Сохранение в БД
        saved_tx = self.tx_repo.create(transaction)
        
        # 6. Обновление баланса счёта
        self._update_account_balance(account_id, signed_amount)
        
        return saved_tx
    
    def delete_transaction(self, tx_id: int) -> bool:
        """
        Удаляет транзакцию и коррекцией баланса счёта.
        
        Args:
            tx_id: ID транзакции для удаления
            
        Returns:
            True при успешном удалении
        """
        # Получаем транзакцию, чтобы вернуть баланс на место
        tx = self.tx_repo.get_by_id(tx_id)
        if not tx:
            raise ValueError(f"Транзакция #{tx_id} не найдена")
            
        # Удаляем запись
        self.tx_repo.delete(tx_id)
        
        # Возвращаем баланс: вычитаем сумму (т.к. она уже со знаком)
        self._update_account_balance(tx.account_id, -tx.amount)
        return True

    def _parse_amount(self, raw: str) -> Tuple[float, float]:
        """
        Разбирает строку суммы: поддерживает "100*3", "10,50", "1000".
        
        Args:
            raw: исходная строка из поля ввода
            
        Returns:
            Кортеж (общая_сумма, количество)
            
        Raises:
            ValueError: при недопустимом формате
        """
        normalized = raw.replace(",", ".").strip()
        
        # Формат "сумма*количество"
        if "*" in normalized:
            parts = normalized.split("*", maxsplit=1)
            if len(parts) != 2:
                raise ValueError("Некорректный формат умножения. Используйте: сумма*количество")
            unit_price = float(parts[0])
            quantity = float(parts[1])
            if quantity <= 0:
                raise ValueError("Количество должно быть больше 0")
            return round(unit_price * quantity, 2), quantity
            
        # Обычное число
        total = float(normalized)
        if total <= 0:
            raise ValueError("Сумма должна быть положительным числом")
        return total, 1.0

    def _validate_inputs(self, trans_type: str, account_id: int, category_id: int, amount: float):
        """
        Проверяет бизнес-правила перед сохранением транзакции.
        
        Args:
            trans_type: тип операции
            account_id: ID счёта
            category_id: ID категории
            amount: итоговая сумма операции
        """
        if trans_type not in ("income", "expense", "correct"):
            raise ValueError(f"Недопустимый тип транзакции: {trans_type}")
            
        if amount <= 0:
            raise ValueError("Сумма операции должна быть больше нуля")
            
        account = self.acc_repo.get_by_id(account_id)
        if not account:
            raise ValueError(f"Счёт #{account_id} не найден")
        if not account.is_active:
            raise ValueError(f"Счёт '{account.name}' деактивирован")
            
        # Корректировка может быть без категории, остальные требуют
        if trans_type != "correct" and not category_id:
            raise ValueError("Для доходов/расходов необходимо указать категорию")

    def _update_account_balance(self, account_id: int, amount: float):
        """
        Обновляет текущий баланс счёта на указанную сумму.
        
        Args:
            account_id: ID счёта для обновления
            amount: сумма с учётом знака (+ для дохода, - для расхода)
        """
        account = self.acc_repo.get_by_id(account_id)
        if account:
            account.current_balance = round(account.current_balance + amount, 2)
            self.acc_repo.update(account)