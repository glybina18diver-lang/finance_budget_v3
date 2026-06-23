# ui/dialogs/loan_details_dialog.py
"""
Диалог просмотра деталей займа с историей платежей.
Архитектура MVP: наследование от BaseDialog, работа через презентер.
"""
from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QGroupBox, QFormLayout, QLabel, QVBoxLayout, QHBoxLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu,
    QMessageBox, QDialogButtonBox, QFrame
)
from PySide6.QtCore import Qt
from ui.dialogs.base_dialog import BaseDialog


class LoanDetailsDialog(BaseDialog):
    """Диалог для просмотра деталей займа с историей платежей."""

    def __init__(self, parent=None, presenter=None, loan_id: int = None):
        """
        Инициализация диалога деталей займа.
        
        Args:
            parent: родительское окно
            presenter: экземпляр LoanPresenter
            loan_id: ID займа для просмотра
        """
        super().__init__(parent)
        self.presenter = presenter
        self.loan_id = loan_id
        self.loan_data: Optional[Dict] = None
        self.payments: List[Dict] = []
        
        self.setWindowTitle("Детали займа")
        self.resize(800, 600)
        
        self._init_ui()
        
        # Загружаем данные через презентер
        if self.presenter and self.loan_id:
            self.presenter.load_loan_details(self, self.loan_id)

    def _init_ui(self):
        """Инициализация интерфейса."""
        # Используем layout из BaseDialog
        self._main_layout.setSpacing(10)
        
        # === Информация о займе ===
        info_group = QGroupBox("Информация о займе")
        info_layout = QFormLayout()
        
        self.contact_label = QLabel()
        info_layout.addRow("Контрагент:", self.contact_label)
        
        self.type_label = QLabel()
        info_layout.addRow("Тип займа:", self.type_label)
        
        self.amount_label = QLabel()
        info_layout.addRow("Общая сумма:", self.amount_label)
        
        self.remaining_label = QLabel()
        info_layout.addRow("Остаток долга:", self.remaining_label)
        
        self.issue_date_label = QLabel()
        info_layout.addRow("Дата выдачи:", self.issue_date_label)
        
        self.due_date_label = QLabel()
        info_layout.addRow("Дата погашения:", self.due_date_label)
        
        self.description_label = QLabel()
        info_layout.addRow("Описание:", self.description_label)
        
        info_group.setLayout(info_layout)
        self._main_layout.addWidget(info_group)
        
        # === История платежей ===
        payments_group = QGroupBox("История платежей")
        payments_layout = QVBoxLayout()
        
        self.payments_table = QTableWidget()
        self.payments_table.setColumnCount(4)
        self.payments_table.setHorizontalHeaderLabels([
            "Дата", "Сумма", "Счёт", "Описание"
        ])
        
        # Настройка ширины колонок
        header = self.payments_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Дата
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Сумма
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Счёт
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # Описание
        
        self.payments_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.payments_table.setSelectionMode(QTableWidget.SingleSelection)
        self.payments_table.setAlternatingRowColors(True)
        self.payments_table.verticalHeader().setVisible(False)
        
        # Контекстное меню
        self.payments_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.payments_table.customContextMenuRequested.connect(
            self._show_payments_context_menu
        )
        
        payments_layout.addWidget(self.payments_table)
        payments_group.setLayout(payments_layout)
        self._main_layout.addWidget(payments_group, 1)
        
        # === Итоговая информация ===
        total_frame = QFrame()
        total_layout = QHBoxLayout(total_frame)
        total_layout.setContentsMargins(0, 0, 0, 0)
        
        self.total_paid_label = QLabel("Всего выплачено: 0.00 ₽")
        self.total_paid_label.setStyleSheet("font-weight: bold; color: #28a745;")
        
        self.outstanding_label = QLabel("Остаток: 0.00 ₽")
        self.outstanding_label.setStyleSheet("font-weight: bold; color: #dc3545;")
        
        total_layout.addWidget(self.total_paid_label)
        total_layout.addStretch()
        total_layout.addWidget(self.outstanding_label)
        
        self._main_layout.addWidget(total_frame)
        
        # Кнопка закрытия
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        self._main_layout.addWidget(button_box)

    def _show_payments_context_menu(self, position):
        """
        Показывает контекстное меню для таблицы платежей.
        
        Args:
            position: координаты курсора относительно таблицы
        """
        selected_rows = self.payments_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        menu = QMenu(self)
        
        delete_action = menu.addAction("🗑️ Удалить платеж")
        delete_action.triggered.connect(self._delete_selected_payment)
        
        menu.addSeparator()
        
        print_action = menu.addAction("🖨️ Печать квитанции")
        print_action.triggered.connect(self._stub_method)
        
        menu.exec(self.payments_table.viewport().mapToGlobal(position))

    def _delete_selected_payment(self):
        """Удаляет выбранный платёж через презентер."""
        selected_rows = self.payments_table.selectionModel().selectedRows()
        if not selected_rows:
            self.show_status("Выберите платёж для удаления", "warning")
            return
        
        row = selected_rows[0].row()
        payment_id = self.payments_table.item(row, 0).data(Qt.UserRole)
        payment_date = self.payments_table.item(row, 0).text()
        payment_amount = self.payments_table.item(row, 1).text()
        
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить платёж от {payment_date} на сумму {payment_amount} ₽?\n\n"
            "Остаток по займу будет пересчитан.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes and self.presenter:
            self.presenter.delete_loan_payment(self.loan_id, payment_id)

    # =================== Контракт View <-> Presenter ===================

    def populate_loan_info(self, loan_data: Dict):
        """
        Заполняет информационный блок данными займа.
        
        Args:
            loan_data: словарь с ключами: contact_name, loan_type, loan_amount,
                       remaining, issue_date, due_date, description
        """
        self.loan_data = loan_data
        
        # Обновляем заголовок окна
        self.setWindowTitle(f"Детали займа: {loan_data.get('contact_name', '')}")
        
        self.contact_label.setText(loan_data.get("contact_name", ""))
        
        # Маппинг типа займа
        loan_type = loan_data.get("loan_type", "")
        if loan_type == "issued":
            self.type_label.setText("Выданный (я дал)")
        elif loan_type == "received":
            self.type_label.setText("Полученный (мне дали)")
        else:
            self.type_label.setText(loan_type)
        
        self.amount_label.setText(f"{loan_data.get('loan_amount', 0):,.2f} ₽")
        self.remaining_label.setText(f"{loan_data.get('remaining', 0):,.2f} ₽")
        self.issue_date_label.setText(loan_data.get("issue_date", ""))
        self.due_date_label.setText(loan_data.get("due_date", "") or "—")
        self.description_label.setText(loan_data.get("description", "") or "—")
        
        # Обновляем итоговую информацию
        loan_amount = loan_data.get("loan_amount", 0)
        remaining = loan_data.get("remaining", 0)
        total_paid = loan_amount - remaining
        
        self.total_paid_label.setText(f"Всего выплачено: {total_paid:,.2f} ₽")
        self.outstanding_label.setText(f"Остаток: {remaining:,.2f} ₽")

    def load_payments(self, payments: List[Dict]):
        """
        Заполняет таблицу историей платежей.
        
        Args:
            payments: список словарей с ключами: id, date, amount, account_name, description
        """
        self.payments = payments
        self.payments_table.setRowCount(0)
        
        for i, payment in enumerate(payments):
            self.payments_table.insertRow(i)
            
            # Дата
            date_item = QTableWidgetItem(str(payment.get("date", "")))
            date_item.setData(Qt.UserRole, payment.get("id"))  # Сохраняем ID платежа
            self.payments_table.setItem(i, 0, date_item)
            
            # Сумма
            amount = payment.get("amount", 0)
            self.payments_table.setItem(i, 1, QTableWidgetItem(f"{amount:,.2f} ₽"))
            
            # Счёт
            self.payments_table.setItem(i, 2, QTableWidgetItem(
                payment.get("account_name", "")
            ))
            
            # Описание
            self.payments_table.setItem(i, 3, QTableWidgetItem(
                payment.get("description", "")
            ))