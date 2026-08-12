# ui/analytics/kpi_cards_widget.py
"""KPI-карточки на нативных Qt-виджетах для окна аналитики."""

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from ui.styles.theme_manager import ThemeManager

logger = logging.getLogger(__name__)


class KpiCard(QFrame):
    """Одна KPI-карточка: заголовок, крупное значение и подпись."""

    def __init__(self, title: str, parent=None):
        """
        Инициализация карточки.

        Args:
            title: текст заголовка карточки
            parent: родительский виджет
        """
        try:
            super().__init__(parent)
            self.setObjectName("kpiCard")
            self._title = title
            self._setup_ui()
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def _setup_ui(self):
        """Собирает внутреннюю структуру карточки."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        self.title_label = QLabel(self._title)
        self.value_label = QLabel("—")
        self.sub_label = QLabel("")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addStretch(1)
        layout.addWidget(self.sub_label)

    def apply_theme(self, colors: dict) -> None:
        """
        Применяет цвета темы к каркасу карточки и базовым подписям.

        Args:
            colors: словарь цветов из ThemeManager
        """
        try:
            self.setStyleSheet(
                "QFrame#kpiCard {"
                f"background-color: {colors['card_bg']};"
                f"border: 1px solid {colors['border']};"
                "border-radius: 10px;"
                "}"
            )
            self.title_label.setStyleSheet(
                f"color: {colors['text_secondary']};"
                "font-size: 11px; letter-spacing: 0.5px;"
            )
            self.value_label.setStyleSheet(
                f"color: {colors['text_primary']};"
                "font-size: 22px; font-weight: 700;"
            )
            self.sub_label.setStyleSheet(
                f"color: {colors['text_secondary']}; font-size: 11px;"
            )
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def set_value(self, value: str, sub: str, sub_color: str) -> None:
        """
        Обновляет значение и подпись карточки.

        Args:
            value: основной текст (число/процент)
            sub: текст подписи под значением
            sub_color: цвет подписи (HEX)
        """
        try:
            self.value_label.setText(value)
            self.sub_label.setText(sub)
            self.sub_label.setStyleSheet(
                f"color: {sub_color}; font-size: 11px;"
            )
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise


class KpiCardsWidget(QFrame):
    """Панель из пяти KPI-карточек: доходы, расходы, чистый поток, savings rate, исполнение бюджета."""

    _TITLES = {
        "income": "💰 Доходы",
        "expense": "💸 Расходы",
        "net_flow": "📈 Чистый поток",
        "savings_rate": "🏦 Savings Rate",
        "budget_execution": "🎯 Исполнение бюджета",
    }

    def __init__(self, parent=None):
        """
        Инициализация панели KPI-карточек.

        Args:
            parent: родительский виджет
        """
        try:
            super().__init__(parent)
            self.setProperty("variant", "panel")
            self.cards = {}
            self._setup_ui()
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def _setup_ui(self):
        """Собирает горизонтальный ряд из пяти карточек."""
        try:
            layout = QHBoxLayout(self)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(10)

            for key, title in self._TITLES.items():
                card = KpiCard(title, self)
                self.cards[key] = card
                layout.addWidget(card, 1)

            self._apply_theme_to_cards()
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def render_kpi(self, kpi: dict) -> None:
        """
        Отображает KPI-метрики в карточках с учётом текущей темы.

        Args:
            kpi: словарь с ключами total_income, total_expense, net_flow,
                 savings_rate, budget_execution

        Raises:
            ValueError: если данных недостаточно
        """
        try:
            required = ("total_income", "total_expense", "net_flow",
                        "savings_rate", "budget_execution")
            missing = [k for k in required if k not in kpi]
            if missing:
                raise ValueError(f"Недостаточно KPI-данных: {', '.join(missing)}")

            colors = self._theme_colors()
            self._apply_theme_to_cards(colors)

            self.cards["income"].set_value(
                self._fmt_money(kpi["total_income"]), "за период", colors["success"])
            self.cards["expense"].set_value(
                self._fmt_money(kpi["total_expense"]), "за период", colors["danger"])

            net = kpi["net_flow"]
            net_sign = "+" if net >= 0 else "−"
            net_color = colors["success"] if net >= 0 else colors["danger"]
            self.cards["net_flow"].set_value(
                net_sign + self._fmt_money(abs(net)), "доходы − расходы", net_color)

            sr = kpi["savings_rate"]
            sr_color, sr_sub = self._savings_rate_status(sr, colors)
            self.cards["savings_rate"].set_value(f"{sr:.1f}%", sr_sub, sr_color)

            be = kpi["budget_execution"]
            be_color = colors["success"] if be <= 100 else colors["danger"]
            be_sub = "в рамках бюджета" if be <= 100 else "бюджет превышен"
            self.cards["budget_execution"].set_value(f"{be:.1f}%", be_sub, be_color)
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def _apply_theme_to_cards(self, colors: dict = None) -> None:
        """Применяет тему ко всем карточкам."""
        if colors is None:
            colors = self._theme_colors()
        for card in self.cards.values():
            card.apply_theme(colors)

    def _theme_colors(self) -> dict:
        """
        Возвращает палитру для карточек из активной темы.

        Returns:
            Словарь цветов: фоны, текст, семантические цвета
        """
        theme = ThemeManager.current()
        return {
            "card_bg": theme.get("BG_SECONDARY", "#FFFFFF"),
            "border": theme.get("BORDER", "#E0E0E0"),
            "text_primary": theme.get("TEXT_PRIMARY", "#2C3E50"),
            "text_secondary": theme.get("TEXT_SECONDARY", "#7F8C8D"),
            "success": theme.get("SUCCESS", "#27AE60"),
            "danger": theme.get("DANGER", "#C0392B"),
            "warning": theme.get("WARNING", "#F39C12"),
        }

    def _savings_rate_status(self, rate: float, colors: dict) -> tuple:
        """
        Возвращает цвет и подпись для Savings Rate.

        Args:
            rate: норма сбережений в процентах
            colors: словарь цветов темы

        Returns:
            Кортеж (цвет, подпись)
        """
        if rate >= 20:
            return colors["success"], "отлично"
        if rate >= 10:
            return colors["warning"], "хорошо"
        return colors["danger"], "низкая"

    def _fmt_money(self, value: float) -> str:
        """Форматирует сумму в рублях с разделителями тысяч."""
        return f"{value:,.0f}".replace(",", " ") + " ₽"