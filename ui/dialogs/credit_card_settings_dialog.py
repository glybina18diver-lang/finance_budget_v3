"""
Диалог редактирования настроек кредитной карты (CreditCardSettingsDialog).

Позволяет пользователю изменить параметры существующей карты:
название, ставку, льготный период, дни выписки/платежа и лимит.
"""

import logging
from decimal import Decimal

from PySide6.QtWidgets import (
    QPushButton, QLabel, QLineEdit, QDoubleSpinBox, 
    QSpinBox, QFormLayout, QDialogButtonBox
)
from PySide6.QtCore import Signal

from ui.dialogs.base_dialog import BaseDialog

logger = logging.getLogger(__name__)


class CreditCardSettingsDialog(BaseDialog):
    """
    Диалог настроек кредитной карты.
    
    Сигналы:
        settings_updated: Вызывается после успешного сохранения настроек.
    """
    
    settings_updated = Signal()

    def __init__(self, parent, presenter, card_id: int):
        """
        Инициализация диалога настроек.
        
        Args:
            parent: родительское окно
            presenter: экземпляр CreditCardPresenter
            card_id: ID редактируемой карты
        """
        super().__init__(parent)
        self.presenter = presenter
        self.card_id = card_id
        
        self.setWindowTitle("Настройки кредитной карты")
        self.resize(400, 450)
        
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        """Настраивает интерфейс диалога."""
        form_layout = QFormLayout()
        
        # Название карты
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например, Сбер Молодёжная")
        form_layout.addRow("Название карты:", self.name_input)
        
        # Годовая ставка %
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0.0, 100.0)
        self.rate_spin.setDecimals(1)
        self.rate_spin.setSingleStep(0.1)
        self.rate_spin.setSuffix(" %")
        form_layout.addRow("Годовая ставка:", self.rate_spin)
        
        # Льготный период (месяцев)
        self.grace_spin = QSpinBox()
        self.grace_spin.setRange(0, 12)
        self.grace_spin.setSuffix(" мес.")
        form_layout.addRow("Льготный период:", self.grace_spin)
        
        # Мин. платёж %
        self.min_payment_spin = QDoubleSpinBox()
        self.min_payment_spin.setRange(0.0, 100.0)
        self.min_payment_spin.setDecimals(1)
        self.min_payment_spin.setSingleStep(0.1)
        self.min_payment_spin.setSuffix(" %")
        form_layout.addRow("Мин. платёж:", self.min_payment_spin)
        
        # День платежа
        self.payment_day_spin = QSpinBox()
        self.payment_day_spin.setRange(1, 31)
        form_layout.addRow("День платежа:", self.payment_day_spin)
        
        # День выписки
        self.statement_day_spin = QSpinBox()
        self.statement_day_spin.setRange(1, 31)
        form_layout.addRow("День выписки:", self.statement_day_spin)
        
        # Кредитный лимит
        self.limit_spin = QDoubleSpinBox()
        self.limit_spin.setRange(0.0, 10000000.0)
        self.limit_spin.setDecimals(2)
        self.limit_spin.setSingleStep(1000)
        self.limit_spin.setPrefix("₽ ")
        form_layout.addRow("Кредитный лимит:", self.limit_spin)
        
        self._main_layout.addLayout(form_layout)
        
        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        self._main_layout.addWidget(button_box)

    def _load_data(self):
        """Заполняет поля формы текущими данными карты."""
        try:
            data = self.presenter.get_card_settings(self.card_id)
            
            self.name_input.setText(data["name"])
            self.rate_spin.setValue(data["annual_rate"])
            self.grace_spin.setValue(data["grace_months"])
            self.min_payment_spin.setValue(data["min_payment_percent"])
            self.payment_day_spin.setValue(data["payment_day"])
            self.statement_day_spin.setValue(data["statement_day"])
            self.limit_spin.setValue(data["credit_limit"])
            
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при загрузке настроек: {e}", exc_info=True)
            self.show_status("Произошла ошибка при загрузке настроек", "error")

    def _on_accept(self):
        """Обрабатывает нажатие кнопки 'Сохранить'."""
        try:
            name = self.name_input.text().strip()
            if not name:
                raise ValueError("Название карты не может быть пустым")
                
            card_data = {
                "id": self.card_id,
                "account_id": 0, # Не меняется в этом диалоге, обновится из БД в сервисе
                "name": name,
                "annual_rate": self.rate_spin.value(),
                "grace_months": self.grace_spin.value(),
                "min_payment_percent": self.min_payment_spin.value(),
                "payment_day": self.payment_day_spin.value(),
                "statement_day": self.statement_day_spin.value(),
                "credit_limit": self.limit_spin.value()
            }
            
            self.presenter.update_card_settings(card_data)
            self.settings_updated.emit()
            self.accept()
            
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при сохранении настроек: {e}", exc_info=True)
            self.show_status("Произошла ошибка при сохранении настроек", "error")