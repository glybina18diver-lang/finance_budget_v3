# ui/dialogs/duplicate_dialog.py
import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit,
    QPushButton, QLineEdit, QFormLayout, QGroupBox, QCheckBox
)
from PySide6.QtCore import QDate
from PySide6.QtGui import QDoubleValidator

from ui.widgets.buttons import  CompactButton
from core.models import Transaction

logger = logging.getLogger(__name__)


class DuplicateTransactionDialog(QDialog):
    """Диалог настройки параметров дублирования транзакции."""
    
    def __init__(self, transaction: Transaction, account_name: str,
                 category_name: str, currency: str, parent=None):
        """
        Инициализация диалога дублирования.
        
        Args:
            transaction: оригинальная транзакция для дублирования
            account_name: название счёта (для отображения)
            category_name: название категории (для отображения)
            currency: валюта счёта (для отображения)
            parent: родительское окно
        """
        super().__init__(parent)
        self.transaction = transaction
        self.account_name = account_name
        self.category_name = category_name
        self.currency = currency
        
        self.setWindowTitle("Настройки дублирования")
        self.resize(400, 350)
        
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация интерфейса диалога."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # Информация об оригинале
        main_layout.addWidget(self._create_info_group())
        
        # Настройки копии
        main_layout.addWidget(self._create_settings_group())
        
        # Кнопки
        main_layout.addLayout(self._create_buttons())
    
    def _create_info_group(self) -> QGroupBox:
        """
        Создаёт блок информации об оригинальной транзакции.
        
        Returns:
            QGroupBox с информацией об оригинале
        """
        group = QGroupBox("Оригинальная операция")
        layout = QFormLayout()
        
        type_name = "Доход" if self.transaction.trans_type == "income" else "Расход"
        
        layout.addRow("Дата:", QLabel(self.transaction.date))
        layout.addRow("Сумма:", QLabel(f"{abs(self.transaction.amount):,.2f} {self.currency}"))
        layout.addRow("Тип:", QLabel(type_name))
        layout.addRow("Категория:", QLabel(self.category_name))
        layout.addRow("Счёт:", QLabel(self.account_name))
        
        if self.transaction.description:
            layout.addRow("Описание:", QLabel(self.transaction.description[:50]))
        
        group.setLayout(layout)
        return group
    
    def _create_settings_group(self) -> QGroupBox:
        """
        Создаёт блок настроек копии.
        
        Returns:
            QGroupBox с полями ввода для новой транзакции
        """
        group = QGroupBox("Параметры копии")
        layout = QFormLayout()
        
        # Дата
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        try:
            year, month, day = map(int, self.transaction.date.split('-'))
            qdate = QDate(year, month, day)
            self.date_edit.setDate(qdate if qdate.isValid() else QDate.currentDate())
        except (ValueError, AttributeError):
            self.date_edit.setDate(QDate.currentDate())
        layout.addRow("Новая дата:", self.date_edit)
        
        # Сумма (QLineEdit с валидатором)
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Сумма")
        self.amount_input.setText(f"{abs(self.transaction.amount):.2f}")
        amount_validator = QDoubleValidator(0.01, 999999999.99, 2)
        self.amount_input.setValidator(amount_validator)
        layout.addRow("Новая сумма:", self.amount_input)
        
        # Описание (QLineEdit)
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Описание...")
        self.description_input.setText(self.transaction.description or "")
        layout.addRow("Описание:", self.description_input)
        
        # Количество (QLineEdit с валидатором)
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Количество")
        self.quantity_input.setText(f"{self.transaction.quantity:.2f}" if self.transaction.quantity else "1.00")
        quantity_validator = QDoubleValidator(0.01, 999999.99, 2)
        self.quantity_input.setValidator(quantity_validator)
        layout.addRow("Количество:", self.quantity_input)
        
        # Чекбокс сохранения количества
        self.copy_quantity_cb = QCheckBox("Копировать количество")
        self.copy_quantity_cb.setChecked(True)
        self.copy_quantity_cb.toggled.connect(self.quantity_input.setEnabled)
        layout.addRow("", self.copy_quantity_cb)
        
        group.setLayout(layout)
        return group
    
    def _create_buttons(self) -> QHBoxLayout:
        """
        Создаёт блок кнопок диалога.
        
        Returns:
            QHBoxLayout с кнопками "Создать копию" и "Отмена"
        """
        layout = QHBoxLayout()
        
        ok_button = CompactButton("Создать копию", "success")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        
        cancel_button = CompactButton("Отмена", "danger")
        cancel_button.clicked.connect(self.reject)
        
        layout.addWidget(ok_button)
        layout.addWidget(cancel_button)
        layout.addStretch()
        
        return layout
    
    def get_duplicate_data(self) -> dict:
        """
        Возвращает данные для создания копии транзакции.
        
        Returns:
            Словарь с параметрами:
            - date: новая дата (str, формат yyyy-MM-dd)
            - amount: новая сумма (float)
            - description: описание (str)
            - quantity: количество (float)
        
        Raises:
            ValueError: если введены некорректные данные
        """
        try:
            # Дата
            new_date = self.date_edit.date().toString("yyyy-MM-dd")
            
            # Сумма
            amount_str = self.amount_input.text().strip()
            if not amount_str:
                raise ValueError("Сумма не может быть пустой")
            new_amount = float(amount_str.replace(',', '.'))
            if new_amount <= 0:
                raise ValueError("Сумма должна быть больше нуля")
            
            # Описание
            description = self.description_input.text().strip()
            
            # Количество
            if self.copy_quantity_cb.isChecked():
                quantity_str = self.quantity_input.text().strip()
                if not quantity_str:
                    raise ValueError("Количество не может быть пустым")
                quantity = float(quantity_str.replace(',', '.'))
                if quantity <= 0:
                    raise ValueError("Количество должно быть больше нуля")
            else:
                quantity = 1.0
            
            return {
                'date': new_date,
                'amount': new_amount,
                'description': description,
                'quantity': quantity
            }
        
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация данных дублирования: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка получения данных дублирования: {e}", exc_info=True)
            raise