# ui/analytics/analytics_test_window.py
"""Тестовое окно аналитики v0.0.1: KPI-карточки и интерактивный график Plotly."""

import logging

from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout
from PySide6.QtWidgets import QComboBox, QHBoxLayout

from ui.analytics.html_chart_widget import HtmlChartWidget
from ui.analytics.kpi_cards_widget import KpiCardsWidget

logger = logging.getLogger(__name__)


class AnalyticsTestWindow(QDialog):
    """Окно-прототип аналитики: KPI-карточки и интерактивный график."""

    def __init__(self, presenter, parent=None):
        """
        Инициализация тестового окна аналитики.

        Args:
            presenter: экземпляр AnalyticsPresenter, внедрённый из главного окна
            parent: родительское окно
        """
        try:
            super().__init__(parent)
            self.presenter = presenter
            self.setWindowTitle("Аналитика — прототип v0.0.1")
            self.setModal(False)
            self.resize(1500, 800)
            self._setup_ui()
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def _setup_ui(self):
        """Собирает интерфейс окна."""
        try:
            layout = QVBoxLayout(self)

            header_row = QHBoxLayout()
            header = QLabel("📈 Аналитика трат и бюджета — прототип v0.0.1")
            header.setProperty("variant", "header")
            header_row.addWidget(header)
            header_row.addStretch(1)
            header_row.addWidget(QLabel("Рендерер:"))
            self.renderer_combo = QComboBox()
            self.renderer_combo.addItems(list(self.presenter.RENDERERS.keys()))
            self.renderer_combo.setCurrentText(self.presenter.renderer)
            self.renderer_combo.currentTextChanged.connect(self._on_renderer_changed)
            header_row.addWidget(self.renderer_combo)
            layout.addLayout(header_row)

            # KPI-карточки сверху
            self.kpi_cards = KpiCardsWidget(self)
            self.kpi_cards.setFixedHeight(130)
            layout.addWidget(self.kpi_cards)

            # Большой интерактивный график
            self.html_chart = HtmlChartWidget(self)
            layout.addWidget(self.html_chart, 1)

            self.status_label = QLabel("")
            layout.addWidget(self.status_label)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def render(self, html: str, kpi: dict) -> None:
        """
        Рисует KPI-карточки и интерактивный график.

        Args:
            html: готовая HTML-разметка графика
            kpi: словарь KPI-метрик для нативных карточек
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

    def _on_renderer_changed(self, renderer: str):
        """Обрабатывает смену рендерера в селекторе."""
        try:
            html = self.presenter.set_renderer(renderer)
            self.render_chart(html)
        except ValueError as e:
            self.show_status(str(e), "error")  # Показываем пользователю
        except Exception as e:
            logger.error(f"Ошибка UI: {e}", exc_info=True)
            self.show_status("Произошла ошибка", "error")

    def render_chart(self, html: str) -> None:
        """
        Перерисовывает только график (без KPI).

        Args:
            html: готовая HTML-строка графика
        """
        try:
            self.html_chart.render_html(html)
        except ValueError as e:
            self.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"Ошибка UI: {e}", exc_info=True)
            self.show_status("Произошла ошибка", "error")