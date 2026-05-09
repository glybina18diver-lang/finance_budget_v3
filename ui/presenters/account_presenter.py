# ui/presenters/account_presenter.py
"""
Презентер управления счетами.
Координирует взаимодействие между AccountManagementDialog и AccountService.
"""
from typing import Dict, List
from services.account_service import AccountService
from core.models import Account


class AccountPresenter:
    """Презентер для управления счетами: связывает UI и сервис."""

    def __init__(self, service: AccountService):
        """
        Инициализация презентера.
        
        Args:
            service: экземпляр AccountService
        """
        self.service = service
        self.view = None

    def set_view(self, view):
        """
        Устанавливает ссылку на представление и инициирует загрузку данных.
        
        Args:
            view: объект диалога с методами контракта UI
        """
        self.view = view
        self.load_accounts()

    def load_accounts(self) -> None:
        """Загружает список счетов из сервиса и передаёт в UI."""
        if not self.view:
            return
        accounts = self.service.get_all_accounts()
        self.view.load_accounts(accounts)

    def add_account(self, account_data: Dict) -> None:
        """
        Обрабатывает создание нового счёта.
        
        Args:
            account_data: данные формы
        """
        try:
            self.service.create_account(account_data)
            self.view.show_status("Счёт успешно создан", "success")
            self.load_accounts()
            self.view._reset_form()
        except ValueError as e:
            self.view.show_error(str(e))

    def update_account(self, account_data: Dict) -> None:
        """
        Обрабатывает обновление счёта.
        
        Args:
            account_data: данные формы (должны содержать 'id')
        """
        account_id = account_data.pop("id", None)
        if not account_id:
            self.view.show_error("ID счёта не указан")
            return
            
        try:
            self.service.update_account(account_id, account_data)
            self.view.show_status("Счёт успешно обновлён", "success")
            self.load_accounts()
            self.view._reset_form()
        except ValueError as e:
            self.view.show_error(str(e))

    def delete_account(self, account_id: int) -> None:
        """
        Обрабатывает удаление счёта.
        
        Args:
            account_id: ID удаляемого счёта
        """
        try:
            self.service.delete_account(account_id)
            self.view.show_status("Счёт удалён", "success")
            self.load_accounts()
            self.view._reset_form()
        except ValueError as e:
            self.view.show_error(str(e))

    def select_account(self, account_id: int) -> None:
        """
        Загружает данные выбранного счёта в форму редактирования.
        
        Args:
            account_id: ID выбранного счёта
        """
        account = self.service.get_account(account_id)
        if account:
            self.view.show_account_in_form(account)
        else:
            self.view.show_error("Счёт не найден в базе")