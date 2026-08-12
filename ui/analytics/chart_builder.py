# ui/analytics/chart_builder.py
"""Сборка HTML-графиков (ECharts) для окна аналитики."""

import json
import logging
import os

from ui.styles.theme_manager import ThemeManager

logger = logging.getLogger(__name__)

_ASSETS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets")
)

# --- JS-шаблон ECharts ---
_ECHARTS_JS = """
const D = __DATA_JSON__;
const C = __COLORS_JSON__;
const chart = echarts.init(document.getElementById('chart'));
chart.setOption({
  backgroundColor:'transparent',
  textStyle:{ color:C.text },
  tooltip:{ trigger:'axis', axisPointer:{ type:'cross', label:{ backgroundColor:C.balance } },
    backgroundColor:C.paper, borderColor:C.border, textStyle:{ color:C.text },
    valueFormatter:function(v){ return v==null ? '' : Number(v).toLocaleString() + ' ₽'; } },
  legend:{ top:6, left:10, textStyle:{ color:C.text }, itemWidth:14, itemHeight:10 },
  grid:{ left:70, right:70, top:60, bottom:70 },
  xAxis:{ type:'category', data:D.labels, axisLabel:{ color:C.muted },
    axisLine:{ lineStyle:{ color:C.border } }, axisTick:{ alignWithLabel:true } },
  yAxis:[
    { type:'value', name:'Сумма, ₽', nameTextStyle:{ color:C.muted },
      axisLabel:{ color:C.muted, formatter:function(v){ return v.toLocaleString(); } },
      splitLine:{ lineStyle:{ color:C.gridSoft } } },
    { type:'value', name:'Баланс, ₽', nameTextStyle:{ color:C.balance },
      axisLabel:{ color:C.balance, formatter:function(v){ return v.toLocaleString(); } },
      splitLine:{ show:false } }
  ],
  dataZoom:[
    { type:'inside', xAxisIndex:0 },
    { type:'slider', xAxisIndex:0, height:20, bottom:10, borderColor:C.border }
  ],
  series:[
    { name:'Доходы', type:'bar', data:D.incomes,
      itemStyle:{ color:C.income, borderRadius:[3,3,0,0] }, barGap:'20%' },
    { name:'Расходы', type:'bar', data:D.expenses,
      itemStyle:{ color:C.expense, borderRadius:[3,3,0,0] } },
    { name:'Бюджет', type:'line', data:D.budget, symbol:'none',
      itemStyle:{ color:C.budget }, lineStyle:{ color:C.budget, type:'dashed', width:2 } },
    { name:'Накопительный баланс', type:'line', yAxisIndex:1, data:D.balance,
      smooth:true, symbol:'circle', symbolSize:5,
      itemStyle:{ color:C.balance, borderColor:C.paper, borderWidth:1 },
      lineStyle:{ color:C.balance, width:2.5 }, areaStyle:{ color:C.balanceFill } }
  ]
});
window.addEventListener('resize', function(){ chart.resize(); });
"""


class ChartBuilder:
    """Генерирует HTML-разметку графиков ECharts из данных аналитики."""

    def build_expenses_html(self, data: dict) -> str:
        """
        Собирает интерактивный график «Доходы, расходы, бюджет и баланс» на ECharts.

        Args:
            data: словарь с ключами months, period_dates, incomes,
                  expenses, budget, cumulative_balance

        Returns:
            Готовая HTML-строка для отображения в QWebEngineView

        Raises:
            ValueError: если в данных не хватает обязательных ключей
        """
        try:
            self._validate_chart_data(data)
            colors = self._theme_colors()
            src = self._js_lib_source(
                "echarts.min.js",
                "https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js")
            container = "<div id='chart' style='width:100%;height:100%;'></div>"
            script = (_ECHARTS_JS
                      .replace("__DATA_JSON__", self._chart_payload(data))
                      .replace("__COLORS_JSON__", self._js_colors(colors)))
            return self._js_chart_page(src, container, script, colors["paper"])
        except ValueError as e:
            logger.warning(f"[{self.__class__.__name__}] Валидация: {e}")
            raise
        except Exception as e:
            logger.error(f"[{self.__class__.__name__}] Ошибка: {e}", exc_info=True)
            raise

    def _validate_chart_data(self, data: dict) -> None:
        """
        Проверяет наличие обязательных ключей для построения графика.

        Args:
            data: словарь с данными аналитики

        Raises:
            ValueError: если не хватает обязательных ключей
        """
        required = ("months", "period_dates", "incomes", "expenses",
                    "budget", "cumulative_balance")
        missing = [k for k in required if not data.get(k)]
        if missing:
            raise ValueError(
                f"Недостаточно данных для графика: {', '.join(missing)}"
            )

    def _theme_colors(self) -> dict:
        """
        Возвращает палитру для графика из активной темы.

        Returns:
            Словарь цветов: фоны, текст, сетка и цвета серий
        """
        theme = ThemeManager.current()
        return {
            "paper": theme.get("BG_SECONDARY", "#FFFFFF"),
            "plot": theme.get("BG_SECONDARY", "#FFFFFF"),
            "text": theme.get("TEXT_PRIMARY", "#2C3E50"),
            "muted": theme.get("TEXT_SECONDARY", "#7F8C8D"),
            "grid": theme.get("BORDER", "#E0E0E0"),
            "border": theme.get("BORDER", "#BDC3C7"),
            "income": theme.get("SUCCESS", "#27AE60"),
            "expense": theme.get("DANGER", "#C0392B"),
            "budget": theme.get("WARNING", "#F39C12"),
            "balance": theme.get("COMPACT_INFO", "#2196F3"),
        }

    def _hex_to_rgba(self, hex_color: str, alpha: float) -> str:
        """
        Преобразует HEX-цвет в строку rgba() с прозрачностью.

        Args:
            hex_color: цвет в формате #RRGGBB или #RGB
            alpha: прозрачность от 0.0 до 1.0

        Returns:
            Строка вида rgba(r, g, b, alpha)
        """
        try:
            hex_color = hex_color.lstrip("#")
            if len(hex_color) == 3:
                hex_color = "".join(ch * 2 for ch in hex_color)
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return f"rgba({r}, {g}, {b}, {alpha})"
        except (ValueError, IndexError) as e:
            # Адаптация: битый цвет из темы не должен ронять весь график
            logger.warning(f"[{self.__class__.__name__}] Валидация цвета: {e}, "
                           "используется запасной")
            return "rgba(127, 140, 141, 0.5)"

    def _js_lib_source(self, local_filename: str, cdn_url: str) -> str:
        """
        Возвращает источник JS-библиотеки: локальный файл или CDN.

        Args:
            local_filename: имя файла в assets/js/
            cdn_url: адрес CDN

        Returns:
            Относительный путь 'js/<имя>' или строка CDN
        """
        local_path = os.path.join(_ASSETS_DIR, "js", local_filename)
        if os.path.isfile(local_path):
            logger.debug(f"[{self.__class__.__name__}] {local_filename}: локальный файл")
            return f"js/{local_filename}"
        logger.info(f"[{self.__class__.__name__}] {local_filename} не найден, используется CDN")
        return cdn_url

    def _chart_payload(self, data: dict) -> str:
        """Собирает JSON с данными для графика."""
        payload = {
            "labels": data["months"],
            "incomes": data["incomes"],
            "expenses": data["expenses"],
            "budget": data["budget"],
            "balance": data["cumulative_balance"],
        }
        return json.dumps(payload, ensure_ascii=False)

    def _js_colors(self, colors: dict) -> str:
        """Собирает JSON-палитру для графика."""
        palette = {
            "paper": colors["paper"],
            "text": colors["text"],
            "muted": colors["muted"],
            "border": colors["border"],
            "income": colors["income"],
            "expense": colors["expense"],
            "budget": colors["budget"],
            "balance": colors["balance"],
            "gridSoft": self._hex_to_rgba(colors["grid"], 0.6),
            "balanceFill": self._hex_to_rgba(colors["balance"], 0.10),
        }
        return json.dumps(palette, ensure_ascii=False)

    def _js_chart_page(self, lib_src: str, container_html: str,
                       script_js: str, bg_color: str) -> str:
        """
        Собирает полную HTML-страницу с JS-графиком.

        Args:
            lib_src: путь или CDN к JS-библиотеке
            container_html: HTML контейнера графика
            script_js: JS-код построения
            bg_color: цвет фона страницы из темы

        Returns:
            Готовая HTML-строка для QWebEngineView
        """
        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            f"<script src='{lib_src}'></script>"
            "<style>"
            "html, body { margin:0; padding:0; height:100%; "
            f"background-color:{bg_color}; "
            "font-family:'Segoe UI', Arial, sans-serif; overflow:hidden; }"
            "</style></head><body>"
            f"{container_html}"
            f"<script>{script_js}</script>"
            "</body></html>"
        )