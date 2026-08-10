# ui/dialogs/operation_dialog.py
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from typing import List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QLineEdit, QComboBox, QFrame, QMessageBox, QWidget, QHeaderView, QDateEdit, QPushButton, QTextEdit, QMenu
)
from PySide6.QtCore import Qt, QTimer, QDate
from PySide6.QtGui import QFont, QDoubleValidator

from ui.widgets.buttons import OperationButton, CompactButton
from ui.dialogs.base_dialog import BaseDialog
from core.models import Transaction, Account, Category

logger = logging.getLogger(__name__)


class OperationDialog(BaseDialog):
    """Диалог управления операциями (чистый UI слой, без бизнес-логики)."""

    def __init__(self, parent=None, presenter=None, navigation_service: Optional[Any] = None):
        """
        Инициализация диалога.
        
        Args:
            parent: родительское окно (MainWindow)
            presenter: экземпляр TransactionPresenter для обработки действий
        """
        super().__init__(parent)
        self.parent = parent
        self.presenter = presenter
        self.navigation_service = navigation_service
        self.setWindowTitle("Операции")
        self.resize(1200, 600)
        self._init_ui()
        # Загружаем данные через презентер (если он подключен)
        if self.presenter:
            self.presenter.set_view(self)  # ← Устанавливаем связь
        # Заполняем комбоксы фильтров
        self.load_filter_combos()
        

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
            ("🏦 Счета", self._open_account_management, "accounts"),
            ("📊 Категории", self._open_category_management, "categories"),
            ("📤 Переводы", self._open_transfer_dialog, "transfers"),
            # ("🔍 Сверка", self._stub_method, "reconciliation"),
            ("💰 Займы", self._open_loan_dialog, "loans"),
            ("💳 Кредитные карты", self._open_credit_card_dialog, "credit_cards"),
        ]

        for text, handler, purpose in buttons:
            btn = OperationButton(text, purpose=purpose)
            btn.clicked.connect(handler)
            layout.addWidget(btn)

            

        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def _create_filter_panel(self) -> QWidget:
        """
        Панель фильтров для операций.

        Содержит фильтры по типу, категории, счёту, периоду и поиску по описанию.
        Все изменения автоматически применяют фильтры через _apply_filters().

        Returns:
            QWidget с панелью фильтров
        """
        panel = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 0)

        # --- Период ---
        layout.addWidget(QLabel("С:"))
        self.filter_date_from = QDateEdit()
        self.filter_date_from.setCalendarPopup(True)
        self.filter_date_from.setDisplayFormat("dd.MM.yyyy")
        self.filter_date_from.setDate(QDate.currentDate().addMonths(-1))
        self.filter_date_from.setFixedHeight(26)
        self.filter_date_from.dateChanged.connect(self._apply_filters)
        layout.addWidget(self.filter_date_from)

        layout.addWidget(QLabel("По:"))
        self.filter_date_to = QDateEdit()
        self.filter_date_to.setCalendarPopup(True)
        self.filter_date_to.setDisplayFormat("dd.MM.yyyy")
        self.filter_date_to.setDate(QDate.currentDate())
        self.filter_date_to.setFixedHeight(26)
        self.filter_date_to.dateChanged.connect(self._apply_filters)
        layout.addWidget(self.filter_date_to)

        # --- Тип ---
        layout.addWidget(QLabel("Тип:"))
        self.filter_type_combo = QComboBox()
        self.filter_type_combo.addItems(["Все", "Доход", "Расход", "Возврат"])
        self.filter_type_combo.setFixedHeight(26)
        self.filter_type_combo.setMinimumWidth(90)
        self.filter_type_combo.currentTextChanged.connect(self._apply_filters)
        layout.addWidget(self.filter_type_combo)

        # --- Счёт ---
        layout.addWidget(QLabel("Счёт:"))
        self.filter_account_combo = QComboBox()
        self.filter_account_combo.addItem("Все", userData=None)
        self.filter_account_combo.setFixedHeight(26)
        self.filter_account_combo.setMinimumWidth(120)
        self.filter_account_combo.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.filter_account_combo)

        # --- Категория ---
        layout.addWidget(QLabel("Категория:"))
        self.filter_category_combo = QComboBox()
        self.filter_category_combo.addItem("Все", userData=None)
        self.filter_category_combo.setFixedHeight(26)
        self.filter_category_combo.setMinimumWidth(130)
        self.filter_category_combo.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.filter_category_combo)

        # --- Поиск ---
        self.filter_search = QLineEdit()
        self.filter_search.setPlaceholderText("🔍 поиск по описанию...")
        self.filter_search.setFixedHeight(26)
        self.filter_search.setMinimumWidth(150)
        self.filter_search.textChanged.connect(self._on_search_changed)
        layout.addWidget(self.filter_search)

        # --- Кнопка сброса ---
        reset_btn = CompactButton("Сбросить", "info")
        reset_btn.clicked.connect(self._reset_filters)
        layout.addWidget(reset_btn)

        layout.addStretch()
        panel.setLayout(layout)
        return panel
    
    def keyPressEvent(self, event):
        """
        Обрабатывает нажатие клавиш в диалоге операций.
        
        Перехватывает:
        - Enter для вызова _get_form_data (добавление операции)
        - Delete для удаления выбранной транзакции
        
        Args:
            event: событие нажатия клавиши
        """
        key = event.key()
        
        # Обработка Enter (добавление операции)
        if key in (Qt.Key_Return, Qt.Key_Enter):
            # Игнорируем, если фокус в многострочном поле (чтобы не ломать перенос строки)
            focus_widget = self.focusWidget()
            if not isinstance(focus_widget, QTextEdit):
                self._get_form_data()
                event.accept()
                return
        
        # Обработка Delete (удаление транзакции)
        elif key == Qt.Key_Delete:
            # Проверяем, что есть выбранная транзакция в таблице
            selected_items = self.transactions_tree.selectedItems()
            if selected_items:
                self.delete_transaction()
                event.accept()
                return
        
        super().keyPressEvent(event)

    def _create_input_panel(self) -> QWidget:
        """Панель ввода новой операции."""
        panel = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 2)

        layout.addWidget(QLabel("Новая:"))

        # Сумма (передается как строка, парсинг в сервисе)
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Сумма (100 или 100*3)")
        self.amount_input.setFixedHeight(26)
        self.amount_input.setMinimumWidth(120)
        layout.addWidget(self.amount_input)
        self.amount_input.setFocus()
        # validator = QDoubleValidator(0.0, 999999999.0, 2)  # min=0, max=999M, 2 знака после запятой
        # # validator.setNotation(QDoubleValidator.StandardNotation)
        # self.amount_input.setValidator(validator)

        # Календарь (изолирован для легкой замены на кастомный виджет)
        self.date_input = self._init_date_widget()
        layout.addWidget(self.date_input)

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

        self.add_btn = CompactButton("Добавить")
        self.add_btn.clicked.connect(self._get_form_data)
        
        # Делаем кнопку активной по нажатию Enter
        self.add_btn.setDefault(True) 
        
        layout.addWidget(self.add_btn)
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

        self.transactions_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.transactions_tree.setSelectionBehavior(QTreeWidget.SelectRows)

        header = self.transactions_tree.header()
        header.setStretchLastSection(True)
        header.setSectionsClickable(True)
        
        # Контекстное меню (заглушка)
        self.transactions_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.transactions_tree.customContextMenuRequested.connect(self._show_transactions_context_menu)
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

        export_btn = CompactButton("📥 Экспорт", "neutral") 
        export_btn.clicked.connect(self._stub_method)
        layout.addWidget(export_btn)

        close_btn = CompactButton("❌ Закрыть", "danger")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        panel.setLayout(layout)
        return panel

    # ================= Контракт View <-> Presenter =================

    def clear_form(self):
        """Сбрасывает поля ввода формы к значениям по умолчанию."""
        self.amount_input.clear()
        self.description_input.clear()

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
        Обновляет таблицу транзакций с учётом текущих фильтров.

        Если панель фильтров активна — применяет фильтры.
        Иначе загружает последние 300 записей.
        """
        if self.presenter:
            # Проверяем, есть ли активные фильтры
            has_filters = (
                self.filter_type_combo.currentText() != "Все"
                or self.filter_account_combo.currentData() is not None
                or self.filter_category_combo.currentData() is not None
                or self.filter_search.text().strip()
            )
            if has_filters:
                self._apply_filters()
            else:
                self.presenter.load_transactions()
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
            
        if not category_id:
            self.show_error("Выберите категорию")
            return

        # преаброзем тип для записи в БД
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
        except Exception as e:
            logger.error("[OperationDialog] Ошибка при добавлении транзакции: %s", e, exc_info=True)



    #============Загрузка данных и заполнение UI============
    def load_accounts_combos(self, accounts: List):
        """
        Заполняет комбобоксы счетов данными из БД (исключая системные).
        Вызывается презентером.

        Args:
            accounts: список объектов Account из презентера
            
        Note:
            Системные счета (is_system=True) исключаются из комбобокса
        """
        try:
            self.account_combo.clear()
            
            if not accounts:
                self.account_combo.addItem("Нет счетов", userData=None)
                self.show_status("⚠️ Нет доступных счетов. Создайте счёт в управлении счетами.", message_type="warning")
                return

            # Фильтруем системные счета
            user_accounts = [account for account in accounts if not getattr(account, 'is_system', False)]
            
            if not user_accounts:
                self.account_combo.addItem("Нет пользовательских счетов", userData=None)
                self.show_status("⚠️ Нет пользовательских счетов. Все существующие счета являются системными.", message_type="warning")
                return
        
            # Заполняем комбобоксы реальными счетами
            for account in user_accounts:
                # Формируем текст с балансом
                display_text = f"{account.name} ({account.current_balance:,.2f} {account.currency})"
                
                # Добавляем в основной комбобокс
                self.account_combo.addItem(display_text, userData=account.id)
                
                # Если нужен комбобокс фильтра - раскомментируйте:
                # self.account_filter_combo.addItem(display_text, userData=account.id)
            
            # Выбираем первый счёт по умолчанию
            self.account_combo.setCurrentIndex(0)

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка загрузки счетов: {e}", exc_info=True)
            self.show_status("Ошибка загрузки счетов", message_type="error")

    def load_categories_combos(self, categories: List[Category]):
        """
        Заполняет комбобокс категорий данными из БД в виде дерева.
        Вызывается презентером.

        Args:
            categories: список объектов Category
        """
        try:
            self.category_combo.clear()
            if not categories:
                self.category_combo.addItem("Нет категорий", userData=None)
                self.show_status("️ Нет доступных категорий", message_type="warning")
                return

            # Фильтруем системные категории
            user_categories = [
                cat for cat in categories
                if not getattr(cat, 'is_system', False)
            ]
            if not user_categories:
                self.category_combo.addItem("Нет пользовательских категорий", userData=None)
                self.show_status("⚠️ Нет пользовательских категорий", message_type="warning")
                return

            # Заполняем комбобокс деревом
            self._load_categories_to_combo(self.category_combo, categories)

            # Выбираем первую категорию по умолчанию
            self.category_combo.setCurrentIndex(0)

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка загрузки категорий: {e}", exc_info=True)
            self.show_status("Ошибка загрузки категорий", message_type="error")

    def load_transactions(self, transactions: List[Transaction]):
        """
        Публичный интерфейс для презентера. 
        (загрузка транзакций при открытии диалога и последущих обновлениях таблицы)
        """
        rows = self._prepare_transaction_rows(transactions)
        self._render_transaction_table(rows)
        # self.show_status(f"Загружено {len(transactions)} операций", message_type="success")

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
            # Маппинг типов транзакций
            type_map = {
                "income": "Доход",
                "expense": "Расход",
                "refund": "Возврат",
                "correct": "Корректировка",
            }
            type_str = type_map.get(tx.trans_type, tx.trans_type)
            
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
        """Открывает диалог управления счетами."""
        if hasattr(self.parent, 'navigation_service'):
            dialog = self.parent.navigation_service.open_account_dialog(self.parent)
            if dialog:
                dialog.finished.connect(self._on_child_dialog_closed)
        else:
            self.show_status("Навигация недоступна", message_type="error")

    def _open_category_management(self):
        """Открывает управление категориями."""
        if hasattr(self.parent, 'navigation_service'):
            dialog = self.parent.navigation_service.open_category_dialog(self.parent)
            if dialog:
                dialog.finished.connect(self._on_child_dialog_closed)
        else:
            self.show_status("Навигация недоступна", message_type="error")

    def _open_transfer_dialog(self):
        """Открывает диалог переводов."""
        if hasattr(self.parent, 'navigation_service'):
            dialog = self.parent.navigation_service.open_transfer_dialog(self.parent)
            if dialog:
                dialog.finished.connect(self._on_child_dialog_closed)
        else:
            self.show_status("Навигация недоступна", message_type="error")

    def _open_loan_dialog(self):
        """Открывает диалог управления займами."""
        if hasattr(self.parent, 'navigation_service'):
            dialog = self.parent.navigation_service.open_loan_dialog(self.parent)
            if dialog:
                dialog.finished.connect(self._on_child_dialog_closed)
        else:
            self.show_status("Навигация недоступна", message_type="error")

    def _open_credit_card_dialog(self):
        """Открывает диалог управления кредитными картами."""
        if hasattr(self.parent, 'navigation_service'):
            dialog = self.parent.navigation_service.open_credit_card_dialog(self.parent)
            if dialog:
                dialog.finished.connect(self._on_child_dialog_closed)
        else:
            self.show_status("Навигация недоступна", message_type="error")

    def _on_child_dialog_closed(self):
        """
        Вызывается при закрытии любого дочернего диалога.
        Запускает полное обновление данных (счета, категории, транзакции) через презентер.
        """
        if self.presenter:
            # Сохраняем текущий выбранный тип, чтобы не сбрасывать выбор пользователя
            current_type = self.type_combo.currentText()
            self.presenter.refresh_data(current_type)
            self.show_status("Данные успешно обновлены", message_type="success")
    
    #========== Функции (прочие) ==========
    def _show_transactions_context_menu(self, position):
        """
        Показывает контекстное меню для выбранной транзакции.

        Args:
            position: позиция курсора в координатах виджета
        """
        try:
            item = self.transactions_tree.itemAt(position)
            if not item:
                return

            # Выделяем строку под курсором
            self.transactions_tree.setCurrentItem(item)

            menu = QMenu(self)

            # Получаем тип транзакции из второго столбца (индекс 1)
            transaction_type = item.text(1)
            transaction_id = item.data(0, Qt.UserRole)

            # Создать возврат - только для доход/расход
            return_action = menu.addAction("↩ Создать возврат")
            return_action.triggered.connect(self._create_refund_with_options)
            if transaction_type not in ["Доход", "Расход"]:
                return_action.setEnabled(False)

            menu.addSeparator()

            # Редактировать
            edit_action = menu.addAction("✏️ Редактировать")
            edit_action.triggered.connect(self._edit_transaction)

            # Дублировать
            duplicate_action = menu.addAction("🔄 Дублировать (с настройками)")
            duplicate_action.triggered.connect(self._duplicate_transaction_with_options)

            menu.addSeparator()

            # Показать детали
            details_action = menu.addAction("🔍 Показать детали")
            details_action.triggered.connect(self._show_transaction_details)

            menu.addSeparator()

            # Удалить
            delete_action = menu.addAction("❌ Удалить")
            delete_action.triggered.connect(self.delete_transaction)

            # Показываем меню в позиции курсора
            menu.exec(self.transactions_tree.viewport().mapToGlobal(position))

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка контекстного меню: {e}", exc_info=True)

    def delete_transaction(self):
        """
        Удаляет выбранную транзакцию после подтверждения пользователя.
        
        Получает ID транзакции из выбранной строки таблицы,
        запрашивает подтверждение и вызывает метод презентера.
        После успешного удаления обновляет таблицу операций.
        
        Raises:
            ValueError: если не выбрана транзакция или презентер не подключен
        """
        try:
            # Получаем выбранную строку
            selected_items = self.transactions_tree.selectedItems()
            if not selected_items:
                raise ValueError("Не выбрана транзакция для удаления")
            
            item = selected_items[0]
            tx_id = item.data(0, Qt.UserRole)
            
            if tx_id is None:
                raise ValueError("Не удалось получить ID транзакции")
            
            if not self.presenter:
                self.show_status("Презентер не подключен", message_type="error")
            
            # Запрашиваем подтверждение
            reply = QMessageBox.question(
                self,
                "Подтверждение удаления",
                f"Вы уверены, что хотите удалить эту операцию?\n\n"
                f"Дата: {item.text(0)}\n"
                f"Сумма: {item.text(2)}\n"
                f"Категория: {item.text(4)}",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Вызываем метод презентера
                self.presenter.delete_transaction(tx_id)
                        
        except ValueError as e:
            # Ожидаемые ошибки валидации
            logger.warning(f"[{self.__class__.__name__}] Валидация удаления: {e}")
            self.show_status(str(e), "error")
        
        except Exception as e:
            # Системные ошибки
            logger.error(f"[{self.__class__.__name__}] Ошибка удаления транзакции: {e}", exc_info=True)
            self.show_status("Произошла ошибка при удалении операции", "error")

    def _duplicate_transaction_with_options(self):
        """Открывает диалог дублирования транзакции с настройками."""
        try:
            # Получаем выбранную транзакцию
            selected_items = self.transactions_tree.selectedItems()
            if not selected_items:
                raise ValueError("Выберите операцию для дублирования")
            
            transaction_id = selected_items[0].data(0, Qt.UserRole)
            if not transaction_id:
                raise ValueError("Не удалось получить ID транзакции")
            
            # Получаем транзакцию через презентер
            transaction = self.presenter.get_transaction_by_id(transaction_id)
            if not transaction:
                raise ValueError("Операция не найдена")
            
            # Проверяем тип
            if transaction.trans_type not in ['income', 'expense']:
                raise ValueError("Дублировать можно только доходы и расходы")
            
            # Получаем названия из кэша
            account = self._account_cache.get(transaction.account_id)
            category = self._category_cache.get(transaction.category_id) if transaction.category_id else None
            
            account_name = account.name if account else "—"
            category_name = category.name if category else "—"
            currency = account.currency if account else "₽"
            
            # Импортируем и открываем диалог
            from ui.dialogs.duplicate_dialog import DuplicateTransactionDialog
            
            dialog = DuplicateTransactionDialog(
                transaction=transaction,
                account_name=account_name,
                category_name=category_name,
                currency=currency,
                parent=self
            )
            
            if dialog.exec():
                data = dialog.get_duplicate_data()
                
                # Формируем raw_amount
                if data['quantity'] != 1.0:
                    raw_amount = f"{data['amount']}*{data['quantity']}"
                else:
                    raw_amount = str(data['amount'])
                
                # Создаём копию
                self.presenter.add_transaction(
                    raw_amount=raw_amount,
                    trans_type=transaction.trans_type,
                    account_id=transaction.account_id,
                    category_id=transaction.category_id,
                    description=data['description'],
                    date_str=data['date']
                )
                
                self.refresh_transactions()
                self.show_status("Копия операции создана", message_type="success")
                logger.info(f"[{self.__class__.__name__}] Дублирована транзакция ID={transaction_id}")
        
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация дублирования: {e}")
            self.show_status(str(e), message_type="error")
        
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка дублирования: {e}", exc_info=True)
            self.show_status("Ошибка при дублировании", message_type="error")

    def _edit_transaction(self):
        """Открывает диалог редактирования выбранной транзакции."""
        try:
            selected_items = self.transactions_tree.selectedItems()
            if not selected_items:
                raise ValueError("Выберите операцию для редактирования")
            
            transaction_id = selected_items[0].data(0, Qt.UserRole)
            if not transaction_id:
                raise ValueError("Не удалось получить ID транзакции")
            
            transaction = self.presenter.get_transaction_by_id(transaction_id)
            if not transaction:
                raise ValueError("Операция не найдена")
            
            from ui.dialogs.edit_transaction_dialog import EditTransactionDialog
            
            dialog = EditTransactionDialog(
                parent=self,
                presenter=self.presenter,
                transaction=transaction,
                account_cache=self._account_cache,
                category_cache=self._category_cache
            )
            
            dialog.data_updated.connect(self.refresh_transactions)
            dialog.exec()
        
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация редактирования: {e}")
            self.show_status(str(e), message_type="error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка редактирования: {e}", exc_info=True)
            self.show_status("Ошибка при открытии диалога редактирования", message_type="error")

    def _create_refund_with_options(self):
        """
        Открывает диалог создания возврата для выбранной транзакции.

        Получает оригинальную транзакцию, рассчитывает доступную сумму возврата
        (с учётом уже существующих возвратов) и открывает модальное окно
        RefundDialog. После подтверждения вызывает презентер для создания возврата.

        Raises:
            ValueError: если не выбрана транзакция или она не подходит для возврата
            Exception: при системных ошибках
        """
        try:
            # 1. Получаем выбранную транзакцию
            selected_items = self.transactions_tree.selectedItems()
            if not selected_items:
                raise ValueError("Выберите операцию для создания возврата")

            transaction_id = selected_items[0].data(0, Qt.UserRole)
            if not transaction_id:
                raise ValueError("Не удалось получить ID транзакции")

            if not self.presenter:
                raise ValueError("Презентер не подключен")

            # 2. Получаем оригинальную транзакцию
            transaction = self.presenter.get_transaction_by_id(transaction_id)
            if not transaction:
                raise ValueError("Операция не найдена в базе данных")

            # 3. Проверяем тип транзакции
            if transaction.trans_type not in ["income", "expense"]:
                raise ValueError(
                    "Возврат можно создать только для операции типа Доход или Расход"
                )

            # 4. Получаем названия из кэша
            account = self._account_cache.get(transaction.account_id)
            category = (
                self._category_cache.get(transaction.category_id)
                if transaction.category_id
                else None
            )
            account_name = account.name if account else "—"
            category_name = category.name if category else "—"
            currency = account.currency if account else "₽"

            # 5. Рассчитываем доступную сумму возврата через презентер
            refund_info = self.presenter.get_refund_info(transaction_id)
            max_refundable = refund_info["max_refundable"]
            already_refunded = refund_info["already_refunded"]

            if max_refundable <= 0:
                raise ValueError("Полный возврат по этой операции уже создан")

            # 6. Открываем диалог
            from ui.dialogs.refund_dialog import RefundDialog

            dialog = RefundDialog(
                parent=self,
                transaction=transaction,
                max_refundable=max_refundable,
                already_refunded=already_refunded,
                account_name=account_name,
                category_name=category_name,
                currency=currency,
            )

            if dialog.exec():
                data = dialog.get_refund_data()

                # 7. Создаём возврат через презентер
                self.presenter.create_refund(
                    original_transaction_id=transaction_id,
                    data=data,
                )

                # 8. Обновляем таблицу
                self.refresh_transactions()
                self.show_status(
                    f"Возврат на {data['amount']:.2f} {currency} успешно создан",
                    message_type="success",
                )
                logger.info(
                    f"[{self.__class__.__name__}] Создан возврат для транзакции "
                    f"ID={transaction_id}, сумма={data['amount']}"
                )

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация возврата: {e}")
            self.show_status(str(e), message_type="error")

        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка создания возврата: {e}",
                exc_info=True,
            )
            self.show_status("Произошла ошибка при создании возврата", message_type="error")

    def _show_transaction_details(self):
        """
        Открывает диалог с подробной информацией о выбранной транзакции.
        """
        try:
            selected_items = self.transactions_tree.selectedItems()
            if not selected_items:
                raise ValueError("Выберите операцию для просмотра деталей")

            transaction_id = selected_items[0].data(0, Qt.UserRole)
            if not transaction_id:
                raise ValueError("Не удалось получить ID транзакции")

            transaction = self.presenter.get_transaction_by_id(transaction_id)
            if not transaction:
                raise ValueError("Операция не найдена")

            # Получаем данные из кэша
            account = self._account_cache.get(transaction.account_id)
            category = self._category_cache.get(transaction.category_id) if transaction.category_id else None

            type_map = {
                "income": "Доход",
                "expense": "Расход",
                "refund": "Возврат",
                "correct": "Корректировка",
            }
            type_str = type_map.get(transaction.trans_type, transaction.trans_type)

            details = (
                f"ID: {transaction.id}\n"
                f"Дата: {transaction.date}\n"
                f"Тип: {type_str}\n"
                f"Сумма: {transaction.amount:+,.2f}\n"
                f"Количество: {transaction.quantity}\n"
                f"Счёт: {account.name if account else '—'}\n"
                f"Категория: {category.name if category else '—'}\n"
                f"Описание: {transaction.description or '—'}\n"
            )

            if transaction.original_transaction_id:
                details += f"Оригинальная транзакция: #{transaction.original_transaction_id}\n"

            QMessageBox.information(self, "Детали операции", details)

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация деталей: {e}")
            self.show_status(str(e), message_type="error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка показа деталей: {e}", exc_info=True)
            self.show_status("Ошибка при открытии деталей", message_type="error")

    # ================= Фильтры =================
    def _on_search_changed(self, text: str):
        """
        Обрабатывает изменение текста поиска с задержкой (debounce).

        Использует QTimer, чтобы не дёргать БД при каждом нажатии клавиши.

        Args:
            text: текущий текст в поле поиска
        """
        if not hasattr(self, '_search_timer'):
            self._search_timer = QTimer()
            self._search_timer.setSingleShot(True)
            self._search_timer.timeout.connect(self._apply_filters)
        self._search_timer.start(300)  # 300 мс задержка

    def _apply_filters(self):
        """
        Собирает параметры фильтров из UI и передаёт их в презентер.

        Вызывается автоматически при изменении любого фильтра.
        Если все фильтры сброшены, загружает данные без ограничений.
        """
        try:
            if not self.presenter:
                return

            # Собираем параметры
            filters = {}

            # Период
            date_from = self.filter_date_from.date().toString("yyyy-MM-dd")
            date_to = self.filter_date_to.date().toString("yyyy-MM-dd")
            if date_from:
                filters['date_from'] = date_from
            if date_to:
                filters['date_to'] = date_to

            # Тип
            type_text = self.filter_type_combo.currentText()
            type_map = {
                "Доход": "income",
                "Расход": "expense",
                "Возврат": "refund",
            }
            if type_text in type_map:
                filters['trans_type'] = type_map[type_text]
            # "Все" — не добавляем фильтр
    
            # Счёт
            account_id = self.filter_account_combo.currentData()
            if account_id:
                filters['account_id'] = account_id

            # Категория
            category_id = self.filter_category_combo.currentData()
            if category_id:
                filters['category_id'] = category_id

            # Поиск
            search_text = self.filter_search.text().strip()
            if search_text:
                filters['search'] = search_text

            # Загружаем через презентер
            self.presenter.load_with_filters(filters if filters else None)

            logger.debug(f"[{self.__class__.__name__}] Применены фильтры: {filters}")

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация фильтров: {e}")
            self.show_status(str(e), message_type="error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка применения фильтров: {e}", exc_info=True)
            self.show_status("Ошибка применения фильтров", message_type="error")


    def _reset_filters(self):
        """
        Сбрасывает все фильтры к значениям по умолчанию и перезагружает таблицу.
        """
        try:
            self.filter_date_from.setDate(QDate.currentDate().addMonths(-1))
            self.filter_date_to.setDate(QDate.currentDate())
            self.filter_type_combo.setCurrentIndex(0)  # "Все"
            self.filter_account_combo.setCurrentIndex(0)  # "Все"
            self.filter_category_combo.setCurrentIndex(0)  # "Все"
            self.filter_search.clear()

            # Загружаем без фильтров
            if self.presenter:
                self.presenter.load_with_filters(None)

            self.show_status("Фильтры сброшены", message_type="info")
            logger.debug(f"[{self.__class__.__name__}] Фильтры сброшены")

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка сброса фильтров: {e}", exc_info=True)
            self.show_status("Ошибка сброса фильтров", message_type="error")

    def load_filter_combos(self):
        """
        Заполняет комбобоксы фильтров данными из локальных кэшей.
        Использует self._account_cache и self._category_cache,
        которые должны быть инициализированы методом create_caches().
        Фильтрует системные объекты (is_system=True).
        """
        try:
            # Счета
            self.filter_account_combo.clear()
            self.filter_account_combo.addItem("Все", userData=None)

            if hasattr(self, '_account_cache') and self._account_cache:
                user_accounts = [
                    acc for acc in self._account_cache.values()
                    if not getattr(acc, 'is_system', False)
                ]
                for account in user_accounts:
                    display_text = f"{account.name} ({account.currency})"
                    self.filter_account_combo.addItem(display_text, userData=account.id)
            else:
                logger.warning(f"[{self.__class__.__name__}] Кэш счетов не инициализирован")

            # Категории (дерево)
            self.filter_category_combo.clear()
            self.filter_category_combo.addItem("Все", userData=None)

            if hasattr(self, '_category_cache') and self._category_cache:
                categories_list = list(self._category_cache.values())
                self._load_categories_to_combo(
                    self.filter_category_combo,
                    categories_list,
                    include_all=True,
                    default_text="Все"
                )
            else:
                logger.warning(f"[{self.__class__.__name__}] Кэш категорий не инициализирован")

            logger.debug(f"[{self.__class__.__name__}] Заполнены комбобоксы фильтров")

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка заполнения фильтров: {e}", exc_info=True)
            self.show_status("Ошибка загрузки фильтров", message_type="error")

    # =============== Дерево категорий ==================
    def _build_category_tree(self, categories: List[Category]) -> List[tuple]:
        """
        Строит иерархический список категорий для отображения в комбобоксе.

        Преобразует плоский список категорий в список кортежей
        (display_name, category_id, level), где level — уровень вложенности.
        Родительские категории идут без отступа, дочерние — с маркером "• ".

        Args:
            categories: плоский список объектов Category

        Returns:
            Список кортежей: [(display_name, category_id, level), ...]
        """
        try:
            if not categories:
                return []

            # Фильтруем системные категории
            user_categories = [
                cat for cat in categories
                if not getattr(cat, 'is_system', False)
            ]

            # Строим словарь {parent_id: [children]}
            children_map = {}
            roots = []
            for cat in user_categories:
                parent_id = getattr(cat, 'parent_id', None)
                if parent_id:
                    children_map.setdefault(parent_id, []).append(cat)
                else:
                    roots.append(cat)

            # Рекурсивно обходим дерево
            result = []

            def _traverse(category: Category, level: int):
                """Рекурсивный обход дерева категорий."""
                indent = " " * level
                if level > 0:
                    display_name = f"{indent}• {category.name}"
                else:
                    display_name = category.name
                result.append((display_name, category.id, level))

                for child in children_map.get(category.id, []):
                    _traverse(child, level + 1)

            # Сортируем корни по имени
            roots.sort(key=lambda c: c.name)
            for root in roots:
                _traverse(root, 0)

            return result

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка построения дерева категорий: {e}", exc_info=True)
            return []


    def _load_categories_to_combo(self, combo: QComboBox, categories: List[Category],
                                include_all: bool = False, default_text: str = "Все"):
        """
        Универсальный метод заполнения комбобокса категориями в виде дерева.

        Args:
            combo: целевой QComboBox для заполнения
            categories: список объектов Category
            include_all: если True, добавляет пункт "Все" в начало (для фильтров)
            default_text: текст для пункта "Все" (по умолчанию "Все")
        """
        try:
            combo.clear()

            if include_all:
                combo.addItem(default_text, userData=None)

            if not categories:
                combo.addItem("Нет категорий", userData=None)
                return

            # Строим дерево
            tree = self._build_category_tree(categories)

            if not tree:
                combo.addItem("Нет категорий", userData=None)
                return

            # Заполняем комбобокс
            for display_name, category_id, level in tree:
                combo.addItem(display_name, userData=category_id)

            logger.debug(f"[{self.__class__.__name__}] Загружено {len(tree)} категорий в комбобокс")

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка загрузки категорий: {e}", exc_info=True)
            self.show_status("Ошибка загрузки категорий", message_type="error")