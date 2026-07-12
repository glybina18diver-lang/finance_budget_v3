# Finance Budget V3

💰 Десктопное приложение для учёта личных (и не только) финансов.

> ⚠️ **Статус:** Активная разработка (pre-alpha). API и структура могут меняться.

## 🚀 Быстрый старт

```bash
git clone https://github.com/glybina18diver-lang/finance_budget_v3.git
cd finance_budget_v3
pip install -r requirements.txt
python main.py
```

## 🛠 Технологии

- Python 3.14
- PySide6 (Qt6) — GUI
- SQLite — локальная БД
- Matplotlib — графики

## 📁 Структура

```
finance_budget_v3/
├── main.py              # Точка входа
├── config.py            # Конфигурация
├── core/                # Ядро (модели, репозитории, БД, логгер)
├── services/            # Бизнес-логика
├── ui/                  # Интерфейс (диалоги + презентеры)
└── utils/               # Утилиты
```

## 🏗 Архитектура

**MVP (Model-View-Presenter):**
- `ui/dialogs/` — только отображение
- `ui/presenters/` — связка UI и бизнес-логики
- `services/` — правила и валидация
- `core/repositories/` — работа с БД

## 📊 Реализовано

- ✅ Управление счетами (CRUD)
- ✅ Транзакции (доходы/расходы)
- ✅ Категории
- ✅ Кредитные карты (льготный период, проценты, платежи)
- ✅ Займы (выданные/полученные)
- ✅ Система логирования с ротацией

## 🚧 В планах

- [ ] Бюджетирование
- [ ] Экспорт/импорт данных
- [ ] Расширенная аналитика

## 📝 Лицензия

MIT

---

*Предыдущие версии: [finance_budget_archive](https://github.com/glybina18diver-lang/finance_budget_archive)*
