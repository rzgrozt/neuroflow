"""NeuroFlow - Professional EEG Analysis Application."""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from app.ui.main_window import MainWindow
from app.ui.theme import apply_modern_theme


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("assets/neuroflow_icon.png"))
    app.setStyle("Fusion")
    apply_modern_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())
