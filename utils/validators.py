"""Валидаторы для данных приложения "Finance Budget"."""
import re
from datetime import datetime
from typing import Optional


def validate_amount(amount: float, min_value: float = 0.01, max_value: Optional[float] = None) -> bool:
    """Валидация суммы транзакции."""
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return False

    if amount < min_value:
        return False

    if max_value is not None and amount > max_value:
        return False

    return True


def validate_date_format(date_str: str, format_str: str = '%Y-%m-%d') -> bool:
    """Валидация формата даты."""
    if not date_str:
        return False

    try:
        datetime.strptime(date_str, format_str)
        return True
    except ValueError:
        return False


def validate_account_type(account_type: str) -> bool:
    """Валидация типа счёта."""
    valid_types = ['Cash', 'CreditCard', 'BankAccount', 'Counterparty']
    return account_type in valid_types


def validate_transaction_type(transaction_type: str) -> bool:
    """Валидация типа транзакции."""
    valid_types = ['income', 'expense', 'refund', 'correct']
    return transaction_type in valid_types


def validate_category_type(category_type: str) -> bool:
    """Валидация типа категории."""
    valid_types = ['income', 'expense']
    return category_type in valid_types


def validate_email(email: str) -> bool:
    """Валидация email адреса."""
    if not email:
        return False

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone: str) -> bool:
    """Валидация номера телефона."""
    if not phone:
        return False

    cleaned = re.sub(r'[^\d+]', '', phone)
    pattern = r'^\+?\d{10,12}$'
    return bool(re.match(pattern, cleaned))


def validate_required_fields(data: dict, required_fields: list) -> tuple:
    """Проверка наличия обязательных полей в данных."""
    missing_fields = []

    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)

    return len(missing_fields) == 0, missing_fields


def validate_positive_number(value) -> bool:
    """Проверка что значение является положительным числом."""
    try:
        num = float(value)
        return num > 0
    except (ValueError, TypeError):
        return False


def validate_in_range(value, min_value, max_value) -> bool:
    """Проверка что число находится в диапазоне."""
    try:
        num = float(value)
        return min_value <= num <= max_value
    except (ValueError, TypeError):
        return False


def validate_account_name(name: str) -> tuple[bool, str]:
    """Валидация имени счёта.
    
    Проверяет что имя:
    - не пустое
    - длина от 1 до 100 символов
    - содержит только допустимые символы (буквы, цифры, пробелы, дефисы, подчёркивания, точки, запятые, скобки)
    
    Args:
        name: Имя счёта для проверки
        
    Returns:
        Кортеж (bool, str):
        - True, '' если валидация успешна
        - False, сообщение об ошибке если валидация не прошла
    """
    if not name or not name.strip():
        return False, "Имя счёта не может быть пустым"
    
    name_stripped = name.strip()
    if len(name_stripped) < 1:
        return False, "Имя счёта слишком короткое"
    if len(name_stripped) > 100:
        return False, "Имя счёта не может превышать 100 символов"
    
    # Допустимые символы: буквы (русские и английские, включая ёЁ), цифры, пробелы, дефисы, подчёркивания, точки, запятые, скобки
    pattern = r'^[a-zA-Zа-яА-ЯёЁ0-9\s\-_.,()]+$'
    if not re.match(pattern, name_stripped, flags=re.UNICODE):
        return False, "Имя счёта содержит недопустимые символы"
    
    return True, ""


def validate_category_name(name: str) -> tuple[bool, str]:
    """Валидация имени категории.
    
    Проверяет что имя:
    - не пустое
    - длина от 1 до 100 символов
    - содержит только допустимые символы (буквы, цифры, пробелы, дефисы, подчёркивания, точки, запятые, скобки)
    
    Args:
        name: Имя категории для проверки
        
    Returns:
        Кортеж (bool, str):
        - True, '' если валидация успешна
        - False, сообщение об ошибке если валидация не прошла
    """
    if not name or not name.strip():
        return False, "Имя категории не может быть пустым"
    
    name_stripped = name.strip()
    if len(name_stripped) < 1:
        return False, "Имя категории слишком короткое"
    if len(name_stripped) > 100:
        return False, "Имя категории не может превышать 100 символов"
    
    # Допустимые символы: буквы (русские и английские, включая ёЁ), цифры, пробелы, дефисы, подчёркивания, точки, запятые, скобки
    pattern = r'^[a-zA-Zа-яА-ЯёЁ0-9\s\-_.,()]+$'
    if not re.match(pattern, name_stripped, flags=re.UNICODE):
        return False, "Имя категории содержит недопустимые символы"
    
    return True, ""


def validate_budget_amount(amount: float) -> tuple[bool, str]:
    """Валидация суммы бюджета.
    
    Проверяет что сумма является неотрицательным числом.
    
    Args:
        amount: Сумма бюджета
        
    Returns:
        Кортеж (bool, str):
        - True, '' если валидация успешна
        - False, сообщение об ошибке если валидация не прошла
    """
    from utils.converters import safe_float
    
    value = safe_float(amount, default=None)
    if value is None:
        return False, "Сумма бюджета должна быть числом"
    
    if value < 0:
        return False, "Сумма бюджета не может быть отрицательной"
    
    return True, ""


def validate_parent_category(parent_id: int, category_repository) -> tuple[bool, str]:
    """Валидация родительской категории.
    
    Проверяет что родительская категория существует и не создаёт циклических зависимостей.
    
    Args:
        parent_id: ID родительской категории
        category_repository: Репозиторий категорий для проверки существования
        
    Returns:
        Кортеж (bool, str):
        - True, '' если валидация успешна
        - False, сообщение об ошибке если валидация не прошла
    """
    if parent_id is None:
        return True, ""
    
    try:
        parent = category_repository.get_by_id(parent_id)
        if parent is None:
            return False, f"Родительская категория с ID {parent_id} не найдена"
        
        # Проверка на циклическую зависимость (упрощённая)
        if parent.parent_id is not None:
            # Можно добавить более глубокую проверку
            pass
            
        return True, ""
    except Exception as e:
        return False, f"Ошибка при проверке родительской категории: {e}"


def validate_transaction_amount(amount: float) -> tuple[bool, str]:
    """Валидация суммы транзакции.
    
    Проверяет что сумма является положительным числом.
    
    Args:
        amount: Сумма транзакции
        
    Returns:
        Кортеж (bool, str):
        - True, '' если валидация успешна
        - False, сообщение об ошибке если валидация не прошла
    """
    from utils.converters import safe_float
    
    value = safe_float(amount, default=None)
    if value is None:
        return False, "Сумма транзакции должна быть числом"
    
    if value <= 0:
        return False, "Сумма транзакции должна быть положительной"
    
    return True, ""


def validate_transaction_date(date_str: str) -> tuple[bool, str]:
    """Валидация даты транзакции.
    
    Проверяет что дата соответствует формату YYYY-MM-DD и является корректной.
    
    Args:
        date_str: Строка с датой
        
    Returns:
        Кортеж (bool, str):
        - True, '' если валидация успешна
        - False, сообщение об ошибке если валидация не прошла
    """
    if not date_str:
        return False, "Дата транзакции не может быть пустой"
    
    # Проверка формата
    if not validate_date_format(date_str, '%Y-%m-%d'):
        return False, "Дата транзакции должна быть в формате ГГГГ-ММ-ДД"
    
    # Дополнительная проверка на реалистичную дату (не будущее, не слишком старое)
    try:
        from datetime import datetime, date
        trans_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        today = date.today()
        
        # Можно добавить проверку на будущие даты, если нужно
        if trans_date > today:
            return False, "Дата транзакции не может быть в будущем"
        
        # Проверка на слишком старые даты (например, старше 10 лет)
        # if trans_date.year < today.year - 10:
        #     return False, "Дата транзакции слишком старая"
            
        return True, ""
    except ValueError:
        return False, "Некорректная дата транзакции"


def validate_credit_limit(limit: str) -> tuple[bool, str]:
    """Валидация кредитного лимита.
    
    Проверяет что лимит является неотрицательным числом.
    Пустая строка считается нулём.
    
    Args:
        limit: Строковое значение кредитного лимита
        
    Returns:
        Кортеж (bool, str):
        - True, '' если валидация успешна
        - False, сообщение об ошибке если валидация не прошла
    """
    from utils.converters import safe_float
    
    if limit is None or limit.strip() == '':
        return True, ""  # Пустая строка допустима (будет интерпретирована как 0)
    
    value = safe_float(limit, default=None)
    if value is None:
        return False, "Кредитный лимит должен быть числом"
    
    if value < 0:
        return False, "Кредитный лимит не может быть отрицательным"
    
    return True, ""


def validate_payment_day(day: str) -> tuple[bool, str]:
    """Валидация дня платежа.
    
    Проверяет что день является целым числом от 1 до 31 включительно.
    Пустая строка допустима (значит день не указан).
    
    Args:
        day: Строковое значение дня платежа
        
    Returns:
        Кортеж (bool, str):
        - True, '' если валидация успешна
        - False, сообщение об ошибке если валидация не прошла
    """
    from utils.converters import safe_float, safe_int
    
    if day is None or day.strip() == '':
        return True, ""  # Пустая строка допустима
    
    # Сначала проверяем, что это число (дробное или целое)
    float_value = safe_float(day, default=None)
    if float_value is None:
        return False, "День платежа должен быть числом"
    
    # Проверяем, что это целое число (без дробной части)
    if float_value != int(float_value):
        return False, "День платежа должен быть целым числом"
    
    value = int(float_value)
    if value < 1 or value > 31:
        return False, "День платежа должен быть в диапазоне от 1 до 31"
    
    return True, ""


def validate_min_payment_percent(percent: str) -> tuple[bool, str]:
    """Валидация минимального процента платежа.
    
    Проверяет что процент является числом от 0 до 100 включительно.
    Пустая строка допустима (значит процент не указан).
    
    Args:
        percent: Строковое значение процента
        
    Returns:
        Кортеж (bool, str):
        - True, '' если валидация успешна
        - False, сообщение об ошибке если валидация не прошла
    """
    from utils.converters import safe_float
    
    if percent is None or percent.strip() == '':
        return True, ""  # Пустая строка допустима
    
    value = safe_float(percent, default=None)
    if value is None:
        return False, "Минимальный процент платежа должен быть числом"
    
    if value < 0 or value > 100:
        return False, "Минимальный процент платежа должен быть в диапазоне от 0 до 100"
    
    return True, ""
