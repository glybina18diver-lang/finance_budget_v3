"""Форматтеры для данных приложения "Простой Бюджет"."""
from datetime import datetime
from typing import Optional


# Символы валют по умолчанию
DEFAULT_CURRENCY_SYMBOL = '₽'
THOUSAND_SEP = ' '


def format_currency(amount: float, currency_symbol: str = DEFAULT_CURRENCY_SYMBOL,
                    decimals: int = 2) -> str:
    """Форматирование суммы в валюте.

    Args:
        amount: Сумма для форматирования
        currency_symbol: Символ валюты
        decimals: Количество знаков после запятой

    Returns:
        Отформатированная строка суммы
    """
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        amount = 0.0

    # Форматируем с разделением тысяч
    formatted = f"{amount:,.{decimals}f}"
    formatted = formatted.replace(',', THOUSAND_SEP)

    return f"{formatted} {currency_symbol}"


def format_date(date_str: str, format_str: str = '%d.%m.%Y') -> str:
    """Форматирование даты.

    Args:
        date_str: Строка с датой в формате YYYY-MM-DD
        format_str: Формат вывода

    Returns:
        Отформатированная строка даты
    """
    if not date_str:
        return ''

    try:
        # Парсим дату
        if isinstance(date_str, str):
            dt = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            dt = date_str

        return dt.strftime(format_str)
    except (ValueError, TypeError):
        return date_str


def format_transaction_type(trans_type: str) -> str:
    """Форматирование типа транзакции для отображения.

    Args:
        trans_type: Тип транзакции (income, expense, refund, correct)

    Returns:
        Читаемое название типа
    """
    type_map = {
        'income': 'Доход',
        'expense': 'Расход',
        'refund': 'Возврат',
        'correct': 'Корректировка'
    }

    return type_map.get(trans_type, trans_type)


def format_account_type(account_type: str) -> str:
    """Форматирование типа счёта для отображения.

    Args:
        account_type: Тип счёта

    Returns:
        Читаемое название типа
    """
    type_map = {
        'Cash': 'Наличные',
        'Credit Card': 'Кредитная карта',
        'Bank Account': 'Банковский счёт',
        'Counterparty': 'Контрагент'
    }

    return type_map.get(account_type, account_type)


def format_balance(balance: float, show_sign: bool = True) -> str:
    """Форматирование баланса с учётом знака.

    Args:
        balance: Сумма баланса
        show_sign: Показывать ли знак + для положительных значений

    Returns:
        Отформатированная строка баланса
    """
    if balance < 0:
        return f"-{format_currency(abs(balance))}"
    elif show_sign and balance > 0:
        return f"+{format_currency(balance)}"
    else:
        return format_currency(balance)


def format_percentage(value: float, decimals: int = 1) -> str:
    """Форматирование процентов.

    Args:
        value: Значение (0-100 или 0-1)
        decimals: Количество знаков после запятой

    Returns:
        Отформатированная строка процентов
    """
    try:
        value = float(value)
    except (ValueError, TypeError):
        value = 0.0

    # Если значение больше 1, считаем что это проценты (0-100)
    if value > 1:
        value = value

    return f"{value:.{decimals}f}%"


def format_file_size(size_bytes: int) -> str:
    """Форматирование размера файла.

    Args:
        size_bytes: Размер в байтах

    Returns:
        Читаемый размер (KB, MB, GB)
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_period(month_year: str) -> str:
    """Форматирование периода (месяц-год) для отображения.

    Args:
        month_year: Строка в формате YYYY-MM

    Returns:
        Читаемый период (Январь 2024)
    """
    if not month_year or len(month_year) != 7:
        return month_year

    try:
        year, month = month_year.split('-')
        month_num = int(month)

        month_names = {
            1: 'Январь', 2: 'Февраль', 3: 'Март',
            4: 'Апрель', 5: 'Май', 6: 'Июнь',
            7: 'Июль', 8: 'Август', 9: 'Сентябрь',
            10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
        }

        return f"{month_names.get(month_num, '')} {year}"
    except (ValueError, AttributeError):
        return month_year


def truncate_string(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """Обрезание строки до максимальной длины.

    Args:
        text: Исходная строка
        max_length: Максимальная длина
        suffix: Суффикс для обрезанных строк

    Returns:
        Обрезанная строка
    """
    if not text or len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix
