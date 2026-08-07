# ui/styles/theme_manager.py
import os
import logging
from PySide6.QtWidgets import QApplication

from ui.styles.themes import LIGHT_THEME

logger = logging.getLogger(__name__)

class ThemeManager:
    """Менеджер тем для приложения."""

    _current_theme: dict = LIGHT_THEME # Словарь активной темы

    @staticmethod
    def apply_theme(theme_dict: dict = None):
        """
        Загружает все QSS-файлы из папки styles, заменяет плейсхолдеры
        на реальные цвета и применяет итоговый стиль к QApplication.
        
        Args:
            theme_dict: Словарь с палитрой цветов. Если None, используется LIGHT_THEME.
        """
        theme = theme_dict or LIGHT_THEME
        
        try:
            # Определяем путь к папке со стилями относительно этого файла
            current_dir = os.path.dirname(os.path.abspath(__file__))
            styles_dir = os.path.join(current_dir)
            
            # Файлы, которые нужно склеить в один большой CSS
            qss_files = ["global.qss", "forms.qss", "buttons.qss", "tables.qss", "widgets.qss", "menus.qss"]
            final_qss = ""
            
            for file_name in qss_files:
                file_path = os.path.join(styles_dir, file_name)
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Магия: заменяем $VARIABLE$ на значение из словаря
                        for key, value in theme.items():
                            placeholder = f"${key}$"
                            content = content.replace(placeholder, value)
                            
                        final_qss += content + "\n"
                else:
                    logger.warning(f"Файл стиля не найден: {file_path}")
                    
            app = QApplication.instance()
            if app:
                app.setStyleSheet(final_qss)
                logger.info("Глобальная тема успешно применена.")
                ThemeManager._current_theme = theme
                # для отладки создаем итоговый CSS файл
                # ThemeManager._dump_for_debug(final_qss)
            else:
                logger.error("QApplication не инициализирован до применения темы.")
                
        except Exception as e:
            logger.error(f"[{ThemeManager.__name__}] Ошибка при загрузке темы: {e}", exc_info=True)
            raise

    @staticmethod
    def darken_color(hex_color: str, percent: int = 20) -> str:
        """
        Затемняет hex-цвет на указанный процент.
        Используется для локальных динамических кнопок (например, ColoredButton).
        
        Args:
            hex_color: Исходный цвет в формате '#RRGGBB' или 'RRGGBB'.
            percent: Процент затемнения (от 0 до 100).
            
        Returns:
            Строка с новым hex-цветом.
        """
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            
            r = max(0, min(255, int(r * (100 - percent) / 100)))
            g = max(0, min(255, int(g * (100 - percent) / 100)))
            b = max(0, min(255, int(b * (100 - percent) / 100)))
            
            return f'#{r:02x}{g:02x}{b:02x}'
        except ValueError as e:
            logger.warning(f"[{ThemeManager.__class__.__name__}] Валидация цвета: {e}")
            raise
        except Exception as e:
            logger.error(f"[{ThemeManager.__class__.__name__}] Ошибка затемнения: {e}", exc_info=True)
            raise

    @classmethod
    def current(cls) -> dict:
        """Возвращает словарь активной темы."""
        return cls._current_theme

    # в ThemeManager
    @staticmethod
    def _dump_for_debug(qss: str):
        """Сохраняет итоговый QSS в файл для ручного разбора.

        Args:
            qss: итоговая строка стилей после подстановки значений
        """
        try:
            path = os.path.join(os.getcwd(), "debug_styles.css")
            with open(path, "w", encoding="utf-8") as f:
                f.write(qss)
            logger.info(f"[{ThemeManager.__name__}] Итоговый QSS сохранён: {path}")
        except Exception as e:
            logger.error(f"[{ThemeManager.__name__}] Ошибка: {e}", exc_info=True)
            raise