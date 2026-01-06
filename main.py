"""
NeuroFlow - Professional EEG Analysis Application

Entry point for the NeuroFlow application.
"""

import sys
from PyQt6.QtWidgets import QApplication
from app.ui.main_window import MainWindow


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
