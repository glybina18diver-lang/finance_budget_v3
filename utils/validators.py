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


from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

def to_decimal(value: NumericInput, precision: int = 2) -> Decimal:
    """
    Универсально преобразует числовое значение в Decimal с округлением.

    Поддерживает типы: int, float, str, Decimal.
    Для float используется преобразование через str(), чтобы избежать
    потери точности (Decimal(0.1) != Decimal('0.1')).
    
    По умолчанию округляет результат до 2 знаков после запятой
    (режим ROUND_HALF_UP — стандартное математическое округление).

    Args:
        value: значение для преобразования. Допустимые типы:
               int, float, str (числовое представление), Decimal.
               None и пустая строка вызывают ValueError.
        precision: количество знаков после запятой для округления.
                   Если None — округление не выполняется.
                   По умолчанию 2 (для финансовых операций).

    Returns:
        Объект Decimal с точным числовым значением,
        округлённый до указанного количества знаков

    Raises:
        ValueError: если значение None, пустая строка или
                    не может быть преобразовано в число
        TypeError: если тип значения не поддерживается

    Examples:
        >>> to_decimal(100)
        Decimal('100.00')
        >>> to_decimal(123.456)
        Decimal('123.46')
        >>> to_decimal("99.99")
        Decimal('99.99')
        >>> to_decimal("553.05486")
        Decimal('553.05')
        >>> to_decimal(Decimal("50.00"))
        Decimal('50.00')
        >>> to_decimal(100, precision=None)
        Decimal('100')
    """
    try:
        if value is None:
            raise ValueError("Значение не может быть None")

        if isinstance(value, Decimal):
            result = value
        elif isinstance(value, bool):
            raise TypeError(
                f"Тип bool не поддерживается, получено: {value!r}"
            )
        elif isinstance(value, int):
            result = Decimal(value)
        elif isinstance(value, float):
            # Преобразование через str() для сохранения точности
            result = Decimal(str(value))
        elif isinstance(value, str):
            # Удаляем пробелы (например, '1 000,50' -> '1000.50')
            value = value.replace(' ', '')
            logger.debug(f"[to_decimal] Убираем пробелы: {value}")

            # Заменяем запятую на точку для корректного преобразования
            value = value.replace(',', '.')
            logger.debug(f"[to_decimal] Заменяем запятую на точку: {value}")

            stripped = value.strip()
            if not stripped:
                raise ValueError("Строка не может быть пустой")
            result = Decimal(stripped)
        else:
            raise TypeError(
                f"Неподдерживаемый тип: {type(value).__name__}, "
                f"значение: {value!r}"
            )

        # Округление до указанного количества знаков после запятой
        if precision is not None:
            quantize_exp = Decimal(10) ** -precision  # 10^-2 = 0.01
            result = result.quantize(quantize_exp, rounding=ROUND_HALF_UP)
            # logger.debug(f"[to_decimal] Округление до {precision} знаков: {result}")

        return result

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