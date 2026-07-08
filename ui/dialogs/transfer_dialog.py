# ui/dialogs/transfer_dialog.py
"""
Диалог управления переводами между счетами.
Архитектура MVP: UI не содержит бизнес-логики.
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QFormLayout, QRadioButton, QButtonGroup,
    QDateEdit, QLineEdit, QComboBox, QLabel, QTreeWidget,
    QTreeWidgetItem, QHeaderView, QMenu, QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt, QDate
from typing import List, Optional

from PySide6.QtGui import QFont, QDoubleValidator

from ui.dialogs.base_dialog import BaseDialog
from ui.widgets.colored_button import CompactButton


class TransferDialog(BaseDialog):
    """Диалог добавления и просмотра переводов."""

    def __init__(self, parent=None, presenter=None):
        """
        Инициализация диалога переводов.
        
        Args:
            parent: родительское окно
            presenter: экземпляр TransferPresenter
        """
        super().__init__(parent)
        self.presenter = presenter
        self.setWindowTitle("Управление Переводами")
        self.resize(700, 500)
        self._init_ui()
        if self.presenter:
            self.presenter.set_view(self)

    def _init_ui(self):
        """Инициализация интерфейса."""
        layout = self._main_layout
        layout.setContentsMargins(10, 10, 10, 10)

        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self._create_add_tab(), "Добавить перевод")
        self.tab_widget.addTab(self._create_view_tab(), "Все переводы")
        layout.addWidget(self.tab_widget)

        # Строка статуса
        layout.addWidget(self.status_bar)

    def _create_add_tab(self) -> QWidget:
        """Создаёт вкладку добавления перевода."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Тип перевода
        type_group = QGroupBox("Тип перевода")
        type_layout = QHBoxLayout(type_group)
        self.type_group_btn = QButtonGroup()
        self.radio_internal = QRadioButton("Между моими счетами")
        self.radio_external = QRadioButton("Внешний перевод")
        self.radio_internal.setChecked(True)
        self.type_group_btn.addButton(self.radio_internal)
        self.type_group_btn.addButton(self.radio_external)
        self.radio_internal.toggled.connect(self._toggle_transfer_type)
        type_layout.addWidget(self.radio_internal)
        type_layout.addWidget(self.radio_external)
        layout.addWidget(type_group)

        # Форма
        form_layout = QFormLayout()
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setDisplayFormat("dd.MM.yyyy")
        form_layout.addRow("Дата:", self.date_input)

        # Сумма
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("0.00")
        form_layout.addRow("Сумма:", self.amount_input)
        validator = QDoubleValidator(0.0, 999999999.0, 2)  # min=0, max=999M, 2 знака после запятой
        validator.setNotation(QDoubleValidator.StandardNotation)
        self.amount_input.setValidator(validator)

        # Внутренний перевод
        self.internal_frame = QGroupBox("Внутренний перевод")
        int_layout = QFormLayout(self.internal_frame)
        self.from_combo = QComboBox()
        self.to_combo = QComboBox()
        int_layout.addRow("Со счета:", self.from_combo)
        int_layout.addRow("На счет:", self.to_combo)
        layout.addWidget(self.internal_frame)

        # Внешний перевод
        self.external_frame = QGroupBox("Внешний перевод")
        ext_layout = QFormLayout(self.external_frame)
        self.ext_account_combo = QComboBox()
        ext_layout.addRow("Счет:", self.ext_account_combo)

        dir_layout = QHBoxLayout()
        self.dir_group_btn = QButtonGroup()
        self.radio_incoming = QRadioButton("Мне перевели")
        self.radio_outgoing = QRadioButton("Я перевел")
        self.radio_incoming.setChecked(True)
        self.dir_group_btn.addButton(self.radio_incoming)
        self.dir_group_btn.addButton(self.radio_outgoing)
        dir_layout.addWidget(self.radio_incoming)
        dir_layout.addWidget(self.radio_outgoing)
        ext_layout.addRow("Направление:", dir_layout)

        # Контрагент
        self.counterparty_input = QLineEdit()
        self.counterparty_input.setPlaceholderText("Имя контрагента")
        ext_layout.addRow("Контрагент:", self.counterparty_input)
        layout.addWidget(self.external_frame)

        # Описание
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Описание (необязательно)")
        form_layout.addRow("Описание:", self.description_input)

        layout.addLayout(form_layout)

        # Кнопки
        btn_layout = QHBoxLayout()
        self.add_btn = CompactButton("Добавить")
        self.add_btn.clicked.connect(self._on_add_clicked)
        self.close_btn = CompactButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)
        layout.addStretch()

        self._toggle_transfer_type()
        return tab

    def _create_view_tab(self) -> QWidget:
        """Создаёт вкладку просмотра переводов."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.transfers_tree = QTreeWidget()
        self.transfers_tree.setHeaderLabels(["Дата", "Тип", "Сумма", "Откуда", "Куда", "Контрагент", "Описание"])
        
        # === ВАЖНО: разрешаем множественное выделение ===
        self.transfers_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.transfers_tree.setSelectionBehavior(QTreeWidget.SelectRows)
        
        header = self.transfers_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Дата
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Тип
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Сумма
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # Откуда
        header.setSectionResizeMode(4, QHeaderView.Stretch)           # Куда
        header.setSectionResizeMode(5, QHeaderView.Stretch)           # Контрагент
        header.setSectionResizeMode(6, QHeaderView.Stretch)           # Описание
        
        self.transfers_tree.setAlternatingRowColors(True)
        self.transfers_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.transfers_tree.customContextMenuRequested.connect(self._show_context_menu)
        
        layout.addWidget(self.transfers_tree)
        return tab

    def _toggle_transfer_type(self):
        """Переключает видимость блоков внутреннего/внешнего перевода."""
        is_internal = self.radio_internal.isChecked()
        self.internal_frame.setVisible(is_internal)
        self.external_frame.setVisible(not is_internal)

    def _on_add_clicked(self):
        """Обработчик нажатия кнопки 'Добавить'."""
        try:
            data = self._get_form_data()
            
            # Проверяем комиссию для внешних исходящих переводов с кредитки
            if data["type"] == "external" and data["direction"] == "outgoing":
                fee_info = self.presenter.check_credit_card_transfer(
                    data["account_id"], data["amount"]
                )
                
                if fee_info["is_credit_card"]:
                    # Спрашиваем подтверждение
                    reply = QMessageBox.question(
                        self,
                        "Комиссия за перевод",
                        f"Перевод с карты «{fee_info['card_name']}» облагается комиссией:\n\n"
                        f"Сумма перевода: {data['amount']:,.2f} ₽\n"
                        f"Комиссия (5.9% + 590 ₽): {fee_info['commission']:,.2f} ₽\n"
                        f"{'─' * 40}\n"
                        f"Итого будет списано: {fee_info['total']:,.2f} ₽\n\n"
                        f"Продолжить?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    
                    if reply != QMessageBox.StandardButton.Yes:
                        return
                    
                    # Создаём основной перевод
                    self.presenter.add_transfer(data)
                    
                    # Создаём расход на комиссию
                    self.presenter.add_commission_expense({
                        "date": data["date"],
                        "amount": fee_info["commission"],
                        "account_id": data["account_id"],
                        "description": f"Комиссия за перевод ({data['counterparty']})"
                    })
                    
                    self.show_status(
                        f"Перевод создан. Комиссия {fee_info['commission']:,.2f} ₽ учтена как расход.",
                        "success"
                    )
                    return
            
            # Обычный перевод без комиссии
            self.presenter.add_transfer(data)
            
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            self.show_status(f"Ошибка: {e}", "error")

    def _get_form_data(self) -> dict:
        """
        Собирает и валидирует данные формы.
        
        Returns:
            Словарь с данными перевода
            
        Raises:
            ValueError: если данные некорректны
        """
        date = self.date_input.date().toString("yyyy-MM-dd")
        amount_str = self.amount_input.text().strip().replace(',', '.')
        if amount_str == "":
            raise ValueError("Введите сумму перевода")
        try:
            amount = float(amount_str)
        except ValueError:
            raise ValueError("Некорректный формат перевода")

        data = {
            "date": date,
            "amount": amount,
            "description": self.description_input.text().strip()
        }

        if self.radio_internal.isChecked():
            data["type"] = "internal"
            data["from_account_id"] = self.from_combo.currentData()
            data["to_account_id"] = self.to_combo.currentData()
            if not data["from_account_id"] or not data["to_account_id"]:
                raise ValueError("Выберите оба счета.")
            if data["from_account_id"] == data["to_account_id"]:
                raise ValueError("Счета 'Откуда' и 'Куда' не могут совпадать.")
        else:
            data["type"] = "external"
            data["account_id"] = self.ext_account_combo.currentData()
            data["counterparty"] = self.counterparty_input.text().strip()
            data["direction"] = "incoming" if self.radio_incoming.isChecked() else "outgoing"
            if not data["account_id"] or not data["counterparty"]:
                raise ValueError("Заполните счет и имя контрагента.")

        return data

    def _get_selected_transfer_ids(self) -> List[int]:
        """
        Возвращает список ID всех выделенных переводов.
        
        Returns:
            Список целых чисел (ID переводов)
        """
        selected_items = self.transfers_tree.selectedItems()
        ids = []
        for item in selected_items:
            transfer_id = item.data(0, Qt.UserRole)
            if transfer_id is not None:
                ids.append(transfer_id)
        return ids

    def _show_context_menu(self, position):
        """
        Показывает контекстное меню для перевода.

        Args:
            position: позиция клика
        """
        item = self.transfers_tree.itemAt(position)
        if not item:
            return

        is_system = item.data(0, Qt.UserRole + 1)

        # Не показываем меню для системных переводов (или делаем его пустым/неактивным)
        if is_system:
            return

        selected_ids = self._get_selected_transfer_ids()
        if not selected_ids:
            return

        menu = QMenu(self)
        delete_action = menu.addAction("🗑️ Удалить выбранные")
        delete_action.triggered.connect(lambda: self._delete_selected_transfers(selected_ids))
        menu.exec(self.transfers_tree.viewport().mapToGlobal(position))

    def _delete_selected_transfers(self, transfer_ids: List[int]):
        """Удаляет несколько переводов.
        
        Args:
            transfer_ids: список ID переводов
        """
        if not transfer_ids:
            return
            
        count = len(transfer_ids)
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Удалить {count} перевод(ов)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes and self.presenter:
            self.presenter.delete_transfers(transfer_ids)

    # =================== Контракт View <-> Presenter ===================

    def load_transfers(self, transfers: List[dict]):
        """
        Загружает переводы в таблицу.
        
        Args:
            transfers: список словарей с ключами: id, date, amount, type, 
                       from_account_name, to_account_name, counterparty_name, is_system
        """
        self.transfers_tree.clear()
        
        for tx in transfers:
            # Безопасное получение данных с дефолтными значениями
            date_str = tx.get("date", "")
            amount_val = tx.get("amount", 0)
            tx_type = tx.get("type", "internal")
            from_name = tx.get("from_account_name", "")
            to_name = tx.get("to_account_name", "")
            counterparty = tx.get("counterparty_name", "")
            description = tx.get("description", "")
            is_system = bool(tx.get("is_system", False))
            
            # Форматирование типа
            display_type = "Внутренний" if tx_type == "internal" else "Внешний"
            
            # Форматирование суммы
            try:
                amount_formatted = f'{float(amount_val):,.2f}'
            except (ValueError, TypeError):
                amount_formatted = "0.00"

            item = QTreeWidgetItem([
                date_str,
                display_type,
                amount_formatted,
                from_name or "",
                to_name or "",
                counterparty or "",  # ← Теперь здесь будет имя контрагента для внешних переводов
                description or ""
            ])
            
            # Сохраняем ID и флаг системности в скрытых данных элемента
            item.setData(0, Qt.UserRole, tx.get("id"))
            item.setData(0, Qt.UserRole + 1, is_system)
            
            self.transfers_tree.addTopLevelItem(item)

    def clear_selection(self):
        """Очищает выделение в таблице."""
        self.transfers_tree.clearSelection()
        # self._reset_form()

    