"""
Диалог создания банковского кредита.

Поддерживает два режима:
- Потребительский кредит: деньги переводятся на указанный счёт пользователя
- POS-кредит (на покупку): сразу создаётся расход на указанную категорию

Использует CreditPresenter для валидации и создания кредита.
"""

import logging
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QDateEdit, QTextEdit,
    QPushButton, QStackedWidget, QWidget, QMessageBox,
    QGroupBox,
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QDoubleValidator, QIntValidator

from ui.presenters.credit_presenter import CreditPresenter
from utils.validators import parse_float, parse_int

logger = logging.getLogger(__name__)


class CreditCreateDialog(QDialog):
    """Диалог создания банковского кредита."""

    # Сигнал об успешном создании кредита
    credit_created = Signal(int)  # Передаёт loan_id

    # Индексы страниц в stacked widget
    PAGE_CONSUMER = 0
    PAGE_PURCHASE = 1

    def __init__(
        self,
        parent: Optional[QWidget],
        presenter: CreditPresenter,
    ):
        """
        Инициализация диалога.

        Args:
            parent: родительское окно
            presenter: экземпляр CreditPresenter, внедрённый из родительского окна
        """
        super().__init__(parent)
        self.presenter = presenter

        # self._categories: List[Dict[str, Any]] = []
        self._accounts: List[Dict[str, Any]] = []

        self._init_ui()
        self._load_data()
        self._connect_signals()

    # ------------------------------------------------------------------ #
    #                         Инициализация UI                           #
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        """Инициализирует интерфейс диалога."""
        self.setWindowTitle("Новый кредит")
        self.setMinimumWidth(480)
        self.setMinimumHeight(560)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # --- Группа: Тип кредита ---
        type_group = QGroupBox("Тип кредита")
        type_layout = QFormLayout(type_group)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Потребительский (деньги на счёт)", "consumer")
        self.type_combo.addItem("На покупку (POS-кредит)", "purchase")
        type_layout.addRow("Тип:", self.type_combo)

        main_layout.addWidget(type_group)

        # --- Группа: Основные параметры ---
        main_group = QGroupBox("Параметры кредита")
        main_form = QFormLayout(main_group)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например: Кредит в Сбере на ремонт")
        main_form.addRow("Название:", self.name_input)

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("500000.00")
        amount_validator = QDoubleValidator(0.01, 999999999.99, 2, self)
        amount_validator.setNotation(QDoubleValidator.StandardNotation)
        self.amount_input.setValidator(amount_validator)
        main_form.addRow("Сумма кредита:", self.amount_input)

        self.issue_date_edit = QDateEdit()
        self.issue_date_edit.setCalendarPopup(True)
        self.issue_date_edit.setDate(QDate.currentDate())
        self.issue_date_edit.setDisplayFormat("yyyy-MM-dd")
        main_form.addRow("Дата выдачи:", self.issue_date_edit)

        self.rate_input = QLineEdit()
        self.rate_input.setPlaceholderText("0 (опционально)")
        self.rate_input.setText("0")
        rate_validator = QDoubleValidator(0.0, 999.99, 2, self)
        rate_validator.setNotation(QDoubleValidator.StandardNotation)
        self.rate_input.setValidator(rate_validator)
        main_form.addRow("Ставка, %:", self.rate_input)

        self.term_input = QLineEdit()
        self.term_input.setPlaceholderText("36 (опционально)")
        term_validator = QIntValidator(1, 999, self)
        self.term_input.setValidator(term_validator)
        main_form.addRow("Срок, мес.:", self.term_input)

        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDate(QDate())  # Пустая дата
        self.due_date_edit.setSpecialValueText("Не указана")
        self.due_date_edit.setDisplayFormat("yyyy-MM-dd")
        main_form.addRow("Дата окончания:", self.due_date_edit)

        self.due_date_label = QLabel("—")
        self.due_date_label.setStyleSheet("color: #1976d2; font-weight: bold;")
        main_form.addRow("Дата окончания (авто):", self.due_date_label)

        # Скрываем сам QDateEdit, если не исползуем пользовательскую дату
        # self.due_date_edit.hide()

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Описание кредита (опционально)")
        self.description_input.setMaximumHeight(70)
        main_form.addRow("Описание:", self.description_input)

        main_layout.addWidget(main_group)

        # --- Специфичные поля (Stacked Widget) ---
        self.specific_group = QGroupBox("Специфичные параметры")
        specific_layout = QVBoxLayout(self.specific_group)

        self.stacked = QStackedWidget()

        # Страница 0: Потребительский кредит
        consumer_page = QWidget()
        consumer_form = QFormLayout(consumer_page)
        self.target_account_combo = QComboBox()
        consumer_form.addRow("Целевой счёт:", self.target_account_combo)
        self.stacked.addWidget(consumer_page)

        # Страница 1: POS-кредит
        purchase_page = QWidget()
        purchase_form = QFormLayout(purchase_page)
        self.category_combo = QComboBox()
        purchase_form.addRow("Категория покупки:", self.category_combo)

        self.purchase_description_input = QLineEdit()
        self.purchase_description_input.setPlaceholderText(
            "Например: iPhone 15 Pro"
        )
        purchase_form.addRow("Описание покупки:", self.purchase_description_input)
        self.stacked.addWidget(purchase_page)

        specific_layout.addWidget(self.stacked)
        main_layout.addWidget(self.specific_group)

        # --- Подключение сигналов для автоматического расчёта ---
        self.term_input.textChanged.connect(self._calculate_due_date)
        self.issue_date_edit.dateChanged.connect(self._calculate_due_date)

        # --- Статус-бар ---
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red;")
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)

        # --- Кнопки ---
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.create_button = QPushButton("Создать")
        self.create_button.setDefault(True)
        self.create_button.setMinimumWidth(120)
        buttons_layout.addWidget(self.create_button)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setMinimumWidth(120)
        buttons_layout.addWidget(self.cancel_button)

        main_layout.addLayout(buttons_layout)

    # ------------------------------------------------------------------ #
    #                        Загрузка данных                             #
    # ------------------------------------------------------------------ #

    def _load_data(self) -> None:
        """Загружает списки счетов и категорий из презентера."""
        try:
            self._accounts = self.presenter.get_user_accounts()
            for acc in self._accounts:
                self.target_account_combo.addItem(
                    f"{acc['name']} ({acc['account_type']})",
                    acc["id"],
                )

            self._categories = self.presenter.get_user_categories()
            for cat in self._categories:
                # text = имя, userData = ID категории
                self.category_combo.addItem(cat.name, userData=cat.id)

        except Exception as e:
            logger.error(
                f"[CreditCreateDialog] Ошибка загрузки данных: {e}",
                exc_info=True,
            )
            self._show_status("Не удалось загрузить данные", "error")

    # ------------------------------------------------------------------ #
    #                        Подключение сигналов                        #
    # ------------------------------------------------------------------ #

    def _connect_signals(self) -> None:
        """Подключает сигналы к слотам."""
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self.create_button.clicked.connect(self._on_create_clicked)
        self.cancel_button.clicked.connect(self.reject)

    def _on_type_changed(self, index: int) -> None:
        """
        Переключает страницу специфичных параметров при смене типа кредита.

        Args:
            index: индекс выбранного элемента в ComboBox
        """
        loan_type = self.type_combo.currentData()
        if loan_type == "consumer":
            self.stacked.setCurrentIndex(self.PAGE_CONSUMER)
        else:
            self.stacked.setCurrentIndex(self.PAGE_PURCHASE)
        self._clear_status()

    # ------------------------------------------------------------------ #
    #                        Обработка создания                          #
    # ------------------------------------------------------------------ #

    def _on_create_clicked(self) -> None:
        """Обрабатывает нажатие кнопки 'Создать'."""
        self._clear_status()

        try:
            loan_type = self.type_combo.currentData()
            common_data = self._collect_common_data()

            if loan_type == "consumer":
                target_account_id = self.target_account_combo.currentData()
                if target_account_id is None:
                    raise ValueError("Не выбран целевой счёт")

                result = self.presenter.create_consumer_loan(
                    name=common_data["name"],
                    loan_amount_str=common_data["amount"],
                    issue_date_str=common_data["issue_date"],
                    target_account_id=target_account_id,
                    interest_rate_str=common_data["rate"],
                    term_months_str=common_data["term"],
                    due_date_str=common_data["due_date"],
                    description=common_data["description"],
                )
            else:
                category_id = self.category_combo.currentData()
                if category_id is None:
                    raise ValueError("Не выбрана категория покупки")

                purchase_description = (
                    self.purchase_description_input.text().strip()
                )

                result = self.presenter.create_purchase_loan(
                    name=common_data["name"],
                    loan_amount_str=common_data["amount"],
                    issue_date_str=common_data["issue_date"],
                    category_id=category_id,
                    purchase_description=purchase_description,
                    interest_rate_str=common_data["rate"],
                    term_months_str=common_data["term"],
                    due_date_str=common_data["due_date"],
                    description=common_data["description"],
                )

            loan_id = result["loan_id"]
            logger.info(
                f"[CreditCreateDialog] Создан кредит id={loan_id}, "
                f"type={loan_type}"
            )

            self.credit_created.emit(loan_id)
            self.accept()

        except ValueError as e:
            self._show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[CreditCreateDialog] Ошибка UI: {e}", exc_info=True)
            self._show_status("Произошла ошибка при создании кредита", "error")

    # ------------------------------------------------------------------ #
    #                    Сбор и валидация данных                         #
    # ------------------------------------------------------------------ #

    def _collect_common_data(self) -> Dict[str, Any]:
        """
        Собирает общие данные из формы.

        Returns:
            Словарь с данными:
            {
                'name': str,
                'amount': str,
                'issue_date': str,
                'rate': str,
                'term': str,
                'due_date': str,
                'description': str
            }

        Raises:
            ValueError: если обязательные поля не заполнены
        """
        name = self.name_input.text().strip()
        if not name:
            raise ValueError("Название кредита не может быть пустым")

        amount = self.amount_input.text()
        if not amount:
            raise ValueError("Сумма кредита не может быть пустой")

        issue_date = self.issue_date_edit.date().toString("yyyy-MM-dd")

        rate = self.rate_input.text().strip() or "0"

        term = self.term_input.text().strip()
        
        # Дата окончания — опциональная
        due_date = ""
        if self.due_date_edit.date() != QDate():
            due_date = self.due_date_edit.date().toString("yyyy-MM-dd")

        description = self.description_input.toPlainText().strip()

        return {
            "name": name,
            "amount": amount,
            "issue_date": issue_date,
            "rate": rate,
            "term": term,
            "due_date": due_date,
            "description": description,
        }

    # ------------------------------------------------------------------ #
    #                         Вспомогательные методы                     #
    # ------------------------------------------------------------------ #
    def _calculate_due_date(self) -> None:
        """
        Пересчитывает и отображает дату окончания на основе даты выдачи и срока.
        
        Вызывается автоматически при изменении:
        - Даты выдачи (issue_date_edit)
        - Срока в месяцах (term_input)
        """
        try:
            # Получаем дату выдачи
            issue_date = self.issue_date_edit.date()
            
            # Получаем срок в месяцах
            term_str = self.term_input.text().strip()
            
            if not term_str:
                # Если срок не указан — очищаем дату окончания
                self.due_date_edit.setDate(QDate())
                self.due_date_label.setText("—")
                return
            
            # Парсим срок
            term_months = parse_int(term_str)
            if term_months is None or term_months <= 0:
                self.due_date_edit.setDate(QDate())
                self.due_date_label.setText("Некорректный срок")
                self.due_date_label.setStyleSheet("color: #d32f2f;")
                return
            
            # Рассчитываем дату окончания
            due_date = issue_date.addMonths(term_months)
            
            # Устанавливаем дату в поле (без сигнала, чтобы не было рекурсии)
            self.due_date_edit.blockSignals(True)
            self.due_date_edit.setDate(due_date)
            self.due_date_edit.blockSignals(False)
            
            # Обновляем label с отформатированной датой
            formatted_date = due_date.toString("dd.MM.yyyy")
            self.due_date_label.setText(formatted_date)
            self.due_date_label.setStyleSheet("color: #1976d2; font-weight: bold;")
            
        except Exception as e:
            logger.debug(f"[CreditCreateDialog] Ошибка расчёта даты окончания: {e}")
            self.due_date_label.setText("—")

    def _show_status(self, message: str, level: str = "info") -> None:
        """
        Отображает сообщение в статус-баре диалога.

        Args:
            message: текст сообщения
            level: уровень ('error', 'warning', 'info')
        """
        colors = {
            "error": "color: #d32f2f;",
            "warning": "color: #f57c00;",
            "info": "color: #1976d2;",
        }
        self.status_label.setStyleSheet(colors.get(level, colors["info"]))
        self.status_label.setText(message)

    def _clear_status(self) -> None:
        """Очищает статус-бар."""
        self.status_label.setText("")