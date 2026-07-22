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
                self.view.show_status(f"Удалено переводов: {len(transfer_ids)}", "success")
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
            transfer_data = self.service.get_transfers_with_names()
            self.view.load_transfers(transfer_data)

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
        except Exception as e:
            logger.error(f"[TransferPresenter] Ошибка загрузки данных: {e}", exc_info=True)
            if self.view:
                self.view.show_status("Ошибка загрузки данных", "error")

    def check_credit_card_transfer(self, from_account_id: int, amount: Decimal) -> dict:
        """
        Проверяет, является ли счёт кредитной картой, и рассчитывает комиссию.

        Args:
            from_account_id: ID счёта-источника
            amount: сумма перевода (Decimal)

        Returns:
            Словарь {is_credit_card: bool, commission: Decimal, total: Decimal}
        """
        try:
            from core.repositories.credit_card_repository import CreditCardRepository

            repo = CreditCardRepository(self.db)  # или через DI, если есть
            card = repo.get_card_by_account_id(from_account_id)

            if not card:
                return {"is_credit_card": False, "commission": Decimal("0.00"), "total": amount}

            # Комиссия: 5.9% + 590 ₽
            commission = (amount * Decimal("0.059") + Decimal("590.00")).quantize(Decimal("0.01"))
            return {
                "is_credit_card": True,
                "commission": commission,
                "total": amount + commission,
                "card_name": card.name
            }
        except Exception as e:
            logger.error(f"[TransferPresenter] Ошибка проверки кредитной карты: {e}", exc_info=True)
            return {"is_credit_card": False, "commission": Decimal("0.00"), "total": amount}

    def add_commission_expense(self, data: dict):
        """
        Добавляет расход на комиссию за перевод с кредитной карты.

        Args:
            data: {date, amount (комиссия), account_id, description}
        """
        try:
            # Здесь используем существующий сервис транзакций/расходов
            expense_data = {
                "date": data["date"],
                "type": "expense",
                "raw_amount": data["amount"],
                "account_id": data["account_id"],
                "category_id": "4",  # или category_id
                "description": data.get("description", "Комиссия за перевод с кредитной карты")
            }
            self.transaction_service.create_transaction(expense_data)
        except Exception as e:
            logger.error(f"[TransferPresenter] Ошибка добавления комиссии: {e}", exc_info=True)
            raise