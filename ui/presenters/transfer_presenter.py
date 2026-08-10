# ui/presenters/transfer_presenter.py
"""
Презентер переводов.
Связывает UI и бизнес-логику.
"""
from services.transfer_service import TransferService
from services.transaction_service import TransactionService
from typing import Dict, List
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


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
            self.view.show_status("Перевод успешно добавлен", "success")
            self._load_data()
        except ValueError as e:
            self.view.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[TransferPresenter] Ошибка создания перевода: {e}", exc_info=True)
            self.view.show_status("Произошла ошибка при создании перевода", "error")

    def delete_transfers(self, transfer_ids: List[int]) -> None:
        """
        Обрабатывает удаление перевода.

        Args:
            transfer_ids: ID перевода
        """
        try:
            for tid in transfer_ids:
                self.service.delete_transfer(tid)
                self.view.show_status(f"Успешно удалено: {len(transfer_ids)} перевод(ов)",  message_type="success")
            self.view.clear_selection()
            self._load_data()
        except ValueError as e:
            self.view.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[TransferPresenter] Ошибка удаления переводов: {e}", exc_info=True)
            self.view.show_status("Произошла ошибка при удалении переводов", "error")

    def _load_data(self):
        """Загружает переводы и списки счетов в UI."""
        if not self.view:
            return

        try:
            # 1. Загружаем переводы
            transfer_data = self.service.get_all_transfers()
            self.view.load_transfers_tree(transfer_data)

            # Заполняем комбобоксы счетов
            accounts = self.service.get_all_accounts_active()
            self.view.amount_input.clear()
            self.view.description_input.clear()
            self.view.counterparty_input.clear()
            self.view.amount_input.setFocus()
            for acc in accounts:
                self.view.from_combo.addItem(acc.name, acc.id)
                self.view.to_combo.addItem(acc.name, acc.id)
                self.view.ext_account_combo.addItem(acc.name, acc.id)
                self.view.update_account_filter(accounts)

        except Exception as e:
            logger.error(f"[TransferPresenter] Ошибка загрузки данных: {e}", exc_info=True)
            if self.view:
                self.view.show_status("Ошибка загрузки данных", "error")

    def refresh_data(self):
        """
        Обновляет данные в представлении (счета, переводы).
        используется при закрытии дочерних диалогов
        
        Args:
            current_type: текущий выбранный тип операции для сохранения состояния UI
        """
        try:
            # 1. Обновляем переводы в таблице
            transfer_data = self.service.get_all_transfers()
            self.view.load_transfers_tree(transfer_data)
        except Exception as e:
            logger.error(f"[TransferPresenter] Ошибка обновления данных: {e}", exc_info=True)
            self.view.show_status("Ошибка обновления данных", message_type="error")

    def load_transfers_filters(self, filters: Dict):
        """
        Загружает отфильтрованные переводы и передаёт их в View.
        Вызывается при применении фильтров.
        
        Args:
            filters: параметры фильтрации из UI
        """
        try:
            transfers = self.service.get_transfers_with_filters(filters)
            self.view.load_transfers_tree(transfers)
            logger.info(f"[{self.__class__.__name__}] Загружено отфильтрованных переводов: {len(transfers)}")
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация фильтров: {e}")
            if self.view:
                self.view.show_status(str(e), message_type="error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка загрузки отфильтрованных переводов: {e}", exc_info=True)
            if self.view:
                self.view.show_status("Ошибка применения фильтров", message_type="error")

    def search_counterparties(self, search_text: str = "", limit: int = 100) -> list[str]:
        """
        Возвращает список контрагентов для автодополнения.

        Args:
            search_text: текст из поля ввода
            limit: максимальное количество результатов

        Returns:
            Список имён контрагентов

        Raises:
            ValueError: если limit меньше или равен нулю
        """
        try:
            if limit <= 0:
                raise ValueError("Лимит результатов должен быть больше нуля")

            return self.service.search_counterparties(
                search_text=search_text,
                limit=limit,
            )

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка поиска контрагентов: {e}",
                exc_info=True,
            )
            raise