# ui/analytics/analytics_window.py
"""Окно аналитики: KPI-карточки (Qt) и интерактивный график ECharts."""

import logging

from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout

from ui.analytics.html_chart_widget import HtmlChartWidget
from ui.analytics.kpi_cards_widget import KpiCardsWidget

logger = logging.getLogger(__name__)


class AnalyticsWindow(QDialog):
    """Окно аналитики: KPI-карточки и график «доходы, расходы, бюджет, баланс»."""

    def __init__(self, presenter, parent=None):
        """
        Инициализация окна аналитики.

        Args:
            presenter: экземпляр AnalyticsPresenter, внедрённый из главного окна
            parent: родительское окно
        """
        try:
            super().__init__(parent)
            self.presenter = presenter
            self.setWindowTitle("Аналитика")
            self.setModal(False)
            self.resize(1200, 800)
            self._setup_ui()
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def _setup_ui(self):
        """Собирает интерфейс окна."""
        try:
            layout = QVBoxLayout(self)

            header = QLabel("📈 Аналитика трат и бюджета")
            header.setProperty("variant", "header")
            layout.addWidget(header)

            # KPI-карточки (нативные Qt-виджеты)
            self.kpi_cards = KpiCardsWidget(self)
            self.kpi_cards.setFixedHeight(130)
            layout.addWidget(self.kpi_cards)

            # График ECharts
            self.html_chart = HtmlChartWidget(self)
            layout.addWidget(self.html_chart, 1)

            self.status_label = QLabel("")
            layout.addWidget(self.status_label)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def render(self, html: str, kpi: dict) -> None:
        """
        Рисует KPI-карточки и график.

        Args:
            html: готовая HTML-разметка графика ECharts
            kpi: словарь KPI-метрик для карточек
        """
        try:
            self.kpi_cards.render_kpi(kpi)
            self.html_chart.render_html(html)
            self.status_label.setText("")
        except ValueError as e:
            self.show_status(str(e), "error")  # Показываем пользователю
        except Exception as e:
            logger.error(f"Ошибка UI: {e}", exc_info=True)
            self.show_status("Произошла ошибка", "error")

    def show_status(self, text: str, variant: str) -> None:
        """
        Показывает служебную надпись в статусной строке окна.

        Args:
            text: текст сообщения
            variant: стиль оформления ('error', 'muted')
        """
        self.status_label.setText(text)
        self.status_label.setProperty("variant", variant)
        self.status_label.style().polish(self.status_label)