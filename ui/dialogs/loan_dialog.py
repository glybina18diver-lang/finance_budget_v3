# ui/dialogs/loan_dialog.py
"""
Диалог управления займами.
Соответствует архитектуре V3: MVP, наследование от BaseDialog, контракты View-Presenter.
"""
from typing import List
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu, 
    QMessageBox, QPushButton, QFrame, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal
from ui.dialogs.base_dialog import BaseDialog
from ui.widgets.colored_button import CompactButton
from ui.dialogs.edit_loan_dialog import EditLoanDialog
from ui.dialogs.loan_details_dialog import LoanDetailsDialog


class LoanDialog(BaseDialog):
    """Окно управления займами."""
    
    data_updated = Signal()
    
    def __init__(self, parent=None, presenter=None):
        """
        Инициализация диалога управления займами.
        
        Args:
            parent: родительское окно
            presenter: экземпляр LoanPresenter для обработки действий
        """
        super().__init__(parent)
        self.presenter = presenter
        self.setWindowTitle("Управление Займами")
        self.resize(1000, 650)
        
        self._init_ui()
        if self.presenter:
            self.presenter.set_view(self)
            
    def _init_ui(self):
        """Инициализация пользовательского интерфейса."""
        # Используем layout и status_bar из BaseDialog
        layout = self._main_layout
        layout.setSpacing(10)
        
        # === Панель кнопок ===
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)
        
        self.add_loan_btn = CompactButton("➕ Добавить заём")
        self.add_loan_btn.clicked.connect(self._add_loan)
        btn_layout.addWidget(self.add_loan_btn)
        
        btn_layout.addStretch()
        
        self.reset_filters_btn = CompactButton("🔄 Сбросить фильтры")
        self.reset_filters_btn.clicked.connect(self._reset_all_filters)
        btn_layout.addWidget(self.reset_filters_btn)
        
        self._main_layout.addWidget(btn_frame)
        
        # === Таблица займов ===
        self.loans_table = QTableWidget()
        self.loans_table.setColumnCount(8)
        self.loans_table.setHorizontalHeaderLabels([
            "Кому", "Тип", "Сумма", "Остаток", "Статус", 
            "Дата выдачи", "Дата погашения", "Описание"
        ])
        
        # Настройка таблицы
        header = self.loans_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        self.loans_table.setColumnWidth(0, 120)  # Кому
        self.loans_table.setColumnWidth(1, 80)   # Тип
        self.loans_table.setColumnWidth(2, 90)   # Сумма
        self.loans_table.setColumnWidth(3, 90)   # Остаток
        self.loans_table.setColumnWidth(4, 80)   # Статус
        self.loans_table.setColumnWidth(5, 100)  # Дата выдачи
        self.loans_table.setColumnWidth(6, 100)  # Дата погашения
        self.loans_table.setColumnWidth(7, 150)  # Описание
        
        self.loans_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.loans_table.setSelectionMode(QTableWidget.SingleSelection)
        self.loans_table.setAlternatingRowColors(True)
        self.loans_table.verticalHeader().setVisible(False)
        self.loans_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.loans_table.customContextMenuRequested.connect(self._show_context_menu)
        
        self._main_layout.addWidget(self.loans_table, 1)
        
        layout.addWidget(self.status_bar)

    def _show_context_menu(self, position):
        """
        Показывает контекстное меню для таблицы займов.
        
        Args:
            position: координаты курсора относительно таблицы
        """
        selected_rows = self.loans_table.selectionModel().selectedRows()
        menu = QMenu(self)
        
        # Всегда доступные действия
        add_payment_action = menu.addAction("💳 Добавить платеж")
        add_payment_action.triggered.connect(self._add_payment)
        
        view_details_action = menu.addAction("📋 Детали займа")
        view_details_action.triggered.connect(self._view_loan_details)
        
        menu.addSeparator()
        
        if selected_rows:
            edit_action = menu.addAction("✏️ Редактировать")
            edit_action.triggered.connect(self._edit_loan)
            
            delete_action = menu.addAction("🗑️ Удалить")
            delete_action.triggered.connect(self._delete_loan)
            
        menu.exec(self.loans_table.viewport().mapToGlobal(position))

    def _add_payment(self):
        """Запрашивает открытие диалога добавления платежа для выбранного займа."""
        selected = self.loans_table.selectionModel().selectedRows()
        if not selected:
            self.show_status("Выберите заём для добавления платежа", "warning")
            return
            
        if self.presenter:
            loan_id = self.loans_table.item(selected[0].row(), 0).data(Qt.UserRole)
            self.presenter.open_add_payment_dialog(loan_id)

    def _add_loan(self):
        """Запрашивает создание нового займа через презентер."""
        if self.presenter:
            self.presenter.open_add_loan_dialog()

    def _edit_loan(self):
        """Открывает диалог редактирования выбранного займа."""
        selected = self.loans_table.selectionModel().selectedRows()
        if not selected:
            self.show_status("Выберите заём для редактирования", "warning")
            return
        
        loan_id = self.loans_table.item(selected[0].row(), 0).data(Qt.UserRole)
        
        if self.presenter:
            dialog = EditLoanDialog(self, presenter=self.presenter, loan_id=loan_id)
            dialog.exec()

    def _view_loan_details(self):
        """Открывает диалог просмотра деталей выбранного займа."""
        selected = self.loans_table.selectionModel().selectedRows()
        if not selected:
            self.show_status("Выберите займ для просмотра деталей", "warning")
            return
        
        loan_id = self.loans_table.item(selected[0].row(), 0).data(Qt.UserRole)
        
        if self.presenter:
            dialog = LoanDetailsDialog(self, presenter=self.presenter, loan_id=loan_id)
            dialog.exec()

    def _delete_loan(self):
        """Запрашивает подтверждение и удаление выбранного займа."""
        selected = self.loans_table.selectionModel().selectedRows()
        if not selected:
            self.show_status("Выберите заём для удаления", "warning")
            return
            
        reply = QMessageBox.question(
            self, 
            "Подтверждение", 
            "Удалить выбранный заём и все связанные платежи?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes and self.presenter:
            loan_id = self.loans_table.item(selected[0].row(), 0).data(Qt.UserRole)
            self.presenter.delete_loan(loan_id)

    def _reset_all_filters(self):
        """Сбрасывает фильтры и перезагружает данные через презентер."""
        if self.presenter:
            self.presenter.reset_filters_and_reload()

    # =================== Контракт View <-> Presenter ===================
    
    def load_loans(self, loans_data: List[dict]):
        """
        Заполняет таблицу данными о займах.
        
        Args:
            loans_data: список словарей с ключами: id, contact_name, type, amount, 
                        remaining, status, issue_date, due_date, description
        """
        self.loans_table.setRowCount(0)
        for i, loan in enumerate(loans_data):
            self.loans_table.insertRow(i)
            
            self.loans_table.setItem(i, 0, QTableWidgetItem(str(loan.get("contact_name", ""))))
            self.loans_table.setItem(i, 1, QTableWidgetItem(str(loan.get("type", ""))))
            self.loans_table.setItem(i, 2, QTableWidgetItem(f'{loan.get("amount", 0):,.2f}'))
            self.loans_table.setItem(i, 3, QTableWidgetItem(f'{loan.get("remaining", 0):,.2f}'))
            self.loans_table.setItem(i, 4, QTableWidgetItem(str(loan.get("status", ""))))
            self.loans_table.setItem(i, 5, QTableWidgetItem(str(loan.get("issue_date", ""))))
            self.loans_table.setItem(i, 6, QTableWidgetItem(str(loan.get("due_date", ""))))
            self.loans_table.setItem(i, 7, QTableWidgetItem(str(loan.get("description", ""))))
            
            # Сохраняем ID займа в скрытых данных первой ячейки
            self.loans_table.item(i, 0).setData(Qt.UserRole, loan.get("id"))
            
            # Устанавливаем цвет строки в зависимости от статуса займа 
            # TODO как вараинт возможного
            # if loan.get("status", "") == "active":
            #    self.loans_table.item(i, 0).setBackground(QColor("#e6ffe6"))
            # elif loan.get("status", "") == "overdue":
            #    self.loans_table.item(i, 0).setBackground(QColor("#ffe6e6")).

    def clear_selection(self):
        """Очищает выделение в таблице."""
        self.loans_table.clearSelection()