# services/transfer_service.py
"""
Сервис переводов.
Инкапсулирует логику внутренних/внешних переводов, работу с контрагентами и балансами.
"""
from typing import List
from core.repositories.transfer_repository import TransferRepository
from core.repositories.account_repository import AccountRepository
from core.models import Transfer


class TransferService:
    """Сервис управления переводами."""

    def __init__(self, transfer_repo: TransferRepository, account_repo: AccountRepository):
        """
        Инициализация сервиса.
        
        Args:
            transfer_repo: репозиторий переводов
            account_repo: репозиторий счетов (нужен для внешних переводов)
        """
        self.transfer_repo = transfer_repo
        self.account_repo = account_repo

    def create_transfer(self, data: dict) -> Transfer:
        """
        Создаёт перевод, обрабатывая внутреннюю/внешнюю логику.
        
        Args:
            data: данные перевода (type: internal/external)
            
        Returns:
            Созданный объект Transfer
        """
        if data["type"] == "internal":
            return self._create_internal_transfer(data)
        else:
            return self._create_external_transfer(data)

    def delete_transfer(self, transfer_id: int) -> bool:
        """
        Удаляет перевод и возвращает балансы к исходному состоянию.
        
        Args:
            transfer_id: ID перевода
            
        Returns:
            True если успешно
        """
        # 1. Получаем перевод
        tx = self.transfer_repo.get_by_id(transfer_id)
        if not tx:
            raise ValueError("Перевод не найден")
            
        # 2. Откатываем балансы
        self._reverse_balance_changes(tx)
        
        # 3. Удаляем запись
        return self.transfer_repo.delete(transfer_id)

    def get_all_transfers(self) -> List[Transfer]:
        """Возвращает все переводы."""
        return self.transfer_repo.get_all()

    def get_transfers_with_names(self) -> List[Transfer]:
        """Возвращает переводы с именем а не ID."""
        return self.transfer_repo.get_all_with_details()

    def get_all_accounts_active(self) -> List:
        """Возвращает активные счета для комбобоксов."""
        return self.account_repo.get_all_active()

    def _create_internal_transfer(self, data: dict) -> Transfer:
        """Логика внутреннего перевода (Счёт → Счёт)."""
        if data["from_account_id"] == data["to_account_id"]:
            raise ValueError("Счета не могут совпадать")
        
        # Получаем объекты счетов
        from_account = self.account_repo.get_by_id(data["from_account_id"])
        to_account = self.account_repo.get_by_id(data["to_account_id"])
        
        if not from_account or not to_account:
            raise ValueError("Один из счетов не найден")
        
        # Обновляем балансы в объектах
        from_account.current_balance -= data["amount"]
        to_account.current_balance += data["amount"]
        
        # Сохраняем изменения через репозиторий
        self.account_repo.update(from_account)
        self.account_repo.update(to_account)
        
        # Создаём перевод
        transfer = Transfer(
            date=data["date"],
            amount=data["amount"],
            type="internal",
            from_account_id=data["from_account_id"],
            to_account_id=data["to_account_id"],
            description=data.get("description")
        )
        return self.transfer_repo.create(transfer)

    def _create_external_transfer(self, data: dict) -> Transfer:
        """Логика внешнего перевода (Счёт ↔ Контрагент)."""
        counterparty_name = data["counterparty"].strip()
        
        # Получаем объект Account контрагента (создает или находит)
        counterparty_account = self.account_repo.get_or_create_counterparty(counterparty_name)
        counterparty_id = counterparty_account.id  # ← Берем ID из объекта
        
        # Получаем объекты счетов пользователя
        if data["direction"] == "incoming":
            from_account = self.account_repo.get_by_id(counterparty_id)
            to_account = self.account_repo.get_by_id(data["account_id"])
        else:
            from_account = self.account_repo.get_by_id(data["account_id"])
            to_account = self.account_repo.get_by_id(counterparty_id)
            
        if not from_account or not to_account:
            raise ValueError("Ошибка при получении счетов для перевода")
        
        # Обновляем балансы
        from_account.current_balance -= data["amount"]
        to_account.current_balance += data["amount"]
        
        # Сохраняем изменения
        self.account_repo.update(from_account)
        self.account_repo.update(to_account)
        
        # Создаём перевод
        transfer = Transfer(
            date=data["date"],
            amount=data["amount"],
            type="external",
            from_account_id=from_account.id,
            to_account_id=to_account.id,
            description=data.get("description"),
            is_system=False,  # Пользовательский перевод
            loan_id=None
        )
        return self.transfer_repo.create(transfer)

    def _reverse_balance_changes(self, tx: Transfer):
        """
        Откатывает изменение балансов при удалении перевода.
        
        Args:
            tx: объект Transfer, который удаляется
        """
        # Получаем объекты счетов из БД по их ID
        from_account = self.account_repo.get_by_id(tx.from_account_id)
        to_account = self.account_repo.get_by_id(tx.to_account_id)
        
        if not from_account or not to_account:
            # Если счета уже удалены или не найдены, откат невозможен
            # В реальной системе можно логировать ошибку, но здесь просто выходим
            return

        # Логика отката: делаем обратное действие тому, что было при создании
        # При создании: From -= Amount, To += Amount
        # При удалении: From += Amount, To -= Amount
        
        from_account.current_balance += tx.amount
        to_account.current_balance -= tx.amount
        
        # Сохраняем изменения через репозиторий (передаем объекты)
        self.account_repo.update(from_account)
        self.account_repo.update(to_account)