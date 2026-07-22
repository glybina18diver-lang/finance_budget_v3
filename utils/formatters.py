"""Форматтеры для данных приложения "Простой Бюджет"."""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Union

from utils.constants import MONEY_DECIMALS, MONEY_PRECISION


# Символы валют по умолчанию
DEFAULT_CURRENCY_SYMBOL = '₽'
THOUSAND_SEP = ' '

# Тип, который может быть отформатирован как деньги
MoneyValue = Union[Decimal, float, int, str]


def format_currency(
    amount: MoneyValue,
    currency_symbol: str = DEFAULT_CURRENCY_SYMBOL,
    decimals: int = MONEY_DECIMALS,
) -> str:
    """Форматирование суммы в валюте.

    Args:
        amount: Сумма для форматирования (Decimal, float, int, str)
        currency_symbol: Символ валюты
        decimals: Количество знаков после запятой

    Returns:
        Отформатированная строка суммы
    """
    try:
        if not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
        amount = amount.quantize(MONEY_PRECISION)
    except (ValueError, TypeError):
        amount = Decimal("0.00")

    # Форматируем с разделением тысяч
    formatted = f"{amount:,.{decimals}f}"
    formatted = formatted.replace(",", THOUSAND_SEP)

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
        'CreditCard': 'Кредитная карта',
        'BankAccount': 'Банковский счёт',
        'Counterparty': 'Контрагент'
    }

    return type_map.get(account_type, account_type)


def format_balance(
    balance: MoneyValue,
    show_sign: bool = True,
    currency_symbol: str = DEFAULT_CURRENCY_SYMBOL,
) -> str:
    """Форматирование баланса с учётом знака.

    Args:
        balance: Сумма баланса (Decimal, float, int, str)
        show_sign: Показывать ли знак + для положительных значений
        currency_symbol: Символ валюты

    Returns:
        Отформатированная строка баланса
    """
    if not isinstance(balance, Decimal):
        balance = Decimal(str(balance))

    if balance < 0:
        return f"-{format_currency(abs(balance), currency_symbol)}"
    elif show_sign and balance > 0:
        return f"+{format_currency(balance, currency_symbol)}"
    else:
        return format_currency(balance, currency_symbol)


def format_percentage(
    value: Union[Decimal, float, int, str],
    decimals: int = 1,
) -> str:
    """Форматирование процентов.

    Args:
        value: Значение (0-100 или 0-1)
        decimals: Количество знаков после запятой

    Returns:
        Отформатированная строка процентов
    """
    try:
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
    except (ValueError, TypeError):
        value = Decimal("0")

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


def format_decimal(value: Decimal, decimals: int = MONEY_DECIMALS) -> str:
    """Форматирует Decimal в строку для отображения в UI.

    Args:
        value: Decimal для форматирования
        decimals: Количество знаков после запятой

    Returns:
        Отформатированная строка (например, "1 234.56")
    """
    precision = Decimal("0." + "0" * decimals)
    quantized = value.quantize(precision)
    formatted = f"{quantized:,.{decimals}f}"
    return formatted.replace(",", THOUSAND_SEP)
