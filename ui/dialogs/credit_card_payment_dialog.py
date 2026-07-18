"""
Диалог внесения платежа по кредитной карте (CreditCardPaymentDialog).

Позволяет внести платёж с автоматическим распределением на тело долга, 
проценты и комиссии. Использует стандартные сервисы переводов и транзакций.
"""

import logging
from datetime import date

from PySide6.QtWidgets import (
    QComboBox, QPushButton, QLabel, QDoubleSpinBox, 
    QDateEdit, QFormLayout, QDialogButtonBox, QGroupBox, 
    QVBoxLayout, QHBoxLayout, QCheckBox, QFrame
)
from PySide6.QtCore import Signal, Qt

from ui.dialogs.base_dialog import BaseDialog

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
        self.total_spin = QDoubleSpinBox()
        self.total_spin.setRange(0.01, 10000000.00)
        self.total_spin.setDecimals(2)
        self.total_spin.setPrefix("₽ ")
        self.total_spin.valueChanged.connect(self._update_principal_label)
        form_layout.addRow("Общая сумма:", self.total_spin)
        
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
        
        # Блок разбивки платежа
        self.split_group = QGroupBox("Распределение платежа")
        split_layout = QVBoxLayout()
        
        self.split_checkbox = QCheckBox("Разбить платёж на тело долга, проценты и комиссии")
        self.split_checkbox.toggled.connect(self._on_split_toggled)
        split_layout.addWidget(self.split_checkbox)
        
        breakdown_form = QFormLayout()
        
        self.interest_spin = QDoubleSpinBox()
        self.interest_spin.setRange(0.00, 10000000.00)
        self.interest_spin.setDecimals(2)
        self.interest_spin.setPrefix("₽ ")
        self.interest_spin.setEnabled(False)
        self.interest_spin.valueChanged.connect(self._update_principal_label)
        breakdown_form.addRow("На проценты:", self.interest_spin)
        
        self.commission_spin = QDoubleSpinBox()
        self.commission_spin.setRange(0.00, 10000000.00)
        self.commission_spin.setDecimals(2)
        self.commission_spin.setPrefix("₽ ")
        self.commission_spin.setEnabled(False)
        self.commission_spin.valueChanged.connect(self._update_principal_label)
        breakdown_form.addRow("На комиссии:", self.commission_spin)
        
        self.principal_label = QLabel("0.00 ₽")
        self.principal_label.setStyleSheet("font-weight: bold;")
        breakdown_form.addRow("На основной долг (авто):", self.principal_label)
        
        split_layout.addLayout(breakdown_form)
        self.split_group.setLayout(split_layout)
        self._main_layout.addWidget(self.split_group)
        
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
        """Обрабатывает переключение чекбокса разбивки платежа."""
        self.interest_spin.setEnabled(checked)
        self.commission_spin.setEnabled(checked)
        if not checked:
            self.interest_spin.setValue(0.00)
            self.commission_spin.setValue(0.00)
        self._update_principal_label()

    def _update_principal_label(self):
        """Автоматически пересчитывает сумму на погашение основного долга."""
        try:
            total = self.total_spin.value()
            interest = self.interest_spin.value() if self.interest_spin.isEnabled() else 0.00
            commission = self.commission_spin.value() if self.commission_spin.isEnabled() else 0.00
            
            principal = total - interest - commission
            
            if principal < 0:
                self.principal_label.setText(f"{principal:,.2f} ₽".replace(",", " "))
                self.principal_label.setStyleSheet("font-weight: bold; color: #d32f2f;")
            else:
                self.principal_label.setText(f"{principal:,.2f} ₽".replace(",", " "))
                self.principal_label.setStyleSheet("font-weight: bold; color: #2e7d32;")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка UI при пересчёте основного долга: {e}", exc_info=True)

    def _on_pay(self):
        """Обрабатывает нажатие кнопки 'Внести платёж'."""
        try:
            total = self.total_spin.value()
            if total <= 0:
                raise ValueError("Общая сумма платежа должна быть больше нуля")
                
            account_id = self.account_combo.currentData()
            if not account_id:
                raise ValueError("Не выбран счёт для списания")
                
            interest = self.interest_spin.value() if self.interest_spin.isEnabled() else 0.00
            commission = self.commission_spin.value() if self.commission_spin.isEnabled() else 0.00
            
            if interest + commission > total:
                raise ValueError("Сумма процентов и комиссий не может превышать общую сумму платежа")
                
            payment_date = self.date_edit.date().toString("yyyy-MM-dd")
            
            # Вызов презентера
            self.presenter.make_payment(
                card_id=self.card_id,
                amount_str=str(total),
                interest_str=str(interest),
                commission_str=str(commission),
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