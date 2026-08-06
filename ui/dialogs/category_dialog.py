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
from ui.widgets.colored_button import ColoredDialogButtonBox
from ui.widgets.buttons import CompactButton
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
        self.resize(600, 650)
        
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

        self.categories_tree.setSortingEnabled(True)
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
        form_layout.addRow("Родительская категория:", self.parent_combo)

        
        self.budget_input = QLineEdit()
        self.budget_input.setPlaceholderText("0.00")
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
        
        # dialog_buttons = ColoredDialogButtonBox(color="#4CAF50")
        # close_btn = dialog_buttons.addButton("Закрыть", QDialogButtonBox.RejectRole)
        # close_btn.clicked.connect(self.accept)
        # layout.addWidget(dialog_buttons)

        # 6. Строка статуса
        layout.addWidget(self.status_bar)
        
        layout.addLayout(button_layout)

    # =================== Обработчики UI ===================
    
    def _add_category(self):
        """Обработчик нажатия кнопки 'Добавить'."""
        try:
            data = self._get_form_data()
            self.presenter.add_category(data)
        except ValueError as e:
            # Показываем красивое сообщение об ошибке
            self.show_status(str(e), "error")

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

    def _on_context_delete(self, category_id: int):
        """Удаляет ОДНУ категорию по ID с подтверждением."""
        # Находим имя категории
        category_name = "Неизвестная"
        item = self._find_item_by_id_recursive(self.categories_tree.invisibleRootItem(), category_id)
        if item:
            category_name = item.text(0)

        # Подтверждение
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить категорию '{category_name}' и все её подкатегории?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if self.presenter:
            result = self.presenter.delete_category(category_id)
            if result.get('success'):
                self.show_status(f"Удалена: {category_name}", "success")
            else:
                if not result.get('can_delete', True):
                    self._show_cannot_delete_message({
                        'account_name': category_name,  # совместимость с существующим методом
                        'total_operations': result.get('total_operations', 0)
                    })
                else:
                    self.show_status(
                        f"Ошибка удаления '{category_name}': {result.get('message', 'Неизвестная ошибка')}",
                        "error"
                    )
        else:
            self.show_status("Презентер не подключен", "error")

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
        """Показывает контекстное меню с учётом уровня вложенности."""
        item = self.categories_tree.itemAt(position)
        if not item:
            return

        category_id = item.data(0, Qt.UserRole)
        is_system = item.data(0, Qt.UserRole + 1)
        depth = self._get_item_depth(item)

        menu = QMenu(self)

        # 1. Редактировать
        edit_action = menu.addAction("✏️ Редактировать")
        edit_action.triggered.connect(lambda: self._select_and_edit(category_id))

        # 2. Добавить подкатегорию — только если глубина < 2 (т.е. максимум 3 уровня: 0→1→2)
        if depth < 2:
            add_sub_action = menu.addAction("➕ Добавить подкатегорию")
            add_sub_action.triggered.connect(lambda: self._prepare_add_subcategory(category_id))

        menu.addSeparator()

        # 3. Удалить (только для несистемных)
        if not is_system:
            delete_action = menu.addAction("🗑️ Удалить")
            delete_action.triggered.connect(lambda: self._on_context_delete(category_id))

        menu.addSeparator()

        # 4. Статистика
        stats_action = menu.addAction("📊 Статистика")
        stats_action.triggered.connect(self._stub_method)

        menu.exec(self.categories_tree.viewport().mapToGlobal(position))

    def _get_form_data(self) -> dict:
        """
        Собирает данные из формы в словарь.
        
        Returns:
            Словарь с данными категории
        """
        name = self.name_input.text().strip()
        if name == "":
            raise ValueError("Введите название категории")
        parent_id = None
        if self.parent_combo.currentIndex() > 0:
            parent_id = self.parent_combo.currentData()
        budget_str = self.budget_input.text().strip().replace(',', '.')
        if budget_str == "":
            raise ValueError("Введите бюджет категории")
        try:
            budget = float(budget_str)
        except ValueError:
            raise ValueError("Некорректный формат планового бюждета")

        # Маппинг: UI (русский) → БД (английский)
        ui_type = self.type_combo.currentText()
        db_type = "income" if ui_type == "Доход" else "expense"

        return {
            "name": name,
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
        self.budget_input.clear()
        self.editing_category_id = None
        self.add_button.setEnabled(True)
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    # =================== Контракт View <-> Presenter ===================
    
    def load_categories(self, categories: List[Category]):
        """
        Заполняет дерево категорий с поддержкой иерархии до 3 уровней.
        
        Args:
            categories: список всех категорий (включая подкатегории)
        """
        self.categories_tree.clear()
        
        # Группируем категории по parent_id
        from collections import defaultdict
        children_map = defaultdict(list)
        root_items = []
        
        for cat in categories:
            if cat.parent_id is None:
                root_items.append(cat)
            else:
                children_map[cat.parent_id].append(cat)
        
        # Рекурсивное добавление узлов (максимум 3 уровня)
        def add_to_tree(parent_item, category, level=0):
            if level >= 3:  # Ограничиваем глубину
                return
                
            # Маппинг типа для отображения
            display_type = "Доход" if category.cat_type == "income" else "Расход"
            item = QTreeWidgetItem([
                category.name,
                display_type,
                str(category.budget_amount_monthly or 0)
            ])
            item.setData(0, Qt.UserRole, category.id)
            item.setData(0, Qt.UserRole + 1, category.is_system)
            
            if parent_item is None:
                self.categories_tree.addTopLevelItem(item)
            else:
                parent_item.addChild(item)
            
            # Добавляем детей
            for child in children_map.get(category.id, []):
                add_to_tree(item, child, level + 1)
        
        # Строим дерево
        for root_cat in sorted(root_items, key=lambda x: x.name):
            add_to_tree(None, root_cat)
        
        # Раскрываем все узлы
        self.categories_tree.expandAll()

    def load_parent_categories(self, categories: List[Category]):
        """
        Загружает список возможных родителей (только до 2 уровня вложенности).
        Для комбокса.
        """
        self.parent_combo.clear()
        self.parent_combo.addItem("")  # Корень
        
        # Группируем по parent_id
        from collections import defaultdict
        children_map = defaultdict(list)
        roots = [c for c in categories if c.parent_id is None]
        
        for cat in categories:
            if cat.parent_id is not None:
                children_map[cat.parent_id].append(cat)
        
        # Добавляем корни
        for root in sorted(roots, key=lambda x: x.name):
            self.parent_combo.addItem(root.name, userData=root.id)
            # Добавляем их детей (1-й уровень подкатегорий)
            for child in sorted(children_map[root.id], key=lambda x: x.name):
                indent_name = f" └ {child.name}"
                self.parent_combo.addItem(indent_name, userData=child.id)
                # Не добавляем внуков — чтобы не превысить 3 уровня

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

    #================== Вспомнительные методы ===================
    def _select_and_edit(self, category_id: int):
        """Выбирает категорию и переводит форму в режим редактирования."""
        # Находим и выделяем элемент
        for i in range(self.categories_tree.topLevelItemCount()):
            item = self._find_item_by_id(self.categories_tree.topLevelItem(i), category_id)
            if item:
                self.categories_tree.setCurrentItem(item)
                self._on_category_select()
                break

    def _find_item_by_id_recursive(self, parent_item, target_id):
        """Рекурсивный поиск элемента по ID в дереве."""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child.data(0, Qt.UserRole) == target_id:
                return child
            found = self._find_item_by_id_recursive(child, target_id)
            if found:
                return found
        return None

    def _find_item_by_id(self, parent_item, target_id):
        """Рекурсивный поиск от заданного родителя."""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child.data(0, Qt.UserRole) == target_id:
                return child
            found = self._find_item_by_id(child, target_id)
            if found:
                return found
        return None

    def _prepare_add_subcategory(self, parent_id: int):
        """
        Подготавливает форму для добавления подкатегории.
        Автоматически выбирает родителя в комбобоксе.
        """
        # Очищаем форму
        self._reset_form()
        
        # Выбираем родителя в комбобоксе
        for i in range(self.parent_combo.count()):
            if self.parent_combo.itemData(i) == parent_id:
                self.parent_combo.setCurrentIndex(i)
                break
        
        self.show_status("Готово к созданию подкатегории", "info")

    def _get_item_depth(self, item) -> int:
        """
        Возвращает уровень вложенности элемента в дереве (0 = корень).
        
        Args:
            item: QTreeWidgetItem
            
        Returns:
            int: глубина (0, 1, 2, ...)
        """
        depth = 0
        current = item
        while current.parent():
            depth += 1
            current = current.parent()
        return depth