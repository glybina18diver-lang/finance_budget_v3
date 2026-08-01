"""
Диалог управления займами и кредитами.
Соответствует архитектуре V3: MVP, наследование от BaseDialog, контракты View-Presenter.
"""
from typing import List, Dict, Any, Optional
import logging

from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QHeaderView, QMenu,
    QMessageBox, QPushButton, QFrame, QHBoxLayout, QTabWidget, QWidget, QVBoxLayout
)
from PySide6.QtCore import Qt, Signal

from ui.dialogs.base_dialog import BaseDialog
from ui.widgets.colored_button import CompactButton
from ui.dialogs.edit_loan_dialog import EditLoanDialog
from ui.dialogs.loan_details_dialog import LoanDetailsDialog
from ui.presenters.loan_presenter import LoanPresenter

logger = logging.getLogger(__name__)


class LoanDialog(BaseDialog):
    """Окно управления займами и кредитами."""

    data_updated = Signal()

    # Индексы вкладок
    TAB_LOANS = 0
    TAB_CREDITS = 1

    def __init__(self, presenter: LoanPresenter, parent=None,  navigation_service: Optional[Any] = None):
        """
        Инициализация диалога управления займами и кредитами.

        Args:
            parent: родительское окно
            presenter: экземпляр LoanPresenter для обработки действий
        """
        super().__init__(parent, navigation_service=navigation_service)
        self.presenter = presenter
        self.setWindowTitle("Управление Займами и Кредитами")
        self.resize(1000, 650)
        self._init_ui()
        self.presenter.set_view(self)

    def _init_ui(self):
        """Инициализация пользовательского интерфейса."""
        layout = self._main_layout
        layout.setSpacing(10)

        # === Панель кнопок ===
        btn_frame = QFrame()
        btn_layout = QHBoxLayout(btn_frame)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(8)

        self.add_btn = CompactButton("➕ Добавить")
        self.add_btn.clicked.connect(self._on_add_clicked)
        btn_layout.addWidget(self.add_btn)

        btn_layout.addStretch()

        # self.reset_filters_btn = CompactButton("🔄 Сбросить фильтры")
        # self.reset_filters_btn.clicked.connect(self._reset_all_filters)
        # btn_layout.addWidget(self.reset_filters_btn)

        self._main_layout.addWidget(btn_frame)

        # === QTabWidget для вкладок ===
        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self._on_tab_changed)

        # --- Вкладка 1: Займы ---
        loans_tab = QWidget()
        loans_layout = QVBoxLayout(loans_tab)
        loans_layout.setContentsMargins(0, 0, 0, 0)

        self.loans_table = QTableWidget()
        self.loans_table.setColumnCount(8)
        self.loans_table.setHorizontalHeaderLabels([
            "Кому", "Тип", "Сумма", "Остаток", "Статус",
            "Дата выдачи", "Дата погашения", "Описание"
        ])
        self._setup_table(self.loans_table, [120, 120, 90, 90, 80, 100, 100, 150])
        self.loans_table.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(pos, is_loans_tab=True)
        )
        loans_layout.addWidget(self.loans_table)

        self.tab_widget.addTab(loans_tab, "Займы")

        # --- Вкладка 2: Кредиты ---
        credits_tab = QWidget()
        credits_layout = QVBoxLayout(credits_tab)
        credits_layout.setContentsMargins(0, 0, 0, 0)

        self.credits_table = QTableWidget()
        self.credits_table.setColumnCount(7)
        self.credits_table.setHorizontalHeaderLabels([
            "Название", "Тип", "Сумма", "Остаток", "Статус",
            "Дата выдачи", "Дата окончания"
        ])
        self._setup_table(self.credits_table, [150, 120, 100, 100, 80, 100, 100])
        self.credits_table.customContextMenuRequested.connect(
            lambda pos: self._show_context_menu(pos, is_loans_tab=False)
        )
        credits_layout.addWidget(self.credits_table)

        self.tab_widget.addTab(credits_tab, "Кредиты")

        self._main_layout.addWidget(self.tab_widget, 1)
        layout.addWidget(self.status_bar)

    def _setup_table(self, table: QTableWidget, column_widths: List[int]) -> None:
        """
        Настраивает таблицу с указанными ширинами колонок.

        Args:
            table: экземпляр QTableWidget для настройки
            column_widths: список ширин для каждой колонки
        """
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        for i, width in enumerate(column_widths):
            if i < table.columnCount():
                table.setColumnWidth(i, width)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setContextMenuPolicy(Qt.CustomContextMenu)

    def _on_tab_changed(self, index: int) -> None:
        """
        Обрабатывает переключение вкладок.

        Args:
            index: индекс активной вкладки
        """
        if index == self.TAB_LOANS:
            self.add_btn.setText("➕ Добавить заём")
        elif index == self.TAB_CREDITS:
            self.add_btn.setText("➕ Добавить кредит")

    def _on_add_clicked(self) -> None:
        """Обрабатывает нажатие кнопки 'Добавить' в зависимости от активной вкладки."""
        current_tab = self.tab_widget.currentIndex()
        if current_tab == self.TAB_LOANS:
            self._add_loan()
        elif current_tab == self.TAB_CREDITS:
            self._open_credit_create_dialog()

    def _show_context_menu(self, position, is_loans_tab: bool) -> None:
        """
        Показывает контекстное меню для таблицы в зависимости от вкладки.

        Args:
            position: координаты курсора относительно таблицы
            is_loans_tab: True если меню для вкладки "Займы", False для "Кредиты"
        """
        table = self.loans_table if is_loans_tab else self.credits_table
        selected_rows = table.selectionModel().selectedRows()

        menu = QMenu(self)

        if is_loans_tab:
            # Меню для займов
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
        else:
            # Меню для кредитов
            add_payment_action = menu.addAction("💳 Внести платеж")
            add_payment_action.triggered.connect(self._add_credit_payment)

            view_details_action = menu.addAction("📋 Детали кредита")
            view_details_action.triggered.connect(self._view_credit_details)

            menu.addSeparator()

            if selected_rows:
                edit_action = menu.addAction("✏️ Редактировать")
                edit_action.triggered.connect(self._edit_credit)

                delete_action = menu.addAction("🗑️ Удалить")
                delete_action.triggered.connect(self._delete_credit)

        menu.exec(table.viewport().mapToGlobal(position))

    # === Методы для займов ===

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

    # === Методы для кредитов (часть заглушки, будут реализованы позже) ===

    def _open_credit_create_dialog(self) -> None:
        """
        Открывает диалог создания кредита через навигационный сервис.
        """
        try:
            self.navigation_service.open_credit_create_dialog(self)

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            self.show_status(str(e), message_type="error")
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка открытия диалога: {e}",
                exc_info=True,
            )
            self.show_error("Произошла ошибка при открытии диалога")

    def _add_credit_payment(self):
        """
        Открывает диалог внесения платежа по выбранному кредиту.

        Делегирует логику презентеру, который сам создаст диалог.
        """
        try:
            selected = self.credits_table.selectionModel().selectedRows()
            if not selected:
                self.show_status("Выберите кредит для внесения платежа", "warning")
                return

            credit_id = self.credits_table.item(selected[0].row(), 0).data(Qt.UserRole)
            if credit_id is None or credit_id <= 0:
                raise ValueError(f"Некорректный credit_id: {credit_id}")

            # Проверяем, что кредит существует
            credit = self.presenter.credit_check(credit_id)
            if credit is None:
                raise ValueError(f"Кредит #{credit_id} не найден")
    
            dialog = self.navigation_service.open_credit_payment_dialog(self, credit_id)

            dialog.payment_made.connect(self.presenter._on_credit_payment_made)

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            self.show_status(str(e), message_type="error")
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка открытия диалога: {e}",
                exc_info=True,
            )
            self.show_error("Произошла ошибка при открытии диалога")
        
    def _view_credit_details(self):
        """Открывает диалог просмотра деталей выбранного кредита."""
        selected = self.credits_table.selectionModel().selectedRows()
        if not selected:
            self.show_status("Выберите кредит для просмотра деталей", "warning")
            return
        # TODO: реализовать через presenter
        self.show_status("Функция в разработке", "info")

    def _edit_credit(self):
        """Открывает диалог редактирования выбранного кредита."""
        selected = self.credits_table.selectionModel().selectedRows()
        if not selected:
            self.show_status("Выберите кредит для редактирования", "warning")
            return
        # TODO: реализовать через presenter
        self.show_status("Функция в разработке", "info")

    def _delete_credit(self):
        """Запрашивает подтверждение и удаление выбранного кредита."""
        selected = self.credits_table.selectionModel().selectedRows()
        if not selected:
            self.show_status("Выберите кредит для удаления", "warning")
            return
        # TODO: реализовать через presenter
        self.show_status("Функция в разработке", "info")

    def _reset_all_filters(self):
        """Сбрасывает фильтры и перезагружает данные через презентер."""
        if self.presenter:
            self.presenter.reset_filters_and_reload()

    # =================== Контракт View <-> Presenter ===================

    def load_loans(self, loans_data: List[dict]):
        """
        Заполняет таблицу займов данными.

        Args:
            loans_data: список словарей с ключами: id, contact_name, type, amount,
                        remaining, status, issue_date, due_date, description
        """
        self.loans_table.setRowCount(0)
        for i, loan in enumerate(loans_data):
            self.loans_table.insertRow(i)
            self.loans_table.setItem(i, 0, QTableWidgetItem(str(loan.get("contact_name", ""))))

            # Тип займа
            type_loan = loan.get("type", "")
            type_display = "Выдан (я дал)" if type_loan == "issued" else "Получен (мне дали)"
            self.loans_table.setItem(i, 1, QTableWidgetItem(type_display))

            self.loans_table.setItem(i, 2, QTableWidgetItem(f'{loan.get("amount", 0):,.2f}'))
            self.loans_table.setItem(i, 3, QTableWidgetItem(f'{loan.get("remaining", 0):,.2f}'))

            # Статус займа
            status = loan.get("status", "")
            if status == "active":
                status_display = "Активный"
            elif status == "paid":
                status_display = "Закрытый"  
            else:
                status_display = "Просрочен" # default = "Просрочен" 
            self.loans_table.setItem(i, 4, QTableWidgetItem(status_display))

            self.loans_table.setItem(i, 5, QTableWidgetItem(str(loan.get("issue_date", ""))))
            self.loans_table.setItem(i, 6, QTableWidgetItem(str(loan.get("due_date", ""))))
            self.loans_table.setItem(i, 7, QTableWidgetItem(str(loan.get("description", ""))))
            self.loans_table.item(i, 0).setData(Qt.UserRole, loan.get("id"))

    def load_credits(self, credits_data: List[dict]):
        """
        Заполняет таблицу кредитов данными.

        Args:
            credits_data: список словарей с ключами: id, name, loan_purpose, loan_amount,
                          remaining, status, issue_date, due_date
        """
        self.credits_table.setRowCount(0)
        for i, credit in enumerate(credits_data):
            self.credits_table.insertRow(i)
            self.credits_table.setItem(i, 0, QTableWidgetItem(str(credit.get("name", ""))))
            
            # Тип кредита
            purpose = credit.get("loan_purpose", "")
            purpose_display = "Потребительский" if purpose == "consumer" else "POS-кредит"
            self.credits_table.setItem(i, 1, QTableWidgetItem(purpose_display))
            
            self.credits_table.setItem(i, 2, QTableWidgetItem(f'{credit.get("loan_amount", 0):,.2f}'))
            self.credits_table.setItem(i, 3, QTableWidgetItem(f'{credit.get("remaining", 0):,.2f}'))

            # Статус кредита
            status = credit.get("status", "")
            if status == "active":
                status_display = "Активный"
            elif status == "paid":
                status_display = "Закрытый"  
            else:
                status_display = "Просрочен" # default = "Просрочен" 
            self.credits_table.setItem(i, 4, QTableWidgetItem(status_display))

            self.credits_table.setItem(i, 5, QTableWidgetItem(str(credit.get("issue_date", ""))))
            self.credits_table.setItem(i, 6, QTableWidgetItem(str(credit.get("due_date", ""))))
            self.credits_table.item(i, 0).setData(Qt.UserRole, credit.get("id"))

    def clear_selection(self):
        """Очищает выделение в обеих таблицах."""
        self.loans_table.clearSelection()
        self.credits_table.clearSelection()