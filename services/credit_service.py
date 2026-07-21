"""
Сервис для работы с банковскими кредитами.

Инкапсулирует бизнес-логику создания и погашения кредитов:
- Потребительский кредит: создание + перевод на целевой счёт
- POS-кредит: создание + расход на покупку
- Платёж по кредиту: перевод (тело) + опциональный расход (проценты)

Взаимодействует с:
- CreditRepository (CRUD кредитов)
- AccountRepository (создание системных счетов Credit)
- TransferService (переводы между счетами)
- TransactionService (расходы на покупку и проценты)
"""

import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal


from core.models import Loan, Account
from core.repositories.credit_repository import CreditRepository
from core.repositories.account_repository import AccountRepository
from services.transfer_service import TransferService
from services.transaction_service import TransactionService
from services.category_service import CategoryService
from utils.validators import to_decimal



logger = logging.getLogger(__name__)


class CreditService:
    """Сервис банковских кредитов."""

    def __init__(
        self,
        credit_repo: CreditRepository,
        account_repo: AccountRepository,
        transfer_service: TransferService,
        transaction_service: TransactionService,
        cat_service: CategoryService
    ):
        """
        Инициализация сервиса.

        Args:
            db: экземпляр фасада Database
            credit_repo: репозиторий банковских кредитов
            account_repo: репозиторий счетов
            transfer_service: сервис переводов между счетами
            transaction_service: сервис транзакций (доходы/расходы)
        """
        self.credit_repo = credit_repo
        self.account_repo = account_repo
        self.transfer_service = transfer_service
        self.transaction_service = transaction_service
        self.cat_service = cat_service

    def create_consumer_loan(
        self,
        name: str,
        loan_amount: Decimal,
        issue_date: str,
        target_account_id: int,
        interest_rate: float = 0.0,
        term_months: Optional[int] = None,
        due_date: Optional[str] = None,
        description: str = "",
    ) -> Loan:
        """
        Создаёт потребительский кредит с переводом денег на целевой счёт.

        Логика:
        1. Создаёт системный счёт типа 'Credit' (скрытый)
        2. Создаёт запись в loans с loan_purpose='consumer'
        3. Выполняет перевод со счёта кредита на целевой счёт пользователя

        Args:
            name: название кредита (например, "Кредит в Сбере на ремонт")
            loan_amount: сумма кредита
            issue_date: дата выдачи (YYYY-MM-DD)
            target_account_id: ID счёта, куда поступят деньги
            interest_rate: годовая ставка (опционально)
            term_months: срок в месяцах (опционально)
            due_date: дата окончания (опционально)
            description: описание кредита (опционально)

        Returns:
            Созданный объект Loan с присвоенным ID

        Raises:
            ValueError: если сумма <= 0 или целевой счёт не найден
            Exception: при ошибке базы данных или сервиса
        """
        try:
            if loan_amount <= 0:
                raise ValueError(f"Сумма кредита должна быть > 0, получено: {loan_amount}")

            target_account = self.account_repo.get_by_id(target_account_id)
            if target_account is None:
                raise ValueError(f"Целевой счёт #{target_account_id} не найден")

            loan_account = self.account_repo.get_or_create_credit_account(
                f"Кредит: {name}"
            )

            loan = Loan(
                name=name,
                source_type="bank",
                loan_type="received",
                loan_purpose="consumer",
                loan_amount=loan_amount,
                remaining=loan_amount,
                interest_rate=interest_rate,
                term_months=term_months,
                issue_date=issue_date,
                due_date=due_date,
                account_id=loan_account.id,
                counterparty_account_id=target_account_id,
                description=description,
                status="active",
            )

            created_loan = self.credit_repo.create(loan)

            tr_amount = float(loan_amount)
            data = {
                "from_account_id": loan_account.id,
                "to_account_id": target_account_id,
                "type": "internal",
                "amount": tr_amount,
                "date": issue_date,
                "description": (f"Получение кредита: {name}")
            }
            self.transfer_service.create_transfer(data)

            logger.info(
                f"[CreditService] Создан потребительский кредит "
                f"id={created_loan.id}, name='{name}', amount={loan_amount}"
            )
            return created_loan

        except ValueError as e:
            logger.warning(f"[CreditService] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[CreditService] Ошибка создания кредита: {e}", exc_info=True)
            raise

    def create_purchase_loan(
        self,
        name: str,
        loan_amount: Decimal,
        issue_date: str,
        category_id: int,
        purchase_description: str = "",
        interest_rate: float = 0.0,
        term_months: Optional[int] = None,
        due_date: Optional[str] = None,
        description: str = "",
    ) -> Loan:
        """
        Создаёт POS-кредит (кредит на покупку) с немедленным расходом.

        Логика:
        1. Создаёт системный счёт типа 'Credit' (скрытый)
        2. Создаёт запись в loans с loan_purpose='purchase'
        3. Создаёт транзакцию-расход со счёта кредита на указанную категорию
        4. Привязывает транзакцию к кредиту

        Args:
            name: название кредита (например, "Рассрочка на iPhone")
            loan_amount: сумма кредита (= сумма покупки)
            issue_date: дата выдачи/покупки (YYYY-MM-DD)
            category_id: ID категории расхода
            purchase_description: описание покупки
            interest_rate: годовая ставка (опционально)
            term_months: срок в месяцах (опционально)
            due_date: дата окончания (опционально)
            description: описание кредита (опционально)

        Returns:
            Созданный объект Loan с присвоенным ID

        Raises:
            ValueError: если сумма <= 0 или категория не найдена
            Exception: при ошибке базы данных или сервиса
        """
        try:
            if loan_amount <= 0:
                raise ValueError(f"Сумма кредита должна быть > 0, получено: {loan_amount}")

            loan_account = self.account_repo.get_or_create_credit_account(
                f"Кредит: {name}"
            )

            loan = Loan(
                name=name,
                source_type="bank",
                loan_type="received",
                loan_purpose="purchase",
                loan_amount=loan_amount,
                remaining=loan_amount,
                interest_rate=interest_rate,
                term_months=term_months,
                issue_date=issue_date,
                due_date=due_date,
                account_id=loan_account.id,
                description=description,
                status="active",
            )

            created_loan = self.credit_repo.create(loan)

            # ковиртирум перд созднием
            loan_amount_2 = str(loan_amount)
            transaction = self.transaction_service.create_transaction(
                account_id=loan_account.id,
                category_id=category_id,
                trans_type="expense",
                raw_amount=loan_amount_2,
                date_str=issue_date,
                description=purchase_description or f"Покупка в кредит: {name}",
            )

            self.credit_repo.update_purchase_transaction(
                created_loan.id, transaction.id
            )

            logger.info(
                f"[CreditService] Создан POS-кредит id={created_loan.id}, "
                f"name='{name}', amount={loan_amount}, "
                f"transaction_id={transaction.id}"
            )
            return created_loan

        except ValueError as e:
            logger.warning(f"[CreditService] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[CreditService] Ошибка создания POS-кредита: {e}", exc_info=True)
            raise

    def make_payment(
        self,
        loan_id: int,
        from_account_id: int,
        amount: Decimal,
        interest_amount: Decimal = 0.0,
        payment_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Вносит платёж по кредиту.

        Логика:
        1. Валидирует сумму (тело долга <= remaining)
        2. Создаёт перевод с обычного счёта на счёт кредита (тело долга)
        3. Если указаны проценты — создаёт расход в системной категории
        4. Уменьшает remaining в loans

        Args:
            loan_id: идентификатор кредита
            from_account_id: ID счёта, с которого списываются деньги
            amount: общая сумма платежа
            interest_amount: сумма процентов (по умолчанию 0.0)
            payment_date: дата платежа (YYYY-MM-DD, по умолчанию сегодня)

        Returns:
            Словарь с информацией о проведённых операциях:
            {
                'transfer_id': int,
                'transaction_id': int|None,
                'body_amount': float,
                'interest_amount': float,
                'new_remaining': float
            }

        Raises:
            ValueError: если кредит не найден, сумма некорректна или
                        тело долга превышает остаток
            Exception: при ошибке базы данных или сервиса
        """
        try:
            if amount <= 0:
                raise ValueError(f"Сумма платежа должна быть > 0, получено: {amount}")

            if interest_amount < 0:
                raise ValueError(
                    f"Сумма процентов не может быть отрицательной: {interest_amount}"
                )

            if interest_amount >= amount:
                raise ValueError(
                    f"Сумма процентов ({interest_amount}) должна быть меньше "
                    f"общей суммы платежа ({amount})"
                )

            loan = self.credit_repo.get_by_id(loan_id)
            if loan is None:
                raise ValueError(f"Кредит #{loan_id} не найден")

            if loan.status != "active":
                raise ValueError(
                    f"Кредит #{loan_id} не активен (статус: {loan.status})"
                )

            body_amount = round(amount - interest_amount, 2)

            if body_amount > loan.remaining:
                raise ValueError(
                    f"Сумма погашения тела ({body_amount}) превышает "
                    f"остаток долга ({loan.remaining})"
                )

            from_account = self.account_repo.get_by_id(from_account_id)
            if from_account is None:
                raise ValueError(f"Счёт #{from_account_id} не найден")

            loan_account = self.account_repo.get_by_id(loan.account_id)
            if loan_account is None:
                raise ValueError(f"Счёт кредита #{loan.account_id} не найден")

            data = {
                "from_account_id": from_account_id,
                "to_account_id": loan.account_id,
                "type": "internal",
                "amount": body_amount,
                "date": payment_date,
                "description": (f"Платёж по кредиту: {loan.name}")
            }
            transfer = self.transfer_service.create_transfer(data)

            transaction_id = None
            if interest_amount > 0:
                interest_category_id = self._get_interest_category_id()
                transaction = self.transaction_service.create_transaction(
                    account_id=from_account_id,
                    category_id=interest_category_id,
                    trans_type="expense",
                    row_amount=str(interest_amount),
                    date=str(payment_date),
                    description=f"Проценты по кредиту: {loan.name}",
                )
                transaction_id = transaction.id

            self.credit_repo.update_remaining(loan_id, -body_amount)
            new_remaining = round(loan.remaining - body_amount, 2)

            logger.info(
                f"[CreditService] Внесён платёж по кредиту #{loan_id}: "
                f"тело={body_amount}, проценты={interest_amount}, "
                f"остаток={new_remaining}"
            )

            return {
                "transfer_id": transfer.id,
                "transaction_id": transaction_id,
                "body_amount": body_amount,
                "interest_amount": interest_amount,
                "new_remaining": new_remaining,
            }

        except ValueError as e:
            logger.warning(f"[CreditService] Валидация платежа: {e}")
            raise
        except Exception as e:
            logger.error(f"[CreditService] Ошибка внесения платежа: {e}", exc_info=True)
            raise

    def _get_interest_category_id(self) -> int:
        """
        Возвращает ID системной категории 'Проценты по кредитам'.

        Не Создаёт категорию, если она не существует.

        Returns:
            ID системной категории процентов

        Raises:
            RuntimeError: если не удалось получить или создать категорию
        """
        try:
            category_name = "Проценты по кредитам"
            category = self.cat_service.get_category_by_name(category_name)
            
            cat_id = category.id
            return cat_id

        except Exception as e:
            logger.error(
                f"[CreditService] Ошибка получения категории процентов: {e}",
                exc_info=True,
            )
            raise RuntimeError(f"Не удалось получить системную категорию: {e}") from e

    def get_credit_details(self, loan_id: int) -> Optional[Dict[str, Any]]:
        """
        Возвращает расширенную информацию о кредите.

        Делегирует запрос в CreditRepository.get_loan_details().

        Args:
            loan_id: идентификатор кредита

        Returns:
            Словарь с расширенной информацией или None, если кредит не найден

        Raises:
            ValueError: если loan_id <= 0
            Exception: при ошибке базы данных
        """
        try:
            return self.credit_repo.get_loan_details(loan_id)
        except ValueError as e:
            logger.warning(f"[CreditService] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[CreditService] Ошибка получения деталей: {e}",
                exc_info=True,
            )
            raise

    def get_all_credits(self) -> List[Loan]:
        """
        Возвращает список всех банковских кредитов.

        Returns:
            Список объектов Loan (может быть пустым)

        Raises:
            Exception: при ошибке базы данных
        """
        try:
            return self.credit_repo.get_all()
        except Exception as e:
            logger.error(
                f"[CreditService] Ошибка получения списка кредитов: {e}",
                exc_info=True,
            )
            raise

    def get_active_credits(self) -> List[Loan]:
        """
        Возвращает список активных банковских кредитов.

        Returns:
            Список объектов Loan со статусом 'active'

        Raises:
            Exception: при ошибке базы данных
        """
        try:
            return self.credit_repo.get_active()
        except Exception as e:
            logger.error(
                f"[CreditService] Ошибка получения активных кредитов: {e}",
                exc_info=True,
            )
            raise

    def close_credit(self, loan_id: int) -> None:
        """
        Закрывает кредит (помечает как неактивный).

        Можно вызывать только для кредитов с remaining = 0.

        Args:
            loan_id: идентификатор кредита

        Raises:
            ValueError: если кредит не найден или остаток не равен 0
            Exception: при ошибке базы данных
        """
        try:
            loan = self.credit_repo.get_by_id(loan_id)
            if loan is None:
                raise ValueError(f"Кредит #{loan_id} не найден")

            if loan.remaining != 0:
                raise ValueError(
                    f"Нельзя закрыть кредит #{loan_id}: "
                    f"остаток долга = {loan.remaining}"
                )

            self.credit_repo.update(loan_id, {"status": "paid"})

            logger.info(f"[CreditService] Закрыт кредит #{loan_id}")

        except ValueError as e:
            logger.warning(f"[CreditService] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[CreditService] Ошибка закрытия кредита: {e}", exc_info=True)
            raise