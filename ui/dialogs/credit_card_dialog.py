"""
Главный диалог управления кредитными картами (CreditCardDialog).

Отображает сводку по картам (долг, лимит, % использования) и позволяет
вносить платежи, редактировать настройки и удалять карты.
"""

import logging
from datetime import date
from decimal import Decimal

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, 
    QTabWidget, QWidget, QLabel, QHeaderView, QMessageBox, 
    QGroupBox, QGridLayout, QProgressBar, QDialog
)
from PySide6.QtCore import Signal, Qt

from ui.dialogs.base_dialog import BaseDialog

logger = logging.getLogger(__name__)


class CreditCardDialog(BaseDialog):
    """
    Главное окно модуля кредитных карт.
    
    Сигналы:
        data_updated: Вызывается при успешном изменении данных (для обновления родительского окна).
    """
    
    data_updated = Signal()

    def __init__(self, parent, presenter):
        """
        Инициализация диалога кредитных карт.
        
        Args:
            parent: родительское окно
            presenter: экземпляр CreditCardPresenter
        """
        super().__init__(parent)
        self.presenter = presenter
        self.current_card_id = None
        
        self.setWindowTitle("Управление кредитными картами")
        self.resize(700, 500)
        
        self._setup_ui()
        self._load_cards()

    def _setup_ui(self):
        """Настраивает интерфейс диалога."""
        # Верхняя панель: выбор карты и кнопки действий
        top_layout = QHBoxLayout()
        
        self.card_combo = QComboBox()
        self.card_combo.currentIndexChanged.connect(self._on_card_changed)
        top_layout.addWidget(QLabel("Карта:"), 1)
        top_layout.addWidget(self.card_combo, 3)
        
        self.btn_settings = QPushButton("️ Настройки")
        self.btn_settings.clicked.connect(self._on_open_settings)
        self.btn_settings.setEnabled(False)
        top_layout.addWidget(self.btn_settings)
        
        self.btn_payment = QPushButton("💳 Внести платёж")
        self.btn_payment.clicked.connect(self._on_make_payment)
        self.btn_payment.setEnabled(False)
        top_layout.addWidget(self.btn_payment)
        
        # self.btn_hide = QPushButton("Скрыть карту")
        # self.btn_hide.clicked.connect(self._on_hide_card)
        # self.btn_hide.setEnabled(False)
        # self.btn_hide.setStyleSheet("QPushButton { color: red; }")
        # top_layout.addWidget(self.btn_hide)
        
        self._main_layout.addLayout(top_layout)
        
        # Вкладки
        self.tabs = QTabWidget()
        self._main_layout.addWidget(self.tabs)

        self._main_layout.addWidget(self.status_bar)
        
        self._setup_dashboard_tab()

    def _setup_dashboard_tab(self):
        """Настраивает вкладку 'Обзор' (Дашборд)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Метрики
        metrics_group = QGroupBox("Финансовые показатели")
        metrics_layout = QGridLayout()
        
        self.lbl_debt = QLabel("0.00 ₽")
        self.lbl_debt.setStyleSheet("font-weight: bold; color: #d32f2f; font-size: 14px;")
        
        self.lbl_limit = QLabel("0.00 ₽")
        self.lbl_limit.setStyleSheet("font-weight: bold; color: #1976d2; font-size: 14px;")
        
        self.lbl_usage_percent = QLabel("0%")
        self.lbl_usage_percent.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%v%")
        
        self.lbl_payment_day = QLabel("-")
        self.lbl_statement_day = QLabel("-")
        self.lbl_annual_rate = QLabel("-")
        
        metrics_layout.addWidget(QLabel("Текущий долг:"), 0, 0)
        metrics_layout.addWidget(self.lbl_debt, 0, 1)
        metrics_layout.addWidget(QLabel("Кредитный лимит:"), 1, 0)
        metrics_layout.addWidget(self.lbl_limit, 1, 1)
        metrics_layout.addWidget(QLabel("Использование лимита:"), 2, 0)
        metrics_layout.addWidget(self.lbl_usage_percent, 2, 1)
        metrics_layout.addWidget(self.progress_bar, 3, 0, 1, 2)
        metrics_layout.addWidget(QLabel("День платежа:"), 4, 0)
        metrics_layout.addWidget(self.lbl_payment_day, 4, 1)
        metrics_layout.addWidget(QLabel("День выписки:"), 5, 0)
        metrics_layout.addWidget(self.lbl_statement_day, 5, 1)
        metrics_layout.addWidget(QLabel("Годовая ставка:"), 6, 0)
        metrics_layout.addWidget(self.lbl_annual_rate, 6, 1)
        
        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)
        
        # Информационный блок
        info_group = QGroupBox("ℹ️ Информация")
        info_layout = QVBoxLayout()
        self.lbl_info = QLabel(
            "Выберите кредитную карту для просмотра информации.\n\n"
            "• Расходы по карте автоматически увеличивают долг.\n"
            "• Платежи уменьшают долг и могут включать проценты/комиссии.\n"
            "• Настройки карты (лимит, ставка, дни) редактируются через кнопку '⚙️ Настройки'."
        )
        self.lbl_info.setWordWrap(True)
        info_layout.addWidget(self.lbl_info)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        layout.addStretch()
        self.tabs.addTab(tab, " Обзор")

    # --- Загрузка данных ---

    def _load_cards(self):
        """Загружает список карт в ComboBox."""
        try:
            self.card_combo.blockSignals(True)
            self.card_combo.clear()
            
            cards = self.presenter.get_cards_list()
            for card in cards:
                self.card_combo.addItem(card["account_name"], card["id"])
                
            if cards:
                self.current_card_id = cards[0]["id"]
                self._enable_card_actions(True)
                self._load_dashboard()
            else:
                self.current_card_id = None
                self._enable_card_actions(False)
                self._clear_dashboard()
                
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка UI при загрузке карт: {e}", exc_info=True)
            self.show_status("Произошла ошибка при загрузке списка карт", "error")
        finally:
            self.card_combo.blockSignals(False)

    def _on_card_changed(self, index):
        """Обрабатывает смену выбранной карты."""
        if index < 0:
            return
            
        self.current_card_id = self.card_combo.currentData()
        if self.current_card_id:
            self._enable_card_actions(True)
            self._load_dashboard()
        else:
            self._enable_card_actions(False)
            self._clear_dashboard()

    def _enable_card_actions(self, enabled: bool):
        """Включает или отключает кнопки действий для карты."""
        self.btn_settings.setEnabled(enabled)
        self.btn_payment.setEnabled(enabled)
        # self.btn_hide.setEnabled(enabled)

    def _load_dashboard(self):
        """Загружает и отображает данные вкладки 'Обзор'."""
        try:
            data = self.presenter.get_card_dashboard(self.current_card_id)
            
            debt = data["debt"]
            limit = data["credit_limit"]
            usage_percent = data["usage_percent"]
            
            self.lbl_debt.setText(self._format_currency(debt))
            self.lbl_limit.setText(self._format_currency(limit) if limit > 0 else "Не установлен")
            self.lbl_usage_percent.setText(f"{usage_percent:.1f}%")
            
            # Прогресс-бар
            if limit > 0:
                self.progress_bar.setValue(int(usage_percent))
                self.progress_bar.setVisible(True)
            else:
                self.progress_bar.setVisible(False)
            
            # Дополнительные поля
            self.lbl_payment_day.setText(str(data["payment_day"]) if data["payment_day"] else "-")
            self.lbl_statement_day.setText(str(data["statement_day"]) if data["statement_day"] else "-")
            self.lbl_annual_rate.setText(f"{data['annual_rate']:.1f}%" if data["annual_rate"] > 0 else "-")
            
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка UI при загрузке дашборда: {e}", exc_info=True)
            self.show_status("Произошла ошибка при загрузке обзора", "error")

    def _clear_dashboard(self):
        """Очищает данные дашборда."""
        self.lbl_debt.setText("0.00 ₽")
        self.lbl_limit.setText("0.00 ₽")
        self.lbl_usage_percent.setText("0%")
        self.progress_bar.setValue(0)
        self.lbl_payment_day.setText("-")
        self.lbl_statement_day.setText("-")
        self.lbl_annual_rate.setText("-")

    # --- Обработчики кнопок ---

    def _on_open_settings(self):
        """Открывает диалог настроек текущей карты."""
        try:
            from ui.dialogs.credit_card_settings_dialog import CreditCardSettingsDialog
            
            # Получаем название счёта
            settings_data = self.presenter.get_card_settings(self.current_card_id)
            account_name = settings_data["account_name"]
            
            dialog = CreditCardSettingsDialog(
                self, 
                self.presenter, 
                self.current_card_id, 
                account_name
            )
            dialog.settings_updated.connect(self._load_dashboard)
            
            if dialog.exec() == QDialog.Accepted:
                self.show_status("Настройки карты успешно обновлены", "success")
                self._load_cards()  # Перезагружаем список (на случай, если изменилось название счёта)
                self.data_updated.emit()
                
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка UI при открытии настроек: {e}", exc_info=True)
            self.show_status("Произошла ошибка при открытии настроек", "error")

    def _on_make_payment(self):
        """Открывает диалог внесения платежа."""
        try:
            from ui.dialogs.credit_card_payment_dialog import CreditCardPaymentDialog
            
            # Получаем данные карты
            dashboard_data = self.presenter.get_card_dashboard(self.current_card_id)
            card_name = dashboard_data["account_name"]
            current_debt = dashboard_data["debt"]
            
            # Находим account_id текущей карты
            cards = self.presenter.get_cards_list()
            current_card = next((c for c in cards if c["id"] == self.current_card_id), None)
            if not current_card:
                raise ValueError("Данные текущей карты не найдены")
            
            dialog = CreditCardPaymentDialog(
                self, 
                self.presenter, 
                self.current_card_id, 
                card_name,
                current_card["account_id"],
                current_debt
            )
            dialog.payment_made.connect(self._load_dashboard)
            
            if dialog.exec() == QDialog.Accepted:
                self.show_status("Платёж успешно внесён", "success")
                self._load_dashboard()
                self.data_updated.emit()
                
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка UI при открытии диалога платежа: {e}", exc_info=True)
            self.show_status("Произошла ошибка при открытии диалога платежа", "error")

    def _on_hide_card(self):
        """Скрывает из UI текущую карту."""
        try:
            card_name = self.card_combo.currentText()
            reply = QMessageBox.question(
                self, 
                "Подтверждение удаления", 
                f"Вы уверены, что хотите скрыть карту '{card_name}'?\n"
                f"Счёт и все транзакции останутся без изменений.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.presenter.hide_card(self.current_card_id)
                self.show_status(f"Карта '{card_name}' скрыта", "success")
                self._load_cards()
                self.data_updated.emit()
                
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка UI при скрытии карты: {e}", exc_info=True)
            self.show_error("Произошла ошибка при скрытии карты")

    # --- Хелперы ---

    def _format_currency(self, value) -> str:
        """Форматирует число в строку с валютой."""
        try:
            return f"{value:,.2f} ₽".replace(",", " ")
        except (ValueError, TypeError):
            return "0.00 ₽"