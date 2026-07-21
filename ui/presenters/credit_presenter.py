"""
Презентер для работы с банковскими кредитами.

Отвечает за:
- Валидацию входных данных из UI
- Конвертацию типов (str → Decimal, str → int)
- Делегирование бизнес-логики в CreditService
- Возврат данных в читаемом виде для UI

Не содержит бизнес-логики и прямых обращений к БД.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


from services.credit_service import CreditService
from core.repositories.account_repository import AccountRepository
from services.category_service import CategoryService
from utils.validators import parse_float, parse_int
from utils.validators import to_decimal


logger = logging.getLogger(__name__)


class CreditPresenter:
    """Презентер банковских кредитов."""

    def __init__(
        self,
        credit_service: CreditService,
        account_repo: AccountRepository,
        cat_service: CategoryService
    ):
        """
        Инициализация презентера.

        Args:
            credit_service: сервис банковских кредитов
            account_repo: репозиторий счетов (для получения списка целевых счетов)
            cat_service: сервис категорий
        """
        self.credit_service = credit_service
        self.account_repo = account_repo
        self.cat_service = cat_service

    def create_consumer_loan(
        self,
        name: str,
        loan_amount_str: str,
        issue_date_str: str,
        target_account_id: int,
        interest_rate_str: str = "0",
        term_months_str: str = "",
        due_date_str: str = "",
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Создаёт потребительский кредит после валидации входных данных.

        Args:
            name: название кредита
            loan_amount_str: сумма кредита (строка из UI)
            issue_date_str: дата выдачи в формате YYYY-MM-DD
            target_account_id: ID целевого счёта
            interest_rate_str: годовая ставка (опционально)
            term_months_str: срок в месяцах (опционально)
            due_date_str: дата окончания (опционально)
            description: описание кредита (опционально)

        Returns:
            Словарь с информацией о созданном кредите:
            {
                'loan_id': int,
                'name': str,
                'amount': Decimal,
                'target_account_id': int
            }

        Raises:
            ValueError: если входные данные некорректны
            Exception: при системной ошибке
        """
        try:
            self._validate_name(name)
            loan_amount = self._parse_positive_decimal(loan_amount_str, "Сумма кредита")
            issue_date = self._validate_date(issue_date_str, "Дата выдачи")
            self._validate_account_id(target_account_id)

            interest_rate = self._parse_non_negative_decimal(
                interest_rate_str, "Процентная ставка", default=0.0
            )
            term_months = self._parse_optional_positive_int(
                term_months_str, "Срок кредита"
            )
            due_date = self._validate_optional_date(due_date_str, "Дата окончания")


            loan = self.credit_service.create_consumer_loan(
                name=name.strip(),
                loan_amount=loan_amount,
                issue_date=issue_date,
                target_account_id=target_account_id,
                interest_rate=interest_rate,
                term_months=term_months,
                due_date=due_date,
                description=description.strip(),
            )

            logger.info(
                f"[CreditPresenter] Создан потребительский кредит "
                f"id={loan.id}, name='{loan.name}'"
            )

            return {
                "loan_id": loan.id,
                "name": loan.name,
                "amount": loan.loan_amount,
                "target_account_id": target_account_id,
            }

        except ValueError as e:
            logger.warning(f"[CreditPresenter] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[CreditPresenter] Ошибка создания кредита: {e}",
                exc_info=True,
            )
            raise

    def create_purchase_loan(
        self,
        name: str,
        loan_amount_str: str,
        issue_date_str: str,
        category_id: int,
        purchase_description: str = "",
        interest_rate_str: str = "0",
        term_months_str: str = "",
        due_date_str: str = "",
        description: str = "",
    ) -> Dict[str, Any]:
        """
        Создаёт POS-кредит (кредит на покупку) после валидации входных данных.

        Args:
            name: название кредита
            loan_amount_str: сумма кредита (строка из UI)
            issue_date_str: дата выдачи/покупки в формате YYYY-MM-DD
            category_id: ID категории расхода
            purchase_description: описание покупки
            interest_rate_str: годовая ставка (опционально)
            term_months_str: срок в месяцах (опционально)
            due_date_str: дата окончания (опционально)
            description: описание кредита (опционально)

        Returns:
            Словарь с информацией о созданном кредите:
            {
                'loan_id': int,
                'name': str,
                'amount': Decimal,
                'category_id': int
            }

        Raises:
            ValueError: если входные данные некорректны
            Exception: при системной ошибке
        """
        try:
            self._validate_name(name)
            loan_amount = self._parse_positive_decimal(loan_amount_str, "Сумма кредита")
            issue_date = self._validate_date(issue_date_str, "Дата покупки")

            if category_id is None or category_id <= 0:
                raise ValueError("Не выбрана категория покупки")

            interest_rate = self._parse_non_negative_decimal(
                interest_rate_str, "Процентная ставка", default=0.0
            )
            term_months = self._parse_optional_positive_int(
                term_months_str, "Срок кредита"
            )
            due_date = self._validate_optional_date(due_date_str, "Дата окончания")

            loan = self.credit_service.create_purchase_loan(
                name=name.strip(),
                loan_amount=loan_amount,
                issue_date=issue_date,
                category_id=category_id,
                purchase_description=purchase_description.strip(),
                interest_rate=interest_rate,
                term_months=term_months,
                due_date=due_date,
                description=description.strip(),
            )

            logger.info(
                f"[CreditPresenter] Создан POS-кредит id={loan.id}, "
                f"name='{loan.name}', category_id={category_id}"
            )

            return {
                "loan_id": loan.id,
                "name": loan.name,
                "amount": loan.loan_amount,
                "category_id": category_id,
            }

        except ValueError as e:
            logger.warning(f"[CreditPresenter] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[CreditPresenter] Ошибка создания POS-кредита: {e}",
                exc_info=True,
            )
            raise

    def make_payment(
        self,
        loan_id: int,
        from_account_id: int,
        amount_str: str,
        interest_amount_str: str = "0",
        payment_date_str: str = "",
    ) -> Dict[str, Any]:
        """
        Вносит платёж по кредиту после валидации входных данных.

        Args:
            loan_id: идентификатор кредита
            from_account_id: ID счёта, с которого списываются деньги
            amount_str: общая сумма платежа (строка из UI)
            interest_amount_str: сумма процентов (опционально)
            payment_date_str: дата платежа в формате YYYY-MM-DD
                              (по умолчанию — сегодня)

        Returns:
            Словарь с информацией о проведённых операциях:
            {
                'transfer_id': int,
                'transaction_id': int|None,
                'body_amount': Decimal,
                'interest_amount': Decimal,
                'new_remaining': Decimal
            }

        Raises:
            ValueError: если входные данные некорректны
            Exception: при системной ошибке
        """
        try:
            if loan_id is None or loan_id <= 0:
                raise ValueError("Некорректный идентификатор кредита")

            self._validate_account_id(from_account_id)
            amount = self._parse_positive_decimal(amount_str, "Сумма платежа")
            interest_amount = self._parse_non_negative_decimal(
                interest_amount_str, "Сумма процентов", default=0.0
            )

            if interest_amount >= amount:
                raise ValueError(
                    f"Сумма процентов ({interest_amount}) должна быть меньше "
                    f"общей суммы платежа ({amount})"
                )

            payment_date = self._validate_optional_date(
                payment_date_str, "Дата платежа"
            ) or datetime.now().strftime("%Y-%m-%d")

            result = self.credit_service.make_payment(
                loan_id=loan_id,
                from_account_id=from_account_id,
                amount=amount,
                interest_amount=interest_amount,
                payment_date=payment_date,
            )

            logger.info(
                f"[CreditPresenter] Внесён платёж по кредиту #{loan_id}: "
                f"тело={result['body_amount']}, "
                f"проценты={result['interest_amount']}"
            )

            return result

        except ValueError as e:
            logger.warning(f"[CreditPresenter] Валидация платежа: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[CreditPresenter] Ошибка внесения платежа: {e}",
                exc_info=True,
            )
            raise

    def get_all_credits(self) -> List[Dict[str, Any]]:
        """
        Возвращает список всех банковских кредитов в формате для UI.

        Returns:
            Список словарей с информацией о кредитах:
            [
                {
                    'id': int,
                    'name': str,
                    'loan_purpose': str,
                    'loan_amount': Decimal,
                    'remaining': Decimal,
                    'status': str,
                    'issue_date': str,
                    'due_date': str|None
                },
                ...
            ]

        Raises:
            Exception: при системной ошибке
        """
        try:
            loans = self.credit_service.get_all_credits()

            result = []
            for loan in loans:
                result.append({
                    "id": loan.id,
                    "name": loan.name,
                    "loan_purpose": loan.loan_purpose,
                    "loan_amount": loan.loan_amount,
                    "remaining": loan.remaining,
                    "status": loan.status,
                    "issue_date": loan.issue_date,
                    "due_date": loan.due_date,
                })

            return result

        except Exception as e:
            logger.error(
                f"[CreditPresenter] Ошибка получения списка кредитов: {e}",
                exc_info=True,
            )
            raise

    def get_user_categories(self) -> List[Dict[str, Any]]:
        """
        Возвращает список пользовательских категорий для UI типа Расход.
        
        Returns:
            Список словарей:
            [{'id': int, 'name': str}, ...]
        """
        cat_type = "expense"
        return self.cat_service.get_all_by_type(cat_type)

    def get_active_credits(self) -> List[Dict[str, Any]]:
        """
        Возвращает список активных банковских кредитов в формате для UI.

        Returns:
            Список словарей с информацией об активных кредитах

        Raises:
            Exception: при системной ошибке
        """
        try:
            loans = self.credit_service.get_active_credits()

            result = []
            for loan in loans:
                result.append({
                    "id": loan.id,
                    "name": loan.name,
                    "loan_purpose": loan.loan_purpose,
                    "loan_amount": loan.loan_amount,
                    "remaining": loan.remaining,
                    "status": loan.status,
                    "issue_date": loan.issue_date,
                    "due_date": loan.due_date,
                })

            return result

        except Exception as e:
            logger.error(
                f"[CreditPresenter] Ошибка получения активных кредитов: {e}",
                exc_info=True,
            )
            raise

    def get_credit_details(self, loan_id: int) -> Optional[Dict[str, Any]]:
        """
        Возвращает расширенную информацию о кредите.

        Args:
            loan_id: идентификатор кредита

        Returns:
            Словарь с расширенной информацией или None, если кредит не найден

        Raises:
            ValueError: если loan_id некорректен
            Exception: при системной ошибке
        """
        try:
            if loan_id is None or loan_id <= 0:
                raise ValueError("Некорректный идентификатор кредита")

            return self.credit_service.get_credit_details(loan_id)

        except ValueError as e:
            logger.warning(f"[CreditPresenter] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[CreditPresenter] Ошибка получения деталей кредита: {e}",
                exc_info=True,
            )
            raise

    def close_credit(self, loan_id: int) -> None:
        """
        Закрывает кредит (помечает как неактивный).

        Args:
            loan_id: идентификатор кредита

        Raises:
            ValueError: если loan_id некорректен или остаток не равен 0
            Exception: при системной ошибке
        """
        try:
            if loan_id is None or loan_id <= 0:
                raise ValueError("Некорректный идентификатор кредита")

            self.credit_service.close_credit(loan_id)
            logger.info(f"[CreditPresenter] Закрыт кредит #{loan_id}")

        except ValueError as e:
            logger.warning(f"[CreditPresenter] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[CreditPresenter] Ошибка закрытия кредита: {e}",
                exc_info=True,
            )
            raise

    def get_user_accounts(self) -> List[Dict[str, Any]]:
        """
        Возвращает список пользовательских счетов для UI.

        Исключает системные счета (Counterparty, Credit).

        Returns:
            Список словарей:
            [
                {'id': int, 'name': str, 'account_type': str},
                ...
            ]

        Raises:
            Exception: при системной ошибке
        """
        try:
            accounts = self.account_repo.get_user_accounts()

            return [
                {
                    "id": acc.id,
                    "name": acc.name,
                    "account_type": acc.account_type,
                }
                for acc in accounts
            ]

        except Exception as e:
            logger.error(
                f"[CreditPresenter] Ошибка получения счетов: {e}",
                exc_info=True,
            )
            raise

    # ------------------------------------------------------------------ #
    #                    Приватные методы валидации                      #
    # ------------------------------------------------------------------ #

    def _validate_name(self, name: str) -> None:
        """
        Проверяет, что название кредита не пустое.

        Args:
            name: название для проверки

        Raises:
            ValueError: если название пустое
        """
        if not name or not name.strip():
            raise ValueError("Название кредита не может быть пустым")

    def _validate_account_id(self, account_id: int) -> None:
        """
        Проверяет, что ID счёта корректен и счёт существует.

        Args:
            account_id: ID счёта для проверки

        Raises:
            ValueError: если ID некорректен или счёт не найден
        """
        if account_id is None or account_id <= 0:
            raise ValueError("Некорректный идентификатор счёта")

        account = self.account_repo.get_by_id(account_id)
        if account is None:
            raise ValueError(f"Счёт #{account_id} не найден")

    def _validate_date(self, date_str: str, field_name: str) -> str:
        """
        Проверяет, что дата в формате YYYY-MM-DD и не пустая.

        Args:
            date_str: строка с датой
            field_name: название поля для сообщения об ошибке

        Returns:
            Нормализованная строка даты

        Raises:
            ValueError: если дата некорректна
        """
        if not date_str or not date_str.strip():
            raise ValueError(f"{field_name} не может быть пустой")

        try:
            datetime.strptime(date_str.strip(), "%Y-%m-%d")
            return date_str.strip()
        except ValueError:
            raise ValueError(
                f"{field_name} должна быть в формате YYYY-MM-DD"
            )

    def _validate_optional_date(
        self, date_str: str, field_name: str
    ) -> Optional[str]:
        """
        Проверяет дату, если она указана. Пустая строка допустима.

        Args:
            date_str: строка с датой
            field_name: название поля для сообщения об ошибке

        Returns:
            Нормализованная строка даты или None, если пустая

        Raises:
            ValueError: если дата указана в неверном формате
        """
        if not date_str or not date_str.strip():
            return None
        return self._validate_date(date_str, field_name)

    def _parse_positive_decimal(self, value_str: str, field_name: str) -> Decimal:
        """
        Парсит строку в положительное число.

        Args:
            value_str: строка для парсинга
            field_name: название поля для сообщения об ошибке

        Returns:
            Положительное число 

        Raises:
            ValueError: если строка некорректна или число <= 0
        """
        value = to_decimal(value_str)
        if value is None:
            raise ValueError(f"{field_name}: некорректное число")
        if value <= 0:
            raise ValueError(f"{field_name} должна быть больше 0")
        return value

    def _parse_non_negative_decimal(
        self, value_str: str, field_name: str, default: Decimal = 0.0
    ) -> Decimal:
        """
        Парсит строку в неотрицательное число. Пустая строка → default.

        Args:
            value_str: строка для парсинга
            field_name: название поля для сообщения об ошибке
            default: значение по умолчанию

        Returns:
            Неотрицательное число 

        Raises:
            ValueError: если число отрицательное
        """
        if not value_str or not value_str.strip():
            return default

        value = to_decimal(value_str)
        if value is None:
            raise ValueError(f"{field_name}: некорректное число")
        if value < 0:
            raise ValueError(f"{field_name} не может быть отрицательной")
        return value

    def _parse_optional_positive_int(
        self, value_str: str, field_name: str
    ) -> Optional[int]:
        """
        Парсит строку в положительное целое число. Пустая строка → None.

        Args:
            value_str: строка для парсинга
            field_name: название поля для сообщения об ошибке

        Returns:
            Положительное число int или None

        Raises:
            ValueError: если число некорректно или <= 0
        """
        if not value_str or not value_str.strip():
            return None

        value = parse_int(value_str)
        if value is None:
            raise ValueError(f"{field_name}: некорректное целое число")
        if value <= 0:
            raise ValueError(f"{field_name} должна быть больше 0")
        return value