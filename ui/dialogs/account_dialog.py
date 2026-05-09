# ui/dialogs/account_dialog.py
from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QTreeWidget, QTreeWidgetItem,
    QLabel, QLineEdit, QComboBox, QGridLayout, QHBoxLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent
from ui.widgets.colored_button import CompactButton, ColoredDialogButtonBox
from core.models import Account


class AccountDialog(QDialog):
    """Диалог управления счетами (чистый UI-слой)."""

    def __init__(self, parent=None, presenter=None):
        """
        Инициализация диалога управления счетами.
        
        Args:
            parent: родительское окно (обычно MainWindow)
            presenter: экземпляр AccountPresenter для обработки действий
        """
        super().__init__(parent)
        self.presenter = presenter
        self.setWindowTitle("Управление Счетами")
        self.resize(500, 640)
        self.editing_account_id: Optional[int] = None
        self._init_ui()

        # Устанавливаем связь с презентером и загружаем данные
        if self.presenter:
            self.presenter.set_view(self)

    def _init_ui(self):
        """Инициализация интерфейса диалога."""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 1. Таблица счетов
        tree_group = QGroupBox("Счета")
        tree_layout = QVBoxLayout(tree_group)
        self.accounts_tree = QTreeWidget()
        self.accounts_tree.setHeaderLabels(["Название", "Тип", "Баланс"])
        self.accounts_tree.setAlternatingRowColors(True)
        self.accounts_tree.itemSelectionChanged.connect(self._on_account_select)
        self.accounts_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.accounts_tree.customContextMenuRequested.connect(self._show_context_menu)
        tree_layout.addWidget(self.accounts_tree)
        main_layout.addWidget(tree_group)

        # 2. Форма редактирования
        form_group = QGroupBox("Добавить/Редактировать счёт")
        form_layout = QGridLayout(form_group)

        row = 0
        form_layout.addWidget(QLabel("Название:"), row, 0)
        self.name_input = QLineEdit()
        self.name_input.setFixedHeight(26)
        form_layout.addWidget(self.name_input, row, 1)
        row += 1

        form_layout.addWidget(QLabel("Тип:"), row, 0)
        self.type_combo = QComboBox()
        self.type_combo.setFixedHeight(26)
        self.type_combo.addItems(["Cash", "Bank Account", "Credit Card"])
        self.type_combo.currentTextChanged.connect(self._on_type_change)
        form_layout.addWidget(self.type_combo, row, 1)
        row += 1

        form_layout.addWidget(QLabel("Начальный баланс:"), row, 0)
        self.initial_balance_input = QLineEdit("0.00")
        self.initial_balance_input.setFixedHeight(26)
        form_layout.addWidget(self.initial_balance_input, row, 1)
        row += 1

        # 🔑 Основное изменение: создаем отдельный виджет для полей кредитной карты
        self.credit_card_group = QGroupBox("Параметры кредитной карты")
        credit_card_layout = QGridLayout(self.credit_card_group)
        
        # Поля кредитной карты (теперь в отдельном контейнере)
        credit_card_layout.addWidget(QLabel("Кредитный лимит:"), 0, 0)
        self.credit_limit_input = QLineEdit("0.00")
        self.credit_limit_input.setFixedHeight(26)
        credit_card_layout.addWidget(self.credit_limit_input, 0, 1)
        
        credit_card_layout.addWidget(QLabel("День платежа (1-31):"), 1, 0)
        self.payment_day_input = QLineEdit("1")
        self.payment_day_input.setFixedHeight(26)
        credit_card_layout.addWidget(self.payment_day_input, 1, 1)
        
        credit_card_layout.addWidget(QLabel("Мин. платёж (%):"), 2, 0)
        self.min_payment_input = QLineEdit("5.0")
        self.min_payment_input.setFixedHeight(26)
        credit_card_layout.addWidget(self.min_payment_input, 2, 1)
        
        # Скрываем всю группу сразу
        self.credit_card_group.setVisible(False)
        form_layout.addWidget(self.credit_card_group, row, 0, 1, 2)
        row += 1

        form_layout.addWidget(QLabel("Валюта:"), row, 0)
        self.currency_combo = QComboBox()
        self.currency_combo.setFixedHeight(26)
        self.currency_combo.addItems(["RUB", "USD", "EUR", "GBP", "CNY", "JPY"])
        form_layout.addWidget(self.currency_combo, row, 1)
        row += 1

        # Кнопки формы
        button_layout = QHBoxLayout()
        self.add_button = CompactButton("Добавить")
        self.add_button.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(self.add_button)

        self.edit_button = CompactButton("Сохранить")
        self.edit_button.clicked.connect(self._on_edit_clicked)
        self.edit_button.setEnabled(False)
        button_layout.addWidget(self.edit_button)

        self.cancel_button = CompactButton("Отмена")
        self.cancel_button.clicked.connect(self._reset_form)
        self.cancel_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)

        form_layout.addLayout(button_layout, row, 0, 1, 2)
        main_layout.addWidget(form_group)

        # 3. Кнопки диалога
        dialog_buttons = ColoredDialogButtonBox(color="#4CAF50")
        close_btn = dialog_buttons.addButton("Закрыть", QDialogButtonBox.RejectRole)
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(dialog_buttons)

        # 4. Строка статуса
        self.status_bar = QLabel("Готово")
        self.status_bar.setFixedHeight(26)
        main_layout.addWidget(self.status_bar)

        self.setLayout(main_layout)
        self._on_type_change()  # Инициализация видимости полей

    # =================== Методы-обработчики UI ===================

    def _on_add_clicked(self):
        """Обработчик нажатия кнопки 'Добавить'."""
        if not self.presenter:
            return
        try:
            account_data = self._get_form_data()
            self.presenter.add_account(account_data)
        except ValueError as e:
            self.show_status(str(e), "error")

    def _on_edit_clicked(self):
        """Обработчик нажатия кнопки 'Сохранить'."""
        if not self.presenter or self.editing_account_id is None:
            return
        try:
            account_data = self._get_form_data()
            account_data["id"] = self.editing_account_id
            self.presenter.update_account(account_data)
        except ValueError as e:
            self.show_status(str(e), "error")

    def _on_account_select(self):
        """Обработчик выбора счёта в таблице."""
        items = self.accounts_tree.selectedItems()
        if not items:
            self._reset_form()
            return

        item = items[0]
        account_id = item.data(0, Qt.UserRole)
        if self.presenter:
            self.presenter.select_account(account_id)

    def _show_context_menu(self, position):
        """Показывает контекстное меню для выбранного счёта."""
        self._stub_method()

    def _on_type_change(self):
        """Показывает/скрывает поля кредитной карты."""
        is_credit = self.type_combo.currentText() == "Credit Card"
        self.credit_card_group.setVisible(is_credit)

    def _get_form_data(self) -> dict:
        """
        Собирает данные из формы в словарь.
        
        Returns:
            Словарь с данными счёта
            
        Raises:
            ValueError: если данные некорректны
        """
        name = self.name_input.text().strip()
        if not name:
            raise ValueError("Название счёта не может быть пустым")

        acc_type = self.type_combo.currentText()
        try:
            initial_balance = float(self.initial_balance_input.text() or "0")
            currency = self.currency_combo.currentText()
        except ValueError:
            raise ValueError("Некорректный формат начального баланса")

        data = {
            "name": name,
            "account_type": acc_type,
            "initial_balance": initial_balance,
            "current_balance": initial_balance,
            "currency": currency,
            "is_active": True,
            "is_system": False
        }

        if acc_type == "Credit Card":
            try:
                data["credit_limit"] = float(self.credit_limit_input.text() or "0")
                data["payment_due_day"] = int(self.payment_day_input.text() or "1")
                data["min_payment_percent"] = float(self.min_payment_input.text() or "5.0")
            except ValueError:
                raise ValueError("Некорректные данные кредитной карты")

        return data

    def _reset_form(self):
        """Сбрасывает форму ввода к состоянию 'новый счёт'."""
        self.name_input.clear()
        self.initial_balance_input.setText("0.00")
        self.type_combo.setCurrentIndex(0)
        self.currency_combo.setCurrentIndex(0)
        self.editing_account_id = None
        self.add_button.setEnabled(True)
        self.edit_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self.show_status("Форма очищена", "info")

    def _stub_method(self):
        """Заглушка для нереализованных функций."""
        self.show_status("Функция в разработке", "warning")

    # =================== Контракт View <-> Presenter ===================

    def load_accounts(self, accounts: List[Account]):
        """
        Заполняет таблицу счетов данными из презентера.
        
        Args:
            accounts: список объектов Account
        """
        self.accounts_tree.clear()
        self.current_accounts = accounts
        for acc in accounts:
            balance_str = f"{acc.current_balance:,.2f} {acc.currency}"
            item = QTreeWidgetItem([acc.name, acc.account_type, balance_str])
            item.setData(0, Qt.UserRole, acc.id)
            item.setData(0, Qt.UserRole + 1, acc.is_system)
            self.accounts_tree.addTopLevelItem(item)

    def show_account_in_form(self, account: Account):
        """
        Заполняет форму данными выбранного счёта.
        
        Args:
            account: объект Account для отображения
        """
        self.name_input.setText(account.name)
        self.type_combo.setCurrentText(account.account_type)
        self.initial_balance_input.setText(f"{account.initial_balance:.2f}")
        self.currency_combo.setCurrentText(account.currency or "RUB")

        if account.account_type == "Credit Card":
            self.credit_limit_input.setText(f"{account.credit_limit or 0.0:.2f}")
            self.payment_day_input.setText(str(account.payment_due_day or 1))
            self.min_payment_input.setText(f"{account.min_payment_percent or 5.0:.2f}")

        self.editing_account_id = account.id
        self.add_button.setEnabled(False)
        self.edit_button.setEnabled(True)
        self.cancel_button.setEnabled(True)
        self.show_status(f"Редактирование: {account.name}", "info")

    def show_status(self, message: str, message_type: str = "info"):
        """
        Отображает сообщение в строке статуса.
        
        Args:
            message: текст сообщения
            message_type: тип сообщения ("info", "success", "warning", "error")
        """
        colors = {"info": "#6c757d", "success": "#28a745", "warning": "#fd7e14", "error": "#dc3545"}
        color = colors.get(message_type, "#6c757d")
        self.status_bar.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.status_bar.setText(message)
        QTimer.singleShot(2000, lambda: self.status_bar.setText("Готово"))

    def clear_selection(self):
        """Очищает выделение в таблице."""
        self.accounts_tree.clearSelection()