import logging
import traceback
import calendar
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDateEdit, QMessageBox, QComboBox
)
from PySide6.QtCore import QDate
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from ui.widgets.buttons import CompactButton

logger = logging.getLogger(__name__)

class BankComparisonDialog(QDialog):
    """
    Открывает окно сверки расходов с банковским приложением.
    
    Выводит отдельно расходы за период, переводы (+/-), возвраты и общие суммы.
    """

    # Названия месяцев для выпадающего списка
    MONTHS = [
        "Январь", "Февраль", "Март", "Апрель",
        "Май", "Июнь", "Июль", "Август",
        "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]

    def __init__(self, presenter, parent=None):
        """
        Инициализация диалога.
        
        Args:
            presenter: экземпляр BankComparisonPresenter, внедрённый из родительского окна.
            parent: родительское окно.
        """
        super().__init__(parent)
        self.presenter = presenter
        self.setWindowTitle("Сверка с банковским приложением")
        self.resize(550, 300)
        
        self._init_ui()
        if self.presenter:
            self.presenter.set_view(self)

    def _init_ui(self):
        """Инициализирует UI элементы и компоновку."""
        main_layout = QVBoxLayout(self)
        
        # --- Фильтры: месяц, год, счет ---
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Счет:"))
        self.combo_account = QComboBox()
        self.combo_account.addItem(None, userData=None) 
        filter_layout.addWidget(self.combo_account)

        filter_layout.addWidget(QLabel("Месяц:"))
        self.combo_month = QComboBox()
        self.combo_month.addItems(self.MONTHS)
        # По умолчанию — текущий месяц (индекс = текущий месяц - 1)
        self.combo_month.setCurrentIndex(datetime.now().month - 1)
        filter_layout.addWidget(self.combo_month)

        filter_layout.addWidget(QLabel("Год:"))
        self.combo_year = QComboBox()
        current_year = datetime.now().year
        # Годы от 2000 до текущего (по убыванию, чтобы текущий был первым)
        years = [str(y) for y in range(current_year, 1999, -1)]
        self.combo_year.addItems(years)
        filter_layout.addWidget(self.combo_year)

        self.btn_load = CompactButton("Загрузить сводку", "info")
        filter_layout.addWidget(self.btn_load)

        main_layout.addLayout(filter_layout)
        
        # Сводка
        content_layout = QHBoxLayout()
        
        self.summary_layout = QVBoxLayout()
        self.lbl_income = QLabel("Доходы: 0 ₽")
        self.lbl_expenses = QLabel("Расходы: 0 ₽")
        self.lbl_transfers_in = QLabel("Переводы (+): 0 ₽")
        self.lbl_transfers_out = QLabel("Переводы (-): 0 ₽")
        self.lbl_refunds = QLabel("Возвраты: 0 ₽")
        self.lbl_total_in = QLabel("Всего поступлений: 0 ₽")
        self.lbl_total_out = QLabel("Всего списаний: 0 ₽")
        
        for lbl in [self.lbl_income, self.lbl_expenses, self.lbl_transfers_in, self.lbl_transfers_out, 
                    self.lbl_refunds, self.lbl_total_in, self.lbl_total_out]:
            self.summary_layout.addWidget(lbl)
            
        content_layout.addLayout(self.summary_layout)
                
        main_layout.addLayout(content_layout)
        
        # Сигналы
        self.btn_load.clicked.connect(self._on_load_clicked)

    def _on_load_clicked(self):
        """Обработчик клика по кнопке загрузки сводки."""
        try:
            start_date, end_date = self._get_period_from_combos()
            account_id = self.combo_account.currentData()
            
            self.presenter.load_summary(start_date, end_date, account_id)
            
        except ValueError as e:
            self.show_status(str(e), "error")  # Показываем пользователю
        except Exception as e:
            logger.error(f"Ошибка UI: {e}", exc_info=True)
            self.show_status("Произошла ошибка при загрузке", "error")

    def _get_period_from_combos(self) -> tuple[date, date]:
        """
        Вычисляет начало и конец месяца по выбранным значениям в комбобоксах.

        Returns:
            tuple: (start_date, end_date) — первый и последний день выбранного месяца.

        Raises:
            ValueError: если месяц или год не выбраны, либо данные некорректны.
        """
        try:
            month_index = self.combo_month.currentIndex()
            year_text = self.combo_year.currentText()

            if month_index < 0:
                raise ValueError("Месяц не выбран")

            if not year_text or not year_text.isdigit():
                raise ValueError("Год не выбран или некорректен")

            month = month_index + 1  # индекс 0-11 → месяц 1-12
            year = int(year_text)

            # Валидация диапазона года
            if year < 2000 or year > date.today().year:
                raise ValueError(f"Год должен быть в диапазоне 2000–{date.today().year}")

            # Последний день месяца
            last_day = calendar.monthrange(year, month)[1]

            start_date = date(year, month, 1)
            end_date = date(year, month, last_day)

            logger.debug(
                f"[{self.__class__.__name__}] Период: {start_date} — {end_date}"
            )
            return start_date, end_date

        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация периода: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[{self.__class__.__name__}] Ошибка расчёта периода: {e}",
                exc_info=True,
            )
            raise

    def update_summary(self, summary_data: dict):
        """
        Обновляет текстовые метки и строит круговую диаграмму на основе данных.
        
        Args:
            summary_data: Словарь с агрегированными данными (income, expenses, transfers_in, transfers_out, refunds, total_in, total_out).
        """
        try:
            # Обновление текстовых меток
            self.lbl_income.setText(f"Доходы: {summary_data.get('income', 0):.2f} ₽")
            self.lbl_expenses.setText(f"Расходы: {summary_data.get('expenses', 0):.2f} ₽")
            self.lbl_transfers_in.setText(f"Переводы (+): {summary_data.get('transfers_in', 0):.2f} ₽")
            self.lbl_transfers_out.setText(f"Переводы (-): {summary_data.get('transfers_out', 0):.2f} ₽")
            self.lbl_refunds.setText(f"Возвраты: {summary_data.get('refunds', 0):.2f} ₽")
            self.lbl_total_in.setText(f"Всего поступлений: {summary_data.get('total_in', 0):.2f} ₽")
            self.lbl_total_out.setText(f"Всего списаний: {summary_data.get('total_out', 0):.2f} ₽")
            
        except Exception as e:
            logger.error(f"Ошибка UI: {e}", exc_info=True)
            self.show_status("Ошибка отображения данных", "error")

    def load_accounts_combos(self, accounts: List):
        """
        Заполняет комбобоксы счетов данными из БД (исключая системные).
        Вызывается презентером.

        Args:
            accounts: список объектов Account из презентера
            
        Note:
            Системные счета (is_system=True) исключаются из комбобокса
        """
        try:
            self.combo_account.clear()
            
            if not accounts:
                self.combo_account.addItem("Нет счетов", userData=None)
                self.show_status("⚠️ Нет доступных счетов. Создайте счёт в управлении счетами.", message_type="warning")
                return

            # Фильтруем системные счета
            user_accounts = [account for account in accounts if not getattr(account, 'is_system', False)]
            
            if not user_accounts:
                self.combo_account.addItem("Нет пользовательских счетов", userData=None)
                self.show_status("⚠️ Нет пользовательских счетов. Все существующие счета являются системными.", message_type="warning")
                return
        
            # Заполняем комбобоксы реальными счетами
            for account in user_accounts:
                display_text = account.name
                
                # Добавляем в основной комбобокс
                self.combo_account.addItem(display_text, userData=account.id)
                
                # Если нужен комбобокс фильтра - раскомментируйте:
                # self.account_filter_combo.addItem(display_text, userData=account.id)
            
            # Выбираем первый счёт по умолчанию
            self.combo_account.setCurrentIndex(0)

        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка загрузки счетов: {e}", exc_info=True)
            self.show_status("Ошибка загрузки счетов", message_type="error")

    def show_status(self, message: str, level: str):
        """
        Показывает статусное сообщение пользователю.
        
        Args:
            message: Текст сообщения.
            level: Уровень (info, error).
        """
        if level == "error":
            QMessageBox.critical(self, "Ошибка", message)
        else:
            QMessageBox.information(self, "Информация", message)