"""
Диалог редактирования настроек кредитной карты (CreditCardSettingsDialog).

Позволяет пользователю изменить опциональные параметры существующей карты:
лимит, ставку, льготный период, дни выписки/платежа и мин. платёж.
Название карты редактируется через диалог счетов (AccountDialog).
"""

import logging
from decimal import Decimal
from typing import Optional

from PySide6.QtWidgets import (
    QPushButton, QLabel, QDoubleSpinBox, 
    QSpinBox, QFormLayout, QDialogButtonBox, QGroupBox, QVBoxLayout, QLineEdit
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QDoubleValidator, QIntValidator

from ui.dialogs.base_dialog import BaseDialog
from utils.validators import parse_float, parse_int  
from ui.widgets.buttons import CompactButton

logger = logging.getLogger(__name__)


class CreditCardSettingsDialog(BaseDialog):
    """
    Диалог настроек кредитной карты.
    
    Сигналы:
        settings_updated: Вызывается после успешного сохранения настроек.
    """
    
    settings_updated = Signal()

    def __init__(self, parent, presenter, card_id: int, account_name: str):
        """
        Инициализация диалога настроек.
        
        Args:
            parent: родительское окно
            presenter: экземпляр CreditCardPresenter
            card_id: ID редактируемой карты
            account_name: название счёта (для отображения в заголовке)
        """
        super().__init__(parent)
        self.presenter = presenter
        self.card_id = card_id
        
        self.setWindowTitle(f"Настройки: {account_name}")
        self.resize(450, 480)
        
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        """Настраивает интерфейс диалога."""
        # Информационная плашка
        info_label = QLabel("💡 Название карты изменяется в диалоге управления счетами.")
        info_label.setWordWrap(True)
        # info_label.setStyleSheet("color: #757575; margin-bottom: 10px;")
        self._main_layout.addWidget(info_label)

        form_group = QGroupBox("Параметры кредитной карты (опционально)")
        form_layout = QFormLayout()
        
        # Кредитный лимит
        self.limit_input = QLineEdit()
        self.limit_input.setPlaceholderText("Например: 100000")
        self.limit_input.setFixedHeight(26)
        limit_validator = QDoubleValidator(0.0, 999999999.0, 0)
        limit_validator.setNotation(QDoubleValidator.StandardNotation)
        self.limit_input.setValidator(limit_validator)
        form_layout.addRow("Кредитный лимит:", self.limit_input)
        
        # Годовая ставка %
        self.rate_input = QLineEdit()
        self.rate_input.setPlaceholderText("Например: 49.8")
        self.rate_input.setFixedHeight(26)
        rate_validator = QDoubleValidator(0.0, 100.0, 1)
        rate_validator.setNotation(QDoubleValidator.StandardNotation)
        self.rate_input.setValidator(rate_validator)
        form_layout.addRow("Годовая ставка (%):", self.rate_input)
        
        # Льготный период (дней)
        self.grace_days_input = QLineEdit()
        self.grace_days_input.setPlaceholderText("Например: 120")
        self.grace_days_input.setFixedHeight(26)
        grace_validator = QIntValidator(0, 365)
        self.grace_days_input.setValidator(grace_validator)
        form_layout.addRow("Льготный период (дн.):", self.grace_days_input)
        
        # Мин. платёж %
        self.min_payment_input = QLineEdit()
        self.min_payment_input.setPlaceholderText("Например: 2.0")
        self.min_payment_input.setFixedHeight(26)
        min_pay_validator = QDoubleValidator(0.0, 100.0, 1)
        min_pay_validator.setNotation(QDoubleValidator.StandardNotation)
        self.min_payment_input.setValidator(min_pay_validator)
        form_layout.addRow("Мин. платёж (%):", self.min_payment_input)
        
        # День платежа
        self.payment_day_input = QLineEdit()
        self.payment_day_input.setPlaceholderText("1-31")
        self.payment_day_input.setFixedHeight(26)
        pay_day_validator = QIntValidator(1, 31)
        self.payment_day_input.setValidator(pay_day_validator)
        form_layout.addRow("День платежа:", self.payment_day_input)
        
        # День выписки
        self.statement_day_input = QLineEdit()
        self.statement_day_input.setPlaceholderText("1-31")
        self.statement_day_input.setFixedHeight(26)
        stmt_day_validator = QIntValidator(1, 31)
        self.statement_day_input.setValidator(stmt_day_validator)
        form_layout.addRow("День выписки:", self.statement_day_input)
        
        form_group.setLayout(form_layout)
        self._main_layout.addWidget(form_group)
        
        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=self)
        button_box.button(QDialogButtonBox.Ok).setText("Сохранить")     
        button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
        self.apply_role_purposes(button_box)    
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        self._main_layout.addWidget(button_box)

    def _load_data(self):
        """Заполняет поля формы текущими данными карты."""
        try:
            data = self.presenter.get_card_settings(self.card_id)
            
            if data.get("credit_limit") is not None:
                self.limit_input.setText(str(data["credit_limit"]))
                
            if data.get("annual_rate") is not None:
                self.rate_input.setText(str(data["annual_rate"]))
                
            if data.get("grace_months") is not None:
                # Конвертируем месяцы в дни для отображения (если это старая логика)
                grace_val = data["grace_months"]
                days = grace_val * 30 if grace_val < 13 else grace_val
                self.grace_days_input.setText(str(days))
                
            if data.get("min_payment_percent") is not None:
                # Конвертируем долю в проценты (0.02 -> 2.0)
                self.min_payment_input.setText(str(data["min_payment_percent"] * 100))
                
            if data.get("payment_day") is not None:
                self.payment_day_input.setText(str(data["payment_day"]))
                
            if data.get("statement_day") is not None:
                self.statement_day_input.setText(str(data["statement_day"]))
            
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка UI при загрузке настроек: {e}", exc_info=True)
            self.show_status("Произошла ошибка при загрузке настроек", "error")

    def _on_accept(self):
        """Обрабатывает нажатие кнопки 'Сохранить'."""
        try:
            card_data = {
                "id": self.card_id,
                "account_id": 0,  # Не меняется здесь
                
                "credit_limit": parse_float(self.limit_input.text()),
                "annual_rate": parse_float(self.rate_input.text()),
                "grace_months": parse_int(self.grace_days_input.text()) // 30 if parse_int(self.grace_days_input.text()) else None,
                "min_payment_percent": parse_float(self.min_payment_input.text()) / 100 if parse_float(self.min_payment_input.text()) else None,
                "payment_day": parse_int(self.payment_day_input.text()),
                "statement_day": parse_int(self.statement_day_input.text()),
            }
            
            self.presenter.update_card(card_data)
            self.settings_updated.emit()
            self.accept()
            
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка UI при сохранении настроек: {e}", exc_info=True)
            self.show_status("Произошла ошибка при сохранении настроек", "error")