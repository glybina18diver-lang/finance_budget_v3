# ui/widgets/colored_button.py
from PySide6.QtWidgets import QPushButton, QDialogButtonBox
from ui.styles.theme_manager import ThemeManager

class CompactButton(QPushButton):
    """Компактная кнопка с минимальным размером (базовый стиль)"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("compactButton")
        # self.setStyleSheet("""
        #     QPushButton {
        #         background-color: #4CAF50;
        #         color: white;
        #         border: none;
        #         border-radius: 4px;
        #         padding: 5px 10px;
        #         font-weight: 500;
        #         font-size: 12px;
        #         margin: 1px;
        #     }
        #     QPushButton:hover {
        #         background-color: #45a049;
        #     }
        #     QPushButton:pressed {
        #         background-color: #3d8b40;
        #     }
        #     QPushButton:disabled {
        #         background-color: #cccccc;
        #         color: #666666;
        #     }
        # """)
        self.setFixedHeight(26)


class FilterButton(QPushButton):
    """Компактная кнопка для фильтров"""
    
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setObjectName("filterButton")
        self.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 11px;
                margin: 1px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.setFixedHeight(26)


class ColoredButton(QPushButton):
    """Динамическая цветная кнопка с автоматическим затемнением"""
    
    def __init__(self, text="", color="#2196F3", parent=None):
        super().__init__(text, parent)
        self._base_color = color
        self._update_style()
        self.setFixedHeight(26)
    
    def _update_style(self):
        """Обновляет стиль кнопки на основе текущего цвета"""
        hover_color = ThemeManager.darken_color(self._base_color, 20)
        pressed_color = ThemeManager.darken_color(self._base_color, 30)
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {self._base_color};
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 12px;
                font-weight: 500;
                font-size: 11px;
                margin: 0px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
                color: #666666;
            }}
        """)
    
    def set_color(self, color):
        """Устанавливает новый цвет кнопки"""
        self._base_color = color
        self._update_style()
    
    def get_color(self):
        """Возвращает текущий цвет кнопки"""
        return self._base_color


class ColoredDialogButtonBox(QDialogButtonBox):
    """QDialogButtonBox с возможностью указать цвет кнопок"""
    
    def __init__(self, color="#2196F3", parent=None):
        super().__init__(parent)
        self._base_color = color
        self._update_style()
    
    def _update_style(self):
        """Обновляет стиль всех кнопок внутри на основе текущего цвета"""
        hover_color = ThemeManager.darken_color(self._base_color, 20)
        pressed_color = ThemeManager.darken_color(self._base_color, 30)
        
        style = f"""
            QDialogButtonBox QPushButton {{
                background-color: {self._base_color};
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 12px;
                font-weight: 500;
                font-size: 11px;
                margin: 0px;
                min-width: 80px;
                min-height: 26px;
                max-height: 26px;
                height: 26px;
            }}
            QDialogButtonBox QPushButton:hover {{
                background-color: {hover_color};
            }}
            QDialogButtonBox QPushButton:pressed {{
                background-color: {pressed_color};
            }}
            QDialogButtonBox QPushButton:disabled {{
                background-color: #cccccc;
                color: #666666;
            }}
        """
        self.setStyleSheet(style)
    
    def set_color(self, color):
        """Устанавливает новый цвет кнопок"""
        self._base_color = color
        self._update_style()
    
    def get_color(self):
        """Возвращает текущий цвет кнопок"""
        return self._base_color