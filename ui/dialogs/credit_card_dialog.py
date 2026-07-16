"""
Главный диалог управления кредитными картами (CreditCardDialog).

Отображает дашборд, список траншей и историю выписок.
Связывает действия пользователя с CreditCardPresenter.
"""

import logging
from datetime import date
from decimal import Decimal

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, 
    QTabWidget, QWidget, QLabel, QTableWidget, QTableWidgetItem,
    QListWidget, QHeaderView, QMessageBox, QGroupBox, QGridLayout, QDialog
)
from PySide6.QtCore import Qt, Signal

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
        self.resize(800, 600)
        
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
        
        self.btn_add_card = QPushButton("➕ Добавить карту")
        self.btn_add_card.clicked.connect(self._on_add_card)
        top_layout.addWidget(self.btn_add_card)
        
        self.btn_settings = QPushButton("⚙️ Настройки")
        self.btn_settings.clicked.connect(self._on_open_settings)
        self.btn_settings.setEnabled(False)
        top_layout.addWidget(self.btn_settings)
        
        self.btn_payment = QPushButton("💳 Внести платёж")
        self.btn_payment.clicked.connect(self._on_make_payment)
        self.btn_payment.setEnabled(False)
        top_layout.addWidget(self.btn_payment)

        self.btn_recalc = QPushButton("🔄 Пересчитать %")
        self.btn_recalc.clicked.connect(self._on_recalculate_interest)
        self.btn_recalc.setEnabled(False)
        top_layout.addWidget(self.btn_recalc)
        
        self.btn_delete = QPushButton("🗑️ Удалить")
        self.btn_delete.clicked.connect(self._on_delete_card)
        self.btn_delete.setEnabled(False)
        self.btn_delete.setStyleSheet("QPushButton { color: red; }")
        top_layout.addWidget(self.btn_delete)
        
        self._main_layout.addLayout(top_layout)
        
        # Вкладки
        self.tabs = QTabWidget()
        self._main_layout.addWidget(self.tabs)
        
        self._setup_dashboard_tab()
        self._setup_tranches_tab()
        self._setup_statements_tab()

        #  Строка статуса
        self._main_layout.addWidget(self.status_bar)

    def _setup_dashboard_tab(self):
        """Настраивает вкладку 'Обзор' (Дашборд)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Метрики
        metrics_group = QGroupBox("Финансовые показатели")
        metrics_layout = QGridLayout()
        
        self.lbl_total_debt = QLabel("0.00 ₽")
        self.lbl_available_limit = QLabel("0.00 ₽")
        self.lbl_burn_rate = QLabel("0.00 ₽/день")
        self.lbl_min_payment = QLabel("0.00 ₽")
        
        metrics_layout.addWidget(QLabel("Общий долг:"), 0, 0)
        metrics_layout.addWidget(self.lbl_total_debt, 0, 1)
        metrics_layout.addWidget(QLabel("Доступный лимит:"), 1, 0)
        metrics_layout.addWidget(self.lbl_available_limit, 1, 1)
        metrics_layout.addWidget(QLabel("Стоимость дня (Burn Rate):"), 2, 0)
        metrics_layout.addWidget(self.lbl_burn_rate, 2, 1)
        metrics_layout.addWidget(QLabel("Мин. платёж до конца месяца:"), 3, 0)
        metrics_layout.addWidget(self.lbl_min_payment, 3, 1)
        
        metrics_group.setLayout(metrics_layout)
        layout.addWidget(metrics_group)
        
        # Алерты Grace Saver
        alerts_group = QGroupBox("⚠️ Спасение грейс-периода")
        alerts_layout = QVBoxLayout()
        self.lst_alerts = QListWidget()
        self.lst_alerts.setAlternatingRowColors(True)
        alerts_layout.addWidget(self.lst_alerts)
        alerts_group.setLayout(alerts_layout)
        layout.addWidget(alerts_group)
        
        self.tabs.addTab(tab, "📊 Обзор")

    def _setup_tranches_tab(self):
        """Настраивает вкладку 'Транши'."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.tbl_tranches = QTableWidget()
        self.tbl_tranches.setColumnCount(7)
        self.tbl_tranches.setHorizontalHeaderLabels([
            "Дата", "Тип", "Сумма", "Остаток", "Комиссия", "Конец грейса", "Статус"
        ])
        self.tbl_tranches.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_tranches.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.tbl_tranches)
        self.tabs.addTab(tab, "📦 Транши")

    def _setup_statements_tab(self):
        """Настраивает вкладку 'Выписки'."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.tbl_statements = QTableWidget()
        self.tbl_statements.setColumnCount(5)
        self.tbl_statements.setHorizontalHeaderLabels([
            "Дата выписки", "Дата платежа", "Закрывающий баланс", "Мин. платёж", "Статус"
        ])
        self.tbl_statements.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tbl_statements.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.tbl_statements)
        self.tabs.addTab(tab, "📄 Выписки")

    # --- Загрузка данных ---

    def _load_cards(self):
        """Загружает список карт в ComboBox."""
        try:
            self.card_combo.blockSignals(True)
            self.card_combo.clear()
            
            credit_cards = self.presenter.get_cards_list()

            if not credit_cards:
                self.card_combo.addItem("Нет доступных карт", None)
                self.card_combo.setEnabled(False)
                return
            
            for card in credit_cards:
                self.card_combo.addItem(card["name"], card["id"])
                
            if credit_cards:
                self.current_card_id = credit_cards[0]["id"]
                self._enable_card_actions(True)
                self._load_dashboard()
                self._load_tranches()
                self._load_statements()
            else:
                self.current_card_id = None
                self._enable_card_actions(False)
                
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при загрузке карт: {e}", exc_info=True)
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
            self._load_tranches()
            self._load_statements()

    def _enable_card_actions(self, enabled: bool):
        """Включает или отключает кнопки действий для карты."""
        self.btn_settings.setEnabled(enabled)
        self.btn_payment.setEnabled(enabled)
        self.btn_recalc.setEnabled(enabled)
        self.btn_delete.setEnabled(enabled)

    def _load_dashboard(self):
        """Загружает и отображает данные вкладки 'Обзор'."""
        try:
            data = self.presenter.get_dashboard_data(self.current_card_id)
            
            metrics = data["metrics"]
            self.lbl_total_debt.setText(self._format_currency(metrics["total_debt"]))
            self.lbl_available_limit.setText(self._format_currency(metrics["available_limit"]))
            self.lbl_burn_rate.setText(f"{self._format_currency(metrics['burn_rate'])} / день")
            self.lbl_min_payment.setText(self._format_currency(metrics["min_payment"]))
            
            self.lst_alerts.clear()
            for alert in data.get("grace_alerts", []):
                text = (
                    f"Транш ID {alert['tranche_id']}: {self._format_currency(alert['amount'])} ₽. "
                    f"Осталось {alert['days_left']} дн. (до {alert['grace_end_date']}). "
                    f"Цена ошибки: ~{self._format_currency(alert['retroactive_cost'])} ₽"
                )
                self.lst_alerts.addItem(text)
                
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при загрузке дашборда: {e}", exc_info=True)
            self.show_status("Произошла ошибка при загрузке обзора", "error")

    def _load_tranches(self):
        """Загружает и отображает список траншей."""
        try:
            tranches = self.presenter.get_tranches(self.current_card_id)
            self.tbl_tranches.setRowCount(len(tranches))
            
            for row, t in enumerate(tranches):
                self.tbl_tranches.setItem(row, 0, QTableWidgetItem(t["transaction_date"]))
                self.tbl_tranches.setItem(row, 1, QTableWidgetItem(self._translate_tranche_type(t["type"])))
                self.tbl_tranches.setItem(row, 2, QTableWidgetItem(self._format_currency(t["original_amount"])))
                self.tbl_tranches.setItem(row, 3, QTableWidgetItem(self._format_currency(t["remaining_amount"])))
                self.tbl_tranches.setItem(row, 4, QTableWidgetItem(self._format_currency(t["commission"])))
                self.tbl_tranches.setItem(row, 5, QTableWidgetItem(t["grace_end_date"] or "-"))
                self.tbl_tranches.setItem(row, 6, QTableWidgetItem(self._translate_status(t["status"])))
                
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при загрузке траншей: {e}", exc_info=True)
            self.show_status("Произошла ошибка при загрузке траншей", "error")

    def _load_statements(self):
        """Загружает и отображает историю выписок."""
        try:
            statements = self.presenter.get_statements(self.current_card_id)
            self.tbl_statements.setRowCount(len(statements))
            
            for row, s in enumerate(statements):
                self.tbl_statements.setItem(row, 0, QTableWidgetItem(s["statement_date"]))
                self.tbl_statements.setItem(row, 1, QTableWidgetItem(s["due_date"] or "-"))
                self.tbl_statements.setItem(row, 2, QTableWidgetItem(self._format_currency(s["closing_balance"])))
                self.tbl_statements.setItem(row, 3, QTableWidgetItem(self._format_currency(s["min_payment_required"])))
                self.tbl_statements.setItem(row, 4, QTableWidgetItem(self._translate_status(s["status"])))
                
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при загрузке выписок: {e}", exc_info=True)
            self.show_status("Произошла ошибка при загрузке выписок", "error")

    # --- Обработчики кнопок ---

    def _on_add_card(self):
        """Открывает диалог создания новой карты."""
        try:
            from ui.dialogs.credit_card_create_dialog import CreditCardCreateDialog
            
            dialog = CreditCardCreateDialog(self, self.presenter)
            dialog.card_created.connect(self._load_cards) # Перезагрузить список после создания
            
            # TODO: если нажал OK но нет достпунх счето (счет не выбран) то выдавть ошибку выберете счет
            if dialog.exec() == QDialog.Accepted:
                self.show_status("Карта успешно создана", "success")
                self.data_updated.emit()
                
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при открытии диалога создания: {e}", exc_info=True)
            self.show_status("Произошла ошибка", "error")

    def _on_open_settings(self):
        """Открывает диалог настроек текущей карты."""
        try:
            # TODO: Реализовать вызов CreditCardSettingsDialog
            # После закрытия диалога настроек:
            self.show_status("Настройки сохранены (заглушка)", "success")
            self._load_cards() # Перезагрузить, если изменилось название
            self.data_updated.emit()
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при открытии настроек: {e}", exc_info=True)
            self.show_status("Произошла ошибка при сохранении настроек", "error")

    def _on_make_payment(self):
        """Открывает диалог внесения платежа."""
        try:
            # TODO: Реализовать вызов CreditCardPaymentDialog
            # После успешного платежа:
            self.show_status("Платёж внесён (заглушка)", "success")
            self._load_dashboard()
            self._load_tranches()
            self.data_updated.emit()
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при внесении платежа: {e}", exc_info=True)
            self.show_status("Произошла ошибка при внесении платежа", "error")

    def _on_recalculate_interest(self):
        """Вручную пересчитывает проценты на текущую дату."""
        try:
            today_str = date.today().isoformat()
            result = self.presenter.recalculate_interest(self.current_card_id, today_str)
            
            if result:
                self.show_status(f"Проценты пересчитаны. Затронуто траншей: {len(result)}", "success")
            else:
                self.show_status("Нечего пересчитывать (нет активных траншей вне грейса)", "info")
                
            self._load_dashboard()
            self._load_tranches()
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при пересчёте процентов: {e}", exc_info=True)
            self.show_status("Произошла ошибка при пересчёте процентов", "error")

    def _on_delete_card(self):
        """Мягко удаляет текущую карту."""
        try:
            card_name = self.card_combo.currentText()
            reply = QMessageBox.question(
                self, 
                "Подтверждение удаления", 
                f"Вы уверены, что хотите удалить карту '{card_name}'?\n"
                f"Все транши и история выписок будут удалены.",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.presenter.delete_card(self.current_card_id)
                self.show_status(f"Карта '{card_name}' удалена", "success")
                self._load_cards()
                self.data_updated.emit()
                
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI при удалении карты: {e}", exc_info=True)
            self.show_status("Произошла ошибка при удалении карты", "error")

    # --- Хелперы ---

    def _format_currency(self, value) -> str:
        """Форматирует число в строку с валютой."""
        try:
            return f"{value:,.2f} ₽".replace(",", " ")
        except (ValueError, TypeError):
            return "0.00 ₽"

    def _translate_tranche_type(self, tranche_type: str) -> str:
        """Переводит тип транша на русский."""
        types = {
            "purchase": "Покупка",
            "transfer": "Перевод",
            "refund": "Возврат"
        }
        return types.get(tranche_type, tranche_type)

    def _translate_status(self, status: str) -> str:
        """Переводит статус на русский."""
        statuses = {
            "in_grace": "В грейсе",
            "grace_expired": "Грейс истёк",
            "partial": "Частично погашен",
            "paid": "Погашен",
            "open": "Открыта",
            "closed": "Закрыта",
            "overdue": "Просрочена"
        }
        return statuses.get(status, status)