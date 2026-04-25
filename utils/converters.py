"""Утилиты для безопасного преобразования типов данных."""
from typing import Any, Optional, Union


def safe_float(value: Any, default: float = 0.0) -> float:
    """Безопасное преобразование в float.

    Args:
        value: Значение для преобразования
        default: Значение по умолчанию, если преобразование не удалось

    Returns:
        Преобразованное значение или default
    """
    if value is None:
        return default

    try:
        return float(value)
    except (ValueError, TypeError, AttributeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Безопасное преобразование в int.
    
    Args:
        value: Значение для преобразования
        default: Значение по умолчанию, если преобразование не удалось
    
    Returns:
        Преобразованное значение или default
    """
    if value is None:
        return default
    
    try:
        return int(float(value))  # Сначала в float, потом в int
    except (ValueError, TypeError, AttributeError):
        return default


def safe_str(value: Any, default: str = '') -> str:
    """Безопасное преобразование в строку.
    
    Args:
        value: Значение для преобразования
        default: Значение по умолчанию, если преобразование не удалось
    
    Returns:
        Преобразованное значение или default
    """
    if value is None:
        return default
    
    try:
        return str(value)
    except (ValueError, TypeError, AttributeError):
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    """Безопасное преобразование в bool.
    
    Args:
        value: Значение для преобразования
        default: Значение по умолчанию, если преобразование не удалось
    
    Returns:
        Преобразованное значение или default
    """
    if value is None:
        return default
    
    # Уже bool
    if isinstance(value, bool):
        return value
    
    # Числа
    if isinstance(value, (int, float)):
        return bool(value)
    
    # Строки
    if isinstance(value, str):
        lower = value.lower().strip()
        if lower in ('true', '1', 'yes', 'on', 'да'):
            return True
        elif lower in ('false', '0', 'no', 'off', 'нет'):
            return False
    
    return default


def safe_list(value: Any, default: Optional[list] = None) -> list:
    """Безопасное преобразование в список.
    
    Args:
        value: Значение для преобразования
        default: Значение по умолчанию
    
    Returns:
        Преобразованное значение или default
    """
    if value is None:
        return default if default is not None else []
    
    if isinstance(value, list):
        return value
    
    if isinstance(value, (tuple, set, frozenset)):
        return list(value)
    
    if isinstance(value, str):
        if not value.strip():
            return default if default is not None else []
        return [value]
    
    return default if default is not None else []


def parse_bool(value: Union[str, int, bool]) -> Optional[bool]:
    """Парсинг булева значения из строки.
    
    Args:
        value: Значение для парсинга
    
    Returns:
        Булево значение или None если не удалось распознать
    """
    if isinstance(value, bool):
        return value
    
    if isinstance(value, str):
        lower = value.lower().strip()
        if lower in ('true', '1', 'yes', 'on', 'да', 'y'):
            return True
        if lower in ('false', '0', 'no', 'off', 'нет', 'n'):
            return False
    
    return None


def normalize_date(date_str: str) -> Optional[str]:
    """Нормализация даты к формату YYYY-MM-DD.
    
    Args:
        date_str: Строка с датой в любом формате
    
    Returns:
        Нормализованная строка даты или None
    """
    from datetime import datetime
    
    if not date_str:
        return None
    
    formats = [
        '%Y-%m-%d',
        '%d.%m.%Y',
        '%d/%m/%Y',
        '%Y/%m/%d',
        '%d-%m-%Y',
        '%m/%d/%Y',
        '%Y%m%d'
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    
    return None


def clamp(value: Union[int, float], min_value: Union[int, float],
          max_value: Union[int, float]) -> Union[int, float]:
    """Ограничение значения диапазоном.
    
    Args:
        value: Значение для ограничения
        min_value: Минимальное значение
        max_value: Максимальное значение
    
    Returns:
        Значение в пределах диапазона
    """
    try:
        value = float(value)
        min_value = float(min_value)
        max_value = float(max_value)
        return max(min_value, min(max_value, value))
    except (ValueError, TypeError):
        return min_value


def default_if_none(value: Any, default: Any) -> Any:
    """Возвращает значение по умолчанию, если value is None.
    
    Args:
        value: Проверяемое значение
        default: Значение по умолчанию
    
    Returns:
        value если не None, иначе default
    """
    return value if value is not None else default


def safe_date(value: Any, default: str = '') -> str:
    """Безопасное преобразование в строку даты в формате YYYY-MM-DD.
    
    Args:
        value: Значение для преобразования (строка, datetime, date)
        default: Значение по умолчанию, если преобразование не удалось
    
    Returns:
        Строка даты в формате YYYY-MM-DD или default
    """
    if value is None:
        return default
    
    # Если уже строка, пытаемся нормализовать
    if isinstance(value, str):
        normalized = normalize_date(value)
        if normalized is not None:
            return normalized
        return default
    
    # Если datetime или date объект
    try:
        from datetime import datetime, date
        if isinstance(value, (datetime, date)):
            return value.strftime('%Y-%m-%d')
    except (AttributeError, TypeError):
        pass
    
    # Любой другой тип - пытаемся преобразовать в строку и нормализовать
    try:
        str_value = str(value)
        normalized = normalize_date(str_value)
        if normalized is not None:
            return normalized
    except Exception:
        pass
    
    return default


def coalesce(*values) -> Any:
    """Возвращает первое не-None значение.
    
    Args:
        values: Список значений для проверки
    
    Returns:
        Первое не-None значение или None
    """
    for value in values:
        if value is not None:
            return value
    return None
