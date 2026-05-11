# ui/presenters/transfer_presenter.py
"""
Презентер переводов.
Связывает UI и бизнес-логику.
"""
from services.transfer_service import TransferService


class TransferPresenter:
    """Презентер для управления переводами."""

    def __init__(self, service: TransferService):
        """
        Инициализация презентера.
        
        Args:
            service: экземпляр TransferService
        """
        self.service = service
        self.view = None

    def set_view(self, view):
        """
        Устанавливает связь с представлением и загружает данные.
        
        Args:
            view: объект TransferDialog
        """
        self.view = view
        self._load_data()

    def add_transfer(self, transfer_data: dict) -> None:
        """
        Обрабатывает создание нового перевода.
        
        Args:
            transfer_data: данные формы
        """
        try:
            self.service.create_transfer(transfer_data)
            self.view.show_status("✅ Перевод успешно добавлен", "success")
            self._load_data()
        except ValueError as e:
            self.view.show_status(str(e), "error")

    def delete_transfer(self, transfer_id: int) -> None:
        """
        Обрабатывает удаление перевода.
        
        Args:
            transfer_id: ID перевода
        """
        try:
            self.service.delete_transfer(transfer_id)
            self.view.show_status("Перевод удалён", "success")
            self.view.clear_selection() 
            self._load_data()
        except ValueError as e:
            self.view.show_status(str(e), "error")

    def _load_data(self):
        """Загружает переводы и списки счетов в UI."""
        if not self.view:
            return
        transfers = self.service.get_all_transfers()
        self.view.load_transfers(transfers)
        
        # Заполняем комбобоксы счетов
        accounts = self.service.get_all_accounts_active()
        self.view.from_combo.clear()
        self.view.to_combo.clear()
        self.view.ext_account_combo.clear()
        for acc in accounts:
            self.view.from_combo.addItem(acc.name, acc.id)
            self.view.to_combo.addItem(acc.name, acc.id)
            self.view.ext_account_combo.addItem(acc.name, acc.id)