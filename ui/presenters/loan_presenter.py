# ui/presenters/loan_presenter.py
"""
Презентер для управления займами.
Координирует взаимодействие между LoanDialog и LoanService.
"""
from PySide6.QtWidgets import QDialog
from services.loan_service import LoanService

from ui.dialogs.loan_dialog import LoanDialog
from ui.dialogs.add_loan_dialog import AddLoanDialog
from ui.dialogs.add_payment_dialog import AddPaymentDialog


class LoanPresenter:
    """Презентер займов."""

    def __init__(self, service: LoanService):
        """
        Инициализация.
        
        Args:
            service: экземпляр LoanService
        """
        self.service = service
        self.view: LoanDialog = None

    def set_view(self, view: LoanDialog):
        """
        Устанавливает ссылку на UI и загружает начальные данные.
        """
        self.view = view
        self.load_loans()

    def load_loans(self):
        """Загружает список займов из сервиса в таблицу."""
        try:
            # Можно передать фильтры из view.current_filters, если нужно
            loans = self.service.get_all_loans()
            self.view.load_loans(loans)
        except Exception as e:
            self.view.show_status(f"Ошибка загрузки займов: {e}", "error")

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
            self.load_loans() # Обновляем таблицу
            self.view.data_updated.emit() # Сигнал главному окну (обновить балансы)
        except ValueError as e:
            self.view.show_status(str(e), "error")

    def load_data_for_payment_dialog(self, dialog, loan_id: int):
        """Загружает данные займа и счетов для диалога платежа."""
        try:
            loan_data = self.service.get_loan_by_id(loan_id)
            accounts_objects = self.service.get_all_accounts_active()
            
            # Конвертируем объекты Account в словари для UI
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
            dialog.show_status(f"Ошибка загрузки: {e}", "error")

    def load_accounts_for_loan_dialog(self, dialog):
        """Загружает активные счета в диалог добавления займа."""
        accounts = self.service.get_all_accounts_active()
        dialog.load_accounts(accounts)

    def delete_loan_payment(self, loan_id: int, payment_id: int):
        """Удаляет платёж по займу и пересчитывает остаток."""
        try:
            self.service.delete_loan_payment(loan_id, payment_id)
            dialog = self.view  # LoanDialog
            
            # Обновляем данные в открытом диалоге деталей
            # (если диалог деталей ещё открыт, нужно передать ему обновлённые данные)
            self.view.show_status("Платёж удалён", "success")
            self.load_loans()  # Обновляем таблицу в LoanDialog
            self.view.data_updated.emit()
        except ValueError as e:
            self.view.show_status(str(e), "error")

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

    def delete_loan(self, loan_id: int):
        """Обрабатывает удаление займа."""
        try:
            self.service.delete_loan(loan_id)
            self.view.show_status("Заём удален", "success")
            self.view.clear_selection()
            self.load_loans()
        except ValueError as e:
            self.view.show_status(str(e), "error")

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

    def reset_filters_and_reload(self):
        """Сбрасывает фильтры в UI и перезагружает данные."""
        if self.view:
            # Очистка фильтров в UI (зависит от реализации LoanDialog)
            # self.view.current_filters = {...} 
            self.load_loans()