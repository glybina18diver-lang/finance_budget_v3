# ui/dialogs/add_payment_dialog.py
"""
Диалог добавления платежа по займу.
Архитектура MVP.
"""
from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox, QLabel,
    QComboBox, QLineEdit, QDateEdit, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import QDate
from PySide6.QtGui import QDoubleValidator
from ui.dialogs.base_dialog import BaseDialog


class AddPaymentDialog(BaseDialog):
    """Диалог для добавления платежа по займу."""

    def __init__(self, parent=None, presenter=None, loan_id: int = None):
        super().__init__(parent)
        self.presenter = presenter
        self.loan_id = loan_id
        self.loan_data: Optional[Dict] = None
        
        self.setWindowTitle("Добавить платёж по займу")
        self.setFixedSize(450, 500)
        
        self._init_ui()
        
        if self.presenter and self.loan_id:
            self.presenter.load_data_for_payment_dialog(self, self.loan_id)

    def _init_ui(self):
        layout = self._main_layout
        layout.setSpacing(10)
        
        # === Инфо-блок ===
        info_group = QGroupBox("Информация о займе")
        info_layout = QFormLayout()
        
        self.contact_label = QLabel()
        self.type_label = QLabel()
        self.amount_label = QLabel()
        self.remaining_label = QLabel()
        
        info_layout.addRow("Контрагент:", self.contact_label)
        info_layout.addRow("Тип:", self.type_label)
        info_layout.addRow("Сумма займа:", self.amount_label)
        info_layout.addRow("Остаток долга:", self.remaining_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # === Форма платежа ===
        form_group = QGroupBox("Данные платежа")
        self.form_layout = QFormLayout()
        self.form_layout.setSpacing(10)
        
        # Виджеты для счёта (создаем оба, будем переключать видимость)
        self.account_label = QLabel()
        self.account_label.setStyleSheet("font-weight: bold;")
        
        self.account_combo = QComboBox()
        
        # Добавляем их в layout, но скроем один из них в populateа_data
        self.form_layout.addRow("Счёт:", self.account_label)
        self.form_layout.addRow("Счёт:", self.account_combo)
        
        # Дата
        self.date_input = QDateEdit(QDate.currentDate())
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd.MM.yyyy")
        self.form_layout.addRow("Дата платежа:", self.date_input)
        
        # Сумма
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("0.00")
        validator = QDoubleValidator(0.0, 9999999.0, 2)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.amount_input.setValidator(validator)
        self.form_layout.addRow("Сумма платежа:", self.amount_input)
        
        # Описание
        self.description_input = QLineEdit()
        self.form_layout.addRow("Описание:", self.description_input)
        
        form_group.setLayout(self.form_layout)
        layout.addWidget(form_group)
        
        # Подсказка
        self.hint_label = QLabel()
        self.hint_label.setStyleSheet("color: blue; font-size: 9pt;")
        layout.addWidget(self.hint_label)
        
        layout.addStretch()
        
        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        layout.addWidget(self.status_bar)

    def _on_accept(self):
        data = self._get_form_data()
        if data and self.presenter:
            try:
                self.presenter.add_payment(self.loan_id, data)
                self.accept()
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка", str(e))

    def _get_form_data(self) -> Optional[Dict]:
        amount_str = self.amount_input.text().strip().replace(',', '.')
        if not amount_str:
            QMessageBox.warning(self, "Ошибка", "Укажите сумму платежа")
            return None
        
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Сумма должна быть положительной")
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))
            return None
        
        # Определяем ID счёта
        account_id = None
        if self.account_combo.isVisible():
            account_id = self.account_combo.currentData()
            if not account_id:
                QMessageBox.warning(self, "Ошибка", "Выберите счёт")
                return None
        else:
            # Если label виден, значит счёт фиксирован (issued)
            account_id = self.loan_data.get("account_id") if self.loan_data else None
            
        return {
            "amount": amount,
            "date": self.date_input.date().toString("yyyy-MM-dd"),
            "account_id": account_id,
            "description": self.description_input.text().strip()
        }

    # =================== Контракт ===================

    def populate_data(self, loan_data: Dict, accounts: List[Dict]):
        """
        Заполняет форму данными займа и счетов.
        
        Args:
            loan_data: словарь с ключами: id, contact_name, loan_type, loan_amount,
                       remaining, issue_date, due_date, description
            accounts: список словарей с ключами: id, name
        """
        self.loan_data = loan_data
        
        # Инфо
        self.contact_label.setText(loan_data.get("contact_name", ""))
        self.amount_label.setText(f"{loan_data.get('loan_amount', 0):,.2f} ₽")
        self.remaining_label.setText(f"{loan_data.get('remaining', 0):,.2f} ₽")
        
        loan_type = loan_data.get("loan_type", "")
        if loan_type == "issued":
            self.type_label.setText("Выданный (я дал)")
            self.hint_label.setText("💡 Возврат денег от заемщика")
            
            # Показываем Label, скрываем Combo
            self.account_label.setText(self._get_account_name(loan_data.get("account_id"), accounts))
            self.account_label.setVisible(True)
            self.account_combo.setVisible(False)
            
        else:  # received
            self.type_label.setText("Полученный (мне дали)")
            self.hint_label.setText("💡 Возврат денег кредитору")
            
            # Показываем Combo, скрываем Label
            self.account_combo.clear()
            for acc in accounts:
                self.account_combo.addItem(acc.get("name", ""), acc.get("id"))
            self.account_label.setVisible(False)
            self.account_combo.setVisible(True)

    def _get_account_name(self, account_id: int, accounts: List[Dict]) -> str:
        for acc in accounts:
            if acc.get("id") == account_id:
                return acc.get("name", "Неизвестно")
        return "Неизвестно"