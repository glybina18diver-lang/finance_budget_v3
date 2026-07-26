# core/repositories/category_repository.py
from typing import List, Dict, Any, Optional
import logging
from core.db import Database
from core.models import Category
from decimal import Decimal

logger = logging.getLogger(__name__)


class CategoryRepository:
    """Репозиторий для работы с категориями."""

    def __init__(self, db: Database):
        self.db = db

    def _row_to_category(self, row: Dict[str, Any]) -> Category:
        """Преобразует строку из БД в объект Category.
        Числовые поля конвертируются из float (SQLite REAL) в Decimal.

        Args:
            row: строка из БД

        Returns:
            Объект Category
        """
        
        return Category(
            id=row.get("id"),
            name=row.get("name", ""),
            cat_type=row.get("cat_type", "expense"),
            budget_amount_monthly=Decimal(str(row.get("budget_amount_monthly", 0.0))),
            parent_id=row.get("parent_id"),
            color=row.get("color", "#3498db"),
            icon=row.get("icon", ""),
            is_system=bool(row.get("is_system", 0))
        )

    def get_all_by_type(self, cat_type: str) -> List[Category]:
        """
        Возвращает список активных категорий указанного типа (доход/расход).

        Args:
            cat_type: тип категории ('income' или 'expense')

        Returns:
            Список объектов Category, отсортированный по имени
        """
        try:
            query = """
                SELECT * FROM categories 
                WHERE cat_type = ?
                   AND is_active = 1 AND is_system = 0
                ORDER BY name
            """
            rows = self.db.fetchall(query, (cat_type,))
            return [self._row_to_category(row) for row in rows]
        except Exception as e:
            logger.error(f"[CategoryRepository] Ошибка получения категорий типа '{cat_type}': {e}", exc_info=True)
            raise

    def get_all_active_categories(self) -> List[Category]:
        """
        Возвращает все активные категории (без фильтрации по типу).

        Returns:
            Список объектов Category
        """
        try:
            query = """
                SELECT * FROM categories
                WHERE is_active = 1 
                ORDER BY cat_type, name
            """
            rows = self.db.fetchall(query)
            return [self._row_to_category(row) for row in rows]
        except Exception as e:
            logger.error(f"[CategoryRepository] Ошибка получения всех категорий: {e}", exc_info=True)
            raise

    def get_user_categories(self) -> List[Category]:
        """
        Возвращает список активных пользовательских категрий для UI.

        Исключает системные,
        которые используются только для внутренней логики.

        Returns:
            Список объектов Category
        """
        try:
            query = """
                SELECT * FROM categories
                WHERE is_active = 1 AND is_system = 0
                ORDER BY cat_type, name
            """
            rows = self.db.fetchall(query)
            return [self._row_to_category(row) for row in rows]
        except Exception as e:
            logger.error(f"[CategoryRepository] Ошибка получения пользовательских категорий: {e}", exc_info=True)
            raise

    def get_all_categories(self) -> List[Category]:
        """
        Возвращает все категории (без фильтрации по типу).

        Returns:
            Список объектов Category
        """
        try:
            query = """
                SELECT * FROM categories
                ORDER BY cat_type, name
            """
            rows = self.db.fetchall(query)
            return [self._row_to_category(row) for row in rows]
        except Exception as e:
            logger.error(f"[CategoryRepository] Ошибка получения всех категорий: {e}", exc_info=True)
            raise

    def get_by_id(self, category_id: int) -> Optional[Category]:
        """
        Возвращает категорию по её ID.

        Args:
            category_id: идентификатор категории

        Returns:
            Объект Category, если найден, иначе None
        """
        try:
            query = "SELECT * FROM categories WHERE id = ?"
            row = self.db.fetchone(query, (category_id,))
            if row:
                return self._row_to_category(row)
            return None
        except Exception as e:
            logger.error(f"[CategoryRepository] Ошибка получения категории #{category_id}: {e}", exc_info=True)
            raise

    def get_by_name(self, name: str) -> Optional[Category]:
        """
        Возвращает категорию по ее названию.

        Args:
            name: название категории

        Returns:
            Объект Category, если найден, иначе None
        """
        try:
            query = "SELECT * FROM categories WHERE name = ?"
            row = self.db.fetchone(query, (name,))
            if row:
                return self._row_to_category(row)
            return None
        except Exception as e:
            logger.error(f"[CategoryRepository] Ошибка получения категории '{name}': {e}", exc_info=True)
            raise
        
    def create(self, category: Category) -> Category:
        """
        Создаёт новую категорию.

        Args:
            category: объект Category

        Returns:
            Объект Category с ID
        """
        try:
            query = """
                INSERT INTO categories (name, cat_type, parent_id, budget_amount_monthly, is_active, is_system)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (
                category.name,
                category.cat_type,
                category.parent_id,
                float(category.budget_amount_monthly or Decimal("0.00")),
                1 if category.is_active else 0,
                0  # is_system = False для новых категорий
            )
            new_id = self.db.execute(query, params)
            category.id = new_id
            return category
        except Exception as e:
            logger.error(f"[CategoryRepository] Ошибка создания категории '{category.name}': {e}", exc_info=True)
            raise

    def update(self, category: Category) -> bool:
        """
        Обновляет категорию.

        Args:
            category: объект Category

        Returns:
            True, если обновление прошло успешно
        """
        try:
            query = """
                UPDATE categories SET
                    name = ?, cat_type = ?, parent_id = ?, budget_amount_monthly = ?
                WHERE id = ?
            """
            params = (
                category.name,
                category.cat_type,
                category.parent_id,
                float(category.budget_amount_monthly or Decimal("0.00")),
                category.id
            )
            self.db.execute(query, params)
            return True
        except Exception as e:
            logger.error(f"[CategoryRepository] Ошибка обновления категории #{category.id}: {e}", exc_info=True)
            raise

    def delete(self, category_id: int) -> bool:
        try:
            if not self.get_by_id(category_id):
                return False
            query = "DELETE FROM categories WHERE id = ?"
            self.db.execute(query, (category_id,))
            return True
        except Exception as e:
            logger.error(f"[CategoryRepository] Ошибка удаления категории #{category_id}: {e}", exc_info=True)
            raise