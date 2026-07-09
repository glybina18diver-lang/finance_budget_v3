# ui/dialogs/base_dialog.py
"""
Базовый диалог с общими функциями: статус-бар, сообщения, заглушки.
"""
from PySide6.QtWidgets import (
    QDialog, QLabel, QVBoxLayout, QHBoxLayout, QMessageBox, QTextEdit, QDialogButtonBox
)
from PySide6.QtCore import QTimer


class BaseDialog(QDialog):
    """Базовый класс для всех диалогов приложения."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_base_ui()

    def _init_base_ui(self):
        """Инициализирует общий UI: статус-бар."""
        # Сохраняем основной layout как атрибут
        self._main_layout = QVBoxLayout()
        self._main_layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(self._main_layout)

        # Статус-бар (будет добавлен в конце)
        self.status_bar = QLabel("Готово")
        self.status_bar.setFixedHeight(26)
        self.status_bar.setStyleSheet("""
            color: #6c757d;
            font-weight: bold;
            padding: 2px 4px;
            border-top: 1px solid #e9ecef;
        """)
        # Пока не добавляем в layout — сделаем это в дочернем классе


    def show_status(self, message: str, message_type: str = "info"):
        """
        Отображает сообщение в строке статуса.
        
        Args:
            message: текст сообщения
            message_type: тип сообщения ("info", "success", "warning", "error")
        """
        colors = {"info": "#6c757d", "success": "#28a745", "warning": "#fd7e14", "error": "#dc3545"}
        color = colors.get(message_type, "#6c757d")
        self.status_bar.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.status_bar.setText(message)
        QTimer.singleShot(2000, self._reset_status_bar)

    def show_error(self, message: str):
        """
        Показывает критическое сообщение об ошибке.
        
        Args:
            message: текст ошибки
        """
        QMessageBox.critical(self, "Ошибка", message)

    def _reset_status_bar(self):
        """Возвращает статус-бар в состояние 'Готово'."""
        self.status_bar.setText("Готово")
        self.status_bar.setStyleSheet("QLabel { padding: 2px 6px; border-top: 1px solid #ddd; }")

    def _stub_method(self):
        """Заглушка для функций, находящихся в разработке."""
        self.show_status("Функция в разработке", "warning")

    def _show_cannot_delete_message(self, result_info):
        """
        Показывает диалог с причиной невозможности удаления счёта.
        
        Args:
            result_info: словарь с ключами 'account_name', 'total_operations'
        """
        account_name = result_info.get('account_name', 'Счёт')
        total_ops = result_info.get('total_operations', 0)
        
        html_text = f"""
            <h3 style='color: #dc3545; margin-top: 0;'>❌ Счёт нельзя удалить</h3>
            <p>Счёт <b>{account_name.replace('<', '&lt;').replace('>', '&gt;')}</b> имеет связанные операции.</p>
            <p><b>Всего операций:</b> {total_ops}</p>
            <p style='color: #6c757d; margin-bottom: 0;'>
                Для удаления счёта необходимо сначала удалить все связанные операции 
                или перенести их на другие счета.
                Если карта крединая сначало удалите карту в окне кредиток.
            </p>
        """
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Невозможно удалить счёт")
        dialog.resize(450, 220)
        
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(html_text)
        layout.addWidget(text_edit)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(dialog.accept)
        layout.addWidget(button_box)
        
        dialog.exec()
