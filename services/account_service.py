# services/account_service.py
"""
Сервис управления счетами.
Инкапсулирует бизнес-логику: валидацию данных, CRUD-операции и проверку ограничений.
"""
from typing import Dict, Optional, List, Any
from decimal import Decimal
import logging
from core.repositories.account_repository import AccountRepository
from core.repositories.credit_card_repository import CreditCardRepository
from core.models import Account

logger = logging.getLogger(__name__)


class AccountService:
    """Сервис для управления счетами: валидация, CRUD, бизнес-логика."""

    def __init__(self, acc_repo: AccountRepository, card_repo: CreditCardRepository):
        """
        Инициализация сервиса счетов.

        Args:
            acc_repo: репозиторий счетов
            credit_card_service: сервис кредитных карт (для проверки зависимостей)
        """
        self.acc_repo = acc_repo
        self.card_repo = card_repo

    def create_account(self, account_data: Dict[str, Any]) -> Account:
        """
        Создаёт новый счёт после валидации.
        
        Для счёта типа CreditCard принудительно устанавливает
        initial_balance и current_balance в 0, независимо от переданных данных.
        
        Args:
            account_data: словарь с данными счёта. Для типа CreditCard может содержать
                дополнительный ключ 'credit_card_data' (словарь с параметрами карты)
                
        Returns:
            Созданный объект Account
            
        Raises:
            ValueError: если данные некорректны или счёт с таким именем уже существует
        """
        try:
            existing = self.acc_repo.get_by_name(account_data["name"])
            if existing:
                raise ValueError(f"Счёт с именем '{account_data['name']}' уже существует")

            self._validate_account_data(account_data)
            
            # Защита: для CreditCard баланс всегда 0
            if account_data.get("account_type") == "CreditCard":
                account_data["initial_balance"] = Decimal("0.00")
                account_data["current_balance"] = Decimal("0.00")
            
            # Извлекаем данные кредитной карты перед созданием может не быть если из presenter не передали
            credit_card_data = account_data.pop("credit_card_data", None)
            
            account = Account(**account_data)
            created_account = self.acc_repo.create(account)
            
            # Если тип CreditCard — создаём запись в credit_cards
            if account.account_type == "CreditCard":
                self._create_credit_card_record(created_account.id, credit_card_data)
            
            return created_account

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при создании счёта: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Критическая ошибка при создании счёта: {e}",
                exc_info=True
            )
            raise RuntimeError(f"Системная ошибка при создании счёта: {e}") from e

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
        try:
            self._validate_account_data(account_data)
            account = self.acc_repo.get_by_id(account_id)
            if not account:
                raise ValueError("Счёт не найден")

            for key, value in account_data.items():
                if hasattr(account, key):
                    setattr(account, key, value)

            return self.acc_repo.update(account)

        except ValueError as e:
            logger.warning(f"[AccountService] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[AccountService] Критическая ошибка при обновлении счёта #{account_id}: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise RuntimeError(f"Системная ошибка при обновлении счёта: {e}") from e

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
        try:
            account = self.acc_repo.get_by_id(account_id)
            if not account:
                raise ValueError("Счёт не найден")
            if account.is_system:
                raise ValueError("Системные счета нельзя удалить")

            # Проверка на наличие связанных транзакций
            if self._has_transactions(account_id):
                raise ValueError("Невозможно удалить: у счёта есть связанные операции")

            return self.acc_repo.delete(account_id)

        except ValueError as e:
            logger.warning(f"[AccountService] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[AccountService] Критическая ошибка при удалении счёта #{account_id}: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise RuntimeError(f"Системная ошибка при удалении счёта: {e}") from e

    def _has_transactions(self, account_id: int) -> bool:
        """
        Проверяет наличие зависимостей у счёта во всех связанных таблицах.

        Для счетов типа CreditCard всегда возвращает True,
        так как удаление должно происходить через диалог кредитных карт.

        Returns:
            True если к счёту привязаны операции или это кредитная карта
        """
        try:
            # 1. Проверяем транзакции (расходы/доходы)
            query = "SELECT COUNT(*) AS cnt FROM transactions WHERE account_id = ?"
            result = self.acc_repo.db.fetchone(query, (account_id,))
            if result and result["cnt"] > 0:
                return True

            # 2. Проверяем переводы (from_account_id и to_account_id)
            query = """
                SELECT COUNT(*) AS cnt FROM transfers 
                WHERE from_account_id = ? OR to_account_id = ?
            """
            result = self.acc_repo.db.fetchone(query, (account_id, account_id))
            if result and result["cnt"] > 0:
                return True

            # 3. Проверяем займы (account_id и counterparty_account_id)
            query = """
                SELECT COUNT(*) AS cnt FROM loans 
                WHERE account_id = ? OR counterparty_account_id = ?
            """
            result = self.acc_repo.db.fetchone(query, (account_id, account_id))
            if result and result["cnt"] > 0:
                return True

            return False
        except Exception as e:
            logger.error(f"[AccountService] Ошибка проверки зависимостей счёта #{account_id}: {e}", exc_info=True)
            raise
    
    def _get_transaction_count(self, account_id: int) -> int:
        """
        Вспомогательный метод для получения количества операций по счёту.
        Проверяет все связанные таблицы: transactions, transfers, loans.

        Для кредитных карт: считаются только карты с операциями (periods/payments).
        Пустые карты игнорируются, так как они удаляются вместе со счётом.

        Args:
            account_id: ID счёта

        Returns:
            Общее количество связанных операций
        """
        try:
            total_count = 0

            # 1. Транзакции (расходы/доходы)
            query = "SELECT COUNT(*) AS cnt FROM transactions WHERE account_id = ?"
            result = self.acc_repo.db.fetchone(query, (account_id,))
            if result:
                total_count += result["cnt"]

            # 2. Переводы (отправитель или получатель)
            query = """
                SELECT COUNT(*) AS cnt FROM transfers 
                WHERE from_account_id = ? OR to_account_id = ?
            """
            result = self.acc_repo.db.fetchone(query, (account_id, account_id))
            if result:
                total_count += result["cnt"]

            # 3. Займы (наш счёт или счёт контрагента)
            query = """
                SELECT COUNT(*) AS cnt FROM loans 
                WHERE account_id = ? OR counterparty_account_id = ?
            """
            result = self.acc_repo.db.fetchone(query, (account_id, account_id))
            if result:
                total_count += result["cnt"]

            return total_count
        except Exception as e:
            logger.error(f"[AccountService] Ошибка подсчёта операций счёта #{account_id}: {e}", exc_info=True)
            raise

    def _create_credit_card_record(
        self, 
        account_id: int, 
        credit_card_data: Optional[Dict[str, Any]]
    ):
        """
        Создаёт запись в таблице credit_cards для счёта типа CreditCard.
        
        Все параметры карты опциональны. Если данные не переданы, создаётся
        запись только с account_id (остальные поля будут NULL).
        
        Args:
            account_id: ID созданного счёта
            credit_card_data: словарь с параметрами карты (может быть None или пустым)
            
        Raises:
            ValueError: если не удалось создать запись
        """
        try:
            from core.models import CreditCard
            from decimal import Decimal
            
            # Подготавливаем данные, конвертируя строки в Decimal при необходимости
            card_kwargs = {"account_id": account_id}
            
            if credit_card_data:
                decimal_fields = ["credit_limit", "annual_rate", "min_payment_percent"]
                int_fields = ["grace_months", "payment_day", "statement_day"]
                
                for field in decimal_fields:
                    value = credit_card_data.get(field)
                    if value is not None and value != "":
                        card_kwargs[field] = Decimal(str(value))
                
                for field in int_fields:
                    value = credit_card_data.get(field)
                    if value is not None and value != "":
                        card_kwargs[field] = int(value)
            
            card = CreditCard(**card_kwargs)
            card_id = self.card_repo.create(card)
            
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация при создании записи карты: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка создания записи кредитной карты: {e}", 
                exc_info=True
            )
            raise

    def get_all_accounts(self) -> List[Account]:
        """
        Возвращает список всех счетов (не только активных).

        Returns:
            Список объектов Account
        """
        logger.debug(f"[AccountService] Получение всех счетов не реализовано")
        try:
            # self.acc_repo.get_all() # релизовать метод
            return 
        except Exception as e:
            logger.error(f"[AccountService] Ошибка загрузки счетов (метод 'get_all_accounts' не реализован): {e}", exc_info=True)
            raise

    def get_all_active_accounts(self) -> List[Account]:
        """
        Возвращает список всех активных счетов.

        Returns:
            Список объектов Account
        """
        try:
            self._all_active_accounts = self.acc_repo.get_all_active()
            return self._all_active_accounts
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка загрузки активных счетов: {e}", exc_info=True)
            raise
    
    def get_accounts_by_type(self, account_type: str) -> List[Account]:
        """
        Возвращает список активных счетов по типу.

        Args:
            account_type: тип счета

        Returns:
            Список объектов Account
        """
        try:
            # Гарантируем, что список счетов загружен
            if not hasattr(self, '_all_active_accounts'):
                self.get_all_active_accounts()
            
            # Фильтруем по типу
            filtered_accounts = [
                acc for acc in self._all_active_accounts 
                if acc.account_type == account_type
            ]
            return filtered_accounts
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка фильтрации счетов по типу {account_type}: {e}", exc_info=True)
            raise

    def get_user_accounts(self) -> List[Account]:
        """
        Возвращает список пользовательских счетов для UI

        Returns:
            Список объектов Account
        """
        try:
            return self.acc_repo.get_user_accounts()
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка загрузки пользовательских счетов: {e}", exc_info=True)
            raise

    def get_account(self, account_id: int) -> Optional[Account]:
        """
        Возвращает счёт по ID.

        Args:
            account_id: ID счёта

        Returns:
            Объект Account или None
        """
        try:
            return self.acc_repo.get_by_id(account_id)
        except Exception as e:
            logger.error(f"[AccountService] Ошибка загрузки счёта #{account_id}: {e}", exc_info=True)
            raise

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
        initial_balance = account_data.get("initial_balance", Decimal("0.00"))
        if isinstance(initial_balance, (int, float)):
            initial_balance = Decimal(str(initial_balance))
        if initial_balance < 0:
            raise ValueError("Начальный баланс не может быть отрицательным")