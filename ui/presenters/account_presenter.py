# ui/presenters/account_presenter.py
"""
Презентер управления счетами.
Координирует взаимодействие между AccountManagementDialog и AccountService.
"""
from typing import Dict, List
import logging
from services.account_service import AccountService
from core.models import Account

logger = logging.getLogger(__name__)


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
        try:
            accounts = self.service.get_all_active_accounts()
            self.view.load_accounts(accounts)
        except Exception as e:
            logger.error(f"[AccountPresenter] Ошибка загрузки счетов: {e}", exc_info=True)
            self.view.show_error(f"Ошибка загрузки счетов: {e}")

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
            self.view.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[AccountPresenter] Ошибка создания счёта: {e}", exc_info=True)
            self.view.show_status("Произошла ошибка при создании счёта", "error")

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
            self.view.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[AccountPresenter] Ошибка обновления счёта #{account_id}: {e}", exc_info=True)
            self.view.show_status("Произошла ошибка при обновлении счёта", "error")

    def delete_account(self, account_id: int) -> dict:
        """
        Удаляет счёт и возвращает детальный результат.

        Returns:
            Словарь с ключами:
            - 'success': bool (удаление прошло успешно)
            - 'can_delete': bool (можно ли удалить вообще)
            - 'message': str (описание результата)
            - 'total_operations': int (если есть операции)
        """
        try:
            # Сначала проверим, можно ли удалить
            can_delete = True
            total_ops = 0

            # Проверка через сервис (должен бросать ValueError при ошибках)
            self.service.delete_account(account_id)
            self.view.clear_selection()
            self.load_accounts()
            return {
                'success': True,
                'can_delete': True,
                'message': "Счёт успешно удалён"
            }

        except ValueError as e:
            error_msg = str(e)
            # Определяем тип ошибки по тексту
            if "связанные операции" in error_msg:
                # Запрашиваем количество операций
                total_ops = self.service._get_transaction_count(account_id)
                return {
                    'success': False,
                    'can_delete': False,
                    'message': error_msg,
                    'total_operations': total_ops
                }
            else:
                # Другие ошибки (баланс, системный и т.д.)
                return {
                    'success': False,
                    'can_delete': False,
                    'message': error_msg
                }
        except Exception as e:
            logger.error(f"[AccountPresenter] Ошибка удаления счёта #{account_id}: {e}", exc_info=True)
            return {
                'success': False,
                'can_delete': False,
                'message': f"Системная ошибка: {e}"
            }

    def select_account(self, account_id: int) -> None:
        """
        Загружает данные выбранного счёта в форму редактирования.

        Args:
            account_id: ID выбранного счёта
        """
        try:
            account = self.service.get_account(account_id)
            if account:
                self.view.show_account_in_form(account)
            else:
                self.view.show_error("Счёт не найден в базе")
        except Exception as e:
            logger.error(f"[AccountPresenter] Ошибка загрузки счёта #{account_id}: {e}", exc_info=True)
            self.view.show_error(f"Ошибка загрузки счёта: {e}")