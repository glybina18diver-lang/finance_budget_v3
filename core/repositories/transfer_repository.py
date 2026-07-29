"""
Репозиторий для работы с переводами в базе данных.
Инкапсулирует CRUD-операции и маппинг данных.
"""
import logging
from datetime import datetime
from typing import List, Optional, Dict
from decimal import Decimal
from core.models import Transfer
from utils.validators import to_decimal

logger = logging.getLogger(__name__)


class TransferRepository:
    """Репозиторий управления переводами между счетами."""

    def __init__(self, db):
        """
        Инициализация репозитория.

        Args:
            db: экземпляр подключения к базе данных
        """
        self.db = db

    def _row_to_transfer(self, row: Dict) -> Transfer:
        """
        Преобразует словарь данных из БД в объект Transfer.
        Динамически добавляет имена счетов и контрагента, если они есть в словаре.
        
        Args:
            row: словарь с данными перевода из репозитория
            
        Returns:
            Объект Transfer с заполненными полями
            
        Raises:
            ValueError: при некорректных данных в словаре
            RuntimeError: при непредвиденной ошибке маппинга
        """
        try:
            transfer = Transfer(
                id=row.get('id'),
                date=str(row.get('date', '')),
                amount=Decimal(str(row.get('amount', 0))),
                type=row.get('type', 'internal'),
                from_account_id=row.get('from_account_id', 0),
                to_account_id=row.get('to_account_id', 0),
                description=row.get('description'),
                is_system=bool(row.get('is_system', 0)),
                loan_id=row.get('loan_id')
            )
            
            # Динамически добавляем поля для отображения (их нет в базовой модели)
            if 'from_account_name' in row:
                setattr(transfer, 'from_account_name', row['from_account_name'])
            if 'to_account_name' in row:
                setattr(transfer, 'to_account_name', row['to_account_name'])
            if 'counterparty_name' in row:
                setattr(transfer, 'counterparty', row['counterparty_name'])
                
            return transfer
            
        except (ValueError, TypeError, KeyError) as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: Ошибка маппинга строки перевода: {e}")
            raise ValueError(f"Некорректные данные перевода: {e}") from e
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка маппинга строки перевода: {e}", exc_info=True)
            raise RuntimeError("Не удалось преобразовать данные перевода") from e

    def get_by_id(self, transfer_id: int) -> Optional[Transfer]:
        """
        Возвращает перевод по ID.

        Args:
            transfer_id: ID искомого перевода

        Returns:
            Объект Transfer или None, если не найден
        """
        try:
            query = "SELECT * FROM transfers WHERE id = ?"
            row = self.db.fetchone(query, (transfer_id,))
            return self._row_to_transfer(row) if row else None
        except Exception as e:
            logger.error("[TransferRepository] Ошибка при получении перевода по ID %s: %s", transfer_id, e, exc_info=True)
            raise

    def get_all(self) -> List[Transfer]:
        """
        Возвращает ID вместо имен
        Возвращает все переводы, отсортированные по дате (новые сверху).

        Returns:
            Список объектов Transfer
        """
        try:
            query = "SELECT * FROM transfers ORDER BY date DESC"
            rows = self.db.fetchall(query)
            return [self._row_to_transfer(row) for row in rows]
        except Exception as e:
            logger.error("[TransferRepository] Ошибка при получении списка переводов: %s", e, exc_info=True)
            raise

    def get_all_with_names(self) -> List[Transfer]:
        """
        Возвращает все пользовательские переводы с именами счетов и контрагентов.
        
        Returns:
            Список объектов Transfer (без системных записей)
            
        Raises:
            RuntimeError: при ошибке работы с БД
        """
        try:
            query = """
                SELECT
                    t.id, t.date, t.amount, t.type, t.description, t.is_system,
                    a1.name AS from_account_name,
                    a2.name AS to_account_name,
                    CASE
                        WHEN t.type = 'external' AND a1.account_type = 'Counterparty' THEN a1.name
                        WHEN t.type = 'external' AND a2.account_type = 'Counterparty' THEN a2.name
                        ELSE ''
                    END AS counterparty_name
                FROM transfers t
                LEFT JOIN accounts a1 ON t.from_account_id = a1.id
                LEFT JOIN accounts a2 ON t.to_account_id = a2.id
                WHERE t.is_system = 0
                ORDER BY t.date DESC
            """
            rows = self.db.fetchall(query)
            return [self._row_to_transfer(row) for row in rows]
            
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения переводов: {e}", exc_info=True)
            raise RuntimeError("Не удалось получить список переводов") from e


    def get_filtered(self, filters: Dict) -> List[Transfer]:
        """
        Возвращает отфильтрованные переводы с именами счетов и контрагентов.
        
        Args:
            filters: параметры фильтрации:
                - date_from: дата начала периода (YYYY-MM-DD)
                - date_to: дата окончания периода (YYYY-MM-DD)
                - search: поисковый запрос по описанию/контрагенту/именам счетов
                - account_id: ID счёта для фильтрации (from или to)
                
        Returns:
            Список объектов Transfer, удовлетворяющих фильтрам
            
        Raises:
            ValueError: при некорректных параметрах фильтра
            RuntimeError: при ошибке работы с БД
        """
        try:
            if not filters:
                raise ValueError("Параметры фильтра обязательны")
            
            query = """
                SELECT
                    t.id, t.date, t.amount, t.type, t.description, t.is_system,
                    a1.name AS from_account_name,
                    a2.name AS to_account_name,
                    CASE
                        WHEN t.type = 'external' AND a1.account_type = 'Counterparty' THEN a1.name
                        WHEN t.type = 'external' AND a2.account_type = 'Counterparty' THEN a2.name
                        ELSE ''
                    END AS counterparty_name
                FROM transfers t
                LEFT JOIN accounts a1 ON t.from_account_id = a1.id
                LEFT JOIN accounts a2 ON t.to_account_id = a2.id
                WHERE t.is_system = 0
            """
            params = []
            
            if filters.get('date_from'):
                query += " AND t.date >= ?"
                params.append(filters['date_from'])
            
            if filters.get('date_to'):
                query += " AND t.date <= ?"
                params.append(filters['date_to'])
            
            if filters.get('search'):
                search_pattern = f"%{filters['search']}%"
                query += " AND (t.description LIKE ? OR a1.name LIKE ? OR a2.name LIKE ?)"
                params.extend([search_pattern, search_pattern, search_pattern])
            
            if filters.get('account_id'):
                query += " AND (t.from_account_id = ? OR t.to_account_id = ?)"
                params.extend([filters['account_id'], filters['account_id']])
            
            query += " ORDER BY t.date DESC"
            
            rows = self.db.fetchall(query, params) if params else self.db.fetchall(query)
            return [self._row_to_transfer(row) for row in rows]
            
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация фильтров: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения отфильтрованных переводов: {e}", exc_info=True)
            raise RuntimeError("Не удалось получить отфильтрованный список переводов") from e

    def create(self, transfer: Transfer) -> int:
        try:
            query = """
                INSERT INTO transfers (
                    date, amount, type,
                    from_account_id, to_account_id,
                    description, is_system, loan_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                transfer.date,
                float(transfer.amount),
                transfer.type,
                transfer.from_account_id,
                transfer.to_account_id,
                transfer.description,
                1 if transfer.is_system else 0,
                transfer.loan_id
            )
            transfer.id = self.db.execute(query, params)
            return transfer
        except Exception as e:
            logger.error("[TransferRepository] Ошибка при создании перевода: %s", e, exc_info=True)
            raise

    def delete(self, transfer_id: int) -> bool:
        """
        Удаляет перевод по ID.

        Args:
            transfer_id: ID удаляемого перевода

        Returns:
            True если операция прошла успешно
        """
        try:
            query = "DELETE FROM transfers WHERE id = ?"
            self.db.execute(query, (transfer_id,))
            return True
        except Exception as e:
            logger.error("[TransferRepository] Ошибка при удалении перевода ID %s: %s", transfer_id, e, exc_info=True)
            raise