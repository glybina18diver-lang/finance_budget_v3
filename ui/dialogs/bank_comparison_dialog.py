import logging
import traceback
import calendar
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDateEdit, QMessageBox, QComboBox, QFrame, QWidget
)
from PySide6.QtCore import QDate
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from ui.widgets.buttons import CompactButton
from ui.styles.theme_manager import ThemeManager

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
        """Инициализирует UI элементы и компоновку.

        Интерфейс собирается из трёх блоков: фильтры, карточки сводки
        и круговая диаграмма. Всё оформление — через глобальную тему (QSS).
        """
        try:
            main_layout = QVBoxLayout(self)
            main_layout.setSpacing(10)
            main_layout.setContentsMargins(12, 12, 12, 12)

            main_layout.addLayout(self._create_filters_panel())

            content_layout = QHBoxLayout()
            content_layout.setSpacing(10)
            content_layout.addLayout(self._create_summary_panel(), 3)
            content_layout.addWidget(self._create_chart_panel(), 2)
            main_layout.addLayout(content_layout, 1)

            self.btn_load.clicked.connect(self._on_load_clicked)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise


    def _create_filters_panel(self) -> QHBoxLayout:
        """Создаёт панель фильтров: счёт, месяц, год и кнопка загрузки.

        Returns:
            Готовый QHBoxLayout для добавления в основной layout
        """
        try:
            filter_layout = QHBoxLayout()
            filter_layout.setSpacing(8)

            filter_layout.addWidget(QLabel("Счет:"))
            self.combo_account = QComboBox()
            self.combo_account.addItem("", userData=None)
            filter_layout.addWidget(self.combo_account)

            filter_layout.addWidget(QLabel("Месяц:"))
            self.combo_month = QComboBox()
            self.combo_month.addItems(self.MONTHS)
            self.combo_month.setCurrentIndex(datetime.now().month - 1)
            filter_layout.addWidget(self.combo_month)

            filter_layout.addWidget(QLabel("Год:"))
            self.combo_year = QComboBox()
            current_year = datetime.now().year
            # Годы от 2000 до текущего (по убыванию, чтобы текущий был первым)
            self.combo_year.addItems([str(y) for y in range(current_year, 1999, -1)])
            filter_layout.addWidget(self.combo_year)

            self.btn_load = CompactButton("Загрузить сводку", "info")
            filter_layout.addWidget(self.btn_load)
            filter_layout.addStretch(1)

            return filter_layout
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise


    def _create_summary_panel(self) -> QVBoxLayout:
        """Создаёт левую панель с карточками сводки на QFrame.

        Карточки: «Поступления», «Списания», «Итог за период».
        Цвета значений приходят из темы через variant-селекторы.

        Returns:
            QVBoxLayout с тремя карточками
        """
        try:
            summary_layout = QVBoxLayout()
            summary_layout.setSpacing(10)

            # --- Поступления ---
            income_card, income_content = self._create_card("Поступления", "accent-success")
            self.lbl_total_in = self._add_summary_row(income_content, "Всего поступлений:", "value-success")
            self.lbl_transfers_in = self._add_summary_row(income_content, "Переводы (+):", "card-value")
            self.lbl_refunds = self._add_summary_row(income_content, "Возвраты:", "card-value")
            summary_layout.addWidget(income_card)

            # --- Списания ---
            expense_card, expense_content = self._create_card("Списания", "accent-danger")
            self.lbl_total_out = self._add_summary_row(expense_content, "Всего списаний:", "value-danger")
            self.lbl_expenses = self._add_summary_row(expense_content, "Расходы:", "value-danger")
            self.lbl_transfers_out = self._add_summary_row(expense_content, "Переводы (-):", "value-danger")
            summary_layout.addWidget(expense_card)

            # --- Итог за период ---
            total_card, total_content = self._create_card("Итог за период")
            self.lbl_total = QLabel("+0 ₽")
            self.lbl_total.setProperty("variant", "total-positive")
            self.lbl_total.setAlignment(Qt.AlignCenter)
            total_content.addWidget(self.lbl_total)
            summary_layout.addWidget(total_card)

            summary_layout.addStretch(1)
            return summary_layout
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise


    def _create_chart_panel(self) -> QFrame:
        """Создаёт правую панель с круговой диаграммой (donut).

        Диаграмма рисуется matplotlib цветами активной темы.

        Returns:
            QFrame-контейнер для диаграммы
        """
        try:
            card = QFrame()
            card.setProperty("variant", "chart_card")

            layout = QVBoxLayout(card)
            layout.setContentsMargins(8, 8, 8, 8)

            self.chart_widget = QWidget()
            self.chart_layout = QVBoxLayout(self.chart_widget)
            self.chart_layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.chart_widget, 1)

            self.figure = None
            self.canvas = None
            return card
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    # Хелперы карточек
    def _create_card(self, title: str, accent: str = None):
        """Создаёт карточку сводки на QFrame со стилем из темы.

        Args:
            title: заголовок карточки
            accent: вариант акцентной полосы ('accent-success'/'accent-danger') или None

        Returns:
            Кортеж (card: QFrame, content: QVBoxLayout для строк)
        """
        try:
            card = QFrame()
            card.setProperty("variant", "card")

            card_layout = QHBoxLayout(card)
            card_layout.setSpacing(10)
            card_layout.setContentsMargins(10, 10, 10, 10)

            if accent:
                bar = QFrame()
                bar.setProperty("variant", accent)
                bar.setFixedWidth(8)
                card_layout.addWidget(bar)

            content = QVBoxLayout()
            content.setSpacing(4)
            title_label = QLabel(title)
            title_label.setProperty("variant", "card-title")
            content.addWidget(title_label)
            card_layout.addLayout(content, 1)

            return card, content
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise


    def _add_summary_row(self, layout, caption: str, variant: str) -> QLabel:
        """Добавляет строку «подпись + значение» в карточку.

        Args:
            layout: контент-layout карточки
            caption: текст подписи
            variant: QSS-вариант цвета значения

        Returns:
            QLabel значения для динамического обновления
        """
        try:
            row = QHBoxLayout()
            row.setSpacing(6)
            row.addWidget(QLabel(caption))

            value_label = QLabel("0 ₽")
            value_label.setProperty("variant", variant)
            row.addWidget(value_label)
            row.addStretch(1)

            layout.addLayout(row)
            return value_label
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    # Диаграмма и динамический итог
    def _render_donut(self, totals: dict):
        """Рисует кольцевую диаграмму цветами активной темы.

        Args:
            totals: словарь {'метка': сумма}, например {'Расходы': 25000.0}
        """
        try:
            self._clear_chart()
            theme = ThemeManager.current()
            palette = [
                theme.get("SUCCESS", "#2EA44F"),
                theme.get("DANGER", "#DE4139"),
                theme.get("ACCENT_PRIMARY", "#2E90E0"),
                theme.get("WARNING", "#F29B31"),
                theme.get("ENTITY_CATEGORIES", "#9C27B0"),
            ]

            labels = [k for k, v in totals.items() if v > 0]
            values = [v for v in totals.values() if v > 0]
            if not values:
                return

            face = theme.get("BG_ELEVATED", "#2A3641")
            self.figure = Figure(figsize=(5, 5), dpi=80, facecolor=face)
            self.canvas = FigureCanvas(self.figure)
            ax = self.figure.add_subplot(111)
            ax.set_facecolor(face)

            wedges, _ = ax.pie(
                values,
                colors=palette[:len(values)],
                wedgeprops=dict(width=0.4, edgecolor=face, linewidth=3),
                startangle=90,
                counterclock=False,
            )
            ax.legend(
                wedges, labels,
                loc="lower center", fontsize=9, frameon=False, ncol=min(len(labels), 3),
                labelcolor=theme.get("TEXT_PRIMARY", "#E8ECEF"),
            )
            self.figure.subplots_adjust(left=0.05, right=0.95, top=0.95, bottom=0.12)

            self.chart_layout.addWidget(self.canvas)
            self.canvas.draw()
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise


    def _clear_chart(self):
        """Очищает диаграмму и освобождает ресурсы matplotlib."""
        try:
            if self.canvas:
                self.chart_layout.removeWidget(self.canvas)
                self.canvas.deleteLater()
                self.canvas = None
            if self.figure:
                import matplotlib.pyplot as plt
                plt.close(self.figure)
                self.figure = None
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise


    def _update_total(self, total: float):
        """Обновляет итог за период с цветом по знаку суммы.

        Args:
            total: итоговая сумма (может быть отрицательной)
        """
        try:
            sign = "+" if total >= 0 else "-"
            self.lbl_total.setText(f"{sign}{abs(total):,.0f} ₽")

            self.lbl_total.setProperty(
                "variant", "total-positive" if total >= 0 else "total-negative"
            )
            self.lbl_total.style().unpolish(self.lbl_total)
            self.lbl_total.style().polish(self.lbl_total)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

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
        """Обновляет метки карточек, итог за период и круговую диаграмму.

        В метки значений пишутся только суммы — подписи строк статичны
        и создаются один раз в _create_summary_panel.

        Args:
            summary_data: словарь с агрегированными данными:
                income, expenses, transfers_in, transfers_out,
                refunds, total_in, total_out
        """
        try:
            income = float(summary_data.get("income", 0))
            expenses = float(summary_data.get("expenses", 0))
            transfers_in = float(summary_data.get("transfers_in", 0))
            transfers_out = float(summary_data.get("transfers_out", 0))
            refunds = float(summary_data.get("refunds", 0))
            total_in = float(summary_data.get("total_in", 0))
            total_out = float(summary_data.get("total_out", 0))

            # --- Карточка «Поступления» ---
            self.lbl_total_in.setText(f"{total_in:,.2f} ₽")
            self.lbl_transfers_in.setText(f"{transfers_in:,.2f} ₽")
            self.lbl_refunds.setText(f"{refunds:,.2f} ₽")

            # --- Карточка «Списания» ---
            self.lbl_total_out.setText(f"{total_out:,.2f} ₽")
            self.lbl_expenses.setText(f"{expenses:,.2f} ₽")
            self.lbl_transfers_out.setText(f"{transfers_out:,.2f} ₽")

            # --- Итог за период (цвет переключается по знаку) ---
            self._update_total(total_in - total_out)

            # --- Круговая диаграмма: структура движений ---
            self._render_donut({
                "Доходы": income,
                "Расходы": expenses,
                "Переводы (+)": transfers_in,
                "Переводы (-)": transfers_out,
                "Возвраты": refunds,
            })
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            self.show_status("Некорректные данные сводки", "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
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