# ui/widgets/buttons.py
import logging

from PySide6.QtWidgets import QPushButton

logger = logging.getLogger(__name__)


class CompactButton(QPushButton):
    """Компактная кнопка с цветом по назначению и фиксированной высотой 26px.

    Размер определяется variant (QSS), цвет — purpose (QSS + тема).
    Высота управляется только из Python, чтобы padding в QSS
    не увеличивал итоговый размер кнопки.
    """

    PURPOSES = ("success", "info", "warning", "danger", "neutral")
    VARIANT = "compact"
    FIXED_HEIGHT = 28

    def __init__(self, text: str = "", purpose: str = None, parent=None):
        """Инициализация компактной кнопки.

        Args:
            text: текст кнопки
            purpose: назначение кнопки, определяет цвет; если None — первый из PURPOSES
            parent: родительский виджет
        """
        try:
            super().__init__(text, parent)
            self.setObjectName("compactButton")
            self.setProperty("variant", self.VARIANT)
            self.setFixedHeight(self.FIXED_HEIGHT)
            self.set_purpose(purpose or self.PURPOSES[0])
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка инициализации: {e}", exc_info=True)
            raise

    def set_purpose(self, purpose: str):
        """Устанавливает назначение кнопки (меняет цвет через QSS).

        Args:
            purpose: одно из значений PURPOSES

        Raises:
            ValueError: если purpose не в списке допустимых
        """
        try:
            if purpose not in self.PURPOSES:
                raise ValueError(
                    f"Недопустимый purpose '{purpose}'. "
                    f"Допустимые: {self.PURPOSES}"
                )

            self.setProperty("purpose", purpose)

            # Перерисовка стилей после смены свойства
            self.style().unpolish(self)
            self.style().polish(self)
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

class OperationButton(CompactButton):
    """Кнопка открытия диалога сущности (счета, категории, переводы и т.д.).

    Отличается от CompactButton только variant: шире отступы и min-width.
    Цвет берётся из purpose, как и у всех кнопок.
    """

    PURPOSES = ("accounts", "categories", "transfers",
                "reconciliation", "loans", "credit_cards")
    VARIANT = "operation"