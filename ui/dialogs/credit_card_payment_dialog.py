"""
Диалог внесения платежа по кредитной карте (CreditCardPaymentDialog).

Позволяет внести платёж с автоматическим распределением на тело долга, 
проценты и комиссии. Использует стандартные сервисы переводов и транзакций.
"""

import logging
from datetime import date
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

logger = logging.getLogger(__name__)

class CreditCardPaymentDialog(BaseDialog):
    """
    Диалог внесения платежа по кредитной карте.
    
    Сигналы:
        payment_made: Вызывается после успешного внесения платежа.
    """
    
    payment_made = Signal()

    def __init__(self, parent, presenter, card_id: int, card_name: str, card_account_id: int, current_debt: float):
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
        self.resize(450, 550)
        
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
            total = parse_float(self.total_input.text()) or 0.0
            interest = parse_float(self.interest_input.text()) or 0.0 if self.interest_input.isEnabled() else 0.0
            
            principal = total - interest
            
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
        """Обрабатывает нажатие кнопки 'Внести платёж'."""
        try:
            total = parse_float(self.total_input.text())
            if total is None or total <= 0:
                raise ValueError("Общая сумма платежа должна быть больше нуля")
                
            account_id = self.account_combo.currentData()
            if not account_id:
                raise ValueError("Не выбран счёт для списания")
                
            interest = parse_float(self.interest_input.text()) or 0.0 if self.interest_input.isEnabled() else 0.0
            
            # Расчёт тела долга
            principal = total - interest
            
            # Проверка: тело долга не должно превышать сумму долга
            if principal > self.current_debt:
                raise ValueError(
                    f"Сумма погашения тела долга ({principal:,.2f} ₽) превышает текущий долг ({self.current_debt:,.2f} ₽). "
                    f"Увеличьте сумму процентов или уменьшите общую сумму платежа.".replace(",", " ")
                )
            
            if principal < 0:
                raise ValueError("Сумма процентов не может превышать общую сумму платежа")
                
            payment_date = self.date_edit.date().toString("yyyy-MM-dd")
            
            # Вызов презентера
            self.presenter.make_payment(
                card_id=self.card_id,
                amount_str=str(total),
                interest_str=str(interest),
                payment_date_str=payment_date,
                from_account_id=account_id
            )
            
            self.show_status("Платёж успешно внесён", "success")
            self.payment_made.emit()
            self.accept()
            
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка UI при внесении платежа: {e}", exc_info=True)
            self.show_status("Произошла ошибка при внесении платежа", "error")