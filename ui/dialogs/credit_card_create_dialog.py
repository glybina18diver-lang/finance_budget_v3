"""
Диалог создания новой кредитной карты (CreditCardCreateDialog).

Позволяет пользователю выбрать счёт типа CreditCard без карты 
и заполнить все обязательные настройки.
"""

import logging
from decimal import Decimal

from PySide6.QtWidgets import (
    QComboBox, QPushButton, QLabel, QLineEdit, 
    QDoubleSpinBox, QSpinBox, QFormLayout, QDialogButtonBox, QDialog
)
from PySide6.QtCore import Signal

from ui.dialogs.base_dialog import BaseDialog

logger = logging.getLogger(__name__)


class CreditCardCreateDialog(BaseDialog):
    """
    Диалог создания новой кредитной карты.
    
    Сигналы:
        card_created: Вызывается после успешного создания карты (передаёт ID).
    """
    
    card_created = Signal(int)

    def __init__(self, parent, presenter):
        """
        Инициализация диалога создания карты.
        
        Args:
            parent: родительское окно
            presenter: экземпляр CreditCardPresenter
        """
        super().__init__(parent)
        self.presenter = presenter
        
        self.setWindowTitle("Создание кредитной карты")
        self.resize(400, 500)
        
        self._setup_ui()
        self._load_accounts()

    def _setup_ui(self):
        """Настраивает интерфейс диалога."""
        form_layout = QFormLayout()
        
        # Счёт
        self.account_combo = QComboBox()
        form_layout.addRow("Счёт:", self.account_combo)
        
        # Название карты
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например, Сбер Молодёжная")
        form_layout.addRow("Название карты:", self.name_input)
        
        # Годовая ставка %
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0.0, 100.0)
        self.rate_spin.setDecimals(1)
        self.rate_spin.setSingleStep(0.1)
        self.rate_spin.setValue(49.8)
        self.rate_spin.setSuffix(" %")
        form_layout.addRow("Годовая ставка:", self.rate_spin)
        
        # Льготный период (месяцев)
        self.grace_spin = QSpinBox()
        self.grace_spin.setRange(0, 12)
        self.grace_spin.setValue(3)
        self.grace_spin.setSuffix(" мес.")
        form_layout.addRow("Льготный период:", self.grace_spin)
        
        # Мин. платёж %
        self.min_payment_spin = QDoubleSpinBox()
        self.min_payment_spin.setRange(0.0, 100.0)
        self.min_payment_spin.setDecimals(1)
        self.min_payment_spin.setSingleStep(0.1)
        self.min_payment_spin.setValue(2.0)
        self.min_payment_spin.setSuffix(" %")
        form_layout.addRow("Мин. платёж:", self.min_payment_spin)
        
        # День платежа
        self.payment_day_spin = QSpinBox()
        self.payment_day_spin.setRange(1, 31)
        self.payment_day_spin.setValue(1)
        form_layout.addRow("День платежа:", self.payment_day_spin)
        
        # День выписки
        self.statement_day_spin = QSpinBox()
        self.statement_day_spin.setRange(1, 31)
        self.statement_day_spin.setValue(1)
        form_layout.addRow("День выписки:", self.statement_day_spin)
        
        # Кредитный лимит
        self.limit_spin = QDoubleSpinBox()
        self.limit_spin.setRange(0.0, 10000000.0)
        self.limit_spin.setDecimals(2)
        self.limit_spin.setSingleStep(1000)
        self.limit_spin.setValue(100000)
        self.limit_spin.setPrefix("₽ ")
        form_layout.addRow("Кредитный лимит:", self.limit_spin)
        
        self._main_layout.addLayout(form_layout)
        
        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        self._main_layout.addWidget(button_box)

        #  Строка статуса
        self._main_layout.addWidget(self.status_bar)

    def _load_accounts(self):
        """Загружает доступные счета в ComboBox."""
        try:
            self.account_combo.clear()
            accounts = self.presenter.get_available_accounts_for_card_creation()
            
            if not accounts:
                self.account_combo.addItem("Нет доступных счетов", None)
                self.account_combo.setEnabled(False)
                return
                
            for acc in accounts:
                self.account_combo.addItem(acc["name"], acc["id"])
                
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при загрузке счетов: {e}", exc_info=True)
            self.show_status("Произошла ошибка при загрузке счетов", "error")

    def _on_accept(self):
        """Обрабатывает нажатие кнопки 'Создать'."""
        try:
            account_id = self.account_combo.currentData()
            if not account_id:
                raise ValueError("Не выбран счёт для привязки карты")
                
            name = self.name_input.text().strip()
            if not name:
                raise ValueError("Название карты не может быть пустым")
                
            card_data = {
                "account_id": account_id,
                "name": name,
                "annual_rate": self.rate_spin.value(),
                "grace_months": self.grace_spin.value(),
                "min_payment_percent": self.min_payment_spin.value(),
                "payment_day": self.payment_day_spin.value(),
                "statement_day": self.statement_day_spin.value(),
                "credit_limit": self.limit_spin.value()
            }
            
            card_id = self.presenter.create_card(card_data)
            self.card_created.emit(card_id)
            self.accept()
            
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при создании карты: {e}", exc_info=True)
            self.show_status("Произошла ошибка при создании карты", "error")