"""
Основной диалог управления кредитной картой.
Отображает задолженность, периоды, минимальный платёж (как в приложении банка).
Архитектура MVP: наследование от BaseDialog, работа через презентер.
"""
from typing import List, Dict
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDateEdit, QLineEdit, QFormLayout, QMessageBox,
    QFrame, QTabWidget, QWidget, QProgressBar
)
from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QFont
from ui.dialogs.base_dialog import BaseDialog
from ui.widgets.colored_button import CompactButton



class CreditCardDialog(BaseDialog):
    """Основной диалог управления кредитной картой."""

    def __init__(self, parent=None, presenter=None, card_id: int = None, account_id: int = None):
        """
        Инициализация диалога.
        
        Args:
            parent: родительское окно
            presenter: экземпляр CreditCardPresenter
            card_id: ID из таблицы credit_cards
            account_id: ID счёта в таблице accounts
        """
        super().__init__(parent)
        self.presenter = presenter
        self.card_id = card_id
        self.account_id = account_id
        
        self.setWindowTitle("Кредитная карта beta")
        self.resize(900, 700)
        
        self._init_ui()
        
        if self.presenter and self.card_id and self.account_id:
            self.presenter.set_current_card(self.card_id, self.account_id)
            self.presenter.set_view(self)

    def _init_ui(self):
        """Инициализация интерфейса."""
        # Используем layout из BaseDialog
        self._main_layout.setSpacing(10)
        
        # === Заголовок ===
        header_frame = QFrame()
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        self.card_name_label = QLabel("Сбер Молодёжная")
        self.card_name_label.setFont(QFont("Arial", 16, QFont.Bold))
        header_layout.addWidget(self.card_name_label)
        
        header_layout.addStretch()
        
        # Кнопака настроек  карты
        self.settings_btn = CompactButton("Настройки")
        self.settings_btn.clicked.connect(self._on_settings_card)
        header_layout.addWidget(self.settings_btn)

        # Кнопка внесения платежа
        self.payment_btn = CompactButton("💳 Внести платёж")
        self.payment_btn.clicked.connect(self._open_payment_dialog)
        header_layout.addWidget(self.payment_btn)

        self.delete_card_btn = CompactButton("🗑️ Удалить карту")
        self.delete_card_btn.clicked.connect(self._on_delete_card)
        header_layout.addWidget(self.delete_card_btn)

        self._main_layout.addWidget(header_frame)
        
        # === Блок общей задолженности ===
        debt_frame = QFrame()
        debt_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        debt_layout = QVBoxLayout(debt_frame)
        
        self.total_debt_label = QLabel("Вся задолженность: 0.00 ₽")
        self.total_debt_label.setFont(QFont("Arial", 20, QFont.Bold))
        self.total_debt_label.setStyleSheet("color: #dc3545;")
        debt_layout.addWidget(self.total_debt_label)
        
        self.debt_hint_label = QLabel("Если внести эту сумму, то полностью погасите задолженность")
        self.debt_hint_label.setStyleSheet("color: #6c757d; font-size: 9pt;")
        debt_layout.addWidget(self.debt_hint_label)
        
        # Блок с советом (как в банке: "Чтобы перестали начисляться проценты...")
        self.advice_frame = QFrame()
        self.advice_frame.setStyleSheet("""
            QFrame {
                background-color: #1e3a5f;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        advice_layout = QHBoxLayout(self.advice_frame)
        
        bulb_label = QLabel("💡")
        bulb_label.setFont(QFont("Arial", 24))
        advice_layout.addWidget(bulb_label)
        
        self.advice_label = QLabel("Чтобы перестали начисляться проценты, внесите 0.00 ₽")
        self.advice_label.setStyleSheet("color: white; font-weight: bold;")
        self.advice_label.setWordWrap(True)
        advice_layout.addWidget(self.advice_label)
        
        debt_layout.addWidget(self.advice_frame)
        
        self._main_layout.addWidget(debt_frame)
        
        # === Табы: Детализация и Периоды ===
        tabs = QTabWidget()
        
        # Вкладка 1: Детализация задолженности
        details_widget = QWidget()
        details_layout = QVBoxLayout(details_widget)
        
        # Основной долг
        self.principal_group = QGroupBox("Основной долг")
        self.principal_layout = QFormLayout()
        self.principal_label = QLabel("0.00 ₽")
        self.principal_label.setStyleSheet("font-weight: bold; color: #28a745;")
        self.principal_layout.addRow("", self.principal_label)
        self.principal_group.setLayout(self.principal_layout)
        details_layout.addWidget(self.principal_group)
        
        # Проценты
        self.interest_group = QGroupBox("Начисленные проценты")
        self.interest_layout = QFormLayout()
        self.interest_retro_label = QLabel("Ретроактивные: 0.00 ₽")
        self.interest_daily_label = QLabel("Ежедневные: 0.00 ₽")
        self.interest_layout.addRow(self.interest_retro_label)
        self.interest_layout.addRow(self.interest_daily_label)
        self.interest_group.setLayout(self.interest_layout)
        details_layout.addWidget(self.interest_group)
        
        # Минимальный платёж
        self.min_payment_group = QGroupBox("Минимальный платёж")
        self.min_payment_layout = QFormLayout()
        self.min_payment_label = QLabel("0.00 ₽")
        self.min_payment_label.setStyleSheet("font-weight: bold; color: #007bff; font-size: 14pt;")
        self.min_payment_layout.addRow("Обязательный платёж:", self.min_payment_label)
        self.min_payment_group.setLayout(self.min_payment_layout)
        details_layout.addWidget(self.min_payment_group)
        
        details_layout.addStretch()
        tabs.addTab(details_widget, "📊 Детализация")
        
        # Вкладка 2: Периоды
        periods_widget = QWidget()
        periods_layout = QVBoxLayout(periods_widget)
        
        self.periods_table = QTableWidget()
        self.periods_table.setColumnCount(7)
        self.periods_table.setHorizontalHeaderLabels([
            "Период", "Покупки", "Переводы", "Льгота до", "Погашено", "Проценты", "Статус"
        ])
        
        # Настройка колонок
        header = self.periods_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Период
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Покупки
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Переводы
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Льгота до
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Погашено
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Проценты
        header.setSectionResizeMode(6, QHeaderView.Stretch)           # Статус
        
        self.periods_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.periods_table.setSelectionMode(QTableWidget.SingleSelection)
        self.periods_table.setAlternatingRowColors(True)
        self.periods_table.verticalHeader().setVisible(False)
        
        periods_layout.addWidget(self.periods_table)
        tabs.addTab(periods_widget, "📅 Периоды")
        
        self._main_layout.addWidget(tabs, 1)
        
        # === Кнопка закрытия ===
        close_btn = CompactButton("Закрыть")
        close_btn.clicked.connect(self.reject)
        self._main_layout.addWidget(close_btn)

    def _open_payment_dialog(self):
        """Открывает диалог внесения платежа."""
        if self.presenter:
            self.presenter._open_payment_dialog()
        
    def _on_delete_card(self):
        """Обработчик нажатия кнопки 'Удалить карту'."""
        from PySide6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self,
            "Удаление карты",
            "Вы уверены, что хотите удалить эту кредитную карту?\n\n"
            "Все данные о периодах и платежах будут удалены безвозвратно.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes and self.presenter:
            self.presenter.delete_card()

    def _on_settings_card(self):
        """Открывает диалог настроек кредитной карты."""
        if self.presenter:
            self.presenter.open_settings_dialog()

    # =================== Контракт View <-> Presenter ===================

    def populate_card_info(self, card_data: Dict):
        """
        Заполняет информацию о карте.
        
        Args:
            card_data: {id, name, annual_rate, grace_months, min_payment_percent}
        """
        self.card_name_label.setText(card_data.get("name", "Кредитная карта"))

    def populate_periods(self, periods: List[Dict]):
        """
        Заполняет таблицу периодов.
        
        Args:
            periods: список словарей с данными периодов
        """
        self.periods_table.setRowCount(0)
        
        for i, period in enumerate(periods):
            self.periods_table.insertRow(i)
            
            # Период
            period_item = QTableWidgetItem(period.get("period_month", ""))
            self.periods_table.setItem(i, 0, period_item)
            
            # Покупки
            purchases = period.get("total_purchases", 0)
            self.periods_table.setItem(i, 1, QTableWidgetItem(f"{purchases:,.2f} ₽"))
            
            # Переводы
            transfers = period.get("total_transfers", 0)
            self.periods_table.setItem(i, 2, QTableWidgetItem(f"{transfers:,.2f} ₽"))
            
            # Льгота до
            grace_end = period.get("grace_period_end", "")
            self.periods_table.setItem(i, 3, QTableWidgetItem(grace_end))
            
            # Погашено
            paid = period.get("paid_amount", 0)
            self.periods_table.setItem(i, 4, QTableWidgetItem(f"{paid:,.2f} ₽"))
            
            # Проценты
            interest = period.get("total_interest", 0)
            self.periods_table.setItem(i, 5, QTableWidgetItem(f"{interest:,.2f} ₽"))
            
            # Статус
            is_paid = period.get("is_paid", False)
            status = "✅ Погашено" if is_paid else "⏳ Активен"
            status_item = QTableWidgetItem(status)
            if not is_paid:
                status_item.setForeground(Qt.red)
            self.periods_table.setItem(i, 6, status_item)

    def populate_debt_summary(self, min_payment: Dict, full_payoff: Dict):
        """
        Заполняет сводку по задолженности.
        
        Args:
            min_payment: {min_payment, principal_part, interest_part, total_debt, ...}
            full_payoff: {total, principal, interest_retroactive, interest_daily}
        """
        # Общая задолженность
        total_deft = full_payoff.get("total", 0)
        self.total_debt_label.setText(f"Вся задолженность: {total_deft:,.2f} ₽")
        
        # Основной долг
        principal = full_payoff.get("principal", 0)
        self.principal_label.setText(f"{principal:,.2f} ₽")
        
        # Проценты
        interest_retro = full_payoff.get("interest_retroactive", 0)
        interest_daily = full_payoff.get("interest_daily", 0)
        self.interest_retro_label.setText(f"Ретроактивные: {interest_retro:,.2f} ₽")
        self.interest_daily_label.setText(f"Ежедневные: {interest_daily:,.2f} ₽")
        
        # Минимальный платёж
        min_pay = min_payment.get("min_payment", 0)
        self.min_payment_label.setText(f"{min_pay:,.2f} ₽")
        
        # Совет (как в банке)
        if interest_retro > 0 or interest_daily > 0:
            self.advice_label.setText(
                f"Чтобы перестали начисляться проценты, внесите {interest_retro + interest_daily:,.2f} ₽"
            )
            self.advice_frame.setVisible(True)
        else:
            self.advice_frame.setVisible(False)

    def populate_accounts_for_payment(self, accounts: List[Dict]):
        """
        Заполняет список счетов для платежа (используется в payment_dialog).
        Этот метод может быть вызван из payment_dialog через presenter.
        
        Args:
            accounts: список {id, name, current_balance}
        """
        pass  # Реализуется в CreditCardPaymentDialog