# ui/presenters/analytics_presenter.py
"""Презентер окна аналитики: связывает View, Service и ChartBuilder."""

import logging

from core.repositories.analytics_repository import AnalyticsRepository
from services.analytics_service import AnalyticsService
from ui.analytics.analytics_window import AnalyticsWindow
from ui.analytics.chart_builder import ChartBuilder

logger = logging.getLogger(__name__)


class AnalyticsPresenter:
    """Связывает окно аналитики с сервисом данных и сборщиком графиков."""

    def __init__(self, parent_window, db_manager):
        """
        Инициализация презентера аналитики.

        Args:
            parent_window: родительское окно для окна аналитики
            db_manager: экземпляр Database для создания репозитория
        """
        try:
            self.parent_window = parent_window
            self.repo = AnalyticsRepository(db_manager)
            self.service = AnalyticsService(self.repo)
            self.builder = ChartBuilder()
            self.window = None
            self.current_start_date = None
            self.current_end_date = None
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def open_analytics_window(self) -> None:
        """
        Открывает окно аналитики и рисует KPI и график.

        Raises:
            ValueError: если данные аналитики не прошли валидацию
        """
        try:
            start_date, end_date = self.service.get_default_period()
            self.current_start_date = start_date
            self.current_end_date = end_date

            data = self.service.get_analytics_data(start_date, end_date)
            kpi = self.service.get_kpi_metrics(data)
            html = self.builder.build_expenses_html(data)

            if self.window is None:
                self.window = AnalyticsWindow(self, self.parent_window)
            self.window.render(html, kpi)
            self.window.show()
            self.window.raise_()
            self.window.activateWindow()
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise