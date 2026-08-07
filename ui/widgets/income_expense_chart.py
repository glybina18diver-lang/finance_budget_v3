# ui/widgets/income_expense_chart.py
"""График доходов/расходов и остатка."""
import logging
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PySide6.QtWidgets import (QFrame, QVBoxLayout, QHBoxLayout, QLabel,
                               QComboBox, QWidget, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QTimer

from ui.styles.theme_manager import ThemeManager
from ui.widgets.buttons import CompactButton

logger = logging.getLogger(__name__)


class IncomeExpenseChart(QFrame):
    """График доходов, расходов и накопленного баланса по месяцам.

    Оформление берётся из глобальной темы (QSS + ThemeManager).
    Размеры не фиксируются — виджет растягивается под выделенное место
    и ДОЛЖЕН корректно отображается от ~630x300 до удвоенного размера.
    """

    data_updated = Signal()

    def __init__(self, parent=None, db_manager=None):
        """Инициализация виджета графика.

        Args:
            parent: родительский виджет
            db_manager: фасад базы данных для получения сводок
        """
        try:
            super().__init__(parent)
            self.db = db_manager
            self.current_year = datetime.now().year
            self.figure = None
            self.canvas = None
            self.ax = None

            # Рамка и фон — из темы, вместо setFrameStyle
            self.setProperty("variant", "panel")

            self._setup_ui()
            self._setup_connections()
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def _setup_ui(self):
        """Собирает интерфейс без фиксированных размеров."""
        try:
            main_layout = QVBoxLayout(self)
            main_layout.setSpacing(5)
            main_layout.setContentsMargins(8, 8, 8, 8)

            # === Шапка: заголовок + год + обновление ===
            header_widget = QWidget()
            header_layout = QHBoxLayout(header_widget)
            header_layout.setContentsMargins(0, 0, 0, 0)

            title_label = QLabel("📈 Динамика доходов/расходов")
            title_label.setProperty("variant", "header")
            # Заголовок может сжиматься/растягиваться — не ломает узкие окна
            title_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            header_layout.addWidget(title_label, 1)

            header_layout.addWidget(QLabel("Год:"))

            self.year_combo = QComboBox()
            self.year_combo.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            header_layout.addWidget(self.year_combo)

            self.refresh_btn = CompactButton("Обновить", purpose="info")
            self.refresh_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            header_layout.addWidget(self.refresh_btn)

            main_layout.addWidget(header_widget)

            # === Контейнер графика (растягивается) ===
            self.chart_widget = QWidget()
            self.chart_layout = QVBoxLayout(self.chart_widget)
            self.chart_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.addWidget(self.chart_widget, 1)

            self._populate_years()
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def _setup_connections(self):
        """Настраивает соединения сигналов и дебаунс обновления."""
        try:
            self.year_combo.currentTextChanged.connect(self.on_year_changed)
            self.refresh_btn.clicked.connect(self.update_chart)

            self.update_timer = QTimer()
            self.update_timer.setSingleShot(True)
            self.update_timer.timeout.connect(self.update_chart)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def schedule_update(self, data_type=None):
        """Планирует отложенное обновление графика (группировка частых вызовов).

        Args:
            data_type: тип изменившихся данных ('transactions', 'accounts' или None)
        """
        if data_type in (None, "transactions", "accounts"):
            self.update_timer.start(500)

    def _populate_years(self):
        """Заполняет комбобокс списком годов и выбирает текущий."""
        try:
            current_year = datetime.now().year
            years = list(range(2020, current_year + 2))
            self.year_combo.addItems([str(y) for y in years])
            self.year_combo.setCurrentText(str(current_year))
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def on_year_changed(self, year_str: str):
        """Обрабатывает смену года в комбобоксе.

        Args:
            year_str: строка с годом из комбобокса
        """
        try:
            if not year_str:
                return
            self.current_year = int(year_str)
            self.update_chart()
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            self._show_message(f"Некорректный год: {year_str}", "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def clear_chart(self):
        """Очищает текущий график и освобождает ресурсы matplotlib."""
        try:
            if self.canvas:
                self.chart_layout.removeWidget(self.canvas)
                self.canvas.deleteLater()
                self.canvas = None
            if self.figure:
                plt.close(self.figure)
                self.figure = None
                self.ax = None
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def _chart_colors(self) -> dict:
        """Возвращает цвета для matplotlib из активной темы.

        Returns:
            Словарь с ключами face, muted, grid, income, expense, balance
        """
        theme = ThemeManager.current()
        return {
            "face": theme.get("BG_SECONDARY", "#FFFFFF"),
            "muted": theme.get("TEXT_SECONDARY", "#7F8C8D"),
            "grid": theme.get("BORDER", "#BDC3C7"),
            "income": theme.get("SUCCESS", "#27AE60"),
            "expense": theme.get("DANGER", "#C0392B"),
            "balance": theme.get("COMPACT_INFO", "#2196F3"),
        }

    def _apply_axes_theme(self, ax, colors: dict):
        """Применяет цвета активной темы к оси matplotlib.

        Args:
            ax: ось matplotlib для оформления
            colors: словарь цветов из _chart_colors
        """
        try:
            ax.set_facecolor("none")
            ax.tick_params(colors=colors["muted"], labelsize=8)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{int(x):,}"))
            ax.set_axisbelow(True)
            ax.grid(True, alpha=0.3, linestyle="--", axis="y", color=colors["grid"])
            for spine in ax.spines.values():
                spine.set_color(colors["grid"])
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_color(colors["muted"])
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def update_chart(self):
        """Перестраивает график по данным за выбранный год."""
        self.clear_chart()
        try:
            year = self.current_year
            monthly_data = self.get_monthly_data(year)
            if not monthly_data:
                self._show_message(f"Нет данных за {year} год", "muted")
                return

            colors = self._chart_colors()

            self.figure = Figure(figsize=(8, 5), dpi=80, facecolor=colors["face"])
            self.canvas = FigureCanvas(self.figure)
            self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.ax = self.figure.add_subplot(111)
            self.ax.set_facecolor(colors["face"])
            self.figure.subplots_adjust(left=0.07, right=0.93, top=0.95, bottom=0.15)

            # === Подготовка данных ===
            months = list(range(1, 13))
            month_names = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн",
                           "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
            incomes, expenses, cumulative_balances = [], [], []
            cumulative = 0
            for month in months:
                data = monthly_data.get(f"{year}-{month:02d}")
                if data:
                    income = data.get("income", 0)
                    expense = data.get("expense", 0)
                    cumulative += income - expense
                else:
                    income, expense = 0, 0
                incomes.append(income)
                expenses.append(expense)
                cumulative_balances.append(cumulative)

            x_pos = np.arange(len(months))
            bar_width = 0.35

            # === Столбцы и линия баланса ===
            self.ax.bar(x_pos - bar_width / 2, incomes, bar_width,
                        label="Доходы", color=colors["income"], alpha=0.85)
            self.ax.bar(x_pos + bar_width / 2, expenses, bar_width,
                        label="Расходы", color=colors["expense"], alpha=0.85)

            ax2 = self.ax.twinx()
            ax2.plot(x_pos, cumulative_balances, label="Накопленный баланс",
                     color=colors["balance"], marker="^", linewidth=2, linestyle="--")

            # === Оси (компактно, чтобы помещаться в 300px высоты) ===
            self.ax.set_ylabel("Сумма, ₽", fontsize=9, color=colors["muted"])
            ax2.set_ylabel("Баланс, ₽", fontsize=9, color=colors["muted"])
            self.ax.set_xticks(x_pos)
            self.ax.set_xticklabels(month_names, rotation=45, fontsize=8)

            self._apply_axes_theme(self.ax, colors)
            self._apply_axes_theme(ax2, colors)

            # === Масштаб ===
            all_values = incomes + expenses
            max_value = max(all_values) if all_values else 0
            self.ax.set_ylim(0, max_value * 1.2 if max_value > 0 else 100)

            # === Подписи текущего месяца ===
            if year == datetime.now().year:
                cur = datetime.now().month - 1
                if incomes[cur] > 0:
                    self.ax.text(cur - bar_width / 2, incomes[cur],
                                 f"{incomes[cur]:,.0f}", ha="center", va="bottom",
                                 fontsize=8, color=colors["income"])
                if expenses[cur] > 0:
                    self.ax.text(cur + bar_width / 2, expenses[cur],
                                 f"{expenses[cur]:,.0f}", ha="center", va="bottom",
                                 fontsize=8, color=colors["expense"])

            self.chart_layout.addWidget(self.canvas)
            self.canvas.draw()
            self.data_updated.emit()
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            self._show_message(str(e), "error")
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            self._show_message("Ошибка при построении графика", "error")

    def get_monthly_data(self, year: int) -> dict:
        """Получает помесячную сводку за указанный год.

        Args:
            year: год, за который нужны данные

        Returns:
            Словарь {'YYYY-MM': {'income': float, 'expense': float}} или {}
        """
        try:
            if not self.db:
                return {}
            data = self.db.get_yearly_summary(year)
            if not data:
                return {}
            return {
                month_key: {
                    "income": month_data.get("income", 0),
                    "expense": month_data.get("expense", 0),
                }
                for month_key, month_data in data.items()
            }
        except Exception as e:
            # Адаптация шаблона: график не должен ронять окно — мягко отдаём {}
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            return {}

    def _show_message(self, text: str, variant: str):
        """Показывает служебную надпись вместо графика.

        Args:
            text: текст сообщения
            variant: оформление через QLabel[variant=...] ('muted' или 'error')
        """
        try:
            label = QLabel(text)
            label.setAlignment(Qt.AlignCenter)
            label.setProperty("variant", variant)
            label.style().polish(label)
            self.chart_layout.addWidget(label)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise