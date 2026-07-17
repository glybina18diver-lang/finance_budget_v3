"""
Диалог внесения платежа по кредитной карте (CreditCardPaymentDialog).

Позволяет выбрать сумму, дату и счёт-источник. 
После оплаты отображает детализацию распределения платежа (Payment Waterfall).
"""

import logging
from datetime import date
from decimal import Decimal

from PySide6.QtWidgets import (
    QComboBox, QPushButton, QLabel, QDoubleSpinBox, 
    QDateEdit, QFormLayout, QDialogButtonBox, QTextEdit, QGroupBox, QVBoxLayout
)
from PySide6.QtCore import Signal, Qt

from ui.dialogs.base_dialog import BaseDialog

logger = logging.getLogger(__name__)


class CreditCardPaymentDialog(BaseDialog):
    """
    Диалог внесения платежа по кредитной карте.
    
    Сигналы:
        payment_made: Вызывается после успешного внесения платежа.
    """
    
    payment_made = Signal()

    def __init__(self, parent, presenter, card_id: int, card_name: str, card_account_id: int):
        """
        Инициализация диалога платежа.
        
        Args:
            parent: родительское окно
            presenter: экземпляр CreditCardPresenter
            card_id: ID кредитной карты
            card_name: Название карты (для заголовка)
            card_account_id: ID счёта карты (чтобы исключить его из списка источников)
        """
        super().__init__(parent)
        self.presenter = presenter
        self.card_id = card_id
        self.card_account_id = card_account_id
        
        self.setWindowTitle(f"Внесение платежа: {card_name}")
        self.resize(450, 500)
        
        self._setup_ui()
        self._load_accounts()

    def _setup_ui(self):
        """Настраивает интерфейс диалога."""
        # Форма ввода
        form_group = QGroupBox("Параметры платежа")
        form_layout = QFormLayout()
        
        # Сумма
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.01, 10000000.00)
        # self.amount_spin.setPlaceholderText("1000")
        self.amount_spin.setDecimals(2)
        self.amount_spin.setPrefix("₽ ")
        form_layout.addRow("Сумма платежа:", self.amount_spin)
        
        # Дата
        self.date_edit = QDateEdit()
        self.date_edit.setDate(date.today())
        self.date_edit.setCalendarPopup(True)
        form_layout.addRow("Дата платежа:", self.date_edit)
        
        # Счёт списания
        self.account_combo = QComboBox()
        form_layout.addRow("Списать со счёта:", self.account_combo)
        
        form_group.setLayout(form_layout)
        self._main_layout.addWidget(form_group)
        
        # Кнопка оплаты
        self.btn_pay = QPushButton("💳 Внести платёж")
        self.btn_pay.setStyleSheet("QPushButton { font-weight: bold; padding: 8px; background-color: #4CAF50; color: white; }")
        self.btn_pay.clicked.connect(self._on_pay)
        self._main_layout.addWidget(self.btn_pay)
        
        # Блок результата (изначально скрыт)
        self.result_group = QGroupBox("Распределение платежа (Waterfall)")
        result_layout = QVBoxLayout()
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("QTextEdit { background-color: #f0f0f0; font-family: monospace; }")
        result_layout.addWidget(self.result_text)
        self.result_group.setLayout(result_layout)
        self.result_group.setVisible(False)
        self._main_layout.addWidget(self.result_group)
        
        # Кнопка закрытия
        self.btn_close = QPushButton("Закрыть")
        self.btn_close.clicked.connect(self.accept)
        self.btn_close.setVisible(False)
        self._main_layout.addWidget(self.btn_close)

    def _load_accounts(self):
        """Загружает доступные счета в ComboBox."""
        try:
            self.account_combo.clear()
            accounts = self.presenter.get_accounts_for_payment(self.card_account_id)
            
            if not accounts:
                self.account_combo.addItem("Нет доступных счетов", None)
                self.btn_pay.setEnabled(False)
                return
                
            for acc in accounts:
                balance_str = f"{acc['balance']:,.2f} ₽".replace(",", " ")
                self.account_combo.addItem(f"{acc['name']} ({balance_str})", acc["id"])
                
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при загрузке счетов для платежа: {e}", exc_info=True)
            self.show_status("Произошла ошибка при загрузке счетов", "error")

    def _on_pay(self):
        """Обрабатывает нажатие кнопки 'Внести платёж'."""
        try:
            amount = self.amount_spin.value()
            if amount <= 0:
                raise ValueError("Сумма платежа должна быть больше нуля")
                
            account_id = self.account_combo.currentData()
            if not account_id:
                raise ValueError("Не выбран счёт для списания")
                
            payment_date = self.date_edit.date().toString("yyyy-MM-dd")
            
            # Вызов презентера
            result = self.presenter.make_payment(
                card_id=self.card_id,
                amount_str=str(amount),
                payment_date_str=payment_date,
                from_account_id=account_id
            )
            
            # Отображение результата
            self._display_allocation(result)
            
            # Блокируем форму и показываем кнопку закрытия
            self.amount_spin.setEnabled(False)
            self.date_edit.setEnabled(False)
            self.account_combo.setEnabled(False)
            self.btn_pay.setVisible(False)
            self.result_group.setVisible(True)
            self.btn_close.setVisible(True)
            
            self.payment_made.emit()
            self.show_status("Платёж успешно распределён", "success")
            
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при внесении платежа: {e}", exc_info=True)
            self.show_status("Произошла ошибка при внесении платежа", "error")

    def _display_allocation(self, result: dict):
        """Форматирует и отображает распределение платежа."""
        try:
            allocation = result.get("allocation", {})
            amount = result.get("amount", 0)
            
            text = f"Внесено: {amount:,.2f} ₽\n"
            text += "─" * 30 + "\n"
            text += f"Комиссии:  {allocation.get('commissions_paid', 0):>10,.2f} ₽\n"
            text += f"Проценты:  {allocation.get('interest_paid', 0):>10,.2f} ₽\n"
            text += f"Тело долга: {allocation.get('principal_paid', 0):>10,.2f} ₽\n"
            
            remaining = allocation.get('remaining_amount', 0)
            if remaining > 0:
                text += "─" * 30 + "\n"
                text += f"⚠️ Сдача (не распределена): {remaining:,.2f} ₽\n"
                
            self.result_text.setPlainText(text)
        except Exception as e:
            logger.error(f"Ошибка UI при отображении аллокации: {e}", exc_info=True)