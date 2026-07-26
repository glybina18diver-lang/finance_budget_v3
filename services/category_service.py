# services/category_service.py
"""
Сервис управления категориями.
Инкапсулирует бизнес-логику: CRUD, валидацию и работу с иерархией.
"""
from typing import Dict, Optional, List
import logging
from core.repositories.category_repository import CategoryRepository
from core.models import Category

logger = logging.getLogger(__name__)


class CategoryService:
    """Сервис для управления категориями."""

    def __init__(self, cat_repo: CategoryRepository):
        """
        Инициализация сервиса.

        Args:
            cat_repo: репозиторий категорий
        """
        self.cat_repo = cat_repo

    def get_all_categories(self) -> List[Category]:
        """
        Возвращает все  категории (без фильтрации по типу).

        Returns:
            Список объектов Category
        """
        try:
            return self.cat_repo.get_all_categories()
        except Exception as e:
            logger.error(f"[CategoryService] Ошибка загрузки категорий: {e}", exc_info=True)
            raise

    def get_user_categories(self) -> List[Category]:
        """
        Возвращает список активных пользовательские категории (без фильтрации по типу).

        Returns:
            Список объектов Category
        """
        try:
            return self.cat_repo.get_user_categories()
        except Exception as e:
            logger.error(f"[CategoryService] Ошибка загрузки категорий: {e}", exc_info=True)
            raise

    def get_all_by_type(self, cat_type: str) -> List[Category]:
        """
        Возвращает список активных категорий указанного типа (доход/расход).

        Args:
            cat_type: тип категории ('income' или 'expense')

        Returns:
            Список объектов Category, отсортированный по имени
        """
        try:
            return self.cat_repo.get_all_by_type(cat_type)
        except Exception as e:
            logger.error(f"[CategoryService] Ошибка загрузки категорий: {e}", exc_info=True)
            raise

    def get_all_active_categories(self) -> List[Category]:
        """
        Возвращает все активные категории (без фильтрации по типу).

        Returns:
            Список объектов Category
        """
        try:
            return self.cat_repo.get_all_active_categories()
        except Exception as e:
            logger.error(f"[CategoryService] Ошибка загрузки категорий: {e}", exc_info=True)
            raise

    def get_category(self, category_id: int) -> Optional[Category]:
        """
        Возвращает категорию по ID.

        Args:
            category_id: ID запрашиваемой категории

        Returns:
            Объект Category или None, если не найден
        """
        try:
            return self.cat_repo.get_by_id(category_id)
        except Exception as e:
            logger.error(f"[CategoryService] Ошибка загрузки категории #{category_id}: {e}", exc_info=True)
            raise

    def get_category_by_name(self, name: str) -> Optional[Category]:
        """
        Возвращает категорию по имени.

        Args:
            name: имя запрашиваемой категории

        Returns:
            Объект Category или None, если не найдена

        Raises:
            ValueError: если имя пустое
            Exception: при системной ошибке
        """
        try:
            if not name or not name.strip():
                raise ValueError("Имя категории не может быть пустым")

            return self.cat_repo.get_by_name(name.strip())

        except ValueError as e:
            logger.warning(f"[CategoryService] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(
                f"[CategoryService] Ошибка загрузки категории '{name}': {e}",
                exc_info=True,
            )
            raise
        
    def create_category(self, data: dict) -> Category:
        """
        Создаёт новую категорию.

        Args:
            data: данные категории в формате словаря

        Returns:
            Объект Category
        """
        try:
            self._validate_category_data(data)
            category = Category(**data)
            return self.cat_repo.create(category)

        except ValueError as e:
            logger.warning(f"[CategoryService] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[CategoryService] Критическая ошибка при создании категории: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise RuntimeError(f"Системная ошибка при создании категории: {e}") from e

    def update_category(self, category_id: int, data: dict) -> bool:
        """
        Обновляет категорию по ID.

        Args:
            category_id: ID категории
            data: данные категории в формате словаря

        Returns:
            True, если обновление успешно
        """
        try:
            self._validate_category_data(data)
            category = self.cat_repo.get_by_id(category_id)
            if not category:
                raise ValueError("Категория не найдена")

            for key, value in data.items():
                if hasattr(category, key):
                    setattr(category, key, value)

            return self.cat_repo.update(category)

        except ValueError as e:
            logger.warning(f"[CategoryService] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[CategoryService] Критическая ошибка при обновлении категории #{category_id}: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise RuntimeError(f"Системная ошибка при обновлении категории: {e}") from e

    def delete_category(self, category_id: int) -> bool:
        """
        Удаляет категорию по ID.

        Args:
            category_id: ID категории

        Returns:
            True, если удаление успешно
        """
        try:
            category = self.cat_repo.get_by_id(category_id)
            if not category:
                raise ValueError("Категория не найдена")
            if category.is_system:
                raise ValueError("Системные категории нельзя удалять")

            # Проверка на связанные транзакции
            if self._has_transactions(category_id):
                raise ValueError("Невозможно удалить: к категории привязаны операции")

            return self.cat_repo.delete(category_id)

        except ValueError as e:
            logger.warning(f"[CategoryService] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[CategoryService] Критическая ошибка при удалении категории #{category_id}: {e}")
            logger.error("Ошибка: %s", e, exc_info=True)
            raise RuntimeError(f"Системная ошибка при удалении категории: {e}") from e

    def _has_transactions(self, category_id: int) -> bool:
        """
        Проверяет наличие транзакций, связанных с категорией.

        Args:
            category_id: ID категории

        Returns:
            True, если категория связана с транзакциями
        """
        try:
            query = "SELECT COUNT(*) AS cnt FROM transactions WHERE category_id = ?"
            result = self.cat_repo.db.fetchone(query, (category_id,))
            return result["cnt"] > 0 if result else False
        except Exception as e:
            logger.error(f"[CategoryService] Ошибка проверки зависимостей категории #{category_id}: {e}", exc_info=True)
            raise

    def _validate_category_data(self, data: dict) -> None:
        """
        Валидирует данные категории перед сохранением в БД.

        Args:
            data: словарь с данными категории

        Raises:
            ValueError: если данные не прошли валидацию
        """
        # 1. Обязательное поле: название
        name = data.get("name", "").strip()
        if not name:
            raise ValueError("Название категории не может быть пустым")
        if len(name) > 100:
            raise ValueError("Название категории не должно превышать 100 символов")

        # 2. Тип категории (должен быть income или expense)
        cat_type = data.get("cat_type")
        if cat_type not in ("income", "expense"):
            raise ValueError("Тип категории должен быть 'income' или 'expense'")

        # 3. Родительская категория (если указана — должна существовать)
        parent_id = data.get("parent_id")
        if parent_id is not None:
            if not isinstance(parent_id, int) or parent_id <= 0:
                raise ValueError("Некорректный ID родительской категории")
            parent = self.cat_repo.get_by_id(parent_id)
            if not parent:
                raise ValueError("Родительская категория не найдена")

        # 4. Плановый бюджет (должен быть числом >= 0)
        budget = data.get("budget_amount_monthly", 0.0)
        if not isinstance(budget, (int, float)):
            raise ValueError("Плановый бюджет должен быть числом")
        if budget < 0:
            raise ValueError("Плановый бюджет не может быть отрицательным")

        # 5. Запрет создания системных категорий через UI
        if data.get("is_system", False):
            raise ValueError("Системные категории нельзя создавать вручную")

        # 6.
        is_active = data.get("is_active", True)
        if not isinstance(is_active, bool):
            raise ValueError("Поле 'is_active' должно быть логическим значением")
