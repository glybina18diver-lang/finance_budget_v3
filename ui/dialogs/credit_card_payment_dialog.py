"""
Диалог внесения платежа по кредитной карте.
Показывает минимальный платёж, полную задолженность, распределение.
"""
from typing import List, Dict
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox, QLabel,
    QComboBox, QLineEdit, QDateEdit, QDialogButtonBox, QMessageBox,
    QFrame, QHBoxLayout
)
from PySide6.QtCore import QDate
from PySide6.QtGui import QDoubleValidator
from ui.dialogs.base_dialog import BaseDialog
from ui.widgets.colored_button import CompactButton


class CreditCardPaymentDialog(BaseDialog):
    """Диалог внесения платежа по кредитной карте."""

    def __init__(self, parent=None, presenter=None):
        """
        Инициализация диалога.
        
        Args:
            parent: родительское окно
            presenter: экземпляр CreditCardPresenter
        """
        super().__init__(parent)
        self.presenter = presenter
        
        self.setWindowTitle("Внести платёж")
        self.setFixedSize(500, 550)
        
        self._init_ui()
        
        if self.presenter:
            self.presenter.load_data_for_payment_dialog(self)

    def _init_ui(self):
        """Инициализация интерфейса."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # === Информация о платеже ===
        info_group = QGroupBox("Текущая задолженность")
        info_layout = QFormLayout()
        
        self.min_payment_label = QLabel("0.00 ₽")
        self.min_payment_label.setStyleSheet("font-weight: bold; color: #007bff; font-size: 12pt;")
        info_layout.addRow("Минимальный платёж:", self.min_payment_label)
        
        self.total_debt_label = QLabel("0.00 ₽")
        self.total_debt_label.setStyleSheet("font-weight: bold; color: #dc3545;")
        info_layout.addRow("Вся задолженность:", self.total_debt_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # === Данные платежа ===
        form_group = QGroupBox("Данные платежа")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Счёт для списания
        self.account_combo = QComboBox()
        form_layout.addRow("Счёт списания:", self.account_combo)
        
        # Дата платежа
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd.MM.yyyy")
        form_layout.addRow("Дата платежа:", self.date_input)
        
        # Сумма платежа
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("0.00")
        validator = QDoubleValidator(0.0, 9999999.0, 2)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.amount_input.setValidator(validator)
        self.amount_input.textChanged.connect(self._on_amount_changed)
        form_layout.addRow("Сумма платежа:", self.amount_input)
        
        # Быстрые кнопки
        quick_frame = QFrame()
        quick_layout = QHBoxLayout(quick_frame)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        
        self.min_payment_btn = CompactButton("Минимум")
        self.min_payment_btn.clicked.connect(self._set_min_payment)
        quick_layout.addWidget(self.min_payment_btn)
        
        self.full_payment_btn = CompactButton("Полностью")
        self.full_payment_btn.clicked.connect(self._set_full_payment)
        quick_layout.addWidget(self.full_payment_btn)
        
        form_layout.addRow("", quick_frame)
        
        # Распределение платежа (preview)
        self.allocation_group = QGroupBox("Распределение платежа")
        self.allocation_layout = QFormLayout()
        
        self.allocation_interest_label = QLabel("На проценты: 0.00 ₽")
        self.allocation_principal_label = QLabel("На долг: 0.00 ₽")
        
        self.allocation_layout.addRow(self.allocation_interest_label)
        self.allocation_layout.addRow(self.allocation_principal_label)
        
        self.allocation_group.setLayout(self.allocation_layout)
        self.allocation_group.setVisible(False)
        form_layout.addRow("", self.allocation_group)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Подсказка
        hint = QLabel("💡 Платёж распределяется: сначала проценты, затем основной долг")
        hint.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(hint)
        
        layout.addStretch()
        
        # Кнопки
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_amount_changed(self, text):
        """Обновляет preview распределения платежа."""
        # Здесь можно добавить логику предпросмотра распределения
        pass

    def _set_min_payment(self):
        """Устанавливает сумму минимального платежа."""
        # Будет установлено из populate_payment_data
        pass

    def _set_full_payment(self):
        """Устанавливает сумму полного погашения."""
        # Будет установлено из populate_payment_data
        pass

    def _on_accept(self):
        """Обработчик нажатия OK."""
        amount_str = self.amount_input.text().strip().replace(',', '.')
        if not amount_str:
            QMessageBox.warning(self, "Ошибка", "Укажите сумму платежа")
            return
        
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Сумма должна быть положительной")
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))
            return
        
        account_id = self.account_combo.currentData()
        if not account_id:
            QMessageBox.warning(self, "Ошибка", "Выберите счёт")
            return
        
        payment_data = {
            "date": self.date_input.date().toString("yyyy-MM-dd"),
            "amount": amount,
            "from_account_id": account_id
        }
        
        if self.presenter:
            allocation = self.presenter.make_payment(payment_data)
            if allocation:
                self.accept()

    # =================== Контракт ===================

    def populate_payment_data(self, min_payment: Dict, full_payoff: Dict, accounts: List[Dict]):
        """
        Заполняет форму данными для платежа.
        
        Args:
            min_payment: {min_payment, principal_part, interest_part, ...}
            full_payoff: {total, principal, ...}
            accounts: список {id, name, current_balance}
        """
        # Счета
        self.account_combo.clear()
        for acc in accounts:
            self.account_combo.addItem(
                f"{acc['name']} ({acc['current_balance']:,.2f} ₽)",
                acc['id']
            )
        
        # Сохраняем значения для кнопок
        self._min_payment_value = min_payment.get("min_payment", 0)
        self._full_payment_value = full_payoff.get("total", 0)
        
        # Labels
        self.min_payment_label.setText(f"{min_payment.get('min_payment', 0):,.2f} ₽")
        self.total_debt_label.setText(f"{full_payoff.get('total', 0):,.2f} ₽")

    def set_min_payment_value(self, value: float):
        """Устанавливает значение минимального платежа для кнопки."""
        self._min_payment_value = value
        self.amount_input.setText(f"{value:.2f}")

    def set_full_payment_value(self, value: float):
        """Устанавливает значение полного погашения для кнопки."""
        self._full_payment_value = value
        self.amount_input.setText(f"{value:.2f}")