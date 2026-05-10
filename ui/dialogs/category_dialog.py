# ui/dialogs/category_dialog.py
"""
Диалог управления категориями (иерархия с подкатегориями).
Чистый UI-слой без бизнес-логики.
"""
from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QLineEdit, QComboBox, QGroupBox, QFormLayout,
    QPushButton, QHeaderView, QMenu, QApplication, QDialogButtonBox, QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QDoubleValidator
from ui.widgets.colored_button import CompactButton, ColoredDialogButtonBox
from ui.dialogs.base_dialog import BaseDialog
from core.models import Category



class CategoryDialog(BaseDialog):
    """Диалог управления категориями с поддержкой иерархии."""

    def __init__(self, parent=None, presenter=None):
        """
        Инициализация диалога управления категориями.
        
        Args:
            parent: родительское окно
            presenter: экземпляр CategoryPresenter для обработки действий
        """
        super().__init__(parent)
        self.parent = parent
        self.presenter = presenter
        self.setWindowTitle("Управление Категориями")
        self.resize(600, 550)
        
        # Состояние редактирования
        self.editing_category_id: Optional[int] = None
        
        self._init_ui()
        if self.presenter:
            self.presenter.set_view(self)

    def _init_ui(self):
        """Инициализация интерфейса диалога."""
        layout = self._main_layout
        layout.setSpacing(10)

        # 1 Заголовок
        title_label = QLabel("Управление Категориями")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 2 Дерево категорий
        tree_group = QGroupBox("Дерево категорий")
        tree_layout = QVBoxLayout(tree_group)
        
        self.categories_tree = QTreeWidget()
        self.categories_tree.setHeaderLabels(["Название", "Тип", "Бюджет (мес.)"])
        self.categories_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.categories_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.categories_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        self.categories_tree.itemSelectionChanged.connect(self._on_category_select)
        self.categories_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.categories_tree.customContextMenuRequested.connect(self._show_context_menu)
        
        tree_layout.addWidget(self.categories_tree)
        layout.addWidget(tree_group, 1)

        # 4 Форма редактирования
        form_group = QGroupBox("Добавить/Редактировать категорию")
        form_layout = QFormLayout(form_group)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название категории")
        form_layout.addRow("Название:", self.name_input)
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Расход", "Доход"])
        form_layout.addRow("Тип:", self.type_combo)
        
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("")  # Пустой элемент = корневая категория
        form_layout.addRow("Родитель:", self.parent_combo)
        
        self.budget_input = QLineEdit("0.0")
        form_layout.addRow("Плановый бюджет:", self.budget_input)
        validator = QDoubleValidator(0.0, 999999999.0, 2)  # min=0, max=999M, 2 знака после запятой
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.budget_input.setValidator(validator)

        self.is_active_checkbox = QCheckBox("Активная категория")
        self.is_active_checkbox.setChecked(True)  # по умолчанию активна
        form_layout.addRow("", self.is_active_checkbox)
        
        layout.addWidget(form_group)

        # 5 Кнопки формы
        button_layout = QHBoxLayout()
        
        self.add_button = CompactButton("Добавить")
        self.add_button.clicked.connect(self._add_category)
        button_layout.addWidget(self.add_button)
        
        self.edit_button = CompactButton("Сохранить")
        self.edit_button.clicked.connect(self._edit_category)
        self.edit_button.setEnabled(False)
        button_layout.addWidget(self.edit_button)
        
        self.delete_button = CompactButton("Удалить")
        self.delete_button.clicked.connect(self._delete_category)
        self.delete_button.setEnabled(False)
        button_layout.addWidget(self.delete_button)

        self.cancel_button = CompactButton("Сброс")
        self.cancel_button.clicked.connect(self._reset_form)
        self.cancel_button.setEnabled(True)
        button_layout.addWidget(self.cancel_button)
        
        dialog_buttons = ColoredDialogButtonBox(color="#4CAF50")
        close_btn = dialog_buttons.addButton("Закрыть", QDialogButtonBox.RejectRole)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(dialog_buttons)

        # 6. Строка статуса
        layout.addWidget(self.status_bar)
        
        layout.addLayout(button_layout)

    # =================== Обработчики UI ===================
    
    def _add_category(self):
        """Обработчик нажатия кнопки 'Добавить'."""
        if self.presenter:
            self.presenter.add_category(self._get_form_data())

    def _edit_category(self):
        """Обработчик нажатия кнопки 'Сохранить'."""
        if self.presenter and self.editing_category_id is not None:
            data = self._get_form_data()
            data["id"] = self.editing_category_id
            self.presenter.update_category(data)

    def _delete_category(self):
        """Обработчик нажатия кнопки 'Удалить'."""
        selected_items = self.categories_tree.selectedItems()
        if not selected_items:
            self.show_status("Выберите категорию для удаления", "warning")
            return
            
        category_id = selected_items[0].data(0, Qt.UserRole)
        if self.presenter:
            self.presenter.delete_category(category_id)

    def _on_category_select(self):
        """Обработчик выбора категории в дереве."""
        items = self.categories_tree.selectedItems()
        if not items:
            self._reset_form()
            return
            
        item = items[0]
        category_id = item.data(0, Qt.UserRole)
        if self.presenter:
            self.presenter.select_category(category_id)

    def _show_context_menu(self, position):
        """Показывает контекстное меню для дерева категорий."""
        self._stub_method()

    def _get_form_data(self) -> dict:
        """
        Собирает данные из формы в словарь.
        
        Returns:
            Словарь с данными категории
        """
        parent_id = None
        if self.parent_combo.currentIndex() > 0:
            parent_id = self.parent_combo.currentData()
            
        try:
            budget = float(self.budget_input.text() or "0.0")
        except ValueError:
            raise ValueError("Некорректный формат планового бюждета")

        # Маппинг: UI (русский) → БД (английский)
        ui_type = self.type_combo.currentText()
        db_type = "income" if ui_type == "Доход" else "expense"

        return {
            "name": self.name_input.text().strip(),
            "cat_type": db_type,
            "parent_id": parent_id,
            "budget_amount_monthly": budget,
            "is_active": self.is_active_checkbox.isChecked() 
        }

    def _reset_form(self):
        """Сбрасывает форму к состоянию 'новая категория'."""
        self.name_input.clear()
        #self.type_combo.setCurrentIndex(0)
        self.parent_combo.setCurrentIndex(0)
        self.budget_input.setText("0.0")
        self.editing_category_id = None
        self.add_button.setEnabled(True)
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    # =================== Контракт View <-> Presenter ===================
    
    def load_categories(self, categories: List[Category]):
        """Заполняет дерево категорий (вызываеться из Presenter).
        
        Args:
            categories: список объектов Category (с поддержкой иерархии)
        """
        self.categories_tree.clear()
        # TODO: Реализовать добавление узлов в QTreeWidget
        # TODO: Реализовать рекурсивное добавление узлов
        for cat in categories:
            display_type = "Доход" if cat.cat_type == "income" else "Расход"
            item = QTreeWidgetItem([cat.name, display_type, str(cat.budget_amount_monthly or 0)])
            item.setData(0, Qt.UserRole, cat.id)
            self.categories_tree.addTopLevelItem(item)

    def show_category_in_form(self, category):
        """
        Заполняет форму данными выбранной категории.
        
        Args:
            category: объект Category
        """
        self.name_input.setText(category.name)
        # Маппинг: БД (английский) → UI (русский)
        ui_type = "Доход" if category.cat_type == "income" else "Расход"
        self.type_combo.setCurrentText(ui_type)
        self.budget_input.setText(str(category.budget_amount_monthly or "0.0"))

        self.is_active_checkbox.setChecked(category.is_active)
        
        # Устанавливаем родителя в комбобоксе
        if category.parent_id:
            for i in range(self.parent_combo.count()):
                if self.parent_combo.itemData(i) == category.parent_id:
                    self.parent_combo.setCurrentIndex(i)
                    break
        else:
            self.parent_combo.setCurrentIndex(0)
            
        self.editing_category_id = category.id
        
        self.add_button.setEnabled(False)
        self.edit_button.setEnabled(True)
        self.delete_button.setEnabled(True)

    def clear_selection(self):
        """Очищает выделение в таблице."""
        self.categories_tree.clearSelection()
        self._reset_form()