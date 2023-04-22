"""
This module creates a QApplication and a Widget using PySide6.QtWidgets module and
executes the application.

Usage:
    1. Install dependencies from `requirements.txt`
    2. Run the module to launch the application.
"""

__author__ = "Ilya Molodkin"
__date__ = "2023-04-22"
__version__ = "1.0"
__license__ = "MIT License"


import sys
from PySide6.QtWidgets import QApplication
from ui.widgets.Widget import Widget


if __name__ == '__main__':
    app = QApplication(sys.argv)
    widget = Widget()
    widget.show()
    sys.exit(app.exec())
