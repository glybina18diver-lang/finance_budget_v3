from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QMessageBox, QMenuBar, QMenu,
    QFileDialog, QApplication, QScrollArea, QDialog, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QFont

from config import WINDOW_TITLE


class MainWindow(QMainWindow):
    """Главное окно приложения на PySide6."""

    def __init__(self, db, parent=None):
        super().__init__(parent)

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1300, 680)

        # Простой центральный виджет для теста
        central_widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Приложение запущено успешно!"))
        layout.addWidget(QLabel(f"БД подключена: {db.db_path}"))
        central_widget.setLayout(layout)
        
        self.setCentralWidget(central_widget)
