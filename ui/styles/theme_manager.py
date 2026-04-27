# ui/styles/theme_manager.py
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QTextStream
import os

class ThemeManager:
    """Менеджер тем для приложения"""
    
    @staticmethod
    def load_global_styles():
        """Загружает глобальные стили из global.qss"""
        style_file = QFile("ui/styles/global.qss")
        if style_file.open(QFile.ReadOnly | QFile.Text):
            stream = QTextStream(style_file)
            style = stream.readAll()
            QApplication.instance().setStyleSheet(style)
            style_file.close()
            return True
        return False
    
    @staticmethod
    def load_stylesheet(file_path):
        """Загружает стили из указанного файла"""
        if not os.path.exists(file_path):
            return ""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    @staticmethod
    def darken_color(hex_color, percent=20):
        """Затемняет hex-цвет на указанный процент"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = max(0, min(255, int(r * (100 - percent) / 100)))
        g = max(0, min(255, int(g * (100 - percent) / 100)))
        b = max(0, min(255, int(b * (100 - percent) / 100)))
        
        return f'#{r:02x}{g:02x}{b:02x}'
    
    @staticmethod
    def lighten_color(hex_color, percent=20):
        """Осветляет hex-цвет на указанный процент"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        r = min(255, int(r + (255 - r) * percent / 100))
        g = min(255, int(g + (255 - g) * percent / 100))
        b = min(255, int(b + (255 - b) * percent / 100))
        
        return f'#{r:02x}{g:02x}{b:02x}'