# ui/dialogs/credit_card_settings_dialog.py
"""
Диалог настроек кредитной карты.
Позволяет изменить название, ставку, льготный период и другие параметры.
"""
from typing import Dict
from PySide6.QtWidgets import (
    QVBoxLayout, QFormLayout, QGroupBox, QLabel,
    QLineEdit, QDialogButtonBox, QMessageBox, QDoubleSpinBox, QSpinBox
)
from ui.dialogs.base_dialog import BaseDialog


class CreditCardSettingsDialog(BaseDialog):
    """Диалог настроек кредитной карты."""

    def __init__(self, parent=None, presenter=None):
        """
        Инициализация диалога настроек.
        
        Args:
            parent: родительское окно
            presenter: экземпляр CreditCardPresenter
        """
        super().__init__(parent)
        self.presenter = presenter
        
        self.setWindowTitle("Настройки карты")
        self.setFixedSize(450, 500)
        
        self._init_ui()

    def _init_ui(self):
        """Инициализация интерфейса."""
        self._main_layout.setSpacing(10)
        
        # === Основные параметры ===
        main_group = QGroupBox("Основные параметры")
        main_layout = QFormLayout()
        main_layout.setSpacing(10)
        
        # Название карты
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Например: Сбер Молодёжная")
        main_layout.addRow("Название карты:", self.name_input)
        
        # Кредитный лимит
        self.limit_input = QDoubleSpinBox()
        self.limit_input.setRange(0, 10000000)
        self.limit_input.setDecimals(2)
        self.limit_input.setPrefix("₽ ")
        self.limit_input.setSingleStep(1000)
        main_layout.addRow("Кредитный лимит:", self.limit_input)
        
        main_group.setLayout(main_layout)
        self._main_layout.addWidget(main_group)
        
        # === Параметры процентов и платежей ===
        rates_group = QGroupBox("Проценты и платежи")
        rates_layout = QFormLayout()
        rates_layout.setSpacing(10)
        
        # Годовая ставка
        self.rate_input = QDoubleSpinBox()
        self.rate_input.setRange(0, 100)
        self.rate_input.setDecimals(1)
        self.rate_input.setSuffix(" %")
        self.rate_input.setSingleStep(0.5)
        rates_layout.addRow("Годовая ставка:", self.rate_input)
        
        # Льготный период
        self.grace_input = QSpinBox()
        self.grace_input.setRange(0, 24)
        self.grace_input.setSuffix(" мес.")
        rates_layout.addRow("Льготный период:", self.grace_input)
        
        # Минимальный платеж
        self.min_pay_input = QDoubleSpinBox()
        self.min_pay_input.setRange(0, 100)
        self.min_pay_input.setDecimals(1)
        self.min_pay_input.setSuffix(" %")
        self.min_pay_input.setSingleStep(0.5)
        rates_layout.addRow("Мин. платёж:", self.min_pay_input)
        
        rates_group.setLayout(rates_layout)
        self._main_layout.addWidget(rates_group)
        
        # === Даты ===
        dates_group = QGroupBox("Даты отчётности")
        dates_layout = QFormLayout()
        dates_layout.setSpacing(10)
        
        # День выписки
        self.statement_day_input = QSpinBox()
        self.statement_day_input.setRange(1, 31)
        self.statement_day_input.setSuffix(" число")
        dates_layout.addRow("День выписки:", self.statement_day_input)
        
        # День платежа
        self.payment_day_input = QSpinBox()
        self.payment_day_input.setRange(1, 31)
        self.payment_day_input.setSuffix(" число")
        dates_layout.addRow("День платежа:", self.payment_day_input)
        
        dates_group.setLayout(dates_layout)
        self._main_layout.addWidget(dates_group)
        
        # Подсказка
        hint = QLabel("💡 Изменения вступят в силу при следующем расчёте ")
        hint.setStyleSheet("color: gray; font-size: 9pt;")
        self._main_layout.addWidget(hint)
        
        self._main_layout.addStretch()
        
        # Кнопки
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        self._main_layout.addWidget(button_box)

    def _on_save(self):
        """Обработчик нажатия кнопки 'Сохранить'."""
        data = self._get_form_data()
        if data and self.presenter:
            try:
                self.presenter.save_card_settings(data)
                self.accept()
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка", str(e))

    def _get_form_data(self) -> dict:
        """Собирает данные из формы."""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Укажите название карты")
            return None
            
        return {
            "name": name,
            "credit_limit": self.limit_input.value(),
            "annual_rate": self.rate_input.value(),
            "grace_months": self.grace_input.value(),
            "min_payment_percent": self.min_pay_input.value() / 100,  # Сохраняем как 0.02
            "statement_day": self.statement_day_input.value(),
            "payment_day": self.payment_day_input.value()
        }

    # =================== Контракт View <-> Presenter ===================

    def populate_settings(self, card_data: Dict):
        """
        Заполняет форму текущими настройками карты.
        
        Args:
            card_data: словарь с настройками карты
        """
        self.name_input.setText(card_data.get("name", ""))
        self.limit_input.setValue(card_data.get("credit_limit", 0))
        self.rate_input.setValue(card_data.get("annual_rate", 49.8))
        self.grace_input.setValue(card_data.get("grace_months", 3))
        
        # В UI показываем проценты (например, 2.0), а не дроби (0.02)
        self.min_pay_input.setValue(card_data.get("min_payment_percent", 2.0))
        
        self.statement_day_input.setValue(card_data.get("statement_day", 1))
        self.payment_day_input.setValue(card_data.get("payment_day", 10))