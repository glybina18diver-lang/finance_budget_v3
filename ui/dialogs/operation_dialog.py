# ui/dialogs/operation_dialog.py
from datetime import datetime
from typing import List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QLineEdit, QComboBox, QFrame, QMessageBox, QWidget, QHeaderView, QDateEdit
)
from PySide6.QtCore import Qt, QTimer, QDate
from PySide6.QtGui import QFont, QDoubleValidator

from ui.widgets.colored_button import ColoredButton
from ui.dialogs.base_dialog import BaseDialog
from core.models import Transaction, Account, Category


class OperationDialog(BaseDialog):
    """Диалог управления операциями (чистый UI слой, без бизнес-логики)."""

    def __init__(self, parent=None, presenter=None):
        """
        Инициализация диалога.
        
        Args:
            parent: родительское окно (MainWindow)
            presenter: экземпляр TransactionPresenter для обработки действий
        """
        super().__init__(parent)
        self.parent = parent
        self.presenter = presenter
        self.setWindowTitle("Операции")
        self.resize(1200, 600)
        self._init_ui()
        # Загружаем данные через презентер (если он подключен)
        if self.presenter:
            self.presenter.set_view(self)  # ← Устанавливаем связь
        

    # ================= Создание интерфейса =================
    def _init_ui(self):
        """Инициализация интерфейса и компоновки элементов."""
        layout = self._main_layout
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        layout.addWidget(self._create_top_panel())
        layout.addWidget(self._create_filter_panel())
        layout.addWidget(self._create_input_panel())
        layout.addWidget(self._create_table(), stretch=1)
        layout.addWidget(self._create_bottom_panel())
        layout.addWidget(self.status_bar)

        # Фокус на поле суммы при открытии
        QTimer.singleShot(100, lambda: self.amount_input.setFocus())

    def _create_top_panel(self) -> QWidget:
        """Верхняя панель с кнопками навигации (все на заглушках)."""
        panel = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        buttons = [
            ("🏦 Счета", self._open_account_management, "#2196F3"), 
            ("📊 Категории", self._open_category_management, "#9C27B0"),
            ("📤 Переводы", self._open_transfer_dialog, "#FF9800"), 
            ("🔍 Сверка", self._stub_method, "#607D8B"),
            ("💰 Займы", self._stub_method, "#795548"), 
            ("💳 Кредитки", self._stub_method, "#E91E63")
        ]

        for text, callback, color in buttons:
            btn = ColoredButton(text, color)
            btn.clicked.connect(callback)
            layout.addWidget(btn)

            

        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def _create_filter_panel(self) -> QWidget:
        """Панель фильтров (визуальная заглушка)."""
        panel = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        labels = ["Тип:", "Категория:", "Счет:", "Период:", "Поиск:"]
        for lbl_text in labels:
            layout.addWidget(QLabel(lbl_text))
            combo = QComboBox()
            combo.addItem("Все")
            combo.setFixedHeight(26)
            combo.setMinimumWidth(100)
            combo.currentTextChanged.connect(self._stub_method)
            layout.addWidget(combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("по описанию...")
        self.search_input.setFixedHeight(26)
        self.search_input.textChanged.connect(self._stub_method)
        layout.addWidget(self.search_input)

        reset_btn = ColoredButton("Сбросить", "#6c757d")
        reset_btn.clicked.connect(self._stub_method)
        layout.addWidget(reset_btn)
        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def _create_input_panel(self) -> QWidget:
        """Панель ввода новой операции."""
        panel = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(QLabel("Новая:"))

        # Календарь (изолирован для легкой замены на кастомный виджет)
        self.date_input = self._init_date_widget()
        layout.addWidget(self.date_input)

        # Сумма (передается как строка, парсинг в сервисе)
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Сумма (100 или 100*3)")
        self.amount_input.setFixedHeight(26)
        self.amount_input.setMinimumWidth(120)
        layout.addWidget(self.amount_input)
        validator = QDoubleValidator(0.0, 999999999.0, 2)  # min=0, max=999M, 2 знака после запятой
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.amount_input.setValidator(validator)

        # Тип операции
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Расход", "Доход"])
        self.type_combo.setFixedHeight(26)
        self.type_combo.setMinimumWidth(80)
        
        # 🔗 Динамическое обновление категорий при смене типа
        self.type_combo.currentTextChanged.connect(
            lambda text: self.presenter.update_categories_for_type(text) if self.presenter else None
        )
        layout.addWidget(self.type_combo)

        # Категория (будут заполняться презентером)
        self.category_combo = QComboBox()
        self.category_combo.addItem(None, userData=None)  # ← Заглушка до загрузки данных
        self.category_combo.setFixedHeight(26)
        self.category_combo.setMinimumWidth(140)
        layout.addWidget(self.category_combo)

        # Счет
        self.account_combo = QComboBox()
        self.account_combo.addItem(None, userData=None)  # ← Заглушка до загрузки данных
        self.account_combo.setFixedHeight(26)
        self.account_combo.setMinimumWidth(120)
        layout.addWidget(self.account_combo)

        # Описание
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Описание...")
        self.description_input.setFixedHeight(26)
        self.description_input.setMinimumWidth(180)
        layout.addWidget(self.description_input)

        # Кнопка добавления
        add_btn = ColoredButton("✅ Добавить", "#28a745")
        add_btn.clicked.connect(self._get_form_data)
        layout.addWidget(add_btn)

        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def _init_date_widget(self) -> QDateEdit:
        """
        Создает виджет выбора даты.
        Вынесен отдельно, чтобы в будущем заменить на кастомный календарь.
        """
        date_edit = QDateEdit(QDate.currentDate())
        date_edit.setCalendarPopup(True)
        date_edit.setDisplayFormat("dd.MM.yyyy")
        date_edit.setFixedHeight(26)
        date_edit.setMinimumWidth(110)
        return date_edit

    def _create_table(self) -> QTreeWidget:
        """Таблица транзакций (сортировка включена)."""
        self.transactions_tree = QTreeWidget()
        self.transactions_tree.setHeaderLabels(["Дата", "Тип", "Сумма", "Кол-во", "Категория", "Счет", "Описание"])
        self.transactions_tree.setSortingEnabled(True)
        self.transactions_tree.sortItems(0, Qt.DescendingOrder)
        self.transactions_tree.setAlternatingRowColors(True)
        
        header = self.transactions_tree.header()
        header.setStretchLastSection(True)
        header.setSectionsClickable(True)
        
        # Контекстное меню (заглушка)
        self.transactions_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.transactions_tree.customContextMenuRequested.connect(self._stub_method)
        return self.transactions_tree

    def _create_bottom_panel(self) -> QWidget:
        """Нижняя панель с итогами и кнопками действий."""
        panel = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        self.summary_label = QLabel("Операций: 0 | Доход: 0,00 ₽ | Расход: 0,00 ₽")
        self.summary_label.setFixedHeight(26)
        layout.addWidget(self.summary_label)
        layout.addStretch()

        export_btn = ColoredButton("📥 Экспорт", "#17a2b8")
        export_btn.clicked.connect(self._stub_method)
        layout.addWidget(export_btn)

        close_btn = ColoredButton("❌ Закрыть", "#dc3545")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        panel.setLayout(layout)
        return panel

    # ================= Контракт View <-> Presenter =================

    def clear_form(self):
        """Сбрасывает поля ввода формы к значениям по умолчанию."""
        self.amount_input.clear()
        self.description_input.clear()
        self.date_input.setDate(QDate.currentDate())
        self.type_combo.setCurrentIndex(0)  # Расход
        #self.show_status("Форма очищена", "info")

    def create_caches(self, accounts: List[Account], categories: List[Category]):
        """
        Принимает списки счетов и категорий и создаёт локальные кэши.
        
        Args:
            accounts: список объектов Account
            categories: список объектов Category
        """
        self._account_cache = {acc.id: acc for acc in accounts}
        self._category_cache = {cat.id: cat for cat in categories}

    def refresh_transactions(self):
        """
        Обновляет таблицу транзакций, запрашивая свежие данные через презентер.
        Вызывается после добавления или удаления операции.
        """
        if self.presenter:
            # Просим презентер перезагрузить последние 300 записей
            self.presenter.initial_load_transactions(limit=300)
            #self.show_status("Таблица обновлена", message_type="success")
        else:
            self.show_error("Презентер не подключен или ошибка метода")

    # ================= Обработчики событий =================

    def _get_form_data(self):
        """Собирает данные из формы и передает их презентеру. (добовляет операцию)"""
        raw_amount = self.amount_input.text().strip()
        if not raw_amount:
            self.show_error("Введите сумму")
            return

        # Получаем ID из userData комбобоксов (НЕ из текста и НЕ из индекса!)
        account_id = self.account_combo.currentData()
        category_id = self.category_combo.currentData()
        
        # Валидация обязательных полей
        if not account_id:
            self.show_error("Выберите счёт")
            return
            
        # Для типа "Корректировка" категория может быть None, но у тебя пока только Доход/Расход
        if not category_id:
            self.show_status("Выберите категорию", message_type="error")
            return

        trans_type = "income" if self.type_combo.currentText() == "Доход" else "expense"
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        description = self.description_input.text().strip()

        try:
            self.presenter.add_transaction(
                raw_amount=raw_amount,
                trans_type=trans_type,
                account_id=account_id,      # ← Должен быть int
                category_id=category_id,    # ← Должен быть int
                description=description,
                date_str=date_str
            )
        except AttributeError:
            self.show_status("Презентер не подключен", message_type="error")



    #============Загрузка данных и заполнение UI============
    def load_accounts_combos(self, accounts: List):
        """
        Заполняет комбобоксы счетов данными из БД.
        Вызывается презентером.
        
        Args:
            accounts: список объектов Account из презентера
        """
        # Очищаем оба комбобокса
        self.account_combo.clear()
        #self.account_filter_combo.clear()
        
        # Добавляем опцию "Все счета" в фильтр
        #self.account_filter_combo.addItem("Все счета", userData=None)
        
        if not accounts:
            # Если счетов нет, показываем подсказку
            self.account_combo.addItem("Нет активных счетов", userData=None)
            self.show_status("⚠️ Нет активных счетов. Создайте счёт в управлении счетами.", message_type="warning")
            return
        
        # Заполняем комбобоксы реальными счетами
        for account in accounts:
            # Формируем текст с балансом
            display_text = f"{account.name} ({account.current_balance:,.2f} {account.currency})"
            
            # Добавляем в комбобокс ввода (основной)
            self.account_combo.addItem(display_text, userData=account.id)
            
            # Добавляем в комбобокс фильтра
            #self.account_filter_combo.addItem(display_text, userData=account.id)
        
        # Выбираем первый счёт по умолчанию (если есть)
        if len(accounts) > 0:
            self.account_combo.setCurrentIndex(0)
            
        self.show_status(f"Загружено {len(accounts)} счёт(ов)", "success")

    def load_categories_combos(self, categories: List):
        """
        Заполняет комбобокс категорий данными из БД.
        Вызывается презентером.

        Args:
            categories: список объектов Categories
        """
        self.category_combo.clear()
        
        if not categories:
            self.category_combo.addItem("Нет категорий", userData=None)
            self.show_status("⚠️ Нет доступных категорий", message_type="warning")
            return

        for cat in categories:
            # text = имя, userData = ID категории
            self.category_combo.addItem(cat.name, userData=cat.id)
        
        # Выбираем первую категорию по умолчанию
        self.category_combo.setCurrentIndex(0)

    def initial_load_transactions(self, transactions: List[Transaction]):
        """Публичный интерфейс для презентера. (загрузка транзакций при открытии диалога)"""
        rows = self._prepare_transaction_rows(transactions)
        self._render_transaction_table(rows)
        self.show_status(f"Загружено {len(transactions)} операций", message_type="success")

    #========== Загрузка данных для таблицы и заполнение ==========
    def _prepare_transaction_rows(self, transactions: List[Transaction]) -> List[dict]:
        """
        Подготавливает данные транзакций для отображения.
        Возвращает список словарей с готовыми строками таблицы.
        
        Args:
            transactions: список объектов Transaction
            
        Returns:
            Список словарей: {
                'date': str,
                'type': str,
                'amount_str': str,
                'quantity_str': str,
                'category_name': str,
                'account_name': str,
                'description': str,
                'transaction_id': int
            }
        """
        rows = []
        for tx in transactions:
            # Получаем данные из кэшей
            account = self._account_cache.get(tx.account_id)
            category = self._category_cache.get(tx.category_id) if tx.category_id else None
            
            currency = account.currency if account else "–"
            account_name = account.name if account else "–"
            category_name = category.name if category else "–"
            
            amount_str = f"{tx.amount:+,.2f} {currency}"
            qty_str = f"{tx.quantity:.2f}" if tx.quantity != 1.0 else "1"
            type_str = "Доход" if tx.trans_type == "income" else "Расход"
            
            rows.append({
                'date': tx.date,
                'type': type_str,
                'amount_str': amount_str,
                'quantity_str': qty_str,
                'category_name': category_name,
                'account_name': account_name,
                'description': tx.description,
                'transaction_id': tx.id
            })
        return rows
    
    def _render_transaction_table(self, rows: List[dict]):
        """Отрисовывает подготовленные строки в QTreeWidget."""
        self.transactions_tree.clear()
        
        for row in rows:
            item = QTreeWidgetItem([
                row['date'],
                row['type'],
                row['amount_str'],
                row['quantity_str'],
                row['category_name'],
                row['account_name'],
                row['description']
            ])
            item.setData(0, Qt.UserRole, row['transaction_id'])
            self.transactions_tree.addTopLevelItem(item)

    #========== Открытие диалогов ==========
    def _open_account_management(self):
        """
        Открывает диалог управления счетами через навигационный сервис.
        """
        if hasattr(self.parent, 'navigation_service'):
            self.parent.navigation_service.open_account_dialog(self.parent)
        else:
            self.show_status("Навигация недоступна", message_type="error")

    def _open_category_management(self):
        """
        Открывает диалог управления категориями через навигационный сервис.
        """
        if hasattr(self.parent, 'navigation_service'):
            self.parent.navigation_service.open_category_dialog(self.parent)
        else:
            self.show_status("Навигация недоступна", message_type="error")

    def _open_transfer_dialog(self):
        """
        Открывает диалог переводов через навигационный сервис.
        """
        if hasattr(self.parent, 'navigation_service'):
            self.parent.navigation_service.open_transfer_dialog(self.parent)
        else:
            self.show_status("Навигация недоступна", message_type="error")
    
    #========== Функции (прочие) ==========