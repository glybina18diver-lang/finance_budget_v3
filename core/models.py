# core/models.py
from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict
from datetime import datetime

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
    account_type: str = "Cash"  # Cash, Bank Account, Credit Card, Counterparty
    
    # Балансы
    initial_balance: float = 0.0
    current_balance: float = 0.0
    
    # Специфичные поля для Credit Card
    credit_limit: Optional[float] = None       # Лимит кредита
    payment_due_day: Optional[int] = None      # День оплаты (1-31)
    min_payment_percent: Optional[float] = None # Минимальный платеж в %
    last_payment_date: Optional[str] = None    # Дата последнего платежа (YYYY-MM-DD)
    
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