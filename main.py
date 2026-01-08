"""
NeuroFlow - Professional EEG Analysis Application

Entry point for the NeuroFlow application.
"""

import sys
from PyQt6.QtWidgets import QApplication
from app.ui.main_window import MainWindow
from app.ui.theme import apply_modern_theme


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Apply the modern Neural Elegance theme
    apply_modern_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
