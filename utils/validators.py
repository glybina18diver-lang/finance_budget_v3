"""
Утилиты валидации и парсинга пользовательского ввода.

Содержит безопасные функции для конвертации строк из UI
в числовые типы (float, int) с обработкой пустых значений и другие.
"""

from decimal import Decimal, InvalidOperation
from typing import Union
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

"""
Универсальное преобразование числовых типов в Decimal.

Используется для точных финансовых вычислений, где float
может приводить к ошибкам округления (например, 0.1 + 0.2 != 0.3).
"""

# Тип, который может быть преобразован в Decimal
NumericInput = Union[int, float, str, Decimal, None]


def to_decimal(value: NumericInput) -> Decimal:
    """
    Универсально преобразует числовое значение в Decimal.

    Поддерживает типы: int, float, str, Decimal.
    Для float используется преобразование через str(), чтобы избежать
    потери точности (Decimal(0.1) != Decimal('0.1')).

    Args:
        value: значение для преобразования. Допустимые типы:
               int, float, str (числовое представление), Decimal.
               None и пустая строка вызывают ValueError.

    Returns:
        Объект Decimal с точным числовым значением

    Raises:
        ValueError: если значение None, пустая строка или
                    не может быть преобразовано в число
        TypeError: если тип значения не поддерживается

    Examples:
        >>> to_decimal(100)
        Decimal('100')
        >>> to_decimal(123.45)
        Decimal('123.45')
        >>> to_decimal("99.99")
        Decimal('99.99')
        >>> to_decimal(Decimal("50.00"))
        Decimal('50.00')
    """
    try:
        if value is None:
            raise ValueError("Значение не может быть None")

        if isinstance(value, Decimal):
            return value

        if isinstance(value, bool):
            raise TypeError(
                f"Тип bool не поддерживается, получено: {value!r}"
            )

        if isinstance(value, int):
            return Decimal(value)

        if isinstance(value, float):
            # Преобразование через str() для сохранения точности
            return Decimal(str(value))

        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                raise ValueError("Строка не может быть пустой")
            return Decimal(stripped)

        raise TypeError(
            f"Неподдерживаемый тип: {type(value).__name__}, "
            f"значение: {value!r}"
        )

    except (ValueError, TypeError):
        raise
    except InvalidOperation as e:
        raise ValueError(
            f"Невозможно преобразовать в число: {value!r}"
        ) from e
    except Exception as e:
        logger.error(
            f"[validators] Ошибка преобразования в Decimal: {e}",
            exc_info=True,
        )
        raise


def try_to_decimal(value: NumericInput) -> Decimal | None:
    """
    Безопасная версия to_decimal — возвращает None вместо исключения.

    Удобно использовать в UI-слое, где нужно просто проверить,
    является ли строка валидным числом, без обработки исключений.

    Args:
        value: значение для преобразования

    Returns:
        Объект Decimal или None, если преобразование невозможно

    Examples:
        >>> try_to_decimal("123.45")
        Decimal('123.45')
        >>> try_to_decimal("abc")
        None
        >>> try_to_decimal("")
        None
    """
    try:
        return to_decimal(value)
    except (ValueError, TypeError):
        return None