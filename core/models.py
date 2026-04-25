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
    
    # Специфичные поля из V2
    credit_limit: float = 0.0
    payment_due_day: int = 1
    min_payment_percent: float = 5.0
    last_payment_date: Optional[str] = None
    
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
class Transfer(BaseModel):
    """Модель перевода (из схемы V2)."""
    date: str = ""
    amount: float = 0.0
    from_account_id: int = 0
    to_account_id: int = 0
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Loan(BaseModel):
    """Модель займа (из схемы V2)."""
    account_id: int = 0
    counterparty_account_id: int = 0
    contact_name: str = ""
    loan_type: str = "issued"  # issued, received
    loan_amount: float = 0.0
    outstanding_amount: float = 0.0
    interest_rate: float = 0.0
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