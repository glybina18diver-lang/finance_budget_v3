# ui/presenters/category_presenter.py
"""
Презентер управления категориями.
Связывает CategoryDialog и CategoryService.
"""
from typing import List
import logging
from services.category_service import CategoryService
from core.models import Category

logger = logging.getLogger(__name__)


class CategoryPresenter:
    """Презентер для диалога категорий."""

    def __init__(self, service: CategoryService):
        """
        Инициализация презентера.

        Args:
            service: экземпляр CategoryService
        """
        self.service = service
        self.view = None

    def set_view(self, view):
        """
        Устанавливает связь с представлением и загружает данные.

        Args:
            view: объект CategoryDialog
        """
        self.view = view
        self.load_categories()

    def load_categories(self) -> None:
        """Загружает категории из сервиса и передаёт в UI. Исключася системные категории."""
        if not self.view:
            return
        try:
            categories = self.service.get_user_categories()
            self.view.load_categories(categories)
            self.view.load_parent_categories(categories)
        except Exception as e:
            logger.error(f"[CategoryPresenter] Ошибка загрузки категорий: {e}", exc_info=True)
            self.view.show_error(f"Ошибка загрузки категорий: {e}")

    def add_category(self, category_data: dict):
        """
        Создает новую категорию.

        Args:
            category_data: данные категории в формате словаря
        """
        try:
            self.service.create_category(category_data)
            self.view.show_status("Категория создана", "success")
            self.load_categories()  # обновить список.
            self.view._reset_form()
        except ValueError as e:
            self.view.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[CategoryPresenter] Ошибка создания категории: {e}", exc_info=True)
            self.view.show_status("Произошла ошибка при создании категории", "error")

    def update_category(self, data: dict):
        """
        Обновляет категорию.

        Args:
            data: данные категории в формате словаря
        """
        try:
            self.service.update_category(data["id"], data)
            self.view.show_status("Категория обновлена", "success")
            self.load_categories()
            self.view._reset_form()
        except ValueError as e:
            self.view.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[CategoryPresenter] Ошибка обновления категории: {e}", exc_info=True)
            self.view.show_status("Произошла ошибка при обновлении категории", "error")

    def delete_category(self, category_id: int):
        """
        Удаляет категорию.

        Args:
            category_id: ID категории
        """
        try:
            self.service.delete_category(category_id)
            self.view.show_status("Категория удалена", "success")
            self.view.clear_selection()
            self.load_categories()
        except ValueError as e:
            self.view.show_status(str(e), "error")
        except Exception as e:
            logger.error(f"[CategoryPresenter] Ошибка удаления категории #{category_id}: {e}", exc_info=True)
            self.view.show_status("Произошла ошибка при удалении категории", "error")

    def select_category(self, category_id: int) -> None:
        """
        Загружает данные выбранной категории в форму редактирования.

        Args:
            category_id: ID выбранной категории
        """
        try:
            category = self.service.get_category(category_id)
            if category:
                self.view.show_category_in_form(category)
            else:
                self.view.show_error("Категория не найдена в базе")
        except Exception as e:
            logger.error(f"[CategoryPresenter] Ошибка загрузки категории #{category_id}: {e}", exc_info=True)
            self.view.show_error(f"Ошибка загрузки категории: {e}")