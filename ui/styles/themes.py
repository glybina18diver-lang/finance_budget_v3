SHARED_ACCENTS = {
    # Компактные кнопки ======================
    "COMPACT_SUCCESS": "#4CAF50",
    "COMPACT_SUCCESS_HOVER": "#45a049",
    "COMPACT_SUCCESS_PRESSED": "#3d8b40",

    "COMPACT_DISABLED_BG": "#cccccc",
    "COMPACT_DISABLED_TEXT": "#666666",

    # Info (синий)
    "COMPACT_INFO": "#2196F3",
    "COMPACT_INFO_HOVER": "#1976D2",
    "COMPACT_INFO_PRESSED": "#0D47A1",

    # Warning (оранжевый)
    "COMPACT_WARNING": "#FF9800",
    "COMPACT_WARNING_HOVER": "#F57C00",
    "COMPACT_WARNING_PRESSED": "#EF6C00",

    # Danger (красный)
    "COMPACT_DANGER": "#E74C3C",
    "COMPACT_DANGER_HOVER": "#C0392B",
    "COMPACT_DANGER_PRESSED": "#A93226",

    # Neutral (серый)
    "COMPACT_NEUTRAL": "#6c757d",
    "COMPACT_NEUTRAL_HOVER": "#455A64",
    "COMPACT_NEUTRAL_PRESSED": "#37474F",

    # Сущности (кнопки открытия диалогов) ==================
    "ENTITY_ACCOUNTS": "#2196F3",
    "ENTITY_ACCOUNTS_HOVER": "#1976D2",
    "ENTITY_ACCOUNTS_PRESSED": "#0D47A1",

    "ENTITY_CATEGORIES": "#9C27B0",
    "ENTITY_CATEGORIES_HOVER": "#7B1FA2",
    "ENTITY_CATEGORIES_PRESSED": "#6A1B9A",

    "ENTITY_TRANSFERS": "#FF9800",
    "ENTITY_TRANSFERS_HOVER": "#F57C00",
    "ENTITY_TRANSFERS_PRESSED": "#EF6C00",

    "ENTITY_RECONCILIATION": "#607D8B",
    "ENTITY_RECONCILIATION_HOVER": "#455A64",
    "ENTITY_RECONCILIATION_PRESSED": "#37474F",

    "ENTITY_LOANS": "#795548",
    "ENTITY_LOANS_HOVER": "#5D4037",
    "ENTITY_LOANS_PRESSED": "#4E342E",

    "ENTITY_CREDIT_CARDS": "#E91E63",
    "ENTITY_CREDIT_CARDS_HOVER": "#C2185B",
    "ENTITY_CREDIT_CARDS_PRESSED": "#AD1457",

    # Типографика и геометрия таблиц
    "FONT_SIZE_TABLE": "11px",
    "RADIUS_SMALL": "4px",
}

LIGHT_THEME = {
    **SHARED_ACCENTS,

    # Фоны
    "BG_PRIMARY": "#F5F7FA",
    "BG_SECONDARY": "#FFFFFF",
    
    # Текст
    "TEXT_PRIMARY": "#2C3E50",
    "TEXT_SECONDARY": "#7F8C8D",
    
    # Акцентные цвета (Кнопки, ссылки)
    "ACCENT_PRIMARY": "#2980B9",
    "ACCENT_PRIMARY_HOVER": "#3498DB",
    "ACCENT_PRIMARY_PRESSED": "#21618C",
    
    # Статусные цвета
    "SUCCESS": "#27AE60",
    "SUCCESS_HOVER": "#2ECC71",
    "WARNING": "#F39C12",
    "DANGER": "#C0392B",
    "DANGER_HOVER": "#E74C3C",
    
    # Границы и отключенные состояния
    "BORDER": "#BDC3C7",
    "DISABLED_BG": "#ECF0F1",
    "DISABLED_TEXT": "#95A5A6",   

    # Типографика
    "FONT_FAMILY": "Segoe UI, Roboto, sans-serif",
    "FONT_SIZE_BASE": "13px",
    "FONT_SIZE_COMPACT": "12px",
    "FONT_SIZE_HEADER": "16px",

    # Таблицы
    "TABLE_BG": "#FFFFFF",
    "TABLE_ROW_ALT": "#F8F9FA",        # зебра
    "TABLE_GRID": "#E9ECEF",           # линии сетки
    "TABLE_HEADER_BG": "#F1F3F4",
    "TABLE_HEADER_HOVER": "#E9ECEF",
    "TABLE_HEADER_PRESSED": "#DEE2E6",
    "TABLE_HOVER": "#BBDEFB",          # заметный hover (Blue 100)
    "TABLE_SELECTION": "#90CAF9",      # явное выделение (Blue 200)
    "TABLE_SELECTION_TEXT": "#1A1A1A",

    # Полосы прокрутки
    "SCROLLBAR_BG": "#F8F9FA",
    "SCROLLBAR_HANDLE": "#CED4DA",
    "SCROLLBAR_HANDLE_HOVER": "#ADB5BD",

    # Цвета вкладок (QTabWidget)
    "TAB_BG": "#E8EDF2",      # неактивная вкладка
    "TAB_HOVER": "#DCE4EB",
}

DARK_THEME = {
    **SHARED_ACCENTS,
    
    # Фоны
    "BG_PRIMARY": "#121212",      # Основной фон приложения (Material Dark)
    "BG_SECONDARY": "#1E1E1E",    # Фон карточек, инпутов, сайдбаров
    
    # Текст
    "TEXT_PRIMARY": "#E0E0E0",    # Основной текст (не чисто белый, чтобы не резать глаза)
    "TEXT_SECONDARY": "#A0A0A0",  # Второстепенный текст, плейсхолдеры
    
    # Акцентные цвета (Кнопки, ссылки)
    "ACCENT_PRIMARY": "#3498DB",  # Чуть более яркий синий для темного фона
    "ACCENT_PRIMARY_HOVER": "#5DADE2",
    "ACCENT_PRIMARY_PRESSED": "#2980B9",
    
    # Статусные цвета
    "SUCCESS": "#2ECC71",
    "SUCCESS_HOVER": "#58D68D",
    "WARNING": "#F1C40F",
    "DANGER": "#E74C3C",
    "DANGER_HOVER": "#EC7063",
    
    # Границы и отключенные состояния
    "BORDER": "#333333",          # Темно-серая граница, ненавязчивая
    "DISABLED_BG": "#2C2C2C",
    "DISABLED_TEXT": "#555555",

    # Типографика ==================
    "FONT_FAMILY": "Segoe UI, Roboto, sans-serif", # Шрифт
    "FONT_SIZE_BASE": "13px", # БАзавый размер текста
    "FONT_SIZE_COMPACT": "12px", # Для кнопок
    "FONT_SIZE_HEADER": "16px", 

    # Таблицы
    "TABLE_BG": "#1E1E1E",
    "TABLE_ROW_ALT": "#252525",
    "TABLE_GRID": "#333333",
    "TABLE_HEADER_BG": "#2A2A2A",
    "TABLE_HEADER_HOVER": "#353535",
    "TABLE_HEADER_PRESSED": "#404040",
    "TABLE_HOVER": "#2C4A66",          # заметен на тёмном
    "TABLE_SELECTION": "#3A6EA5",
    "TABLE_SELECTION_TEXT": "#FFFFFF",

    # Полосы прокрутки
    "SCROLLBAR_BG": "#1E1E1E",
    "SCROLLBAR_HANDLE": "#4A4A4A",
    "SCROLLBAR_HANDLE_HOVER": "#5F5F5F",

    # Цвета вкладок (QTabWidget)
    "TAB_BG": "#2A2A2A",
    "TAB_HOVER": "#353535",
}   
