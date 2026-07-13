# core/models.py
from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict
from datetime import datetime, date
from decimal import Decimal

@dataclass
class BaseModel:
    """Базовый класс с ID."""
    id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}

@dataclass
class Account(BaseModel):
    """Модель счета (полное соответствие схеме V2)."""
    name: str = ""
    account_type: str = "Cash"  # Cash, BankAccount, CreditCard, Counterparty
    
    # Балансы
    initial_balance: float = 0.0
    current_balance: float = 0.0
    
    # Специфичные поля для CreditCard
    # все пернесены в таблицу credit_cards
    
    # Системные
    is_active: bool = True
    is_system: bool = False
    currency: str = "RUB"

@dataclass
class Category(BaseModel):
    """Модель категории (полное соответствие схеме V2)."""
    name: str = ""
    cat_type: str = "expense"  # income, expense
    
    # Бюджетирование
    budget_amount_monthly: float = 0.0
    
    # Иерархия
    parent_id: Optional[int] = None
    
    # Визуал
    color: str = "#3498db"
    icon: str = ""
    
    # Системные
    is_system: bool = False
    is_active: bool = True


@dataclass
class Transaction(BaseModel):
    """Модель транзакции (полное соответствие схеме V2)."""
    date: str = ""  # YYYY-MM-DD
    amount: float = 0.0
    trans_type: str = "expense"  # income, expense, refund, correct
    
    # Связи
    account_id: int = 0
    category_id: Optional[int] = None
    
    # Детали
    description: str = ""
    quantity: float = 1.0
    # unit_price вычисляется в БД как GENERATED ALWAYS AS (amount / quantity), 
    # но в модели мы можем хранить его для удобства чтения
    unit_price: Optional[float] = None 
    
    # Возвраты
    original_transaction_id: Optional[int] = None
    
    # Время
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Transfer:
    """Модель перевода (Обновленная схема V3)."""
    id: Optional[int] = None
    date: str = ""
    amount: float = 0.0
    type: str = "internal"        # ← внутренний / внешний
    from_account_id: int = 0
    to_account_id: int = 0
    description: Optional[str] = None
    is_system: bool = False       # ← True если системный (займ и др.)
    loan_id: Optional[int] = None # ← ID займа, если есть
    
@dataclass
class Loan(BaseModel):
    """Модель займа (из схемы V2)."""
    account_id: int = 0
    counterparty_account_id: int = 0
    contact_name: str = ""
    loan_type: str = "issued"  # issued, received
    loan_amount: float = 0.0
    remaining: float = 0.0
    # interest_rate: float = 0.0 в займа не исползуется
    issue_date: str = ""
    due_date: Optional[str] = None
    description: str = ""
    status: str = "active"  # active, paid, default
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class LoanPayment(BaseModel):
    """Платеж по займу (из схемы V2)."""
    loan_id: int = 0
    payment_date: str = ""
    payment_amount: float = 0.0
    interest_amount: float = 0.0
    principal_amount: float = 0.0
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Budget(BaseModel):
    """Бюджет на месяц (из схемы V2)."""
    category_id: int = 0
    month_year: str = ""  # YYYY-MM
    planned_amount: float = 0.0
    actual_amount: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class CreditCard:
    """
    Модель кредитной карты.
    
    Все пользовательские поля обязательны для заполнения при создании.
    Системные поля (id, is_active, created_at) заполняются автоматически БД или кодом.
    """
    # --- Пользовательские поля (обязательные, без дефолтов) ---
    account_id: int
    name: str
    annual_rate: Decimal
    grace_months: int
    min_payment_percent: Decimal
    payment_day: int
    statement_day: int
    credit_limit: Decimal
    
    # --- Системные поля (необязательные, с дефолтами) ---
    id: Optional[int] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
@dataclass
class Tranche:
    """
    Транш — независимая порция долга по кредитной карте.
    
    Каждая операция (покупка/перевод/возврат) создаёт отдельный транш
    со своим льготным периодом и статусом.
    """
    id: Optional[int] = None
    card_id: int = 0
    tranche_type: str = "purchase"  # purchase | transfer | refund
    original_amount: Decimal = Decimal("0.00")
    remaining_amount: Decimal = Decimal("0.00")
    commission: Decimal = Decimal("0.00")  # для переводов
    transaction_date: date = field(default_factory=date.today)
    grace_end_date: Optional[date] = None
    status: str = "in_grace"  # in_grace | grace_expired | partial | paid
    is_retroactive_triggered: bool = False
    linked_transaction_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class InterestAccrual:
    """
    Снимок начисления процентов по траншу на определённую дату.
    
    Хранит историю начислений (ретроактивных и ежедневных).
    """
    id: Optional[int] = None
    tranche_id: int = 0
    accrual_date: date = field(default_factory=date.today)
    interest_type: str = "daily"  # retroactive | daily
    amount: Decimal = Decimal("0.00")
    paid_amount: Decimal = Decimal("0.00")
    is_paid: bool = False
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class Statement:
    """
    Биллинговый цикл (выписка).
    
    Формируется 1-го числа каждого месяца.
    Содержит сводку по долгу за предыдущий месяц.
    """
    id: Optional[int] = None
    card_id: int = 0
    statement_date: date = field(default_factory=date.today)
    due_date: Optional[date] = None  # последний день месяца
    opening_balance: Decimal = Decimal("0.00")
    new_charges: Decimal = Decimal("0.00")
    payments_received: Decimal = Decimal("0.00")
    interest_charged: Decimal = Decimal("0.00")
    closing_balance: Decimal = Decimal("0.00")
    min_payment_required: Decimal = Decimal("0.00")
    status: str = "open"  # open | closed | overdue
    created_at: datetime = field(default_factory=datetime.now)