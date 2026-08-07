# ui/dialogs/edit_transaction_dialog.py
import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit,
    QPushButton, QLineEdit, QComboBox, QFormLayout, QGroupBox
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QFont
from core.models import Transaction, Account, Category

from ui.widgets.buttons import CompactButton

logger = logging.getLogger(__name__)


class EditTransactionDialog(QDialog):
    """Диалог редактирования транзакции."""
    
    data_updated = Signal()
    
    def __init__(
        self,
        parent=None,
        presenter=None,
        transaction: Transaction = None,
        account_cache: dict = None,
        category_cache: dict = None,
    ):
        """
        Инициализация диалога редактирования транзакции.
        
        Args:
            parent: родительское окно
            presenter: экземпляр TransactionPresenter для обработки действий
            transaction: объект транзакции для редактирования
            account_cache: словарь {id: Account} для отображения счетов
            category_cache: словарь {id: Category} для отображения категорий
        """
        super().__init__(parent)
        self.presenter = presenter
        self.transaction = transaction
        self._account_cache = account_cache or {}
        self._category_cache = category_cache or {}
        
        self.setWindowTitle("Редактировать транзакцию")
        self.resize(500, 550)
        
        self._init_ui()
        self._load_transaction_data()
    
    def _init_ui(self):
        """Создаёт интерфейс диалога."""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        
        # ID транзакции
        id_label = QLabel(f"ID транзакции: {self.transaction.id}")
        id_font = QFont()
        id_font.setItalic(True)
        id_label.setFont(id_font)
        id_label.setAlignment(Qt.AlignLeft)
        main_layout.addWidget(id_label)
        
        # Форма редактирования
        form_group = QGroupBox("Редактировать данные")
        form_layout = QFormLayout()
        
        # Дата
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd.MM.yyyy")
        form_layout.addRow("Дата:", self.date_input)
        
        # Тип
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Доход", "Расход", "Корректировка"])
        self.type_combo.currentTextChanged.connect(self._on_type_change)
        form_layout.addRow("Тип:", self.type_combo)
        
        # Сумма
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("0.00")
        form_layout.addRow("Сумма:", self.amount_input)
        
        # Количество
        self.quantity_input = QLineEdit()
        self.quantity_input.setText("1.0")
        form_layout.addRow("Количество:", self.quantity_input)
        
        # Категория
        self.category_combo = QComboBox()
        form_layout.addRow("Категория:", self.category_combo)
        
        # Счёт
        self.account_combo = QComboBox()
        form_layout.addRow("Счёт:", self.account_combo)
        
        # Описание
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Описание транзакции")
        form_layout.addRow("Описание:", self.description_input)
        
        form_group.setLayout(form_layout)
        main_layout.addWidget(form_group)
        
        # Кнопки сохранения/отмены
        button_layout = QHBoxLayout()
        
        save_button = CompactButton("💾 Сохранить", "success")
        save_button.setDefault(True)
        save_button.clicked.connect(self._save_changes)
        button_layout.addWidget(save_button)
        
        button_layout.addStretch()
        
        cancel_button = CompactButton("Отмена", "danger")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        main_layout.addLayout(button_layout)
        
        # Кнопка удаления
        delete_button = CompactButton("🗑️ Удалить эту транзакцию", "danger")
        delete_button.clicked.connect(self._delete_transaction)
        main_layout.addWidget(delete_button)
        
        # Дополнительная информация
        info_group = QGroupBox("Дополнительная информация")
        info_layout = QVBoxLayout()
        
        self.info_label = QLabel()
        info_label_font = QFont()
        info_label_font.setPointSize(9)
        self.info_label.setFont(info_label_font)
        self.info_label.setAlignment(Qt.AlignLeft)
        self.info_label.setWordWrap(True)
        
        info_layout.addWidget(self.info_label)
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)
        
        self.setLayout(main_layout)
    
    def _load_transaction_data(self):
        """
        Заполняет поля формы данными редактируемой транзакции.
        
        Загружает данные из объекта Transaction и кэшей счетов/категорий.
        """
        try:
            if not self.transaction:
                raise ValueError("Транзакция не передана в диалог")
            
            # Дата
            try:
                year, month, day = map(int, self.transaction.date.split('-'))
                qdate = QDate(year, month, day)
                self.date_input.setDate(qdate if qdate.isValid() else QDate.currentDate())
            except (ValueError, AttributeError):
                self.date_input.setDate(QDate.currentDate())
            
            # Тип
            type_map = {
                "income": "Доход",
                "expense": "Расход",
                "correct": "Корректировка"
            }
            type_text = type_map.get(self.transaction.trans_type, "Расход")
            self.type_combo.setCurrentText(type_text)
            
            # Сумма (абсолютное значение)
            self.amount_input.setText(f"{abs(self.transaction.amount):.2f}")
            
            # Количество
            self.quantity_input.setText(f"{self.transaction.quantity:.2f}" if self.transaction.quantity else "1.00")
            
            # Заполняем комбобоксы
            self._load_accounts_combo()
            self._load_categories_combo()
            
            # Описание
            self.description_input.setText(self.transaction.description or "")
            
            # Дополнительная информация
            self._update_info_label()
            
            logger.debug(f"[{self.__class__.__name__}] Загружены данные транзакции ID={self.transaction.id}")
        
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация загрузки данных: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка загрузки данных транзакции: {e}", exc_info=True)
            raise
    
    def _load_accounts_combo(self):
        """Заполняет комбобокс счетов данными из кэша."""
        try:
            self.account_combo.clear()
            
            if not self._account_cache:
                self.account_combo.addItem("Нет счетов", userData=None)
                return
            
            # Фильтруем системные счета
            user_accounts = [
                acc for acc in self._account_cache.values()
                if not getattr(acc, 'is_system', False)
            ]
            
            for account in user_accounts:
                display_text = f"{account.name} ({account.current_balance:,.2f} {account.currency})"
                self.account_combo.addItem(display_text, userData=account.id)
            
            # Выбираем счёт транзакции
            for i in range(self.account_combo.count()):
                if self.account_combo.itemData(i) == self.transaction.account_id:
                    self.account_combo.setCurrentIndex(i)
                    break
        
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка загрузки счетов: {e}", exc_info=True)
            raise
    
    def _load_categories_combo(self):
        """Заполняет комбобокс категорий данными из кэша."""
        try:
            self.category_combo.clear()
            
            current_type = self.type_combo.currentText()
            
            # Для корректировки категория не нужна
            if current_type == "Корректировка":
                self.category_combo.setEnabled(False)
                self.category_combo.addItem("Не требуется", userData=None)
                return
            
            self.category_combo.setEnabled(True)
            
            if not self._category_cache:
                self.category_combo.addItem("Нет категорий", userData=None)
                return
            
            # Фильтруем системные категории
            user_categories = [
                cat for cat in self._category_cache.values()
                if not getattr(cat, 'is_system', False)
            ]
            
            for category in user_categories:
                self.category_combo.addItem(category.name, userData=category.id)
            
            # Выбираем категорию транзакции
            if self.transaction.category_id:
                for i in range(self.category_combo.count()):
                    if self.category_combo.itemData(i) == self.transaction.category_id:
                        self.category_combo.setCurrentIndex(i)
                        break
        
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка загрузки категорий: {e}", exc_info=True)
            raise
    
    def _on_type_change(self, type_text: str):
        """
        Обрабатывает изменение типа транзакции.
        
        Args:
            type_text: выбранный тип транзакции (Доход/Расход/Корректировка)
        """
        try:
            if type_text == "Корректировка":
                self.category_combo.setEnabled(False)
                self.category_combo.clear()
                self.category_combo.addItem("Не требуется", userData=None)
            else:
                self.category_combo.setEnabled(True)
                self._load_categories_combo()
            
            logger.debug(f"[{self.__class__.__name__}] Смена типа на: {type_text}")
        
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обработки смены типа: {e}", exc_info=True)
    
    def _update_info_label(self):
        """Обновляет блок дополнительной информации о транзакции."""
        try:
            account = self._account_cache.get(self.transaction.account_id)
            category = self._category_cache.get(self.transaction.category_id) if self.transaction.category_id else None
            
            info_text = (
                f"Создана: {getattr(self.transaction, 'created_at', '—')}\n"
                f"Обновлена: {getattr(self.transaction, 'updated_at', '—')}\n"
                f"Счёт: {account.name if account else '—'}\n"
                f"Категория: {category.name if category else '—'}"
            )
            self.info_label.setText(info_text)
        
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обновления info_label: {e}", exc_info=True)
    
    def _get_form_data(self) -> dict:
        """
        Собирает и валидирует данные из формы.
        
        Returns:
            Словарь с данными для сохранения транзакции:
            - date: str (формат yyyy-MM-dd)
            - raw_amount: str (сумма или выражение "сумма*количество")
            - trans_type: str (income/expense/correct)
            - account_id: int
            - category_id: int или None
            - description: str
        
        Raises:
            ValueError: если введены некорректные данные
        """
        try:
            # Дата
            new_date = self.date_input.date().toString("yyyy-MM-dd")
            
            # Сумма
            amount_str = self.amount_input.text().strip()
            if not amount_str:
                raise ValueError("Сумма не может быть пустой")
            
            # Количество
            quantity_str = self.quantity_input.text().strip()
            if not quantity_str:
                raise ValueError("Количество не может быть пустым")
            
            try:
                quantity = float(quantity_str.replace(',', '.'))
                if quantity <= 0:
                    raise ValueError("Количество должно быть больше нуля")
            except ValueError:
                raise ValueError(f"Некорректное количество: {quantity_str}")
            
            # Формируем raw_amount
            if quantity != 1.0:
                raw_amount = f"{amount_str}*{quantity}"
            else:
                raw_amount = amount_str
            
            # Тип
            type_map = {
                "Доход": "income",
                "Расход": "expense",
                "Корректировка": "correct"
            }
            trans_type = type_map.get(self.type_combo.currentText())
            if not trans_type:
                raise ValueError("Некорректный тип транзакции")
            
            # Счёт
            account_id = self.account_combo.currentData()
            if not account_id:
                raise ValueError("Выберите счёт")
            
            # Категория
            category_id = self.category_combo.currentData()
            if trans_type != "correct" and not category_id:
                raise ValueError("Выберите категорию")
            
            # Описание
            description = self.description_input.text().strip()
            
            return {
                'date': new_date,
                'raw_amount': raw_amount,
                'trans_type': trans_type,
                'account_id': account_id,
                'category_id': category_id,
                'description': description
            }
        
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация формы: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка сбора данных формы: {e}", exc_info=True)
            raise
    
    def _save_changes(self):
        """Сохраняет изменения транзакции через презентер."""
        try:
            if not self.presenter:
                raise ValueError("Презентер не подключен")
            
            data = self._get_form_data()
            
            # Вызываем метод обновления транзакции
            self.presenter.update_transaction(
                transaction_id=self.transaction.id,
                raw_amount=data['raw_amount'],
                trans_type=data['trans_type'],
                account_id=data['account_id'],
                category_id=data['category_id'],
                description=data['description'],
                date_str=data['date']
            )
            
            logger.info(f"[{self.__class__.__name__}] Транзакция ID={self.transaction.id} обновлена")
            self.data_updated.emit()
            self.accept()
        
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация сохранения: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Ошибка валидации", str(e))
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка сохранения транзакции: {e}", exc_info=True)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ошибка", "Произошла ошибка при сохранении")
    
    def _delete_transaction(self):
        """Удаляет транзакцию после подтверждения пользователя."""
        try:
            if not self.presenter:
                raise ValueError("Презентер не подключен")
            
            from PySide6.QtWidgets import QMessageBox
            
            reply = QMessageBox.question(
                self,
                "Подтверждение удаления",
                f"Вы уверены, что хотите удалить транзакцию ID={self.transaction.id}?\n\n"
                f"Это действие нельзя отменить.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.presenter.delete_transaction(self.transaction.id)
                logger.info(f"[{self.__class__.__name__}] Транзакция ID={self.transaction.id} удалена")
                self.data_updated.emit()
                self.accept()
        
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация удаления: {e}")
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Ошибка", str(e))
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка удаления транзакции: {e}", exc_info=True)
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ошибка", "Произошла ошибка при удалении")