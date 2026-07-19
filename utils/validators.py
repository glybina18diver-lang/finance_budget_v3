"""
Утилиты валидации и парсинга пользовательского ввода.

Содержит безопасные функции для конвертации строк из UI
в числовые типы (float, int) с обработкой пустых значений и другие.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def parse_float(text: str) -> Optional[float]:
    """
    Безопасно парсит строку в число с плавающей точкой.
    
    Обрабатывает запятую как разделитель десятичных знаков (заменяет на точку).
    Для пустой строки возвращает None.
    
    Args:
        text: строка для парсинга (например, "100000" или "49,8")
        
    Returns:
        Число float или None, если строка пустая
        
    Raises:
        ValueError: если строка не является корректным числом
    """
    try:
        val = text.strip().replace(",", ".")
        if not val:
            return None
        return float(val)
    except ValueError as e:
        logger.warning(f"[validators] Ошибка парсинга float из '{text}': {e}")
        raise ValueError(f"Некорректное число: '{text}'")
    except Exception as e:
        logger.error(f"[validators] Ошибка парсинга float: {e}", exc_info=True)
        raise


def parse_int(text: str) -> Optional[int]:
    """
    Безопасно парсит строку в целое число.
    
    Для пустой строки возвращает None.
    
    Args:
        text: строка для парсинга (например, "120" или "31")
        
    Returns:
        Целое число int или None, если строка пустая
        
    Raises:
        ValueError: если строка не является корректным целым числом
    """
    try:
        val = text.strip()
        if not val:
            return None
        return int(val)
    except ValueError as e:
        logger.warning(f"[validators] Ошибка парсинга int из '{text}': {e}")
        raise ValueError(f"Некорректное целое число: '{text}'")
    except Exception as e:
        logger.error(f"[validators] Ошибка парсинга int: {e}", exc_info=True)
        raise