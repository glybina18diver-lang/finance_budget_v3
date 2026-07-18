"""
Диалог редактирования настроек кредитной карты (CreditCardSettingsDialog).

Позволяет пользователю изменить опциональные параметры существующей карты:
лимит, ставку, льготный период, дни выписки/платежа и мин. платёж.
Название карты редактируется через диалог счетов (AccountDialog).
"""

import logging
from decimal import Decimal

from PySide6.QtWidgets import (
    QPushButton, QLabel, QDoubleSpinBox, 
    QSpinBox, QFormLayout, QDialogButtonBox, QGroupBox, QVBoxLayout
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
        info_label.setStyleSheet("color: #757575; margin-bottom: 10px;")
        self._main_layout.addWidget(info_label)

        form_group = QGroupBox("Параметры кредитной карты (опционально)")
        form_layout = QFormLayout()
        
        # Кредитный лимит
        self.limit_spin = QDoubleSpinBox()
        self.limit_spin.setRange(0.0, 10000000.0)
        self.limit_spin.setDecimals(2)
        self.limit_spin.setSingleStep(1000)
        self.limit_spin.setPrefix("₽ ")
        self.limit_spin.setSpecialValueText("Не указан")
        form_layout.addRow("Кредитный лимит:", self.limit_spin)
        
        # Годовая ставка %
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0.0, 100.0)
        self.rate_spin.setDecimals(1)
        self.rate_spin.setSingleStep(0.1)
        self.rate_spin.setSuffix(" %")
        self.rate_spin.setSpecialValueText("Не указана")
        form_layout.addRow("Годовая ставка:", self.rate_spin)
        
        # Льготный период (дней)
        self.grace_days_spin = QSpinBox()
        self.grace_days_spin.setRange(0, 365)
        self.grace_days_spin.setSuffix(" дн.")
        self.grace_days_spin.setSpecialValueText("Не указан")
        form_layout.addRow("Льготный период:", self.grace_days_spin)
        
        # Мин. платёж %
        self.min_payment_spin = QDoubleSpinBox()
        self.min_payment_spin.setRange(0.0, 100.0)
        self.min_payment_spin.setDecimals(1)
        self.min_payment_spin.setSingleStep(0.1)
        self.min_payment_spin.setSuffix(" %")
        self.min_payment_spin.setSpecialValueText("Не указан")
        form_layout.addRow("Мин. платёж:", self.min_payment_spin)
        
        # День платежа
        self.payment_day_spin = QSpinBox()
        self.payment_day_spin.setRange(1, 31)
        self.payment_day_spin.setSpecialValueText("Не указан")
        form_layout.addRow("День платежа:", self.payment_day_spin)
        
        # День выписки
        self.statement_day_spin = QSpinBox()
        self.statement_day_spin.setRange(1, 31)
        self.statement_day_spin.setSpecialValueText("Не указан")
        form_layout.addRow("День выписки:", self.statement_day_spin)
        
        form_group.setLayout(form_layout)
        self._main_layout.addWidget(form_group)
        
        # Кнопки
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        self._main_layout.addWidget(button_box)

    def _load_data(self):
        """Заполняет поля формы текущими данными карты."""
        try:
            data = self.presenter.get_card_settings(self.card_id)
            
            # Устанавливаем значения или оставляем SpecialValueText (None)
            if data.get("credit_limit") is not None:
                self.limit_spin.setValue(float(data["credit_limit"]))
                
            if data.get("annual_rate") is not None:
                self.rate_spin.setValue(float(data["annual_rate"]))
                
            if data.get("grace_months") is not None:
                # В новой модели храним дни, но если в БД были месяцы - конвертируем
                # Для обратной совместимости со старыми данными
                grace_val = data["grace_months"]
                self.grace_days_spin.setValue(grace_val * 30 if grace_val < 13 else grace_val)
                
            if data.get("min_payment_percent") is not None:
                # В модели хранится как доля (0.02), в UI показываем проценты (2.0)
                self.min_payment_spin.setValue(float(data["min_payment_percent"]) * 100)
                
            if data.get("payment_day") is not None:
                self.payment_day_spin.setValue(int(data["payment_day"]))
                
            if data.get("statement_day") is not None:
                self.statement_day_spin.setValue(int(data["statement_day"]))
            
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка UI при загрузке настроек: {e}", exc_info=True)
            self.show_status("Произошла ошибка при загрузке настроек", "error")

    def _on_accept(self):
        """Обрабатывает нажатие кнопки 'Сохранить'."""
        try:
            # Собираем данные. Если значение равно minimum() спинбокса (SpecialValueText), 
            # то передаём None, иначе реальное значение.
            card_data = {
                "id": self.card_id,
                "account_id": 0,  # Не меняется здесь, обновляется из БД в сервисе
                
                "credit_limit": self.limit_spin.value() if self.limit_spin.value() > 0 else None,
                "annual_rate": self.rate_spin.value() if self.rate_spin.value() > 0 else None,
                "grace_months": self.grace_days_spin.value() // 30 if self.grace_days_spin.value() > 0 else None,
                "min_payment_percent": self.min_payment_spin.value() / 100 if self.min_payment_spin.value() > 0 else None,
                "payment_day": self.payment_day_spin.value() if self.payment_day_spin.value() > 0 else None,
                "statement_day": self.statement_day_spin.value() if self.statement_day_spin.value() > 0 else None,
            }
            
            self.presenter.update_card(card_data)
            self.settings_updated.emit()
            self.accept()
            
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка UI при сохранении настроек: {e}", exc_info=True)
            self.show_status("Произошла ошибка при сохранении настроек", "error")