# ui/dialogs/refund_dialog.py
import logging
from decimal import Decimal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit,
    QPushButton, QLineEdit, QFormLayout, QGroupBox, QCheckBox, QMessageBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont, QDoubleValidator
from core.models import Transaction
from ui.widgets.buttons import CompactButton


logger = logging.getLogger(__name__)


class RefundDialog(QDialog):
    """Диалог создания возврата по оригинальной транзакции."""

    def __init__(
        self,
        parent=None,
        transaction: Transaction = None,
        max_refundable: Decimal = None,
        already_refunded: Decimal = None,
        account_name: str = "—",
        category_name: str = "—",
        currency: str = "₽",
    ):
        """
        Инициализация диалога возврата.

        Args:
            parent: родительское окно
            transaction: оригинальная транзакция, по которой создаётся возврат
            max_refundable: максимальная доступная сумма для возврата (Decimal)
            already_refunded: уже возвращённая сумма (Decimal)
            account_name: название счёта оригинала (для отображения)
            category_name: название категории оригинала (для отображения)
            currency: валюта счёта (для отображения)
        """
        super().__init__(parent)
        self.transaction = transaction
        self.max_refundable = max_refundable if max_refundable is not None else Decimal("0")
        self.already_refunded = already_refunded if already_refunded is not None else Decimal("0")
        self.account_name = account_name
        self.category_name = category_name
        self.currency = currency

        self.setWindowTitle("Создание возврата")
        self.resize(420, 420)

        self._init_ui()
        self._apply_full_refund_state(True)

    def _init_ui(self):
        """Инициализация интерфейса диалога."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        main_layout.addWidget(self._create_info_group())
        main_layout.addWidget(self._create_settings_group())
        main_layout.addLayout(self._create_buttons())

    def _create_info_group(self) -> QGroupBox:
        """
        Создаёт блок информации об оригинальной транзакции.

        Returns:
            QGroupBox с данными оригинала и состоянием возврата
        """
        group = QGroupBox("Оригинальная операция")
        layout = QFormLayout()

        original_amount = abs(self.transaction.amount)

        layout.addRow("Дата:", QLabel(str(self.transaction.date)))
        layout.addRow("Сумма:", QLabel(f"{original_amount:,.2f} {self.currency}"))
        layout.addRow("Тип:", QLabel("Доход" if self.transaction.trans_type == "income" else "Расход"))
        layout.addRow("Счёт:", QLabel(self.account_name))
        layout.addRow("Категория:", QLabel(self.category_name))
        layout.addRow("Уже возвращено:", QLabel(f"{self.already_refunded:,.2f} {self.currency}"))

        available_label = QLabel(f"{self.max_refundable:,.2f} {self.currency}")
        available_label.setFont(QFont())
        # available_label.setStyleSheet("color: #2e7d32; font-weight: bold;")
        layout.addRow("Доступно для возврата:", available_label)

        if self.transaction.description:
            layout.addRow("Описание:", QLabel(self.transaction.description[:50]))

        group.setLayout(layout)
        return group

    def _create_settings_group(self) -> QGroupBox:
        """
        Создаёт блок настроек возврата.

        Содержит чекбокс полного возврата, поле суммы, дату и описание.

        Returns:
            QGroupBox с полями ввода для параметров возврата
        """
        group = QGroupBox("Параметры возврата")
        layout = QFormLayout()

        # Чекбокс полного возврата (по умолчанию включен)
        self.full_refund_cb = QCheckBox("Полный возврат")
        self.full_refund_cb.setChecked(True)
        self.full_refund_cb.toggled.connect(self._on_full_refund_toggled)
        layout.addRow("", self.full_refund_cb)

        # Сумма возврата (QLineEdit с валидатором)
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Сумма возврата")
        self.amount_input.setText(f"{self.max_refundable:.2f}")
        amount_validator = QDoubleValidator(
            0.01, float(self.max_refundable), 2, self
        )
        self.amount_input.setValidator(amount_validator)
        layout.addRow("Сумма возврата:", self.amount_input)

        # Дата возврата (по умолчанию — сегодня)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setDate(QDate.currentDate())
        layout.addRow("Дата возврата:", self.date_edit)

        # Описание
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Описание возврата...")
        original_desc = (self.transaction.description or "").strip()
        default_description = (
            f"Возврат: {original_desc}"
            if original_desc
            else f"Возврат транзакции #{self.transaction.id}"
        )
        self.description_input.setText(default_description)
        layout.addRow("Описание:", self.description_input)

        group.setLayout(layout)
        return group

    def _create_buttons(self) -> QHBoxLayout:
        """
        Создаёт блок кнопок диалога.

        Returns:
            QHBoxLayout с кнопками "Создать возврат" и "Отмена"
        """
        layout = QHBoxLayout()

        ok_button = CompactButton("Создать возврат", "success")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self._on_accept)

        cancel_button = CompactButton("Отмена", "warning")
        cancel_button.clicked.connect(self.reject)

        layout.addWidget(ok_button)
        layout.addWidget(cancel_button)
        layout.addStretch()

        return layout

    def _on_full_refund_toggled(self, checked: bool):
        """
        Обрабатывает переключение чекбокса полного возврата.

        При включении блокирует поле суммы и подставляет максимальную сумму.
        При выключении разблокирует поле для ручного ввода.

        Args:
            checked: состояние чекбокса (True — полный возврат)
        """
        try:
            self._apply_full_refund_state(checked)
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка обработки чекбокса: {e}",
                exc_info=True,
            )

    def _apply_full_refund_state(self, checked: bool):
        """
        Применяет состояние поля суммы в зависимости от чекбокса.

        Args:
            checked: True — поле заблокировано с максимальной суммой,
                     False — поле активно для ручного ввода
        """
        if checked:
            self.amount_input.setEnabled(False)
            self.amount_input.setText(f"{self.max_refundable:.2f}")
        else:
            self.amount_input.setEnabled(True)
            self.amount_input.setFocus()
            self.amount_input.selectAll()

    def _on_accept(self):
        """Валидирует данные и закрывает диалог с кодом Accept."""
        try:
            self.get_refund_data()  # Проверка валидации
            self.accept()
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация возврата: {e}")
            QMessageBox.warning(self, "Ошибка валидации", str(e))
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка валидации: {e}",
                exc_info=True,
            )
            QMessageBox.critical(self, "Ошибка", "Произошла ошибка при проверке данных")

    def get_refund_data(self) -> dict:
        """
        Собирает и валидирует данные для создания возврата.

        Returns:
            Словарь с параметрами:
            - date: str, формат yyyy-MM-dd
            - amount: float, положительная сумма возврата
            - description: str, описание возврата

        Raises:
            ValueError: если сумма пустая, некорректная или превышает доступную
        """
        try:
            # Сумма
            amount_str = self.amount_input.text().strip()
            if not amount_str:
                raise ValueError("Сумма возврата не может быть пустой")

            try:
                amount = float(amount_str.replace(",", "."))
            except ValueError:
                raise ValueError(f"Некорректная сумма: {amount_str}")

            if amount <= 0:
                raise ValueError("Сумма должна быть больше нуля")

            if amount > float(self.max_refundable):
                raise ValueError(
                    f"Сумма возврата ({amount:.2f}) превышает доступную "
                    f"({self.max_refundable:,.2f})"
                )

            # Дата
            new_date = self.date_edit.date().toString("yyyy-MM-dd")

            # Описание
            description = self.description_input.text().strip()
            if not description:
                raise ValueError("Описание не может быть пустым")

            return {
                "date": new_date,
                "amount": amount,
                "description": description,
            }

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация данных: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка сбора данных: {e}",
                exc_info=True,
            )
            raise