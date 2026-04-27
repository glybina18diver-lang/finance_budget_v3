# ui/dialogs/operation_dialog.py
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QLineEdit, QComboBox, QFrame, QMessageBox, QWidget, QHeaderView, QDateEdit
)
from PySide6.QtCore import Qt, QTimer, QDate
from ui.widgets.colored_button import ColoredButton


class OperationDialog(QDialog):
    """Диалог управления операциями (чистый UI слой, без бизнес-логики)."""

    def __init__(self, parent=None, presenter=None):
        """
        Инициализация диалога.
        
        Args:
            parent: родительское окно (MainWindow)
            presenter: экземпляр TransactionPresenter для обработки действий
        """
        super().__init__(parent)
        self.presenter = presenter
        self.setWindowTitle("Операции")
        self.resize(1200, 600)
        self._init_ui()

    def _init_ui(self):
        """Инициализация интерфейса и компоновки элементов."""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        main_layout.addWidget(self._create_top_panel())
        main_layout.addWidget(self._create_filter_panel())
        main_layout.addWidget(self._create_input_panel())
        main_layout.addWidget(self._create_table(), stretch=1)
        main_layout.addWidget(self._create_bottom_panel())
        main_layout.addWidget(self._create_status_bar())

        self.setLayout(main_layout)
        
        # Фокус на поле суммы при открытии
        QTimer.singleShot(100, lambda: self.amount_input.setFocus())

    def _create_top_panel(self) -> QWidget:
        """Верхняя панель с кнопками навигации (все на заглушках)."""
        panel = QWidget()
        layout = QHBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)

        buttons = [
            ("🏦 Счета", "#2196F3"), ("📊 Категории", "#9C27B0"),
            ("📤 Переводы", "#FF9800"), ("🔍 Сверка", "#607D8B"),
            ("💰 Займы", "#795548"), ("💳 Кредитки", "#E91E63")
        ]

        for text, color in buttons:
            btn = ColoredButton(text, color)
            btn.clicked.connect(self._stub_method)
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

        # Тип операции
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Расход", "Доход"])
        self.type_combo.setFixedHeight(26)
        self.type_combo.setMinimumWidth(80)
        layout.addWidget(self.type_combo)

        # Категория и Счет (будут заполняться презентером)
        self.category_combo = QComboBox()
        self.category_combo.addItem("Загрузка...")
        self.category_combo.setFixedHeight(26)
        self.category_combo.setMinimumWidth(140)
        layout.addWidget(self.category_combo)

        self.account_combo = QComboBox()
        self.account_combo.addItem("Загрузка...")
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
        add_btn.clicked.connect(self._on_add_transaction)
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
        """Таблица транзакций (пока без данных, сортировка включена)."""
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Дата", "Тип", "Сумма", "Кол-во", "Категория", "Счет", "Описание"])
        self.tree.setSortingEnabled(True)
        self.tree.sortItems(0, Qt.DescendingOrder)
        self.tree.setAlternatingRowColors(True)
        
        header = self.tree.header()
        header.setStretchLastSection(True)
        header.setSectionsClickable(True)
        
        # Контекстное меню (заглушка)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._stub_method)
        return self.tree

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

    def _create_status_bar(self) -> QLabel:
        """Строка статуса с авто-сбросом через 2 секунды."""
        self.status_bar = QLabel("Готово")
        self.status_bar.setFixedHeight(26)
        self.status_bar.setStyleSheet("QLabel { padding: 2px 6px; border-top: 1px solid #ddd; }")
        return self.status_bar

    # ================= Контракт View <-> Presenter =================

    def show_status(self, message: str, message_type: str = "info"):
        """
        Выводит сообщение в статус-бар с цветовой индикацией и авто-сбросом.
        
        Args:
            message: текст сообщения
            message_type: тип (info, success, error, warning)
        """
        colors = {"info": "#6c757d", "success": "#28a745", "warning": "#fd7e14", "error": "#dc3545"}
        color = colors.get(message_type, "#6c757d")
        
        self.status_bar.setText(message)
        self.status_bar.setStyleSheet(f"""
            QLabel {{ color: {color}; font-weight: bold; background-color: #f8f9fa; 
                       padding: 2px 6px; border-top: 1px solid #ddd; }}
        """)
        QTimer.singleShot(2000, self._reset_status_bar)

    def show_error(self, message: str):
        """
        Показывает критическое сообщение об ошибке.
        
        Args:
            message: текст ошибки
        """
        QMessageBox.critical(self, "Ошибка валидации", message)
        self.show_status(message, "error")

    def clear_form(self):
        """Сбрасывает поля ввода формы к значениям по умолчанию."""
        self.amount_input.clear()
        self.description_input.clear()
        self.date_input.setDate(QDate.currentDate())
        self.type_combo.setCurrentIndex(0)  # Расход
        self.show_status("Форма очищена", "info")

    def refresh_transactions(self):
        """Заглушка для обновления таблицы (будет вызываться презентером после сохранения)."""
        # В будущем: презентер передаст список Transaction, здесь отрисуются строки
        self.show_status("Таблица обновлена", "success")

    # ================= Обработчики событий =================

    def _on_add_transaction(self):
        """Собирает данные из формы и передает их презентеру."""
        raw_amount = self.amount_input.text().strip()
        if not raw_amount:
            self.show_error("Введите сумму")
            return

        trans_type = "income" if self.type_combo.currentText() == "Доход" else "expense"
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        
        # Временные ID (будут заменены на реальные данные из комбобоксов)
        account_id = 1  # Заглушка
        category_id = 1 # Заглушка
        description = self.description_input.text().strip()

        try:
            self.presenter.add_transaction(
                raw_amount=raw_amount,
                trans_type=trans_type,
                account_id=account_id,
                category_id=category_id,
                description=description,
                date_str=date_str
            )
        except AttributeError:
            self.show_error("Презентер не подключен. Проверьте DI в main.py")

    def _stub_method(self):
        """Заглушка для функций, находящихся в разработке."""
        self.show_status("Функция в разработке", "warning")

    def _reset_status_bar(self):
        """Возвращает статус-бар в состояние 'Готово'."""
        self.status_bar.setText("Готово")
        self.status_bar.setStyleSheet("QLabel { padding: 2px 6px; border-top: 1px solid #ddd; }")