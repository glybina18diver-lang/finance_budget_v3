# core/repositories/category_repository.py
from typing import List, Dict, Any
from core.db import Database
from core.models import Category

class CategoryRepository:
    """Репозиторий для работы с категориями."""

    def __init__(self, db: Database):
        self.db = db

    def _row_to_category(self, row: Dict[str, Any]) -> Category:
        """Преобразует строку из БД в объект Category.
        
        Args:
            row: строка из БД
            
        Returns:
            Объект Category
        """
        return Category(
            id=row.get("id"),
            name=row.get("name", ""),
            cat_type=row.get("cat_type", "expense"),
            budget_amount_monthly=row.get("budget_amount_monthly", 0.0),
            parent_id=row.get("parent_id"),
            color=row.get("color", "#3498db"),
            icon=row.get("icon", ""),
            is_system=bool(row.get("is_system", 0))
        )

    def get_all_by_type(self, cat_type: str) -> List[Category]:#TODO при релизе проверить нужен ли еще метод
        """
        Возвращает список активных категорий указанного типа (доход/расход).
        
        Args:
            cat_type: тип категории ('income' или 'expense')
            
        Returns:
            Список объектов Category, отсортированный по имени
        """
        # Используем cat_type, так как в твоей схеме V2 (db.py) колонка называется cat_type.
        # Фильтруем is_system = 0, чтобы не показывать служебные категории.
        query = """
            SELECT * FROM categories 
            WHERE cat_type = ? AND is_system = 0 
            ORDER BY name
        """
        rows = self.db.fetchall(query, (cat_type,))
        return [self._row_to_category(row) for row in rows]
    
    def get_all_categories(self) -> List[Category]:
        """
        Возвращает все активные категории (без фильтрации по типу).
        
        Returns:
            Список объектов Category
        """
        query = """
            SELECT * FROM categories 
            WHERE is_system = 0 
            ORDER BY cat_type, name
        """
        rows = self.db.fetchall(query)
        return [self._row_to_category(row) for row in rows]