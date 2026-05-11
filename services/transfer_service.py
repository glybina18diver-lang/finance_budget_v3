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

    def get_all_accounts_active(self) -> List:
        """Возвращает активные счета для комбобоксов."""
        return self.account_repo.get_all_active()

    def _create_internal_transfer(self, data: dict) -> Transfer:
        """Логика внутреннего перевода (Счёт → Счёт)."""
        if data["from_account_id"] == data["to_account_id"]:
            raise ValueError("Счета не могут совпадать")
            
        # Снимаем с отправителя
        self.account_repo.update(data["from_account_id"], -data["amount"])
        # Начисляем получателю
        self.account_repo.update(data["to_account_id"], data["amount"])
        
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
        counterparty_name = data["counterparty"].strip().lower()
        
        # Получаем или создаём виртуальный счёт контрагента
        counterparty_id = self.account_repo.get_or_create_counterparty(counterparty_name)
        
        if data["direction"] == "incoming":
            # Контрагент → Наш счёт
            from_id = counterparty_id
            to_id = data["account_id"]
            self.account_repo.update(counterparty_id, -data["amount"])
            self.account_repo.update(data["account_id"], data["amount"])
        else:
            # Наш счёт → Контрагент
            from_id = data["account_id"]
            to_id = counterparty_id
            self.account_repo.update(data["account_id"], -data["amount"])
            self.account_repo.update(counterparty_id, data["amount"])
            
        transfer = Transfer(
            date=data["date"],
            amount=data["amount"],
            type="external",
            from_account_id=from_id,
            to_account_id=to_id,
            description=data.get("description")
        )
        return self.transfer_repo.create(transfer)

    def _reverse_balance_changes(self, tx: Transfer):
        """Откатывает изменение балансов при удалении перевода."""
        # Если перевод был внутренний
        if tx.type == "internal":
            self.account_repo.update(tx.from_account_id, tx.amount)  # Возвращаем деньги
            self.account_repo.update(tx.to_account_id, -tx.amount)   # Забираем обратно
        # Если внешний (логика аналогична, просто меняем знаки)
        else:
            self.account_repo.update(tx.from_account_id, tx.amount)
            self.account_repo.update(tx.to_account_id, -tx.amount)