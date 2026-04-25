# services/transaction_service.py
import logging
from typing import Tuple, Any, Dict
from core.db.repositories.transaction_repository import TransactionRepository
from core.db.repositories.account_repository import AccountRepository
from core.db.models import Transaction
from utils.validators import validate_transaction_amount, validate_required_fields
from utils.converters import safe_float, safe_int, safe_str

logger = logging.getLogger(__name__)

class TransactionService:
    def __init__(self, transaction_repo: TransactionRepository, account_repo: AccountRepository):
        self.repo = transaction_repo
        self.account_repo = account_repo

    def create_transaction(self, data: Dict[str, Any]) -> Tuple[bool, Any]:
        """
        Создает новую транзакцию.
        
        Args:
            data: Словарь из UI. 'amount' всегда положительный!
            
        Returns:
            (True, Transaction) или (False, ErrorMsg)
        """
        # 1. Валидация
        is_valid, error_msg = self._validate_data(data)
        if not is_valid:
            return False, error_msg

        try:
            # 2. Подготовка данных (простановка знака)
            prepared_data = self._prepare_data(data)
            
            # 3. Сохранение в БД
            tx_id = self.repo.create(prepared_data)
            
            # 4. Получаем полный объект транзакции
            new_tx = self.repo.get_by_id(tx_id)
            
            # 5. Обновляем баланс счета
            self._update_account_balance(new_tx)
            
            logger.info(f"Транзакция создана: ID {tx_id}, Тип {new_tx.trans_type}, Сумма {new_tx.amount}")
            return True, new_tx
            
        except Exception as e:
            logger.error(f"Ошибка создания транзакции: {e}")
            return False, str(e)

    def _validate_data(self, data: Dict) -> Tuple[bool, str]:
        required = ['date', 'amount', 'trans_type', 'account_id']
        is_valid, msg = validate_required_fields(data, required)
        if not is_valid:
            return False, msg
            
        amount = safe_float(data['amount'])
        is_valid, msg = validate_transaction_amount(amount) # Проверяет > 0
        if not is_valid:
            return False, msg
            
        return True, ""

    def _prepare_data(self, data: Dict) -> Dict:
        """Проставляет знак суммы в зависимости от типа."""
        prepared = {}
        prepared['date'] = safe_str(data['date'])
        prepared['description'] = safe_str(data.get('description', ''))
        prepared['account_id'] = safe_int(data['account_id'])
        prepared['category_id'] = safe_int(data.get('category_id'))
        prepared['quantity'] = safe_float(data.get('quantity', 1.0))
        
        raw_amount = safe_float(data['amount'])
        tx_type = safe_str(data['trans_type']).lower()
        
        # Логика знака: Доход (+), Расход (-)
        if tx_type == 'income':
            prepared['amount'] = abs(raw_amount)
            prepared['trans_type'] = 'income'
        elif tx_type == 'expense':
            prepared['amount'] = -abs(raw_amount)
            prepared['trans_type'] = 'expense'
        else:
            # Для возвратов и прочего оставляем как есть или обрабатываем отдельно
            prepared['amount'] = raw_amount
            prepared['trans_type'] = tx_type
            
        return prepared

    def _update_account_balance(self, tx: Transaction):
        """Обновляет баланс счета. Работает только с объектами."""
        account = self.account_repo.get_by_id(tx.account_id)
        if not account:
            raise ValueError(f"Счет {tx.account_id} не найден")
            
        # Просто прибавляем сумму транзакции к балансу
        # Так как расход уже отрицательный, баланс уменьшится сам собой
        account.current_balance += tx.amount
        
        self.account_repo.update(account.id, {'current_balance': account.current_balance})
        logger.debug(f"Баланс счета {account.id} обновлен: {account.current_balance}")