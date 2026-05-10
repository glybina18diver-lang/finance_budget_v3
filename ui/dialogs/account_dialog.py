# ui/dialogs/account_dialog.py
from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QGroupBox, QTreeWidget, QTreeWidgetItem,
    QLabel, QLineEdit, QComboBox, QGridLayout, QHBoxLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent
import logging
from datetime import datetime, date

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QLineEdit, QComboBox, QPushButton, QFrame, QMessageBox,
    QScrollArea, QTextEdit, QProgressBar, QGroupBox, QGridLayout,
    QHeaderView, QSplitter, QMenu, QApplication, QWidget,
    QDialogButtonBox, QStatusBar, QProgressDialog, QRadioButton
)
from PySide6.QtCore import Qt, Signal, QTimer, QDate, QThread
from PySide6.QtGui import QFont, QColor, QAction

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
        """
        Показывает контекстное меню при нажатии ПКМ по элементу дерева.
        
        Args:
            position: координаты курсора относительно виджета QTreeWidget
        """
        # Получаем элемент под курсором
        item = self.accounts_tree.itemAt(position)
        if not item:
            return

        account_id = item.data(0, Qt.UserRole)
        is_system = item.data(0, Qt.UserRole + 1)

        menu = QMenu(self)

        # 1. Редактировать
        edit_action = menu.addAction("✏️ Редактировать")
        edit_action.triggered.connect(lambda: self._on_context_edit(account_id))

        # 2. Удалить (скрыто для системных счетов)
        if not is_system:
            delete_action = menu.addAction("🗑️ Удалить")
            delete_action.triggered.connect(lambda: self._on_context_delete(account_id))

        menu.addSeparator()

        # 3. Статистика
        stats_action = menu.addAction("📊 Статистика")
        stats_action.triggered.connect(self._stub_method)

        menu.addSeparator()

        # 4. Обновить список
        refresh_action = menu.addAction("🔄 Обновить список")
        refresh_action.triggered.connect(self._stub_method)

        # Показываем меню в глобальных координатах
        menu.exec(self.accounts_tree.viewport().mapToGlobal(position))

    def _on_context_edit(self, account_id: int):
        """
        Выбирает счёт по ID и переводит форму в режим редактирования.
        
        Args:
            account_id: ID счёта, по которому кликнули ПКМ
        """
        # Находим и выделяем элемент в дереве
        for i in range(self.accounts_tree.topLevelItemCount()):
            item = self.accounts_tree.topLevelItem(i)
            if item.data(0, Qt.UserRole) == account_id:
                self.accounts_tree.setCurrentItem(item)
                self._on_account_select()  # Вызываем существующую логику заполнения формы
                break

    def _on_context_delete_old(self, account_id: int):#TODO старый метод оставлен для справки
        """
        Запрашивает удаление счёта через презентер.
        Презентер выполнит проверку на связанные операции и удалит счёт или вернёт ошибку.
        
        Args:
            account_id: ID удаляемого счёта
        """
        if self.presenter:
            try:
                self.presenter.delete_account(account_id)
            except ValueError as e:
                # Презентер пробросит ошибку, если есть операции или другие ограничения
                self.show_status(str(e), "error")
        else:
            self.show_status("Презентер не подключен", "error")

    def _on_context_delete(self, account_id: int):
        """Удаляет ОДИН счёт по ID с подтверждением.
        
        Args:
            account_id: ID удаляемого счёта
        """
        # Находим элемент по account_id для получения имени
        account_name = "Неизвестный"
        for i in range(self.accounts_tree.topLevelItemCount()):
            item = self.accounts_tree.topLevelItem(i)
            if item.data(0, Qt.UserRole) == account_id:
                account_name = item.text(0)
                break
        
        # Подтверждение для одного счёта
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить счёт '{account_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        if self.presenter:
            # Удаление одного счёта
            result = self.presenter.delete_account(account_id)
            if result.get('success'):
                self.show_status(f"Удалён: {account_name}", "success")
            else:
                if not result.get('can_delete', True):
                    self._show_cannot_delete_message({
                        'account_name': account_name,
                        'total_operations': result.get('total_operations', 0)
                    })
                else:
                    self.show_status(
                        f"Ошибка удаления '{account_name}': {result.get('message', 'Неизвестная ошибка')}",
                        "error"
                    )
        else:
            self.show_status("Презентер не подключен", "error")
        
    def _show_cannot_delete_message(self, result_info):
        """
        Показывает диалог с причиной невозможности удаления счёта.
        
        Args:
            result_info: словарь с ключами 'account_name', 'total_operations'
        """
        account_name = result_info.get('account_name', 'Счёт')
        total_ops = result_info.get('total_operations', 0)
        
        html_text = f"""
            <h3 style='color: #dc3545; margin-top: 0;'>❌ Счёт нельзя удалить</h3>
            <p>Счёт <b>{account_name.replace('<', '&lt;').replace('>', '&gt;')}</b> имеет связанные операции.</p>
            <p><b>Всего операций:</b> {total_ops}</p>
            <p style='color: #6c757d; margin-bottom: 0;'>
                Для удаления счёта необходимо сначала удалить все связанные операции 
                или перенести их на другие счета.
            </p>
        """
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Невозможно удалить счёт")
        dialog.resize(450, 220)
        
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(html_text)
        layout.addWidget(text_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.exec()

    def _show_account_stats(self): #TODO не рабочий (скопирован из V2)
        """Показывает статистику по выбранному счету"""
        selected_items = self.accounts_tree.selectedItems()
        if not selected_items:
            self.show_status("Выберите счет для статистики", "warning")
            return
        
        item = selected_items[0]
        account_id = item.data(0, Qt.UserRole)
        account_name = item.text(0)
        
        try:
            # Получаем данные счета
            account_obj = self.database.accounts.get_by_id(account_id)
            if account_obj is None:
                self.show_status("Данные счета не найдены", "error")
                return
            account_data = account_obj.to_dict()
            
            # Получаем транзакции
            transactions = self.database.transactions.get_transactions(filters={'account_id': account_id, 'exclude_corrections': True})
            
            # Получаем переводы
            transfers = self.database.transfers.get_transfers(filters={'account_id': account_id})
            
            # Вычисляем статистику
            total_income = 0.0
            total_expense = 0.0
            transaction_count = len(transactions)
            
            for t in transactions:
                amount = t['amount']
                if t['type'] == 'income':
                    total_income += amount
                elif t['type'] == 'expense':
                    total_expense += abs(amount)
            
            transfers_in = 0
            transfers_out = 0
            
            for t in transfers:
                if t['to_account_id'] == account_id:
                    transfers_in += 1
                elif t['from_account_id'] == account_id:
                    transfers_out += 1
            
            # Формируем сообщение
            stats_text = f"📊 Статистика счета: {account_data['name']}\n\n"
            stats_text += f"💰 Текущий баланс: {account_data['current_balance']:.2f} {account_data['currency']}\n"
            stats_text += f"📈 Всего доходов: {total_income:.2f} {account_data['currency']}\n"
            stats_text += f"📉 Всего расходов: {total_expense:.2f} {account_data['currency']}\n"
            stats_text += f"🔄 Чистый поток: {total_income - total_expense:.2f} {account_data['currency']}\n\n"
            
            stats_text += f"📋 Количество операций:\n"
            stats_text += f"   • Транзакций: {transaction_count}\n"
            stats_text += f"   • Входящих переводов: {transfers_in}\n"
            stats_text += f"   • Исходящих переводов: {transfers_out}\n"
            stats_text += f"   • Всего: {transaction_count + transfers_in + transfers_out}\n\n"
            
            stats_text += f"🗓️ Тип счета: {account_data['type']}\n"
            
            if account_data['type'] == 'Credit Card':
                stats_text += f"💳 Кредитный лимит: {account_data.get('credit_limit', 0.0):.2f} {account_data['currency']}\n"
                stats_text += f"📅 День платежа: {account_data.get('payment_due_day', 1)}\n"
                stats_text += f"📊 Мин. платеж: {account_data.get('min_payment_percent', 5.0):.1f}%\n"
            
            # Дата создания
            created_at = account_data.get('created_at', '')
            if created_at:
                if isinstance(created_at, str):
                    stats_text += f"📅 Создан: {created_at[:10]}\n"
            
            # Показываем диалог
            stats_dialog = QDialog(self)
            stats_dialog.setWindowTitle(f"Статистика: {account_data['name']}")
            stats_dialog.resize(400, 400)
            
            layout = QVBoxLayout(stats_dialog)
            
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            text_edit.setPlainText(stats_text)
            text_edit.setFont(QFont("Consolas", 10))
            
            layout.addWidget(text_edit)
            
            button_box = QDialogButtonBox(QDialogButtonBox.Ok)
            button_box.accepted.connect(stats_dialog.accept)
            layout.addWidget(button_box)
            
            stats_dialog.exec()
            
        except Exception as e:
            self.show_status(f"Ошибка статистики: {str(e)[:50]}", "error")
    

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

    def show_error(self, message: str):
        """
        Показывает критическое сообщение об ошибке.
        
        Args:
            message: текст ошибки
        """
        QMessageBox.critical(self, "Ошибка", message)
        #self.show_status(message, "error")

    def clear_selection(self):
        """Очищает выделение в таблице."""
        self.accounts_tree.clearSelection()
        self._reset_form()