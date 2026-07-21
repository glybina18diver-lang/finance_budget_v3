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
    account_type: str = "Cash"  # Cash, BankAccount, CreditCard, Counterparty, Credit
    
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
    """
    Модель займа/кредита.
    
    Поддерживает два типа сущностей через поле source_type:
    - 'bank': банковский кредит (создаёт системный счёт Credit)
    - 'person': займ у физического лица (использует счёт Counterparty)
    
    Для банковских кредитов (source_type='bank'):
    - loan_purpose='consumer': деньги переведены на целевой счёт
    - loan_purpose='purchase': сразу совершена покупка (POS-кредит)
    """
    name: str = ""
    
    # Разделение сущностей
    source_type: str = "bank"            # 'bank' / 'person'
    loan_type: str = "received"          # 'issued' / 'received'
    loan_purpose: Optional[str] = None   # 'consumer' / 'purchase' (только для bank)
    
    # Суммы
    loan_amount: Decimal = 0.0
    remaining: Decimal = 0.0
    interest_rate: Decimal = 0.0
    term_months: Optional[int] = None
    
    # Даты
    issue_date: str = ""
    due_date: Optional[str] = None
    
    # Связи со счетами
    account_id: int = 0                  # Счёт Credit (для bank) или мой счёт (для person)
    counterparty_account_id: Optional[int] = None  # Target счёт / счёт Counterparty
    
    # Специфичные поля для POS-кредита
    purchase_transaction_id: Optional[int] = None
    
    # Специфичные поля для займов у людей
    contact_name: Optional[str] = None
    
    # Общее
    description: str = ""
    status: str = "active"               # 'active' / 'paid' / 'default'
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
    
    account_id обязателен. Все параметры карты опциональны.
    Системные поля (id, is_active, created_at) заполняются автоматически.
    """
    # --- Обязательные поля ---
    account_id: int
    
    # --- Опциональные параметры карты ---
    credit_limit: Optional[Decimal] = None
    annual_rate: Optional[Decimal] = None
    grace_months: Optional[int] = None
    min_payment_percent: Optional[Decimal] = None
    payment_day: Optional[int] = None
    statement_day: Optional[int] = None
    
    # --- Системные поля (необязательные, с дефолтами) ---
    id: Optional[int] = None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    # --- Поля только для чтения (не сохраняются в эту таблицу, приходят из JOIN) ---
    account_name: Optional[str] = None
    
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