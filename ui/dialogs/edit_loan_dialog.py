# ui/dialogs/edit_loan_dialog.py
"""
Диалог редактирования займа.
Архитектура MVP: UI не содержит бизнес-логики, работает только через презентер.
"""
from typing import Optional, Dict
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QGroupBox, QLabel,
    QLineEdit, QDateEdit, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QDoubleValidator


class EditLoanDialog(QDialog):
    """Диалог для редактирования займа."""

    def __init__(self, parent=None, presenter=None, loan_id: int = None):
        """
        Инициализация диалога редактирования займа.
        
        Args:
            parent: родительское окно
            presenter: экземпляр LoanPresenter
            loan_id: ID редактируемого займа
        """
        super().__init__(parent)
        self.presenter = presenter
        self.loan_id = loan_id
        self.loan_data: Optional[Dict] = None
        
        self.setWindowTitle("Редактировать заём")
        self.setFixedSize(400, 450)
        
        self._init_ui()
        
        # Загружаем данные займа через презентер
        if self.presenter and self.loan_id:
            self.presenter.load_loan_for_edit(self, self.loan_id)

    def _init_ui(self):
        """Инициализация интерфейса."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # === Информация о займе (только для чтения) ===
        info_group = QGroupBox("Информация о займе (не редактируется)")
        info_layout = QFormLayout()
        
        self.type_label = QLabel()
        info_layout.addRow("Тип:", self.type_label)
        
        self.amount_label = QLabel()
        info_layout.addRow("Сумма:", self.amount_label)
        
        self.remaining_label = QLabel()
        info_layout.addRow("Остаток:", self.remaining_label)
        
        self.issue_date_label = QLabel()
        info_layout.addRow("Дата выдачи:", self.issue_date_label)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # === Редактируемые поля ===
        form_group = QGroupBox("Редактируемые поля")
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Контрагент
        self.contact_input = QLineEdit()
        self.contact_input.setPlaceholderText("Имя контрагента")
        form_layout.addRow("Контрагент:", self.contact_input)
        
        # Дата погашения
        self.due_date_input = QDateEdit()
        self.due_date_input.setCalendarPopup(True)
        self.due_date_input.setDisplayFormat("dd.MM.yyyy")
        self.due_date_input.setDate(QDate.currentDate())
        form_layout.addRow("Дата погашения:", self.due_date_input)
        
        # Описание
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Необязательно")
        form_layout.addRow("Описание:", self.description_input)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # Подсказка
        hint = QLabel("💡 Можно изменить только контрагента, дату погашения и описание")
        hint.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(hint)
        
        layout.addStretch()
        
        # Кнопки
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _on_save(self):
        """Обработчик нажатия кнопки 'Сохранить'."""
        data = self._get_form_data()
        if data and self.presenter:
            try:
                self.presenter.update_loan(self.loan_id, data)
                self.accept()
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка", str(e))

    def _get_form_data(self) -> Optional[Dict]:
        """
        Собирает и валидирует данные из формы.
        
        Returns:
            Словарь с данными для обновления или None при ошибке
        """
        contact_name = self.contact_input.text().strip()
        if not contact_name:
            QMessageBox.warning(self, "Ошибка", "Укажите контрагента")
            return None
        
        return {
            "contact_name": contact_name,
            "due_date": self.due_date_input.date().toString("yyyy-MM-dd"),
            "description": self.description_input.text().strip()
        }

    # =================== Контракт View <-> Presenter ===================

    def populate_loan_data(self, loan_data: Dict):
        """
        Заполняет форму данными займа из презентера.
        
        Args:
            loan_data: словарь с ключами: id, contact_name, loan_type, loan_amount,
                       remaining, issue_date, due_date, description
        """
        self.loan_data = loan_data
        
        # Маппинг типа займа: БД (английский) → UI (русский)
        loan_type = loan_data.get("loan_type", "")
        if loan_type == "issued":
            display_type = "Я дал (выдан)"
        elif loan_type == "received":
            display_type = "Мне дали (получен)"
        else:
            display_type = loan_type
        
        self.type_label.setText(display_type)
        
        # Сумма и остаток
        amount = loan_data.get("loan_amount", 0)
        remaining = loan_data.get("remaining", 0)  
        self.amount_label.setText(f"{amount:,.2f} ₽")
        self.remaining_label.setText(f"{remaining:,.2f} ₽")
        
        # Дата выдачи
        self.issue_date_label.setText(loan_data.get("issue_date", ""))
        
        # Заполняем редактируемые поля
        self.contact_input.setText(loan_data.get("contact_name", ""))
        
        # Дата погашения
        due_date_str = loan_data.get("due_date")
        if due_date_str:
            try:
                date_parts = [int(x) for x in due_date_str.split("-")]
                q_date = QDate(date_parts[0], date_parts[1], date_parts[2])
                self.due_date_input.setDate(q_date)
            except (ValueError, IndexError):
                self.due_date_input.setDate(QDate.currentDate())
        else:
            self.due_date_input.setDate(QDate.currentDate())
        
        self.description_input.setText(loan_data.get("description", ""))