import logging
from decimal import Decimal
from core.repositories.transaction_repository import TransactionRepository
from core.repositories.account_repository import AccountRepository
from core.repositories.credit_card_repository import CreditCardRepository
from core.models import Transaction, Account, Category
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from utils.validators import to_decimal

logger = logging.getLogger(__name__)

class MainWindowService:
    """Сервис Главного Окна"""

    def __init__(self, acc_repo: AccountRepository,
                 credit_card_repo: CreditCardRepository):
        """
        Инициализация сервиса.

        Args:
            acc_repo: репозиторий счетов для проверки и обновления баланса
        """
        self.acc_repo = acc_repo
        self.credit_card_repo = credit_card_repo

    def _load_accounts(self) -> List[Dict[str, Any]]:
            """
            Загружает список счетов.
    
            Returns:
                Список счетов в формате, пригодном для отображения в UI.
            """
            # Получаем все пользовательские счета
            accounts = self.acc_repo.get_user_accounts()
    
            # Разделяем счета по типам  
            regular_accounts: List[Account] = []
            credit_accounts: List[Account] = []

            for account in accounts:
                if account.account_type == "CreditCard":
                    credit_accounts.append(account)
                else:
                    regular_accounts.append(account)
    
            return regular_accounts, credit_accounts