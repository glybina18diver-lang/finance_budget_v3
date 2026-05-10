# core/repositories/category_repository.py
from typing import List, Dict, Any, Optional
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

    def get_by_id(self, category_id: int) -> Optional[Category]:
        """
        Возвращает категорию по её ID.
        
        Args:
            category_id: идентификатор категории
            
        Returns:
            Объект Category, если найден, иначе None
        """
        query = "SELECT * FROM categories WHERE id = ?"
        row = self.db.fetchone(query, (category_id,))
        if row:
            return self._row_to_category(row)
        return None
    
    def create(self, category: Category) -> Category:
        """
        Создаёт новую категорию.
        
        Args:
            category: объект Category
            
        Returns:
            Объект Category с ID
        """
        query = """
            INSERT INTO categories (name, cat_type, parent_id, budget_amount_monthly, is_active, is_system)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            category.name,
            category.cat_type,      # ← "income" или "expense"
            category.parent_id,
            category.budget_amount_monthly or 0.0,
            1 if category.is_active else 0,
            0  # is_system = False для новых категорий
        )
        new_id = self.db.execute(query, params)
        category.id = new_id
        return category
    
    def update(self, category: Category) -> bool:
        """
        Обновляет категорию.
        
        Args:
            category: объект Category
            
        Returns:
            True, если обновление прошло успешно
        """
        query = """
            UPDATE categories SET
                name = ?, cat_type = ?, parent_id = ?, budget_amount_monthly = ?
            WHERE id = ?
        """
        params = (
            category.name,
            category.cat_type,
            category.parent_id,
            category.budget_amount_monthly or 0.0,
            category.id
        )
        self.db.execute(query, params)
        return True
    
    def delete(self, category_id: int) -> bool:
        
        if not self.get_by_id(category_id):
            return False
        query = "DELETE FROM categories WHERE id = ?"
        self.db.execute(query, (category_id,))
        return True