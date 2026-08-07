import sys
import os
import shutil
from datetime import datetime
from pathlib import Path
import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QMessageBox, QMenuBar, QMenu,
    QFileDialog, QApplication, QScrollArea, QDialog, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QFont, QIcon
from config import WINDOW_TITLE, ICON_DIR
from core.db import Database
from ui.widgets.buttons import CompactButton
from services.navigation_service import NavigationService
from ui.dialogs.base_dialog import BaseDialog

from decimal import Decimal
from typing import List, Optional
from core.models import Account, CreditCard
from core.repositories.account_repository import AccountRepository
from core.repositories.credit_card_repository import CreditCardRepository
from ui.presenters.main_window_presenter import MainWindowPresenter

logger = logging.getLogger(__name__)


class MainWindow(BaseDialog):
    """Главное окно приложения."""

    def __init__(self, presenter: MainWindowPresenter, navigation_service: NavigationService):
        """
        Инициализация главного окна.

        Args:
            navigation_service: экземпляр NavigationService для доступа к БД и сервисам
        """
        try:
            super().__init__(parent=None, navigation_service=navigation_service)
            self.setWindowFlags(Qt.Window)
            self.presenter = presenter

            self.setWindowTitle(WINDOW_TITLE)
            self.setWindowIcon(QIcon(ICON_DIR))
            self.setMinimumSize(1300, 680)
            self.resize(1300, 680)

            self._init_ui()

            self.presenter.set_view(self)

            logger.info(f"[{self.__class__.__name__}] Главное окно инициализировано")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка инициализации: {e}", exc_info=True)
            raise

    # Создаем UI
    def _init_ui(self):
        """Инициализация пользовательского интерфейса."""
        try:
            # _main_layout уже создан в BaseDialog
            main_layout = self._main_layout
            main_layout.setContentsMargins(3, 0, 3, 1)
            main_layout.setSpacing(8)

            # === МЕНЮ ===
            self._init_menu()

            # Разделитель после меню
            separator_menu = QFrame()
            separator_menu.setFrameShape(QFrame.HLine)
            separator_menu.setFrameShadow(QFrame.Sunken)
            main_layout.addWidget(separator_menu)

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

            # Статус-бар уже добавлен в BaseDialog
            # self.status_bar.setText("Готово")
            main_layout.addWidget(self.status_bar) #TODO: поправить подключение

            logger.debug(f"[{self.__class__.__name__}] UI инициализирован")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка инициализации UI: {e}", exc_info=True)
            raise

    def _create_top_panel(self):
        """Создает верхнюю панель с кнопками и общим балансом."""
        try:
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(5, 1, 5, 1)

            # Кнопка "Обновить"
            refresh_btn = CompactButton("🔄 Обновить", "info")
            refresh_btn.setMaximumWidth(100)
            refresh_btn.setObjectName("refresh_btn")
            refresh_btn.clicked.connect(self._refresh_data)
            layout.addWidget(refresh_btn)

            # Кнопка "+ Операции"
            add_op_btn = CompactButton("+ Операции", "success")
            add_op_btn.setMaximumWidth(100)
            add_op_btn.setObjectName("add_op_btn")
            add_op_btn.clicked.connect(self._open_operations_dialog)
            layout.addWidget(add_op_btn)

            # Кнопка "Дашборд"
            dashboard_btn = CompactButton("📊 Дашборд", "info")
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
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания верхней панели: {e}", exc_info=True)
            raise

    def _create_balance_widget(self):
        """Создает виджет общего баланса."""
        try:
            container = QWidget()
            container.setObjectName("balance_container")
            layout = QHBoxLayout(container)
            layout.setContentsMargins(2, 2, 2, 2)
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
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания виджета баланса: {e}", exc_info=True)
            raise

    def _create_accounts_panel(self):
        """Создает панель счетов в 2 колонки."""
        try:
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(5, 0, 5, 0)
            layout.setSpacing(10)

            # ЛЕВАЯ КОЛОНКА - Обычные счета
            left_widget = self._create_accounts_column("regular")
            layout.addWidget(left_widget, 1)

            # ПРАВАЯ КОЛОНКА - Кредитные карты
            right_widget = self._create_accounts_column("credit")
            layout.addWidget(right_widget, 1)

            return container
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания панели счетов: {e}", exc_info=True)
            raise

    def _create_accounts_column(self, column_type):
        """
        Создает колонку для счетов.

        Args:
            column_type: тип колонки ("regular" или "credit")

        Returns:
            QWidget с layout для счетов
        """
        try:
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
            scroll_widget.setObjectName("accounts_content")
            scroll_widget.setLayout(accounts_layout)
            scroll.setWidget(scroll_widget)

            layout.addWidget(scroll)
            return widget
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания колонки счетов: {e}", exc_info=True)
            raise

    def _create_charts_panel(self):
            """Создает панель графиков."""
            try:
                container = QWidget()
                layout = QHBoxLayout(container)
                layout.setContentsMargins(550, 0, 5, 0)
                layout.setSpacing(10)

                # Круговая диаграмма РАСХОДОВ
                # from ui.widgets.expense_pie_chart_widget import ExpensePieChartWidget
                # self.pie_chart = ExpensePieChartWidget(self, self.chart_proxy)
                # self.pie_chart.setMinimumHeight(250)
                # self.pie_chart.setMaximumHeight(270)
                # layout.addWidget(self.pie_chart, 1)

                # График доходов/расходов
                from ui.widgets.income_expense_chart import IncomeExpenseChart

                # Передаём экземпляр БД из навигационного сервиса
                self.income_expense_chart = IncomeExpenseChart(
                    self,
                    self.navigation_service.db
                )
                self.income_expense_chart.setMinimumHeight(250)
                self.income_expense_chart.setMaximumHeight(270)
                self.income_expense_chart.setMinimumWidth(650)
                self.income_expense_chart.setMaximumWidth(800)
                layout.addWidget(self.income_expense_chart, 1)

                return container
            except Exception as e:
                logger.error(f"[{self.__class__.__name__}] Ошибка создания панели графиков: {e}", exc_info=True)

    def _init_menu(self):
        """Инициализация главного меню окна."""
        try:
            menubar = QMenuBar(self)

            # === Меню Файл ===
            file_menu = menubar.addMenu("Файл")
            self._add_menu_action(file_menu, "Импорт CSV...", self._stub_method)
            self._add_menu_action(file_menu, "Экспорт в CSV...", self._stub_method)
            file_menu.addSeparator()
            self._add_menu_action(file_menu, "Создать резервную копию...", self._stub_method)
            self._add_menu_action(file_menu, "Восстановить...", self._stub_method)
            self._add_menu_action(file_menu, "Информация о копиях", self._stub_method)
            file_menu.addSeparator()
            self._add_menu_action(file_menu, "Выход", self.close)

            # === Меню Настройки ===
            settings_menu = menubar.addMenu("Настройки")
            self._add_menu_action(settings_menu, "Управление счетами", lambda: self.navigation_service.open_account_dialog(self))
            self._add_menu_action(settings_menu, "Управление категориями", self._stub_method)
            settings_menu.addSeparator()

            # === Меню Отчеты ===
            reports_menu = menubar.addMenu("Отчеты")
            self._add_menu_action(reports_menu, "Дашборд", self._stub_method)
            self._add_menu_action(reports_menu, "Месячный отчет", self._stub_method)
            self._add_menu_action(reports_menu, "Отчет по категориям", self._stub_method)
            self._add_menu_action(reports_menu, "Анализ расходов", self._stub_method)

            # === Меню Помощь ===
            help_menu = menubar.addMenu("Помощь")
            self._add_menu_action(help_menu, "Справка", self._stub_method)
            self._add_menu_action(help_menu, "О программе", self._stub_method)

            # Добавляем menubar в layout как обычный виджет
            self._main_layout.insertWidget(0, menubar)

            logger.info(f"[{self.__class__.__name__}] Меню инициализировано")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка инициализации меню: {e}", exc_info=True)
            raise

    def _add_menu_action(self, menu: QMenu, text: str, callback) -> QAction:
        """
        Добавляет действие в указанное меню.

        Args:
            menu: экземпляр QMenu, в который добавляется действие
            text: отображаемый текст пункта меню
            callback: функция-обработчик, вызываемая при активации действия

        Returns:
            Созданный экземпляр QAction

        Raises:
            ValueError: если text пустой или callback не является вызываемым объектом
            Exception: при системных ошибках создания действия
        """
        try:
            if not text or not text.strip():
                raise ValueError("Текст пункта меню не может быть пустым")
            if not callable(callback):
                raise ValueError(f"callback должен быть вызываемым объектом, получено: {type(callback)}")

            action = QAction(text, self)
            action.triggered.connect(callback)
            menu.addAction(action)
            # logger.debug(f"[{self.__class__.__name__}] Добавлен пункт меню: '{text}'")
            return action
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка добавления пункта меню '{text}': {e}", exc_info=True)
            raise

    # Открывает диалоги
    def _open_operations_dialog(self):
        """Открывает диалог операций через навигационный сервис."""
        try:
            if hasattr(self, '_operations_dialog') and self._operations_dialog and self._operations_dialog.isVisible():
                self._operations_dialog.raise_()
                return

            # Просим навигатор открыть диалог
            dialog = self.navigation_service.open_operation_dialog(parent=self)
            self._operations_dialog = dialog
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка открытия диалога операций: {e}", exc_info=True)

    def _open_dashboard(self):
        """Открывает дашборд."""
        self._stub_method()

    def _update_balance_style(self, balance):
        """
        Обновляет визуальный стиль виджета общего баланса.
        
        Args:
            balance: Текущее значение баланса (float/int).
        """
        try:
            if balance < 0:
                self.total_balance_label.setProperty("variant", "danger")
            elif balance == 0:
                self.total_balance_label.setProperty("variant", "default") 
            else:
                self.total_balance_label.setProperty("variant", "success")
                
            # КРИТИЧЕСКИ ВАЖНО: Заставляем Qt пересчитать стили для виджета после смены свойства
            self.total_balance_label.style().unpolish(self.total_balance_label)
            self.total_balance_label.style().polish(self.total_balance_label)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обновления стиля баланса: {e}", exc_info=True)

    

    # =================== Контракт View <-> Presenter ===================
    def _load_accounts(self, regular_accounts: List[Account], credit_accounts: List[Account]):
        """
        пользовательские счета отображает их в панели.

        Args:
            regular_accounts: Обычные счета
            credit_accounts: Кретиные карты
        
        """
        try:
            # Очищаем существующие layout'ы
            self._clear_layout(self.regular_accounts_layout)
            self._clear_layout(self.credit_accounts_layout)
            
            # Отображаем обычные счета
            for account in regular_accounts:
                self._add_regular_account_widget(account)  # ← Передаём один элемент
            
            # Отображаем кредитные карты с расширенной информацией
            for account in credit_accounts:
                self._add_credit_account_widget(account)
            
            # Обновляем общий баланс
            self._update_total_balance(regular_accounts)
            
            logger.info(f"[{self.__class__.__name__}] Загружено счетов: {len(regular_accounts)} обычных, {len(credit_accounts)} кредитных")
            
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка  счетов: {e}", exc_info=True)
            self.status_bar.setText("Ошибка  счетов")
            

    
    def _clear_layout(self, layout):
        """
        Очищает layout от всех виджетов.
        
        Args:
            layout: QVBoxLayout для очистки
        """
        try:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка очистки layout: {e}", exc_info=True)

    def _add_regular_account_widget(self, account: Account): #TODO: поправить стили
        """
        Добавляет виджет обычного счета в панель.
        
        Args:
            account: объект Account с данными счета
        """
        try:
            widget = QWidget()
            widget.setObjectName(f"account_{account.id}")
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(8, 6, 8, 6)
            layout.setSpacing(10)
            
            # Название счета
            name_label = QLabel(account.name)
            name_label.setStyleSheet("font-weight: bold; font-size: 13px;")
            layout.addWidget(name_label)
            
            layout.addStretch()
            
            # Баланс
            balance_label = QLabel(f"{account.current_balance:,.2f} ₽")
            balance_label.setStyleSheet(self._get_balance_style(account.current_balance))
            balance_label.setMinimumWidth(100)
            balance_label.setAlignment(Qt.AlignRight)
            layout.addWidget(balance_label)
            
            self.regular_accounts_layout.addWidget(widget)
            
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания виджета счета '{account.name}': {e}", exc_info=True)

    def _add_credit_account_widget(self, account: Account): #TODO: поправить стили
        """
        Добавляет виджет кредитной карты с расширенной информацией.
        
        Отображает:
        - Название счета
        - Лимит
        - Долг (текущий баланс с отрицательным знаком)
        - Доступно (лимит - долг)
        - Процент использования лимита
        
        Args:
            account: объект Account с данными счета
            credit_card_repo: репозиторий кредитных карт для получения доп. информации
        """
        try:
            # Получаем информацию о кредитной карте
            credit_card: Optional[CreditCard] = self.presenter.get_credit_cards_info(account.id)
            
            widget = QWidget()
            widget.setObjectName(f"account_{account.id}")
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(8, 6, 8, 6)
            layout.setSpacing(4)
            
            # === ВЕРХНЯЯ СТРОКА: Название и Долг ===
            top_layout = QHBoxLayout()
            top_layout.setSpacing(10)
            
            # Название счета
            name_label = QLabel(account.name)
            name_label.setStyleSheet("font-weight: bold; font-size: 13px;")
            top_layout.addWidget(name_label)
            
            top_layout.addStretch()
            
            # Долг (текущий баланс)
            debt = abs(account.current_balance) if account.current_balance < 0 else Decimal("0")
            debt_label = QLabel(f"Долг: {debt:,.2f} ₽")
            debt_label.setStyleSheet("color: #e74c3c; font-weight: bold;")
            debt_label.setMinimumWidth(120)
            debt_label.setAlignment(Qt.AlignRight)
            top_layout.addWidget(debt_label)
            
            layout.addLayout(top_layout)
            
            # === НИЖНЯЯ СТРОКА: Лимит, Доступно, Процент ===
            bottom_layout = QHBoxLayout()
            bottom_layout.setSpacing(15)
            
            # Лимит (если есть)
            if credit_card and credit_card.credit_limit:
                limit = credit_card.credit_limit
                limit_label = QLabel(f"Лимит: {limit:,.2f} ₽")
                limit_label.setStyleSheet("color: #6c757d; font-size: 12px;")
                bottom_layout.addWidget(limit_label)
                
                # Доступно
                available = max(Decimal("0"), limit - debt)
                available_label = QLabel(f"Доступно: {available:,.2f} ₽")
                available_label.setStyleSheet("color: #27ae60; font-size: 12px; font-weight: bold;")
                bottom_layout.addWidget(available_label)
                
                # Процент использования
                if limit > 0:
                    usage_percent = (debt / limit) * 100
                    percent_label = QLabel(f"({usage_percent:.1f}% лимита)")
                    
                    # Цвет в зависимости от заполнения
                    if usage_percent >= 90:
                        color = "#e74c3c"  # Красный (критично)
                    elif usage_percent >= 70:
                        color = "#f39c12"  # Оранжевый (внимание)
                    else:
                        color = "#27ae60"  # Зеленый (норма)
                    
                    percent_label.setStyleSheet(f"color: {color}; font-size: 11px;")
                    bottom_layout.addWidget(percent_label)
            
            bottom_layout.addStretch()
            
            layout.addLayout(bottom_layout)
            
            # Добавляем разделитель между картами
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            separator.setStyleSheet("color: #e9ecef;")
            layout.addWidget(separator)
            
            self.credit_accounts_layout.addWidget(widget)
            
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка создания виджета кредитной карты '{account.name}': {e}", exc_info=True)
            raise

    def _update_total_balance(self, accounts: List[Account]): #TODO: поправить стили
        """
        Обновляет отображение общего баланса по всем счетам.
        
        Args:
            accounts: список всех пользовательских счетов
            credit_card_repo: репозиторий кредитных карт
        """
        try:
            total_balance = Decimal("0")
            
            for account in accounts:
                if account.account_type == "CreditCard":
                    # Для кредитных карт учитываем только доступный лимит
                    credit_card = self.presenter.get_credit_cards_info(account.id)
                    if credit_card and credit_card.credit_limit:
                        debt = abs(account.current_balance) if account.current_balance < 0 else Decimal("0")
                        available = max(Decimal("0"), credit_card.credit_limit - debt)
                        total_balance += available
                else:
                    # Для обычных счетов просто добавляем баланс
                    total_balance += account.current_balance
            
            self.total_balance_label.setText(f"{total_balance:,.2f} ₽")
            self._update_balance_style(total_balance)
            
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка расчета общего баланса: {e}", exc_info=True)
            raise

    def _get_balance_style(self, balance: Decimal) -> str:
        """
        Возвращает стиль для отображения баланса.
        
        Args:
            balance: сумма баланса
            
        Returns:
            CSS-стиль для QLabel
        """
        if balance < 0:
            color = "#e74c3c"  # Красный
        elif balance == 0:
            color = "#f39c12"  # Оранжевый
        else:
            color = "#27ae60"  # Зеленый
        
        return f"font-size: 13px; font-weight: bold; color: {color};"

    def _refresh_data(self):
        """Обновляет данные счетов с базы."""
        try:
            self.status_bar.setText("Обновление данных...")
            self.presenter._load_accounts()
            # Обноваляем график после смены темы TODO: нужно реализоввать смену типа через натрики проги
            self.income_expense_chart.update_chart()
            self.status_bar.setText("Данные обновлены")
            logger.info(f"[{self.__class__.__name__}] Данные обновлены")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка обновления данных: {e}", exc_info=True)
            self.status_bar.setText("Ошибка обновления")
            raise

    