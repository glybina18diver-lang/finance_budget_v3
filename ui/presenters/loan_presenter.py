# ui/presenters/loan_presenter.py
"""
Презентер для управления займами.
Координирует взаимодействие между LoanDialog и LoanService.
"""
from PySide6.QtWidgets import QDialog
import logging
from services.loan_service import LoanService
from services.credit_service import CreditService

from ui.dialogs.loan_dialog import LoanDialog
from ui.dialogs.add_loan_dialog import AddLoanDialog
from ui.dialogs.add_payment_dialog import AddPaymentDialog

logger = logging.getLogger(__name__)


class LoanPresenter:
    """Презентер займов."""

    def __init__(self, service: LoanService, credit_service: CreditService):
        """
        Инициализация.

        Args:
            service: экземпляр LoanService
        """
        self.service = service
        self.credit_service = credit_service
        self.view: LoanDialog = None

    def set_view(self, view: LoanDialog):
        """
        Устанавливает ссылку на UI и загружает начальные данные.
        """
        self.view = view
        self.load_loans()
        self.load_credits()

    def load_credits(self):
        """Загружает список кредитов из сервиса в таблицу.
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
            loans = self.credit_service.get_all_credits_ui()

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

            self.view.load_credits(result)

        except Exception as e:
            logger.error(
                f"[CreditPresenter] Ошибка получения списка кредитов: {e}",
                exc_info=True,
            )
            self.view.show_error(f"Ошибка загрузки кредитов: {e}")
            raise
        

    def load_loans(self) -> None:
        """
        Загружает список займов из сервиса в таблицу UI.

        Получает все займы у контрагентов и преобразует их
        в формат словарей для отображения в таблице.

        Returns:
            None. Результат передаётся в view через self.view.load_loans(result).

        Raises:
            Exception: при системной ошибке
        """
        try:
            loans = self.service.get_all_loans_ui()

            result = []
            for loan in loans:
                result.append({
                    "id": loan.id,
                    "contact_name": loan.contact_name,
                    "type": loan.loan_type,
                    "amount": loan.loan_amount,
                    "remaining": loan.remaining,
                    "status": loan.status,
                    "issue_date": loan.issue_date,
                    "due_date": loan.due_date,
                    "description": loan.description,
                })

            self.view.load_loans(result)

        except Exception as e:
            logger.error(
                f"[LoanPresenter] Ошибка загрузки списка займов: {e}",
                exc_info=True,
            )
            self.view.show_error(f"Ошибка загрузки займов: {e}")
            raise

    def open_add_loan_dialog(self):
        """
        Открывает модальный диалог создания нового займа.
        """
        if not self.view:
            return

        # 1. Создаём диалог, передавая ссылку на родителя и презентер
        dialog = AddLoanDialog(parent=self.view, presenter=self)

        # 2. Показываем как модальный диалог (блокирует основное окно)
        if dialog.exec() == QDialog.Accepted:
            # Диалог закрыт через OK — данные уже обработаны в _on_accept
            pass
        # Если закрыт через Cancel — ничего не делаем

    def open_add_payment_dialog(self, loan_id: int):
        """
        Открывает диалог добавления платежа для конкретного займа.

        Args:
            loan_id: ID займа, для которого вносится платеж
        """
        # 1. Создаём диалог, передавая ссылку на родителя и презентер
        dialog = AddPaymentDialog(parent=self.view, presenter=self, loan_id=loan_id)
        # 2. Показываем как модальный диалог (блокирует основное окно)
        if dialog.exec() == QDialog.Accepted:
            # Диалог закрыт через OK — данные уже обработаны в _on_accept
            pass
        # Если закрыт через Cancel — ничего не делаем

    def create_loan(self, loan_data: dict):
        """
        Создаёт заём через сервис.

        Args:
            loan_data: данные займа в формате словаря
        """
        try:
            loan_id = self.service.create_loan(loan_data)
            self.view.show_status(f"Заём ID {loan_id} успешно создан", "success")
            self.load_loans()  # Обновляем таблицу
            self.view.data_updated.emit()  # Сигнал главному окну (обновить балансы)
        except ValueError as e:
            self.view.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[LoanPresenter] Ошибка создания займа: {e}", exc_info=True)
            self.view.show_status("Произошла ошибка при создании займа", "error")

    def load_data_for_payment_dialog(self, dialog, loan_id: int):
        """Загружает данные займа и счетов для диалога платежа."""
        try:
            loan_data = self.service.get_loan_by_id(loan_id)
            accounts_objects = self.service.get_all_accounts_active()

            # Конвертируем объекты Account в словари для UI
            # current_balance уже Decimal, передаём как есть
            accounts = [
                {
                    'id': acc.id,
                    'name': acc.name,
                    'account_type': acc.account_type,
                    'current_balance': acc.current_balance
                }
                for acc in accounts_objects
            ]

            if loan_data:
                dialog.populate_data(loan_data, accounts)
            else:
                dialog.show_status("Заём не найден", "error")
                dialog.reject()
        except Exception as e:
            logger.error(f"[LoanPresenter] Ошибка загрузки данных для платежа: {e}", exc_info=True)
            dialog.show_status(f"Ошибка загрузки: {e}", "error")

    def load_loan_for_edit(self, dialog, loan_id: int):
        """Загружает данные займа в диалог редактирования."""
        try:
            loan_data = self.service.get_loan_by_id(loan_id)
            if loan_data:
                dialog.populate_loan_data(loan_data)
            else:
                dialog.show_status("Заём не найден", "error")
                dialog.reject()
        except Exception as e:
            logger.error(f"[LoanPresenter] Ошибка загрузки займа для редактирования: {e}", exc_info=True)
            dialog.show_status(f"Ошибка загрузки: {e}", "error")

    def load_loan_details(self, dialog, loan_id: int):
        """Загружает данные займа и историю платежей в диалог деталей."""
        try:
            loan_data = self.service.get_loan_by_id(loan_id)
            payments = self.service.get_loan_payments(loan_id)

            if loan_data:
                dialog.populate_loan_info(loan_data)
                dialog.load_payments(payments)
            else:
                dialog.show_status("Заём не найден", "error")
                dialog.reject()
        except Exception as e:
            logger.error(f"[LoanPresenter] Ошибка загрузки деталей займа: {e}", exc_info=True)
            dialog.show_status(f"Ошибка загрузки: {e}", "error")

    def load_accounts_for_loan_dialog(self, dialog):
        """Загружает активные счета в диалог добавления займа."""
        try:
            accounts = self.service.get_all_accounts_active()
            dialog.load_accounts(accounts)
        except Exception as e:
            logger.error(f"[LoanPresenter] Ошибка загрузки счетов: {e}", exc_info=True)
            dialog.show_status(f"Ошибка загрузки счетов: {e}", "error")

    def delete_loan_payment(self, loan_id: int, payment_id: int):
        """Удаляет платёж по займу и пересчитывает остаток."""
        try:
            self.service.delete_loan_payment(loan_id, payment_id)
            dialog = self.view  # LoanDialog

            # Обновляем данные в открытом диалоге деталей
            self.view.show_status("Платёж удалён", "success")
            self.load_loans()  # Обновляем таблицу в LoanDialog
            self.view.data_updated.emit()
        except ValueError as e:
            self.view.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[LoanPresenter] Ошибка удаления платежа: {e}", exc_info=True)
            self.view.show_status("Произошла ошибка при удалении платежа", "error")

    def add_payment(self, loan_id: int, payment_data: dict):
        """
        Обрабатывает добавление платежа.

        Args:
            loan_id: ID займа, для которого вносится платеж
            payment_data: данные платежа в формате словаря
        """
        try:
            self.service.add_payment_to_loan(loan_id, payment_data)
            self.view.show_status("Платёж успешно добавлен", "success")
            self.load_loans()
            self.view.data_updated.emit()
        except ValueError as e:
            self.view.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[LoanPresenter] Ошибка добавления платежа: {e}", exc_info=True)
            self.view.show_status("Произошла ошибка при добавлении платежа", "error")

    def delete_loan(self, loan_id: int):
        """Обрабатывает удаление займа."""
        try:
            self.service.delete_loan(loan_id)
            self.view.show_status("Заём удален", "success")
            self.view.clear_selection()
            self.load_loans()
        except ValueError as e:
            self.view.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[LoanPresenter] Ошибка удаления займа: {e}", exc_info=True)
            self.view.show_status("Произошла ошибка при удалении займа", "error")

    def update_loan(self, loan_id: int, update_data: dict):
        """
        Обновляет данные займа.

        Args:
            loan_id: ID займа
            update_data: данные займа в формате словаря
        """
        try:
            self.service.update_loan(loan_id, update_data)
            self.view.show_status("Заём обновлён", "success")
            self.load_loans()
            self.view.data_updated.emit()
        except ValueError as e:
            self.view.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[LoanPresenter] Ошибка обновления займа: {e}", exc_info=True)
            self.view.show_status("Произошла ошибка при обновлении займа", "error")

    def reset_filters_and_reload(self):
        """Сбрасывает фильтры в UI и перезагружает данные."""
        if self.view:
            self.load_loans()