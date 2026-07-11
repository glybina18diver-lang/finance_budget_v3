# services/account_service.py
"""
Сервис управления счетами.
Инкапсулирует бизнес-логику: валидацию данных, CRUD-операции и проверку ограничений.
"""
from typing import Dict, Optional, List
import logging
from core.repositories.account_repository import AccountRepository
from services.credit_card_service import CreditCardService
from core.models import Account

logger = logging.getLogger(__name__)


class AccountService:
    """Сервис для управления счетами: валидация, CRUD, бизнес-логика."""

    def __init__(self, acc_repo: AccountRepository, credit_card_service: CreditCardService = None):
        """
        Инициализация сервиса счетов.

        Args:
            acc_repo: репозиторий счетов
            credit_card_service: сервис кредитных карт (для проверки зависимостей)
        """
        self.acc_repo = acc_repo
        self.credit_card_service = credit_card_service

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
        try:
            existing = self.acc_repo.get_by_name(account_data["name"])
            if existing:
                raise ValueError(f"Счёт с именем '{account_data['name']}' уже существует")

            self._validate_account_data(account_data)
            account = Account(**account_data)
            return self.acc_repo.create(account)

        except ValueError as e:
            logger.warning(f"[AccountService] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[AccountService] Критическая ошибка при создании счёта: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
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

            # 4. Проверяем кредитные карты
            query = "SELECT account_type FROM accounts WHERE id = ?"
            result = self.acc_repo.db.fetchone(query, (account_id,))
            if result and result["account_type"] == "CreditCard":
                return True

            return False
        except Exception as e:
            logger.error(f"[AccountService] Ошибка проверки зависимостей счёта #{account_id}: {e}", exc_info=True)
            raise

    def _get_transaction_count(self, account_id: int) -> int:
        """
        Вспомогательный метод для получения количества операций по счёту.
        Проверяет все связанные таблицы: transactions, transfers, loans, credit_cards.

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

            # 4. Кредитные карты — УМНАЯ ПРОВЕРКА
            card_query = "SELECT id FROM credit_cards WHERE account_id = ?"
            card_row = self.acc_repo.db.fetchone(card_query, (account_id,))

            if card_row:
                card_id = card_row["id"]

                periods_q = "SELECT COUNT(*) AS cnt FROM credit_card_periods WHERE card_id = ?"
                payments_q = "SELECT COUNT(*) AS cnt FROM credit_card_payments WHERE card_id = ?"

                p_result = self.acc_repo.db.fetchone(periods_q, (card_id,))
                pay_result = self.acc_repo.db.fetchone(payments_q, (card_id,))

                card_ops = 0
                if p_result:
                    card_ops += p_result["cnt"]
                if pay_result:
                    card_ops += pay_result["cnt"]

                total_count += card_ops

            return total_count
        except Exception as e:
            logger.error(f"[AccountService] Ошибка подсчёта операций счёта #{account_id}: {e}", exc_info=True)
            raise

    def get_all_accounts(self) -> List[Account]:
        """
        Возвращает список всех активных счетов.

        Returns:
            Список объектов Account
        """
        try:
            return self.acc_repo.get_all_active()
        except Exception as e:
            logger.error(f"[AccountService] Ошибка загрузки счетов: {e}", exc_info=True)
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
        if account_data.get("initial_balance", 0) < 0:
            raise ValueError("Начальный баланс не может быть отрицательным")