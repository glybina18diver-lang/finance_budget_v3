import sys
import os
import shutil
from datetime import datetime
from pathlib import Path
import traceback

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QMessageBox, QMenuBar, QMenu,
    QFileDialog, QApplication, QScrollArea, QDialog, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QFont, QIcon

from config import WINDOW_TITLE
from core.db import Database
from ui.widgets.colored_button import ColoredButton
from ui.dialogs.operation_dialog import OperationDialog

class MainWindow(QMainWindow):
    def __init__(self, database: Database, tx_presenter):
        super().__init__()
        self.database = database
        self.tx_presenter = tx_presenter
        self.operations_dialog = None  

        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(QIcon('./assets/icon.png'))
        self.setMinimumSize(1300, 680)
        self.resize(1300, 680)

        self._init_ui()

    def _init_ui(self):
        """Инициализация пользовательского интерфейса."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # === ВЕРХНЯЯ ЧАСТЬ: КНОПКИ И ОБЩИЙ БАЛАНС ===
        top_container = self._create_top_panel()
        main_layout.addWidget(top_container)
        
        # Разделитель
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.HLine)
        separator1.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator1)
        
        # === СЧЕТА В 2 КОЛОНКИ ===
        accounts_container = self._create_accounts_panel()
        main_layout.addWidget(accounts_container, 0)
        
        # Разделитель
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.HLine)
        separator2.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator2)
        
        # === ГРАФИКИ В 2 КОЛОНКИ ===
        charts_container = self._create_charts_panel()
        main_layout.addWidget(charts_container, 1)
        
        # Статус бар
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Готово")

    def _create_top_panel(self):
        """Создает верхнюю панель с кнопками и общим балансом."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Кнопка "Обновить"
        refresh_btn = ColoredButton("🔄 Обновить", "#3498db")
        refresh_btn.setMaximumWidth(100)
        refresh_btn.setObjectName("refresh_btn")
        refresh_btn.clicked.connect(self._refresh_data)
        layout.addWidget(refresh_btn)
        
        # Кнопка "+ Операции"
        add_op_btn = ColoredButton("+ Операции", "#3498db")
        add_op_btn.setMaximumWidth(100)
        add_op_btn.setObjectName("add_op_btn")
        add_op_btn.clicked.connect(self._open_operations_dialog)
        layout.addWidget(add_op_btn)
        
        # Кнопка "Дашборд"
        dashboard_btn = ColoredButton("📊 Дашборд", "#2ecc71")
        dashboard_btn.setMaximumWidth(100)
        dashboard_btn.setObjectName("dashboard_btn")
        dashboard_btn.clicked.connect(self._open_dashboard)
        layout.addWidget(dashboard_btn)
        
        # Растягиваем пространство
        layout.addStretch()
        
        # Общий баланс
        balance_container = self._create_balance_widget()
        layout.addWidget(balance_container)
        
        return container
    
    def _create_balance_widget(self):
        """Создает виджет общего баланса."""
        container = QWidget()
        container.setObjectName("balance_container")
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Текст "Общий баланс:"
        balance_text_label = QLabel("Общий баланс:")
        balance_text_label.setObjectName("balance_text_label")
        layout.addWidget(balance_text_label)
        
        # Сумма баланса
        self.total_balance_label = QLabel("0.00 ₽")
        self.total_balance_label.setObjectName("total_balance_label")
        self.total_balance_label.setAlignment(Qt.AlignCenter)
        self.total_balance_label.setMinimumWidth(120)
        self._update_balance_style(0)
        layout.addWidget(self.total_balance_label)
        
        return container
    
    def _create_accounts_panel(self):
        """Создает панель счетов в 2 колонки."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # ЛЕВАЯ КОЛОНКА - Обычные счета
        left_widget = self._create_accounts_column("regular")
        layout.addWidget(left_widget, 1)
        
        # ПРАВАЯ КОЛОНКА - Кредитные карты
        right_widget = self._create_accounts_column("credit")
        layout.addWidget(right_widget, 1)
        
        return container
    
    def _create_accounts_column(self, column_type):
        """Создает колонку для счетов."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Создаем layout для счетов
        accounts_layout = QVBoxLayout()
        accounts_layout.setSpacing(2)
        
        # Сохраняем ссылку на layout
        if column_type == "regular":
            self.regular_accounts_layout = accounts_layout
        else:
            self.credit_accounts_layout = accounts_layout
        
        # Создаем scroll area
        scroll = QScrollArea()
        scroll.setObjectName("accounts_scroll")
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(180)
        scroll.setMaximumHeight(220)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Контейнер для счетов
        scroll_widget = QWidget()
        scroll_widget.setLayout(accounts_layout)
        scroll.setWidget(scroll_widget)
        
        layout.addWidget(scroll)
        return widget
    
    def _stub_method(self):
        """Заглушка для нереализованных методов."""
        QMessageBox.information(self, "В разработке", "Функция в разработке")

    def _refresh_data(self):
        """Обновляет данные в панели счетов."""
        self._stub_method()
    
    def _open_operations_dialog(self):
        if self.operations_dialog and self.operations_dialog.isVisible():
            self.operations_dialog.raise_()
            return

        # Создаём диалог и передаём ему УЖЕ СУЩЕСТВУЮЩИЙ презентер
        self.operations_dialog = OperationDialog(
            parent=self,
            presenter=self.tx_presenter  # ← тот самый экземпляр из main.py
        )
        
        self.operations_dialog.show()
    
    def _open_dashboard(self):
        """Открывает дашборд."""
        self._stub_method()

    def _update_balance_style(self, balance):
        """Обновляет стиль отображения баланса."""
        if balance < 0:
            color = "#e74c3c"  # Красный
        elif balance == 0:
            color = "#f39c12"  # Оранжевый
        else:
            color = "#27ae60"  # Зеленый
        
        self.total_balance_label.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {color};
                padding: 6px 12px;
                background-color: white;
                border-radius: 3px;
                border: 1px solid #ced4da;
            }}
        """)

    def _create_charts_panel(self):
        """Создает панель графиков."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Круговая диаграмма РАСХОДОВ
        # from ui.widgets.expense_pie_chart_widget import ExpensePieChartWidget
        # self.pie_chart = ExpensePieChartWidget(self, self.chart_proxy)
        # self.pie_chart.setMinimumHeight(250)
        # self.pie_chart.setMaximumHeight(270)
        # layout.addWidget(self.pie_chart, 1)
        
        # График доходов/расходов
        # self.income_expense_chart = IncomeExpenseChart(self, self.chart_proxy)
        #self.income_expense_chart.setMinimumHeight(250)
        #  self.income_expense_chart.setMaximumHeight(270)
        # layout.addWidget(self.income_expense_chart, 1)
        
        return container