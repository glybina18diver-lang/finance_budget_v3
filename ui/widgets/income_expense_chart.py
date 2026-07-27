# ui/widgets/income_expense_chart.py - График доходов/расходов и остатка
from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QPushButton, QWidget, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPalette, QColor
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime


class IncomeExpenseChart(QFrame):
    """График доходов, расходов и остатка по месяцам на PySide6."""
    
    data_updated = Signal()
    
    def __init__(self, parent=None, db_manager=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_year = datetime.now().year
        
        self.setup_ui()
        self.setup_connections()
        
    def setup_ui(self):
        """Настраивает интерфейс виджета."""
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setLineWidth(1)
        
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок и элементы управления
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок
        title_label = QLabel("📈 Динамика доходов/расходов")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        # Растягивающийся разделитель
        header_layout.addStretch()
        
        # Выбор года
        year_label = QLabel("Год:")
        self.year_combo = QComboBox()
        self.year_combo.setFixedWidth(100)
        header_layout.addWidget(year_label)
        header_layout.addWidget(self.year_combo)
        
        # Кнопка обновления
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.setFixedWidth(80)
        header_layout.addWidget(self.refresh_btn)
        
        main_layout.addWidget(header_widget)
        
        # Виджет для графика
        self.chart_widget = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_widget)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.chart_widget, 1)
        
        # Инициализируем matplotlib
        self.figure = None
        self.canvas = None
        self.ax = None
        
        # Заполняем годы
        self.populate_years()
        
    def setup_connections(self):
        """Настраивает соединения сигналов."""
        self.year_combo.currentTextChanged.connect(self.on_year_changed)
        self.refresh_btn.clicked.connect(self.update_chart)
        
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_chart)
        
    def schedule_update(self, data_type=None):
        """Планирует обновление графика."""
        if data_type in [None, 'transactions', 'accounts']:
            self.update_timer.start(500)  # Задержка 500 мс для группировки обновлений
    
    def populate_years(self):
        """Заполняет список годов."""
        current_year = datetime.now().year
        years = list(range(2020, current_year + 2))
        self.year_combo.addItems([str(year) for year in years])
        self.year_combo.setCurrentText(str(self.current_year))
    
    def on_year_changed(self, year_str):
        """Обработчик изменения года."""
        if year_str:
            self.current_year = int(year_str)
            self.update_chart()
    
    def clear_chart(self):
        """Очищает текущий график."""
        if self.canvas:
            self.chart_layout.removeWidget(self.canvas)
            self.canvas.deleteLater()
            self.canvas = None
        
        if self.figure:
            plt.close(self.figure)
            self.figure = None
            self.ax = None
    
    def update_chart(self):
        """Обновляет график с данными из БД."""
        self.clear_chart()
        
        try:
            year = self.current_year
            monthly_data = self.get_monthly_data(year)
            
            if not monthly_data:
                self.show_no_data_message(year)
                return
            
            # Создаем новый график
            self.figure = Figure(figsize=(8, 5), dpi=80, facecolor='#f5f5f5')
            self.canvas = FigureCanvas(self.figure)
            self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.ax = self.figure.add_subplot(111)
            
            # Убираем отступы для максимального использования пространства
            self.figure.subplots_adjust(left=0.07, right=0.95, top=0.95, bottom=0.15)
            
            # Подготавливаем данные
            months = list(range(1, 13))
            month_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 
                          'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
            
            incomes = []
            expenses = []
            balances = []
            cumulative_balances = []
            
            cumulative = 0
            for month in months:
                month_key = f"{year}-{month:02d}"
                if month_key in monthly_data:
                    data = monthly_data[month_key]
                    income = data.get('income', 0)
                    expense = data.get('expense', 0)
                    balance = income - expense
                    
                    incomes.append(income)
                    expenses.append(expense)
                    balances.append(balance)
                    cumulative += balance
                    cumulative_balances.append(cumulative)
                else:
                    incomes.append(0)
                    expenses.append(0)
                    balances.append(0)
                    cumulative_balances.append(cumulative)
            
            # Создаем графики
            x_pos = np.arange(len(months))
            bar_width = 0.35
            
            # Столбцы доходов и расходов
            bars_income = self.ax.bar(x_pos - bar_width/2, incomes, bar_width, 
                                     label='Доходы', color='#2e7d32', alpha=0.8)
            bars_expense = self.ax.bar(x_pos + bar_width/2, expenses, bar_width, 
                                      label='Расходы', color='#c62828', alpha=0.8)
            
            # Линия баланса (второй Y-ось)
            ax2 = self.ax.twinx()
            line_balance, = ax2.plot(x_pos, cumulative_balances, 
                                    label='Накопленный баланс', 
                                    color='#1565c0', marker='^', 
                                    linewidth=2, linestyle='--')
            
            # Настройка основной оси Y
            self.ax.set_ylabel('Сумма, ₽', fontsize=10)
            self.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
            
            # Настройка второй оси Y
            ax2.set_ylabel('Баланс, ₽', fontsize=10)
            ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
            
            # Настройка оси X
            self.ax.set_xticks(x_pos)
            self.ax.set_xticklabels(month_names, rotation=45, fontsize=9)
            self.ax.set_xlabel('Месяцы', fontsize=10)
            
            # Сетка
            self.ax.grid(True, alpha=0.3, linestyle='--', axis='y')
            
            # Легенда
            #handles = [bars_income, bars_expense, line_balance]
            #labels = ['Доходы', 'Расходы', 'Накопленный баланс']
            #self.ax.legend(handles, labels, loc='upper left', fontsize=9, framealpha=0.9)
            
            # Автоматическое масштабирование
            all_values = incomes + expenses
            if all_values:
                max_value = max(all_values)
                if max_value > 0:
                    self.ax.set_ylim(0, max_value * 1.2)
                else:
                    # Если все значения равны нулю, устанавливаем разумный предел
                    self.ax.set_ylim(0, 100)  # 100 рублей для отображения
            else:
                # Нет данных (все значения нулевые или списки пусты)
                self.ax.set_ylim(0, 100)
            
            # Добавляем подписи значений для текущего месяца
            if year == datetime.now().year:
                current_month = datetime.now().month - 1  # Индекс с 0
                if current_month < len(incomes):
                    # Подпись доходов
                    if incomes[current_month] > 0:
                        self.ax.text(current_month - bar_width/2, incomes[current_month],
                                    f'{incomes[current_month]:,.0f}',
                                    ha='center', va='bottom', fontsize=8, color='#2e7d32')
                    
                    # Подпись расходов
                    if expenses[current_month] > 0:
                        self.ax.text(current_month + bar_width/2, expenses[current_month],
                                    f'{expenses[current_month]:,.0f}',
                                    ha='center', va='bottom', fontsize=8, color='#c62828')
            
            # Добавляем график на виджет
            self.chart_layout.addWidget(self.canvas)
            self.canvas.draw()
            
            # Эмитируем сигнал об обновлении
            self.data_updated.emit()
            
        except Exception as e:
            print(f"Ошибка при построении графика: {e}")
            self.show_error_message(str(e))
    
    def get_monthly_data(self, year):
        """Получает данные по месяцам за указанный год."""
        try:
            if not self.db:
                return {}
            
            data = self.db.get_yearly_summary(year)
            if not data:
                return {}
            
            # Преобразуем данные в формат для графика
            result = {}
            for month_key, month_data in data.items():
                result[month_key] = {
                    'income': month_data.get('income', 0),
                    'expense': month_data.get('expense', 0),
                    'balance': month_data.get('balance', 0)
                }
            
            return result
            
        except Exception as e:
            print(f"Ошибка получения данных: {e}")
            return {}
    
    def show_no_data_message(self, year):
        """Показывает сообщение об отсутствии данных."""
        no_data_label = QLabel(f"Нет данных за {year} год")
        no_data_label.setAlignment(Qt.AlignCenter)
        no_data_label.setStyleSheet("""
            QLabel {
                color: #8b8b8b;
                font-size: 14px;
                font-style: italic;
                padding: 40px;
            }
        """)
        self.chart_layout.addWidget(no_data_label)
    
    def show_error_message(self, error_text):
        """Показывает сообщение об ошибке."""
        error_label = QLabel(f"Ошибка при построении графика:\n{error_text}")
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("""
            QLabel {
                color: #d32f2f;
                font-size: 12px;
                padding: 30px;
            }
        """)
        self.chart_layout.addWidget(error_label)
