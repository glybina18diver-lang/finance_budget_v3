# ui/dialogs/add_loan_dialog.py
"""
Диалог добавления нового займа.
Архитектура MVP: UI не содержит бизнес-логики, работает только через презентер.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QLineEdit,
    QDateEdit, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QDoubleValidator


class AddLoanDialog(QDialog):
    """Диалог для добавления нового займа."""

    def __init__(self, parent=None, presenter=None):
        """
        Инициализация диалога добавления займа.
        
        Args:
            parent: родительское окно
            presenter: экземпляр LoanPresenter для обработки действий
        """
        super().__init__(parent)
        self.presenter = presenter
        self.setWindowTitle("Добавить заём")
        self.setFixedSize(350, 400)
        
        self._init_ui()
        
        # Загружаем счета через презентер
        if self.presenter:
            self.presenter.load_accounts_for_loan_dialog(self)

    def _init_ui(self):
        """Инициализация интерфейса."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Форма ввода
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Счёт
        self.account_combo = QComboBox()
        form_layout.addRow("Счёт:", self.account_combo)
        
        # Контрагент
        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("Имя контрагента")
        form_layout.addRow("Контрагент:", self.contact_input)
        
        # Тип займа (русские названия в UI, английские в БД)
        self.loan_type_combo = QComboBox()
        self.loan_type_combo.addItems(["Я дал", "Мне дали"])
        form_layout.addRow("Тип займа:", self.loan_type_combo)
        
        # Сумма займа
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("0.00")
        validator = QDoubleValidator(0.0, 9999999.0, 2)
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.amount_input.setValidator(validator)
        form_layout.addRow("Сумма займа:", self.amount_input)
        
        # Дата выдачи
        self.issue_date_input = QDateEdit()
        self.issue_date_input.setDate(QDate.currentDate())
        self.issue_date_input.setCalendarPopup(True)
        self.issue_date_input.setDisplayFormat("dd.MM.yyyy")
        form_layout.addRow("Дата выдачи:", self.issue_date_input)
        
        # Дата погашения
        self.due_date_input = QDateEdit()
        self.due_date_input.setCalendarPopup(True)
        self.due_date_input.setDate(QDate.currentDate().addMonths(1))
        self.due_date_input.setDisplayFormat("dd.MM.yyyy")
        form_layout.addRow("Дата погашения:", self.due_date_input)
        
        # Описание
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Необязательно")
        form_layout.addRow("Описание:", self.description_input)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Cancel).setText("Отмена")        
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_accept(self):
        """Обработчик нажатия OK. Валидирует данные и передаёт в презентер."""
        data = self._get_form_data()
        if data and self.presenter:
            self.presenter.create_loan(data)
            self.accept()

    def _get_form_data(self) -> dict:
        """
        Собирает и валидирует данные из формы.
        
        Returns:
            Словарь с данными займа или None при ошибке валидации
        """
        # Валидация контрагента
        contact_name = self.contact_input.text().strip()
        if not contact_name:
            self.show_status("Укажите контрагента", "warning")
            return None
        
        # Валидация суммы
        amount_str = self.amount_input.text().strip().replace(',', '.')
        if not amount_str:
            self.show_status("Укажите сумму займа", "warning")
            return None
        
        # Маппинг типа займа: UI (русский) → БД (английский)
        ui_type = self.loan_type_combo.currentText()
        db_type = "issued" if ui_type == "Я дал" else "received"
        
        return {
            "contact_name": contact_name,
            "loan_type": db_type,
            "loan_amount": float(amount_str),
            "account_id": self.account_combo.currentData(),
            "issue_date": self.issue_date_input.date().toString("yyyy-MM-dd"),
            "due_date": self.due_date_input.date().toString("yyyy-MM-dd"),
            "description": self.description_input.text().strip()
        }

    # =================== Контракт View <-> Presenter ===================

    def load_accounts(self, accounts: list):
        """
        Заполняет комбобокс счетами из презентера.
        
        Args:
            accounts: список объектов Account или словарей с полями id и name
        """
        self.account_combo.clear()
        for acc in accounts:
            # Поддержка как объектов, так и словарей
            if hasattr(acc, 'id'):
                self.account_combo.addItem(acc.name, acc.id)
            else:
                self.account_combo.addItem(acc['name'], acc['id'])