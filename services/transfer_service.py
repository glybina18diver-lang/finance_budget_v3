# services/transfer_service.py
"""
Сервис переводов.
Инкапсулирует логику внутренних/внешних переводов, работу с контрагентами и балансами.
"""
from typing import List, Dict
from decimal import Decimal
import logging
from core.repositories.transfer_repository import TransferRepository
from core.repositories.account_repository import AccountRepository
from core.models import Transfer

logger = logging.getLogger(__name__)


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
        try:
            if data["type"] == "internal":
                transfer_in = self._create_internal_transfer(data)
                logger.debug(f"[{self.__class__.__name__}] ID создаваемого перевода = {transfer_in.id}")
                return transfer_in                
            else:
                transfer_ext = self._create_external_transfer(data)
                logger.debug(f"[{self.__class__.__name__}] ID создаваемого перевода = {transfer_ext.id}")
                return transfer_ext
        except ValueError as e:
            logger.warning(f"[TransferService] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[TransferService] Критическая ошибка при создании перевода: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise RuntimeError(f"Системная ошибка при создании перевода: {e}") from e

    def delete_transfer(self, transfer_id: int) -> bool:
        """
        Удаляет перевод и возвращает балансы к исходному состоянию.

        Args:
            transfer_id: ID перевода

        Returns:
            True если успешно
        """
        try:
            # 1. Получаем перевод
            tx = self.transfer_repo.get_by_id(transfer_id)
            if not tx:
                raise ValueError("Перевод не найден")

            # 2. Откатываем балансы
            self._reverse_balance_changes(tx)

            # 3. Удаляем запись
            return self.transfer_repo.delete(transfer_id)

        except ValueError as e:
            logger.warning(f"[TransferService] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[TransferService] Критическая ошибка при удалении перевода #{transfer_id}: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise RuntimeError(f"Системная ошибка при удалении перевода: {e}") from e

    def get_all_transfers_id(self) -> List[Transfer]:
        """Возвращает все переводы c ID."""
        try:
            return self.transfer_repo.get_all()
        except Exception as e:
            logger.error(f"[TransferService] Ошибка загрузки переводов: {e}", exc_info=True)
            raise

    def get_all_transfers(self) -> List[Transfer]:
        """
        Получает все пользовательские переводы через репозиторий.
        
        Returns:
            Список объектов Transfer
            
        Raises:
            RuntimeError: при ошибке получения данных
        """
        try:
            return self.transfer_repo.get_all_with_names()
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения переводов: {e}", exc_info=True)
            raise

    def get_transfers_with_filters(self, filters: Dict) -> List[Transfer]:
        """
        Получает отфильтрованные переводы через репозиторий.
        
        Args:
            filters: параметры фильтрации (date_from, date_to, search, account_id)
            
        Returns:
            Список объектов Transfer, удовлетворяющих фильтрам
            
        Raises:
            ValueError: при некорректных параметрах фильтра
            RuntimeError: при ошибке получения данных
        """
        try:
            return self.transfer_repo.get_filtered(filters)
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация фильтров: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения отфильтрованных переводов: {e}", exc_info=True)
            raise

    def get_all_accounts_active(self) -> List:
        """
        Возвращает активные счета для комбобоксов.

        Returns:
            Список объектов Account
        """
        try:
            return self.account_repo.get_user_accounts()
        except Exception as e:
            logger.error(f"[TransferService] Ошибка загрузки активных счетов: {e}", exc_info=True)
            raise

    def _create_internal_transfer(self, data: dict) -> Transfer:
        """
        Логика внутреннего перевода (Счёт → Счёт).

        Args:
            data: данные перевода

        Returns:
            Созданный объект Transfer
        """
        if data["from_account_id"] == data["to_account_id"]:
            raise ValueError("Счета не могут совпадать")

        # Получаем объекты счетов
        from_account = self.account_repo.get_by_id(data["from_account_id"])
        to_account = self.account_repo.get_by_id(data["to_account_id"])

        if not from_account or not to_account:
            raise ValueError("Один из счетов не найден")

        # Конвертируем amount в Decimal (из UI может прийти float)
        amount = Decimal(str(data["amount"]))

        # Обновляем балансы в объектах (Decimal арифметика)
        from_account.current_balance -= amount
        to_account.current_balance += amount

        # Сохраняем изменения через репозиторий
        self.account_repo.update(from_account)
        self.account_repo.update(to_account)

        # Создаём перевод
        transfer = Transfer(
            date=data["date"],
            amount=amount,
            type="internal",
            from_account_id=data["from_account_id"],
            to_account_id=data["to_account_id"],
            description=data.get("description")
        )
        return self.transfer_repo.create(transfer)

    def _create_external_transfer(self, data: dict) -> Transfer:
        """Логика внешнего перевода (Счёт ↔ Контрагент)."""
        counterparty_name = data["counterparty"].strip()

        # Конвертируем amount в Decimal
        amount = Decimal(str(data["amount"]))

        # Получаем объект Account контрагента (создает или находит)
        counterparty_account = self.account_repo.get_or_create_counterparty(counterparty_name)
        counterparty_id = counterparty_account.id

        # Получаем объекты счетов пользователя
        if data["direction"] == "incoming":
            from_account = self.account_repo.get_by_id(counterparty_id)
            to_account = self.account_repo.get_by_id(data["account_id"])
        else:
            from_account = self.account_repo.get_by_id(data["account_id"])
            to_account = self.account_repo.get_by_id(counterparty_id)

        if not from_account or not to_account:
            raise ValueError("Ошибка при получении счетов для перевода")

        # Обновляем балансы (Decimal арифметика)
        from_account.current_balance -= amount
        to_account.current_balance += amount

        # Сохраняем изменения
        self.account_repo.update(from_account)
        self.account_repo.update(to_account)

        # Создаём перевод
        transfer = Transfer(
            date=data["date"],
            amount=amount,
            type="external",
            from_account_id=from_account.id,
            to_account_id=to_account.id,
            description=data.get("description"),
            is_system=False,
            loan_id=None
        )
        return self.transfer_repo.create(transfer)

    def _reverse_balance_changes(self, tx: Transfer):
        """
        Откатывает изменение балансов при удалении перевода.

        Args:
            tx: объект Transfer, который удаляется
        """
        try:
            # Получаем объекты счетов из БД по их ID
            from_account = self.account_repo.get_by_id(tx.from_account_id)
            to_account = self.account_repo.get_by_id(tx.to_account_id)

            if not from_account or not to_account:
                # Если счета уже удалены или не найдены, откат невозможен
                logger.warning(f"[TransferService] Невозможно откатить балансы: счета не найдены "
                               f"(from={tx.from_account_id}, to={tx.to_account_id})")
                return

            # Логика отката: делаем обратное действие тому, что было при создании
            from_account.current_balance += tx.amount
            to_account.current_balance -= tx.amount

            # Сохраняем изменения через репозиторий (передаем объекты)
            self.account_repo.update(from_account)
            self.account_repo.update(to_account)

        except Exception as e:
            logger.error(f"[TransferService] Ошибка отката балансов при удалении перевода #{tx.id}: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise