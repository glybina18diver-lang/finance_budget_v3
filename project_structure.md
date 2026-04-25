finance_budget_v3/
│
├── main.py                  # Точка входа
├── config.py                # Настройки (Пути, БД)
│
├── core/                    # ЯДРО ПРИЛОЖЕНИЯ (Логика не зависит от UI)
│   ├── __init__.py
│   ├── models.py            # Модели данных (Account, Transaction, Category)
│   ├── db.py                # Менеджер базы данных (Connection, Transactions)
│   └── repositories/        # Доступ к данным
│       ├── __init__.py
│       ├── base.py          # Базовый репозиторий
│       ├── accounts.py      # Работа со счетами
│       └── transactions.py  # Работа с транзакциями
│
├── services/                # БИЗНЕС-ЛОГИКА
│   ├── __init__.py
│   └── finance_service.py   # Переводы, возвраты, пересчет баланса
│
├── ui/                      # ИНТЕРФЕЙС (PySide6)
│   ├── __init__.py
│   ├── main_window.py       # Главное окно
│   ├── presenters/          # Посредники
│   │   └── main_presenter.py
│   └── dialogs/             # Диалоги
│       └── operation_dialog.py
│
└── utils/                   # Утилиты
    ├── validators.py
    └── formatters.py