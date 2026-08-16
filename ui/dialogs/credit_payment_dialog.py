"""
Диалог внесения платежа по банковскому кредиту.

Платёж разбивается на две операции:
- Перевод (тело долга) — уменьшает remaining кредита
- Расход (проценты) — опционально, в системную категорию

Использует CreditPresenter для валидации и проведения платежа.
"""

import logging
from typing import Optional, Dict, Any
from decimal import Decimal

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QDateEdit,
    QPushButton, QGroupBox, QWidget
)
from PySide6.QtCore import Qt, QDate, Signal

from ui.presenters.credit_presenter import CreditPresenter
from utils.validators import parse_float, try_to_decimal
from ui.widgets.buttons import CompactButton

logger = logging.getLogger(__name__)


class CreditPaymentDialog(QDialog):
    """Диалог внесения платежа по банковскому кредиту."""

    # Сигнал об успешном внесении платежа
    payment_made = Signal(int)  # Передаёт loan_id

    def __init__(
        self,
        parent: Optional[QWidget],
        presenter: CreditPresenter,
        loan_id: int,
    ):
        """
        Инициализация диалога.

        Args:
            parent: родительское окно
            presenter: экземпляр CreditPresenter
            loan_id: идентификатор кредита для внесения платежа
        """
        super().__init__(parent)
        self.presenter = presenter
        self.loan_id = loan_id
        self._loan_info: Optional[Dict[str, Any]] = None
        self._remaining: Decimal = Decimal("0.00")

        self._init_ui()
        self._load_data()
        self._connect_signals()

    # ------------------------------------------------------------------ #
    #                         Инициализация UI                           #
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        """Инициализирует интерфейс диалога."""
        self.setWindowTitle("Внесение платежа по кредиту")
        self.setMinimumWidth(450)
        self.setMinimumHeight(400)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)

        # --- Группа: Информация о кредите ---
        info_group = QGroupBox("Информация о кредите")
        info_layout = QFormLayout(info_group)

        self.credit_name_label = QLabel("—")
        self.credit_name_label.setStyleSheet("font-weight: bold;")
        info_layout.addRow("Название:", self.credit_name_label)

        self.remaining_label = QLabel("—")
        self.remaining_label.setStyleSheet("color: #d32f2f; font-weight: bold;")
        info_layout.addRow("Остаток долга:", self.remaining_label)

        main_layout.addWidget(info_group)

        # --- Группа: Параметры платежа ---
        payment_group = QGroupBox("Параметры платежа")
        payment_layout = QFormLayout(payment_group)

        self.account_combo = QComboBox()
        payment_layout.addRow("Счёт списания:", self.account_combo)

        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("15000")
        payment_layout.addRow("Сумма платежа:", self.amount_input)

        self.interest_input = QLineEdit()
        self.interest_input.setPlaceholderText("0 (опционально)")
        self.interest_input.setText("0")
        payment_layout.addRow("Проценты:", self.interest_input)

        self.body_label = QLabel("0,00 ₽")
        self.body_label.setStyleSheet("font-weight: bold; color: #1976d2;")
        payment_layout.addRow("Тело долга:", self.body_label)

        self.payment_date_edit = QDateEdit()
        self.payment_date_edit.setCalendarPopup(True)
        self.payment_date_edit.setDate(QDate.currentDate())
        self.payment_date_edit.setDisplayFormat("yyyy-MM-dd")
        payment_layout.addRow("Дата платежа:", self.payment_date_edit)

        main_layout.addWidget(payment_group)

        # --- Статус-бар ---
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red;")
        self.status_label.setWordWrap(True)
        main_layout.addWidget(self.status_label)

        # --- Кнопки ---
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.pay_button = CompactButton("Внести платёж", "success")
        self.pay_button.setDefault(True)
        self.pay_button.setMinimumWidth(140)
        buttons_layout.addWidget(self.pay_button)

        self.cancel_button = CompactButton("Отмена", "neutral")
        self.cancel_button.setMinimumWidth(120)
        buttons_layout.addWidget(self.cancel_button)

        main_layout.addLayout(buttons_layout)

    # ------------------------------------------------------------------ #
    #                        Загрузка данных                             #
    # ------------------------------------------------------------------ #

    def _load_data(self) -> None:
        """Загружает информацию о кредите и список пользовательских счетов."""
        try:
            # Загружаем информацию о кредите
            self._loan_info = self.presenter.get_credit_details(self.loan_id)
            if self._loan_info is None:
                self._show_status("Кредит не найден", "error")
                return

            loan = self._loan_info["loan"]
            self.credit_name_label.setText(loan.name)
            self._remaining = loan.remaining
            self.remaining_label.setText(
                f"{self._format_decimal(self._remaining)} ₽"
            )

            # Загружаем пользовательские счета (без системных)
            accounts = self.presenter.get_user_accounts()
            if not accounts:
                self._show_status("Нет доступных счетов для списания", "error")
                self.pay_button.setEnabled(False)
                return

            for acc in accounts:
                self.account_combo.addItem(
                    f"{acc['name']} ({acc['account_type']})",
                    acc["id"],
                )

        except ValueError as e:
            logger.warning(f"[CreditPaymentDialog] Валидация: {e}")
            self._show_status(str(e), "error")
        except Exception as e:
            logger.error(
                f"[CreditPaymentDialog] Ошибка загрузки данных: {e}",
                exc_info=True,
            )
            self._show_status("Не удалось загрузить данные", "error")

    # ------------------------------------------------------------------ #
    #                        Подключение сигналов                        #
    # ------------------------------------------------------------------ #

    def _connect_signals(self) -> None:
        """Подключает сигналы к слотам."""
        self.amount_input.textChanged.connect(self._on_amount_changed)
        self.interest_input.textChanged.connect(self._on_interest_changed)
        self.pay_button.clicked.connect(self._on_pay_clicked)
        self.cancel_button.clicked.connect(self.reject)

    def _on_amount_changed(self, text: str) -> None:
        """
        Пересчитывает тело долга при изменении суммы платежа.

        Args:
            text: текущий текст в поле суммы
        """
        self._calculate_body()

    def _on_interest_changed(self, text: str) -> None:
        """
        Пересчитывает тело долга при изменении суммы процентов.

        Args:
            text: текущий текст в поле процентов
        """
        self._calculate_body()

    # ------------------------------------------------------------------ #
    #                        Обработка платежа                           #
    # ------------------------------------------------------------------ #

    def _on_pay_clicked(self) -> None:
        """Обрабатывает нажатие кнопки 'Внести платёж'."""
        self._clear_status()

        try:
            # Базовая валидация на уровне диалога
            from_account_id = self.account_combo.currentData()
            if from_account_id is None:
                raise ValueError("Не выбран счёт списания")

            amount_str = self.amount_input.text().strip()
            if not amount_str:
                raise ValueError("Сумма платежа не может быть пустой")

            amount = parse_float(amount_str)
            if amount is None or amount <= 0:
                raise ValueError("Сумма платежа должна быть положительным числом")

            interest_str = self.interest_input.text().strip() or "0"
            interest = parse_float(interest_str)
            if interest is None or interest < 0:
                raise ValueError("Сумма процентов не может быть отрицательной")

            if interest >= amount:
                raise ValueError(
                    f"Сумма процентов ({interest}) должна быть меньше "
                    f"суммы платежа ({amount})"
                )

            # Проверка тела долга
            body = amount - interest
            if body > float(self._remaining):
                raise ValueError(
                    f"Тело долга ({body:.2f}) превышает остаток "
                    f"({self._format_decimal(self._remaining)})"
                )

            # Дата платежа
            payment_date = self.payment_date_edit.date().toString("yyyy-MM-dd")

            # Вызываем презентер
            result = self.presenter.make_payment(
                loan_id=self.loan_id,
                from_account_id=from_account_id,
                amount_str=amount_str,
                interest_amount_str=interest_str,
                payment_date_str=payment_date,
            )

            logger.info(
                f"[CreditPaymentDialog] Внесён платёж по кредиту #{self.loan_id}: "
                f"тело={result['body_amount']}, "
                f"проценты={result['interest_amount']}"
            )

            self.payment_made.emit(self.loan_id)
            self.accept()

        except ValueError as e:
            self._show_status(str(e), "error")
        except Exception as e:
            logger.error(
                f"[CreditPaymentDialog] Ошибка UI: {e}",
                exc_info=True,
            )
            self._show_status("Произошла ошибка при внесении платежа", "error")

    # ------------------------------------------------------------------ #
    #                    Вспомогательные методы                          #
    # ------------------------------------------------------------------ #

    def _calculate_body(self) -> None:
        """Пересчитывает и отображает тело долга на основе введённых значений."""
        try:
            amount = try_to_decimal(self.amount_input.text())
            interest = try_to_decimal(self.interest_input.text())

            if amount is None:
                self.body_label.setText("—")
                return

            if interest is None:
                interest = Decimal("0")

            if interest >= amount:
                self.body_label.setText("Некорректные данные")
                self.body_label.setStyleSheet("font-weight: bold; color: #d32f2f;")
                return

            body = amount - interest
            self.body_label.setText(f"{self._format_decimal(body)} ₽")
            self.body_label.setStyleSheet("font-weight: bold; color: #1976d2;")

        except Exception as e:
            logger.debug(f"[CreditPaymentDialog] Ошибка расчёта тела: {e}")
            self.body_label.setText("—")

    def _format_decimal(self, value: Decimal) -> str:
        """
        Форматирует Decimal для отображения в UI.

        Args:
            value: число для форматирования

        Returns:
            Отформатированная строка с разделителями тысяч
        """
        try:
            rounded = value.quantize(Decimal("0.01"))
            str_value = str(rounded)

            if "." in str_value:
                int_part, frac_part = str_value.split(".")
            else:
                int_part = str_value
                frac_part = "00"

            # Добавляем разделители тысяч
            if len(int_part) > 3:
                groups = []
                while int_part:
                    groups.append(int_part[-3:])
                    int_part = int_part[:-3]
                int_part = " ".join(reversed(groups))

            return f"{int_part},{frac_part}"

        except Exception as e:
            logger.debug(f"[CreditPaymentDialog] Ошибка форматирования: {e}")
            return str(value)

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