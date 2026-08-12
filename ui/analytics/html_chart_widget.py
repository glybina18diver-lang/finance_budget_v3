# ui/analytics/html_chart_widget.py
"""HTML-график (Plotly внутри QWebEngineView) для окна аналитики."""

import logging
import os

from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

logger = logging.getLogger(__name__)

_ASSETS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets")
)


class HtmlChartWidget(QFrame):
    """Виджет отображения HTML-графика через QWebEngineView."""

    def __init__(self, parent=None):
        """
        Инициализация виджета HTML-графика.

        Args:
            parent: родительский виджет
        """
        try:
            super().__init__(parent)
            self.setProperty("variant", "panel")
            self.browser = None
            self._setup_ui()
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def _setup_ui(self):
        """Собирает интерфейс виджета."""
        try:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(8, 8, 8, 8)

            title = QLabel("🌐 График доходов и расходов (ECharts)")
            title.setProperty("variant", "header")
            layout.addWidget(title)

            self.browser = QWebEngineView(self)
            layout.addWidget(self.browser, 1)
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def render_html(self, html: str) -> None:
        """
        Отображает готовую HTML-разметку графика.

        Args:
            html: HTML-строка с графиком

        Raises:
            ValueError: если разметка пустая
        """
        try:
            if not html:
                raise ValueError("Пустая HTML-разметка графика")
            # baseUrl нужен, чтобы относительный путь js/plotly.min.js
            # резолвился относительно папки assets/
            base_url = QUrl.fromLocalFile(_ASSETS_DIR + os.sep)
            self.browser.setHtml(html, base_url)
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise