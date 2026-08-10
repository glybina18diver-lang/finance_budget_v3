"""
Диалог внесения платежа по кредитной карте (CreditCardPaymentDialog).

Позволяет внести платёж с автоматическим распределением на тело долга,
проценты и комиссии. Использует стандартные сервисы переводов и транзакций.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional

from PySide6.QtWidgets import (
    QComboBox, QPushButton, QLabel, QLineEdit,
    QDateEdit, QFormLayout, QDialogButtonBox, QGroupBox,
    QVBoxLayout, QCheckBox
)
from PySide6.QtGui import QDoubleValidator
from PySide6.QtCore import Signal

from ui.dialogs.base_dialog import BaseDialog
from utils.validators import parse_float
from utils.validators import to_decimal

logger = logging.getLogger(__name__)

# Константа для нулевого Decimal, чтобы не создавать каждый раз
_DECIMAL_ZERO = Decimal('0.00')


class CreditCardPaymentDialog(BaseDialog):
    """
    Диалог внесения платежа по кредитной карте.
    
    Сигналы:
        payment_made: Вызывается после успешного внесения платежа.
    """
    
    payment_made = Signal()

    def __init__(self, parent, presenter, card_id: int, card_name: str, card_account_id: int, current_debt: Decimal):
        """
        Инициализация диалога платежа.
        
        Args:
            parent: родительское окно
            presenter: экземпляр CreditCardPresenter
            card_id: ID кредитной карты
            card_name: Название карты (для заголовка)
            card_account_id: ID счёта карты (чтобы исключить его из списка источников)
            current_debt: Текущий долг по карте (для отображения)
        """
        super().__init__(parent)
        self.presenter = presenter
        self.card_id = card_id
        self.card_account_id = card_account_id
        self.current_debt = current_debt
        
        self.setWindowTitle(f"Внесение платежа: {card_name}")
        self.resize(450, 330)
        
        self._setup_ui()
        self._load_accounts()
        self._update_principal_label()

    def _setup_ui(self):
        """Настраивает интерфейс диалога."""
        # Блок информации о долге
        info_group = QGroupBox("Информация о карте")
        info_layout = QVBoxLayout()
        self.lbl_debt = QLabel(f"Текущий долг: {self.current_debt:,.2f} ₽".replace(",", " "))
        self.lbl_debt.setStyleSheet("font-weight: bold; color: #d32f2f;")
        info_layout.addWidget(self.lbl_debt)
        info_group.setLayout(info_layout)
        self._main_layout.addWidget(info_group)

        # Форма ввода
        form_group = QGroupBox("Параметры платежа")
        form_layout = QFormLayout()
        
        # Общая сумма
        self.total_input = QLineEdit()
        self.total_input.setPlaceholderText("Введите сумму платежа")
        self.total_input.setFixedHeight(26)
        total_validator = QDoubleValidator(0.01, 10000000.00, 2)
        total_validator.setNotation(QDoubleValidator.StandardNotation)
        self.total_input.setValidator(total_validator)
        self.total_input.textChanged.connect(self._update_principal_label)
        form_layout.addRow("Общая сумма:", self.total_input)
        
        # Дата
        self.date_edit = QDateEdit()
        self.date_edit.setDate(date.today())
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.date_edit.setCalendarPopup(True)
        form_layout.addRow("Дата платежа:", self.date_edit)
        
        # Счёт списания
        self.account_combo = QComboBox()
        form_layout.addRow("Списать со счёта:", self.account_combo)
        
        form_group.setLayout(form_layout)
        self._main_layout.addWidget(form_group)
        
        # Блок распределения платежа
        split_group = QGroupBox("Распределение платежа")
        split_layout = QVBoxLayout()
        
        self.split_checkbox = QCheckBox("Часть платежа идёт на погашение процентов")
        self.split_checkbox.toggled.connect(self._on_split_toggled)
        split_layout.addWidget(self.split_checkbox)
        
        breakdown_form = QFormLayout()
        
        self.interest_input = QLineEdit()
        self.interest_input.setPlaceholderText("Введите сумму процентов")
        self.interest_input.setFixedHeight(26)
        interest_validator = QDoubleValidator(0.00, 10000000.00, 2)
        interest_validator.setNotation(QDoubleValidator.StandardNotation)
        self.interest_input.setValidator(interest_validator)
        self.interest_input.setEnabled(False)
        self.interest_input.textChanged.connect(self._update_principal_label)
        breakdown_form.addRow("На проценты:", self.interest_input)
        
        self.principal_label = QLabel("0.00 ₽")
        self.principal_label.setStyleSheet("font-weight: bold;")
        breakdown_form.addRow("На основной долг (авто):", self.principal_label)
        
        split_layout.addLayout(breakdown_form)
        split_group.setLayout(split_layout)
        self._main_layout.addWidget(split_group)
        
        # Блок результата (изначально скрыт)
        self.result_group = QGroupBox("Результат платежа")
        result_layout = QVBoxLayout()
        self.result_label = QLabel()
        self.result_label.setWordWrap(True)
        
        result_layout.addWidget(self.result_label)
        self.result_group.setLayout(result_layout)
        self.result_group.setVisible(False)
        self._main_layout.addWidget(self.result_group)
        
        # Кнопки
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.button(QDialogButtonBox.Ok).setText("Внести платёж")
        self.button_box.button(QDialogButtonBox.Ok).clicked.connect(self._on_pay)
        self.button_box.button(QDialogButtonBox.Cancel).setText("Закрыть")
        self.button_box.button(QDialogButtonBox.Cancel).clicked.connect(self.reject)
        self._main_layout.addWidget(self.button_box)

    def _load_accounts(self):
        """Загружает доступные счета в ComboBox."""
        try:
            self.account_combo.clear()
            accounts = self.presenter.get_accounts_for_payment(self.card_account_id)
            
            if not accounts:
                self.account_combo.addItem("Нет доступных счетов", None)
                self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
                return
                
            for acc in accounts:
                balance_str = f"{acc['balance']:,.2f} ₽".replace(",", " ")
                self.account_combo.addItem(f"{acc['name']} ({balance_str})", acc["id"])
                
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка UI при загрузке счетов для платежа: {e}", exc_info=True)
            self.show_status("Произошла ошибка при загрузке счетов", "error")

    def _on_split_toggled(self, checked: bool):
        """Обрабатывает переключение чекбокса распределения."""
        self.interest_input.setEnabled(checked)
        if not checked:
            self.interest_input.clear()
        self._update_principal_label()

    def _update_principal_label(self):
        """Автоматически пересчитывает сумму на погашение основного долга."""
        try:
            total = (self.total_input.text()) or _DECIMAL_ZERO
            interest = (self.interest_input.text()) or _DECIMAL_ZERO if self.interest_input.isEnabled() else _DECIMAL_ZERO
            
            principal = to_decimal(total) - to_decimal(interest)
            
            if principal < 0:
                self.principal_label.setText(f"{principal:,.2f} ₽".replace(",", " "))
                self.principal_label.setStyleSheet("font-weight: bold; color: #d32f2f;")
            elif principal > self.current_debt:
                # Тело долга превышает сумму долга — предупреждение
                self.principal_label.setText(f"{principal:,.2f} ₽ (превышает долг!)".replace(",", " "))
                self.principal_label.setStyleSheet("font-weight: bold; color: #ff6f00;")
            else:
                self.principal_label.setText(f"{principal:,.2f} ₽".replace(",", " "))
                self.principal_label.setStyleSheet("font-weight: bold; color: #2e7d32;")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка UI при пересчёте: {e}", exc_info=True)
    
    def _on_pay(self):
        """
        Обрабатывает нажатие кнопки 'Внести платёж'.
        
        После успешного платежа форма очищается и готовится к следующему платежу.
        Текущий долг обновляется, чтобы следующий платёж видел актуальные данные.
        """
        try:
            total = to_decimal(self.total_input.text())
            if total is None or total <= 0:
                raise ValueError("Общая сумма платежа должна быть больше нуля")
                
            account_id = self.account_combo.currentData()
            if not account_id:
                raise ValueError("Не выбран счёт для списания")
                
            interest = to_decimal(self.interest_input.text()) if self.interest_input.isEnabled() else _DECIMAL_ZERO
            
            # Расчёт тела долга
            principal = total - interest
            
            # Проверка: тело долга не должно превышать сумму долга
            if principal > self.current_debt:
                raise ValueError(
                    f"Сумма погашения тела долга ({principal:,.2f} ₽) превышает текущий долг "
                    f"({self.current_debt:,.2f} ₽). Увеличьте сумму процентов или уменьшите "
                    f"общую сумму платежа.".replace(",", " ")
                )
            
            if principal < 0:
                raise ValueError("Сумма процентов не может превышать общую сумму платежа")
                
            payment_date = self.date_edit.date().toString("yyyy-MM-dd")
            
            # Вызов презентера
            result = self.presenter.make_payment(
                card_id=self.card_id,
                amount_str=str(total),
                interest_str=str(interest),
                payment_date_str=payment_date,
                from_account_id=account_id
            )
            
            # Показываем результат и обновляем состояние
            self._display_result(result, principal)
            self._reset_form_after_payment(principal)
            
            self.show_status("Платёж успешно внесён", "success")
            self.payment_made.emit()
            # self.accept()
            
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка UI при внесении платежа: {e}", exc_info=True)
            self.show_status("Произошла ошибка при внесении платежа", "error")

    def _display_result(self, result: dict, principal: Decimal):
        """
        Отображает результат распределения платежа.
        
        Args:
            result: словарь с детализацией (principal_amount, interest_amount, total_amount)
            principal: сумма, направленная на погашение тела долга
        """
        try:
            total = result.get("total_amount", _DECIMAL_ZERO)
            interest = result.get("interest_amount", _DECIMAL_ZERO)
            new_debt = self.current_debt - principal
            
            text = (
                f"✅ Платёж успешно внесён!\n\n"
                f"Внесено всего:        {total:>12,.2f} ₽\n"
                f"─────────────────────────────────\n"
                f"На погашение долга:   {principal:>12,.2f} ₽\n"
                f"На проценты:          {interest:>12,.2f} ₽\n"
                f"─────────────────────────────────\n"
                f"Остаток долга:        {new_debt:>12,.2f} ₽"
            )
            self.result_label.setText(text.replace(",", " "))
            self.result_group.setVisible(True)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка отображения результата: {e}", exc_info=True)
    
    def _reset_form_after_payment(self, principal_paid: Decimal):
        """
        Очищает форму после успешного платежа и обновляет текущий долг.
        
        Подготавливает диалог к следующему платежу: сбрасывает поля ввода,
        обновляет отображение долга и возвращает фокус на поле суммы.
        
        Args:
            principal_paid: сумма, направленная на погашение тела долга
        """
        try:
            # Обновляем текущий долг
            self.current_debt = max(_DECIMAL_ZERO, self.current_debt - principal_paid)
            self.lbl_debt.setText(f"Текущий долг: {self.current_debt:,.2f} ₽".replace(",", " "))
            
            # Если долг погашен полностью — меняем цвет на зелёный
            if self.current_debt <= 0:
                self.lbl_debt.setStyleSheet("font-weight: bold; color: #2e7d32;")
                self.show_status("Долг погашен полностью!", "success")
            else:
                self.lbl_debt.setStyleSheet("font-weight: bold; color: #d32f2f;")
            
            # Очищаем поля ввода
            self.total_input.clear()
            self.interest_input.clear()
            
            # Сбрасываем чекбокс разбивки
            self.split_checkbox.setChecked(False)
            self.interest_input.setEnabled(False)
            
            # Пересчитываем метку основного долга
            self._update_principal_label()
            
            # Возвращаем фокус на поле суммы для удобства ввода следующего платежа
            self.total_input.setFocus()
            
            # Скрываем блок результата через 5 секунд (чтобы не загромождать UI)
            # Но оставляем его видимым, если пользователь хочет посмотреть
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка при очистке формы: {e}",
                exc_info=True
            )