# ui/presenters/transaction_presenter.py
from typing import Optional
from services.transaction_service import TransactionService

class TransactionPresenter:
    """Презентер для координации UI, сервисов и отображения статуса."""

    def __init__(self, tx_service: TransactionService):
        """
        Инициализация презентера.
        
        Args:
            tx_service: экземпляр TransactionService для выполнения бизнес-операций
        """
        self.service = tx_service
        self.view = None  # Ссылка на UI-объект (устанавливается через set_view)

    def set_view(self, view):
        """
        Устанавливает ссылку на представление (диалог/окно).
        
        Args:
            view: объект с методами show_status, show_error, clear_form, refresh_transactions
        """
        self.view = view

    def add_transaction(self, raw_amount: str, trans_type: str, account_id: int,
                        category_id: Optional[int], description: str, date_str: str):
        """
        Обрабатывает добавление новой транзакции из UI.
        
        Args:
            raw_amount: строка суммы из поля ввода (например, "100*3")
            trans_type: тип операции ("income", "expense")
            account_id: ID выбранного счёта
            category_id: ID выбранной категории
            description: текст описания
            date_str: дата операции в формате YYYY-MM-DD
        """
        try:
            tx = self.service.create_transaction(
                raw_amount=raw_amount,
                trans_type=trans_type,
                account_id=account_id,
                category_id=category_id,
                description=description,
                date_str=date_str
            )
            if self.view:
                self.view.show_status(f"Транзакция ID{tx.id} добавлена")
                self.view.clear_form()
                self.view.refresh_transactions()
        except ValueError as e:
            if self.view:
                self.view.show_error(str(e))

    def delete_transaction(self, tx_id: int):
        """
        Обрабатывает удаление транзакции по ID.
        
        Args:
            tx_id: идентификатор транзакции для удаления
        """
        try:
            self.service.delete_transaction(tx_id)
            if self.view:
                self.view.show_status(f"Транзакция ID{tx_id} удалена")
                self.view.refresh_transactions()
        except Exception as e:
            if self.view:
                self.view.show_error(f"Ошибка удаления: {e}")