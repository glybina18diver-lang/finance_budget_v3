# ui/dialogs/transfer_dialog.py
"""
Диалог управления переводами между счетами.
Архитектура MVP: UI не содержит бизнес-логики.
"""
import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QGroupBox, QFormLayout, QRadioButton, QButtonGroup,
    QDateEdit, QLineEdit, QComboBox, QLabel, QTreeWidget, QCompleter,
    QTreeWidgetItem, QHeaderView, QMenu, QMessageBox, QAbstractItemView, QFrame
)
from PySide6.QtCore import Qt, QDate, QPoint
from typing import List, Optional

from PySide6.QtGui import QFont, QDoubleValidator

from ui.dialogs.base_dialog import BaseDialog
from ui.widgets.colored_button import CompactButton
from core.models import Transfer

logger = logging.getLogger(__name__)


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
        try:
            tab = QWidget()
            layout = QVBoxLayout(tab)

            # Тип перевода
            type_group = QGroupBox("Тип перевода")
            type_layout = QHBoxLayout(type_group)
            self.type_group_btn = QButtonGroup()
            self.radio_internal = QRadioButton("Между моими счетами")
            self.radio_external = QRadioButton("Внешний перевод")
            self.radio_internal.setChecked(True)
            self.type_group_btn.addButton(self.radio_internal, 0)
            self.type_group_btn.addButton(self.radio_external, 1)
            self.radio_internal.toggled.connect(self._toggle_transfer_type)
            type_layout.addWidget(self.radio_internal)
            type_layout.addWidget(self.radio_external)
            layout.addWidget(type_group)

            # ---------- Фреймы для разных типов переводов ---------
            # Внутренний перевод
            self.internal_frame = QGroupBox("Внутренний перевод")
            internal_form = QFormLayout()
            internal_form.setContentsMargins(10, 10, 10, 10)

            # Создаем комбобоксы
            self.from_combo = QComboBox()
            self.from_combo.setFixedHeight(26)
            self.from_combo.setMinimumWidth(100)
            self.from_combo.setMaximumWidth(300)
        
            self.to_combo = QComboBox()
            self.to_combo.setFixedHeight(26)
            self.to_combo.setMinimumWidth(100)
            self.to_combo.setMaximumWidth(300)

            # Счета рядом по горизонтали
            accounts_layout = QHBoxLayout()
            accounts_layout.setContentsMargins(0, 0, 0, 0)
            accounts_layout.addWidget(self.from_combo)
            accounts_layout.addWidget(self.to_combo)
            accounts_widget = QWidget()
            accounts_widget.setLayout(accounts_layout)
            internal_form.addRow("Со счета → На счет:", accounts_widget)

            self.internal_frame.setLayout(internal_form) 

            layout.addWidget(self.internal_frame)

            # ------------- Внешний перевод----------------

            self.external_frame = QGroupBox("Внешний перевод")
            external_form = QFormLayout()
            external_form.setContentsMargins(10, 10, 10, 10)

            # Направление внешнего перевода
            dir_layout = QHBoxLayout()
            dir_layout.setContentsMargins(0, 0, 0, 0)
            self.dir_group_btn = QButtonGroup()
            self.radio_incoming = QRadioButton("Мне перевели")
            self.radio_outgoing = QRadioButton("Я перевел")
            self.radio_incoming.setChecked(True)
            
            self.dir_group_btn.addButton(self.radio_incoming)
            self.dir_group_btn.addButton(self.radio_outgoing)
            dir_layout.addWidget(self.radio_incoming)
            dir_layout.addWidget(self.radio_outgoing)
            external_form.addRow("Направление:", dir_layout)

            # Счет и Контрагент в одной строке по горизонтали
            acc_count_layout = QHBoxLayout()
            acc_count_layout.setSpacing(10)

            # Счет 
            self.ext_account_combo = QComboBox()
            self.ext_account_combo.setFixedHeight(26)
            self.ext_account_combo.setMinimumWidth(100)

            # Контрагент
            self.counterparty_input = QLineEdit()
            self.counterparty_input.setFixedHeight(26)
            self.counterparty_input.setMinimumWidth(100)
            self.counterparty_input.setPlaceholderText("Имя контрагента")

            # # Автодополнение для контрагентов
            # self.counterparty_completer = QCompleter()
            # self.counterparty_completer.setModel(self.counterparty_model)
            # self.counterparty_completer.setCaseSensitivity(Qt.CaseInsensitive)
            # self.counterparty_completer.setFilterMode(Qt.MatchContains)
            # self.counterparty_completer.setCompletionMode(QCompleter.PopupCompletion)
            # self.counterparty_input.setCompleter(self.counterparty_completer)
            
            acc_count_layout.addWidget(QLabel("Счет:"))
            acc_count_layout.addWidget(self.ext_account_combo)
            acc_count_layout.addWidget(QLabel("Контрагент:"))
            acc_count_layout.addWidget(self.counterparty_input)
            acc_count_layout.addStretch()

            acc_count_widget = QWidget()
            acc_count_widget.setLayout(acc_count_layout)
            external_form.addRow(acc_count_widget)

            # Подсказка о регистре
            self.counterparty_hint = QLabel("⚠️ Регистр не учитывается: 'иван' и 'Иван' будут одним контрагентом")
            self.counterparty_hint.setStyleSheet("font-size: 11px; color: gray; font-style: italic;")
            external_form.addRow("", self.counterparty_hint)

            
            self.external_frame.setLayout(external_form)

            layout.addWidget(self.external_frame)

            # ---------- Дата, Сумма, Описание -----------
            # Форма
            form_layout = QFormLayout()

            # Дата и Сумма в одной строке по горизонтали
            date_amount_layout = QHBoxLayout()
            date_amount_layout.setSpacing(10)

            # Сумма
            self.amount_input = QLineEdit()
            self.amount_input.setPlaceholderText("0.00")
            self.amount_input.setFixedHeight(26)
            self.amount_input.setFixedWidth(100)
            validator = QDoubleValidator(0.0, 999999999.0, 2)  # min=0, max=999M, 2 знака после запятой
            validator.setNotation(QDoubleValidator.StandardNotation)
            self.amount_input.setValidator(validator)

            # Дата
            self.date_input = QDateEdit()
            self.date_input.setCalendarPopup(True)
            self.date_input.setDate(QDate.currentDate())
            self.date_input.setDisplayFormat("dd.MM.yyyy")
            self.date_input.setFixedHeight(26)
            self.date_input.setFixedWidth(80)

            # Описание
            self.description_input = QLineEdit()
            self.description_input.setPlaceholderText("Описание перевода (необязательно)")
            self.description_input.setFixedHeight(26)
            self.description_input.setMinimumWidth(300)
            # form_layout.addRow("Описание:", self.description_input)

            date_amount_layout.addWidget(QLabel("Сумма:"))
            date_amount_layout.addWidget(self.amount_input)
            date_amount_layout.addWidget(QLabel("Дата:"))
            date_amount_layout.addWidget(self.date_input)
            date_amount_layout.addWidget(QLabel("Описание:"))
            date_amount_layout.addWidget(self.description_input)
            date_amount_layout.addStretch()

            date_amount_widget = QWidget()
            date_amount_widget.setLayout(date_amount_layout)
            form_layout.addRow("", date_amount_widget)

            layout.addLayout(form_layout)

            # Кнопки
            btn_layout = QHBoxLayout()
            # self.add_close_button = CompactButton("Добавить и закрыть")
            # self.add_close_button.clicked.connect(self._add_and_close)
            self.add_btn = CompactButton("Добавить")
            self.add_btn.clicked.connect(self._on_add_clicked)
            self.close_btn = CompactButton("Отмена")
            self.close_btn.clicked.connect(self.accept)
            btn_layout.addWidget(self.add_btn)
            btn_layout.addWidget(self.close_btn)
            layout.addLayout(btn_layout)
            layout.addStretch()

            self._toggle_transfer_type()
            return tab
        except Exception as e:
                    logger.error(f"[{self.__class__.__name__}] Ошибка создания вкладки добавления перевода: {e}", exc_info=True)
                    raise

    def _create_view_tab(self) -> QWidget:
        """Создаёт вкладку просмотра переводов с панелью фильтров."""
        try:
            tab = QWidget()
            layout = QVBoxLayout(tab)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            
            # Панель фильтров
            filter_panel = self._create_filter_panel()
            layout.addWidget(filter_panel)
            
            # Таблица переводов
            self.transfers_tree = QTreeWidget()
            self.transfers_tree.setHeaderLabels([
                "Дата", "Тип", "Сумма", "Откуда", "Куда", "Контрагент", "Описание"
            ])
            
            # Множественное выделение
            self.transfers_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
            self.transfers_tree.setSelectionBehavior(QTreeWidget.SelectRows)
            
            # Настройка заголовков (только размеры колонок)
            header = self.transfers_tree.header()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Дата
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Тип
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Сумма
            header.setSectionResizeMode(3, QHeaderView.Stretch)           # Откуда
            header.setSectionResizeMode(4, QHeaderView.Stretch)           # Куда
            header.setSectionResizeMode(5, QHeaderView.Stretch)           # Контрагент
            header.setSectionResizeMode(6, QHeaderView.Stretch)           # Описание
            
            # Контекстное меню
            self.transfers_tree.setContextMenuPolicy(Qt.CustomContextMenu)
            self.transfers_tree.customContextMenuRequested.connect(self._show_context_menu)
            
            layout.addWidget(self.transfers_tree)
            
            return tab
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания вкладки: {e}", exc_info=True)
            raise

    def _create_filter_panel(self) -> QWidget:
        """
        Создаёт панель фильтров над таблицей переводов.
        
        Returns:
            QWidget с горизонтальной панелью фильтров
        """
        try:
            panel = QFrame()
            panel.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
            layout = QHBoxLayout(panel)
            layout.setContentsMargins(10, 8, 10, 8)
            layout.setSpacing(10)
            
            # Фильтр по дате "С"
            layout.addWidget(QLabel("📅 С:"))
            self.filter_date_from = QDateEdit()
            self.filter_date_from.setCalendarPopup(True)
            self.filter_date_from.setMinimumDate(QDate(2000, 1, 1))
            self.filter_date_from.setDate(QDate(2000, 1, 1))
            self.filter_date_from.setDisplayFormat("dd.MM.yyyy")
            self.filter_date_from.setFixedWidth(95)
            layout.addWidget(self.filter_date_from)
            
            # Фильтр по дате "По"
            layout.addWidget(QLabel("По:"))
            self.filter_date_to = QDateEdit()
            self.filter_date_to.setCalendarPopup(True)
            self.filter_date_to.setDate(QDate.currentDate())
            self.filter_date_to.setDisplayFormat("dd.MM.yyyy")
            self.filter_date_to.setFixedWidth(95)
            layout.addWidget(self.filter_date_to)
            
            layout.addSpacing(10)
            
            # Поиск по тексту
            layout.addWidget(QLabel("🔍"))
            self.filter_search = QLineEdit()
            self.filter_search.setPlaceholderText("Описание...")
            self.filter_search.setFixedWidth(100)
            self.filter_search.returnPressed.connect(self._apply_filters)
            layout.addWidget(self.filter_search)
            
            layout.addSpacing(10)
            
            # Фильтр по счету
            layout.addWidget(QLabel("🏦"))
            self.filter_account = QComboBox()
            self.filter_account.addItem("Все счета", userData=None)
            self.filter_account.setFixedWidth(180)
            layout.addWidget(self.filter_account)
            
            # Кнопка применения
            self.filter_apply_btn = CompactButton("Применить")
            self.filter_apply_btn.clicked.connect(self._apply_filters)
            layout.addWidget(self.filter_apply_btn)
            
            # Кнопка сброса
            self.filter_reset_btn = CompactButton("Сбросить")
            self.filter_reset_btn.clicked.connect(self._reset_filters)
            layout.addWidget(self.filter_reset_btn)
            
            layout.addStretch()
            
            return panel
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания панели фильтров: {e}", exc_info=True)
            raise

    def _toggle_transfer_type(self):
        """
        Переключает видимость блоков внутреннего/внешнего перевода.
        Вызывается сигналом toggled от radio_internal.
        """
        try:
            is_internal = self.radio_internal.isChecked()
            self.internal_frame.setVisible(is_internal)
            self.external_frame.setVisible(not is_internal)
            
            logger.debug(f"[{self.__class__.__name__}] Переключён тип перевода: "
                        f"{'внутренний' if is_internal else 'внешний'}")
            
        except AttributeError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: UI-элементы не инициализированы: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка переключения типа перевода: {e}", exc_info=True)
            raise

    def _on_add_clicked(self):
        """Обработчик нажатия кнопки 'Добавить'."""
        try:
            data = self._get_form_data()
            
            # Проверяем комиссию для внешних исходящих переводов с кредитки
            if data["type"] == "external" and data["direction"] == "outgoing":
                fee_info = self.presenter.check_credit_card_transfer( #TODO: убрать данную проверку
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

    def _show_context_menu(self, position: QPoint):
        """
        Показывает контекстное меню для перевода.
        
        Args:
            position: позиция клика в локальных координатах дерева
        """
        try:
            selected_items = self.transfers_tree.selectedItems()
            if not selected_items:
                return

            # Проверяем наличие системных переводов в выделении
            has_system = any(
                item.data(0, Qt.UserRole + 1) for item in selected_items
            )
            
            menu = QMenu(self)
            count = len(selected_items)
            
            if has_system:
                # Если есть системные — показываем неактивный пункт-предупреждение
                warning_action = menu.addAction("⚠️ Системные переводы нельзя удалять")
                warning_action.setEnabled(False)
            else:
                delete_action = menu.addAction(f"🗑️ Удалить выбранные ({count})")
                delete_action.triggered.connect(
                    lambda: self._delete_selected_transfers(self._get_selected_transfer_ids())
                )
            
            # Конвертируем координаты в глобальные
            global_position = self.transfers_tree.viewport().mapToGlobal(position)
            menu.exec(global_position)
            
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка отображения контекстного меню: {e}", exc_info=True)


    def _delete_selected_transfers(self, transfer_ids: List[int]):
        """Удаляет несколько переводов.
        
        Args:
            transfer_ids: список ID переводов
        """
        try:
            if not transfer_ids:
                return
                
            reply = QMessageBox.question(
                self,
                "Подтверждение удаления",
                f"Вы уверены, что хотите удалить {len(transfer_ids)} перевод(ов)?\n\nЭто действие нельзя отменить.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.StandardButton.Yes and self.presenter:
                self.presenter.delete_transfers(transfer_ids)
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация удаления: {e}")
            self.show_status(str(e), message_type="error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка удаления переводов: {e}", exc_info=True)
            self.show_status("Произошла ошибка при удалении", message_type="error")

    # =================== Фильтры ===================
    
    def _apply_filters(self):
        """
        Применяет фильтры к таблице переводов.
        Собирает параметры из UI и передаёт в презентер.
        """
        try:
            filters = {
                'date_from': self.filter_date_from.date().toString("yyyy-MM-dd"),
                'date_to': self.filter_date_to.date().toString("yyyy-MM-dd"),
                'search': self.filter_search.text().strip() or None,
                'account_id': self.filter_account.currentData()
            }
            
            if self.presenter:
                self.presenter.load_transfers_filters(filters=filters)
                self.show_status("Фильтры применены", message_type="success")
            else:
                self.show_status("Презентер недоступен", message_type="error")
                
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация фильтров: {e}")
            self.show_status(str(e), message_type="error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка применения фильтров: {e}", exc_info=True)
            self.show_status("Ошибка применения фильтров", message_type="error")

    def _reset_filters(self):
        """
        Сбрасывает все фильтры к значениям по умолчанию.
        """
        try:
            self.filter_date_from.setDate(QDate(2000, 1, 1))
            self.filter_date_to.setDate(QDate.currentDate())
            self.filter_search.clear()
            self.filter_account.setCurrentIndex(0)  # "Все счета"
            
            if self.presenter:
                self.presenter.refresh_data()
                self.show_status("Фильтры сброшены", message_type="success")
                
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка сброса фильтров: {e}", exc_info=True)
            self.show_status("Ошибка сброса фильтров", message_type="error")

    def update_account_filter(self, accounts: List):
        """
        Обновляет выпадающий список счетов в панели фильтров.
        
        Args:
            accounts: список объектов Account
        """
        try:
            # Сохраняем текущий выбранный счёт
            current_id = self.filter_account.currentData()
            
            # Очищаем и заполняем заново
            self.filter_account.clear()
            self.filter_account.addItem("Все счета", userData=None)
            
            for account in accounts:
                display_text = f"{account.name} ({account.current_balance:,.2f} {account.currency})"
                self.filter_account.addItem(display_text, userData=account.id)
            
            # Восстанавливаем выбор, если возможно
            if current_id is not None:
                index = self.filter_account.findData(current_id)
                if index >= 0:
                    self.filter_account.setCurrentIndex(index)
                    
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обновления фильтра счетов: {e}", exc_info=True)

    # =================== Контракт View <-> Presenter ===================

    def load_transfers_tree(self, transfers: List[Transfer]):
        """
        Загружает переводы в таблицу.
        
        Args:
            transfers: список объектов Transfer из презентера
        """
        try:
            self.transfers_tree.clear()
            
            if not transfers:
                self.show_status("Нет переводов для отображения", message_type="warning")
                return
            
            for transfer in transfers:
                # Форматирование даты (из "YYYY-MM-DD" в "DD.MM.YYYY")
                date_str = transfer.date
                if date_str and len(date_str) == 10:
                    try:
                        date_str = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
                    except ValueError:
                        pass  # Оставляем как есть, если формат неверный
                
                # Форматирование типа
                display_type = "Внутренний" if transfer.type == "internal" else "Внешний"
                
                # Форматирование суммы (Decimal)
                try:
                    amount_formatted = f"{transfer.amount:,.2f}"
                except (ValueError, TypeError):
                    amount_formatted = "0.00"
                
                # Получение имён счетов (добавлены динамически в репозитории)
                from_name = getattr(transfer, 'from_account_name', '') or ''
                to_name = getattr(transfer, 'to_account_name', '') or ''
                counterparty = getattr(transfer, 'counterparty', '') or ''
                
                item = QTreeWidgetItem([
                    date_str,
                    display_type,
                    amount_formatted,
                    from_name,
                    to_name,
                    counterparty,
                    transfer.description or ""
                ])
                
                # Сохраняем ID и флаг системности в скрытых данных элемента
                item.setData(0, Qt.UserRole, transfer.id)
                item.setData(0, Qt.UserRole + 1, transfer.is_system)
                
                self.transfers_tree.addTopLevelItem(item)
            
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка загрузки переводов: {e}", exc_info=True)
            self.show_status("Ошибка загрузки переводов", message_type="error")

    def clear_selection(self):
        """Очищает выделение в таблице."""
        self.transfers_tree.clearSelection()