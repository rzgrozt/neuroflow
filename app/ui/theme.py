"""Theme Module - Modern dark theme and About dialog for NeuroFlow."""

import math
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsDropShadowEffect, QWidget, QApplication, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QColor, QPainter, QLinearGradient, QPen, QBrush, QMouseEvent
)


class NeuralBackgroundWidget(QWidget):
    """Animated neural network background with floating nodes and connections."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.nodes = []
        self.time_offset = 0.0

        for i in range(14):
            self.nodes.append({
                'x': 30 + (i % 5) * 95 + (i * 17) % 40,
                'y': 30 + (i // 5) * 110 + (i * 23) % 50,
                'radius': 2 + (i % 3) * 1.5,
                'phase': i * 0.5,
                'speed': 0.015 + (i % 5) * 0.006,
                'pulse_phase': i * 0.3,
            })

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(50)

    def _animate(self):
        self.time_offset += 0.04
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for i, node1 in enumerate(self.nodes):
            for j, node2 in enumerate(self.nodes[i+1:], i+1):
                x1 = node1['x'] + math.sin(self.time_offset * node1['speed'] + node1['phase']) * 12
                y1 = node1['y'] + math.cos(self.time_offset * node1['speed'] * 0.7 + node1['phase']) * 10
                x2 = node2['x'] + math.sin(self.time_offset * node2['speed'] + node2['phase']) * 12
                y2 = node2['y'] + math.cos(self.time_offset * node2['speed'] * 0.7 + node2['phase']) * 10

                distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)

                if distance < 160:
                    pulse = 0.5 + 0.5 * math.sin(self.time_offset * 0.6 + i * 0.15)
                    opacity = int((1 - distance / 160) * 50 * pulse)

                    gradient = QLinearGradient(x1, y1, x2, y2)
                    gradient.setColorAt(0, QColor(0, 168, 232, opacity))
                    gradient.setColorAt(1, QColor(100, 140, 220, opacity))

                    pen = QPen(QBrush(gradient), 1.2)
                    painter.setPen(pen)
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        for node in self.nodes:
            x = node['x'] + math.sin(self.time_offset * node['speed'] + node['phase']) * 12
            y = node['y'] + math.cos(self.time_offset * node['speed'] * 0.7 + node['phase']) * 10

            pulse = 0.6 + 0.4 * math.sin(self.time_offset * 1.0 + node['pulse_phase'])
            radius = node['radius'] * (0.8 + 0.4 * pulse)

            for r in range(3, 0, -1):
                glow_opacity = int(20 * (4 - r) * pulse)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 180, 255, glow_opacity))
                painter.drawEllipse(int(x - radius - r * 3), int(y - radius - r * 3),
                                   int((radius + r * 3) * 2), int((radius + r * 3) * 2))

            painter.setBrush(QColor(0, 200, 255, int(200 * pulse)))
            painter.drawEllipse(int(x - radius), int(y - radius), int(radius * 2), int(radius * 2))


class ModernAboutDialog(QDialog):
    """Premium frameless About dialog with neural-inspired aesthetics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About NeuroFlow")
        self.setFixedSize(480, 420)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._drag_pos = None
        self._init_ui()
        self._apply_shadow()

    def _init_ui(self):
        self.container = QWidget(self)
        self.container.setObjectName("aboutContainer")
        self.container.setGeometry(0, 0, 480, 420)
        self.container.setStyleSheet("""
            #aboutContainer {
                background: qlineargradient(
                    x1:0, y1:0, x2:0.5, y2:1,
                    stop:0 #0c0c14,
                    stop:0.5 #101018,
                    stop:1 #0c0c14
                );
                border-radius: 20px;
                border: 1px solid rgba(0, 168, 232, 0.25);
            }
        """)

        self.neural_bg = NeuralBackgroundWidget(self.container)
        self.neural_bg.setGeometry(0, 0, 480, 420)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(36, 28, 36, 32)
        layout.setSpacing(12)

        close_btn = QPushButton("×", self.container)
        close_btn.setFixedSize(36, 36)
        close_btn.move(436, 10)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #505070;
                border: none;
                font-size: 24px;
                font-weight: 300;
                border-radius: 18px;
            }
            QPushButton:hover {
                background: rgba(255, 100, 100, 0.2);
                color: #ff7070;
            }
        """)
        close_btn.clicked.connect(self.close)
        close_btn.raise_()

        icon_label = QLabel("🧠")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("font-size: 56px; background: transparent;")
        layout.addWidget(icon_label)

        name_label = QLabel("NeuroFlow")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("""
            QLabel {
                font-size: 42px;
                font-weight: 700;
                font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
                color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #00c8ff, stop:0.5 #60a0ff, stop:1 #a080ff);
                background: transparent;
                color: #00d4ff;
            }
        """)
        layout.addWidget(name_label)

        version_container = QWidget()
        version_layout = QHBoxLayout(version_container)
        version_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_layout.setContentsMargins(0, 4, 0, 8)

        version_label = QLabel("v2.0.0")
        version_label.setStyleSheet("""
            QLabel {
                background: rgba(0, 180, 232, 0.15);
                color: #00c8ff;
                padding: 6px 20px;
                border-radius: 14px;
                border: 1px solid rgba(0, 180, 232, 0.35);
                font-size: 13px;
                font-weight: 600;
                font-family: 'JetBrains Mono', 'Consolas', 'SF Mono', monospace;
            }
        """)
        version_layout.addWidget(version_label)
        layout.addWidget(version_container)

        desc_label = QLabel(
            "Professional-grade EEG signal analysis platform.\n"
            "Preprocessing • ICA • ERP • TFR • Connectivity"
        )
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setStyleSheet("""
            QLabel {
                color: #9090a8;
                font-size: 13px;
                line-height: 150%;
                background: transparent;
            }
        """)
        layout.addWidget(desc_label)

        powered_label = QLabel("Powered by MNE-Python & PyQt6")
        powered_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        powered_label.setStyleSheet("""
            QLabel {
                color: #606078;
                font-size: 11px;
                font-style: italic;
                background: transparent;
            }
        """)
        layout.addWidget(powered_label)

        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

        links_widget = QWidget()
        links_layout = QHBoxLayout(links_widget)
        links_layout.setSpacing(16)
        links_layout.setContentsMargins(20, 0, 20, 0)

        btn_style = """
            QPushButton {
                background: rgba(20, 20, 35, 0.9);
                color: #b0b0c8;
                border: 1px solid rgba(80, 80, 120, 0.4);
                border-radius: 10px;
                padding: 12px 28px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: rgba(0, 168, 232, 0.15);
                color: #00d4ff;
                border-color: rgba(0, 168, 232, 0.5);
            }
            QPushButton:pressed {
                background: rgba(0, 168, 232, 0.25);
            }
        """

        github_btn = QPushButton("GitHub")
        github_btn.setStyleSheet(btn_style)
        github_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        github_btn.clicked.connect(
            lambda: __import__('webbrowser').open('https://github.com/rzgrozt/neuroflow')
        )

        linkedin_btn = QPushButton("LinkedIn")
        linkedin_btn.setStyleSheet(btn_style)
        linkedin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        linkedin_btn.clicked.connect(
            lambda: __import__('webbrowser').open('https://linkedin.com/in/rzgrozt')
        )

        links_layout.addWidget(github_btn)
        links_layout.addWidget(linkedin_btn)
        layout.addWidget(links_widget)

        footer_label = QLabel("© 2026 Ruzgar Ozturk  •  Open Source MIT License")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_label.setStyleSheet("""
            QLabel {
                color: #404058;
                font-size: 11px;
                padding-top: 16px;
                background: transparent;
            }
        """)
        layout.addWidget(footer_label)

    def _apply_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(50)
        shadow.setColor(QColor(0, 100, 180, 100))
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None


def apply_modern_theme(app: QApplication) -> None:
    """Apply comprehensive modern dark theme to the application."""

    qss = """
    /* ========================================
       GLOBAL STYLES
       ======================================== */

    * {
        font-family: 'Segoe UI', 'SF Pro Display', -apple-system, sans-serif;
    }

    QMainWindow {
        background-color: #0d0d12;
    }

    QWidget {
        color: #e0e0f0;
        font-size: 13px;
        selection-background-color: rgba(0, 180, 232, 0.4);
        selection-color: #ffffff;
    }

    /* ========================================
       BUTTONS - Improved with better feedback
       ======================================== */

    QPushButton {
        background-color: #1c1c28;
        color: #c8c8e0;
        border: 1px solid #2a2a40;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 500;
        font-size: 13px;
        min-height: 18px;
    }

    QPushButton:hover {
        background-color: #252538;
        border-color: #00a8e8;
        color: #ffffff;
    }

    QPushButton:pressed {
        background-color: #00a8e8;
        border-color: #00a8e8;
        color: #ffffff;
    }

    QPushButton:disabled {
        background-color: #141420;
        color: #454560;
        border-color: #1a1a28;
    }

    QPushButton:focus {
        border-color: #00a8e8;
        outline: none;
    }

    /* Primary Action Buttons */
    QPushButton[primary="true"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #0080b8, stop:1 #00a8e8);
        color: #ffffff;
        border: none;
        font-weight: 600;
    }

    QPushButton[primary="true"]:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #0090cc, stop:1 #00b8f8);
    }

    QPushButton[primary="true"]:pressed {
        background: #0070a0;
    }

    /* ========================================
       INPUT FIELDS - Clean flat design
       ======================================== */

    QLineEdit {
        background-color: #181824;
        color: #e0e0f0;
        border: 1px solid #282840;
        border-radius: 8px;
        padding: 6px;
        height: 30px;
        font-size: 13px;
        selection-background-color: rgba(0, 180, 232, 0.4);
    }

    QLineEdit:hover {
        border-color: #383858;
    }

    QLineEdit:focus {
        border: 2px solid #00a8e8;
        padding: 9px 13px;
        background-color: #1c1c2a;
    }

    QLineEdit:disabled {
        background-color: #121220;
        color: #505068;
        border-color: #1a1a28;
    }

    /* ========================================
       SPINBOX & DOUBLESPINBOX - Fixed arrows
       ======================================== */

    QSpinBox, QDoubleSpinBox {
        background-color: #181824;
        color: #e0e0f0;
        border: 1px solid #282840;
        border-radius: 8px;
        padding: 6px;
        padding-right: 30px;
        font-size: 13px;
        height: 30px;
        min-height: 20px;
    }

    QSpinBox:hover, QDoubleSpinBox:hover {
        border-color: #383858;
    }

    QSpinBox:focus, QDoubleSpinBox:focus {
        border: 2px solid #00a8e8;
        padding: 7px 11px;
        padding-right: 29px;
    }

    QSpinBox::up-button, QDoubleSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 24px;
        height: 50%;
        background-color: #222234;
        border: none;
        border-left: 1px solid #282840;
        border-top-right-radius: 7px;
    }

    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
        background-color: #00a8e8;
    }

    QSpinBox::down-button, QDoubleSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 24px;
        height: 50%;
        background-color: #222234;
        border: none;
        border-left: 1px solid #282840;
        border-bottom-right-radius: 7px;
    }

    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
        background-color: #00a8e8;
    }

    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-bottom: 6px solid #8080a0;
    }

    QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover {
        border-bottom-color: #ffffff;
    }

    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #8080a0;
    }

    QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {
        border-top-color: #ffffff;
    }

    /* ========================================
       COMBO BOX
       ======================================== */

    QComboBox {
        background-color: #181824;
        color: #e0e0f0;
        border: 1px solid #282840;
        border-radius: 8px;
        padding: 6px;
        padding-right: 36px;
        font-size: 13px;
        height: 30px;
        min-height: 18px;
    }

    QComboBox:hover {
        border-color: #383858;
    }

    QComboBox:focus {
        border: 2px solid #00a8e8;
        padding: 9px 13px;
        padding-right: 35px;
    }

    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: center right;
        width: 28px;
        border: none;
        background: transparent;
    }

    QComboBox::down-arrow {
        width: 0;
        height: 0;
        border-left: 6px solid transparent;
        border-right: 6px solid transparent;
        border-top: 7px solid #8080a0;
    }

    QComboBox::down-arrow:hover {
        border-top-color: #00c8ff;
    }

    QComboBox QAbstractItemView {
        background-color: #181824;
        color: #e0e0f0;
        border: 1px solid #303048;
        border-radius: 8px;
        padding: 6px;
        selection-background-color: rgba(0, 168, 232, 0.25);
        outline: none;
    }

    QComboBox QAbstractItemView::item {
        padding: 10px 14px;
        border-radius: 6px;
        margin: 2px 0;
    }

    QComboBox QAbstractItemView::item:hover {
        background-color: rgba(0, 168, 232, 0.15);
    }

    QComboBox QAbstractItemView::item:selected {
        background-color: rgba(0, 168, 232, 0.3);
        color: #00d4ff;
    }

    /* ========================================
       TEXT AREAS
       ======================================== */

    QTextEdit, QPlainTextEdit {
        background-color: #0a0a10;
        color: #c0c0d8;
        border: 1px solid #1a1a28;
        border-radius: 10px;
        padding: 14px;
        font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
        font-size: 12px;
        line-height: 160%;
    }

    QTextEdit:focus, QPlainTextEdit:focus {
        border-color: #00a8e8;
    }

    /* ========================================
       LABELS
       ======================================== */

    QLabel {
        color: #b0b0c8;
        background: transparent;
        margin-bottom: 4px;
    }

    /* ========================================
       GROUP BOXES - Improved borders
       ======================================== */

    QGroupBox {
        background-color: rgba(20, 20, 30, 0.5);
        border: 1px solid #252538;
        border-radius: 12px;
        margin-top: 20px;
        padding: 20px 16px 16px 16px;
        font-weight: 600;
    }

    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 16px;
        top: 6px;
        padding: 2px 12px;
        color: #00c8ff;
        font-size: 13px;
        font-weight: 600;
        background: #0d0d12;
        border-radius: 4px;
    }

    /* ========================================
       TOOLBOX (Accordion) - Modern headers
       ======================================== */

    QToolBox {
        background-color: transparent;
    }

    QToolBox::tab {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #1a1a28, stop:1 #151522);
        color: #c0c0d8;
        border: 1px solid #252538;
        border-radius: 10px;
        padding: 14px 18px;
        font-weight: 600;
        font-size: 13px;
        margin-bottom: 6px;
    }

    QToolBox::tab:selected {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #202034, stop:1 #1a1a28);
        color: #00d4ff;
        border-color: #00a8e8;
        border-left: 3px solid #00a8e8;
        padding-left: 16px;
    }

    QToolBox::tab:hover:!selected {
        background: #1e1e2c;
        border-color: #303048;
    }

    /* ========================================
       SCROLL AREA (Sidebar)
       ======================================== */

    #sidebarScrollArea {
        background: transparent;
        border: none;
    }

    #sidebarScrollContent {
        background: transparent;
    }

    /* ========================================
       COLLAPSIBLE BOX
       ======================================== */

    #collapsibleBox {
        background: transparent;
        border: none;
        margin-bottom: 2px;
    }

    #collapsibleHeader {
        background: #2d2d2d;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 8px 12px;
        font-weight: 600;
        font-size: 13px;
        text-align: left;
    }

    #collapsibleHeader:hover {
        background: #3a3a3a;
    }

    #collapsibleContent {
        background: transparent;
    }

    /* Compact inputs for sidebar */
    #collapsibleContent QLineEdit,
    #collapsibleContent QComboBox,
    #collapsibleContent QSpinBox,
    #collapsibleContent QDoubleSpinBox {
        height: 28px;
        min-height: 28px;
        max-height: 28px;
    }

    /* ========================================
       TAB WIDGET
       ======================================== */

    QTabWidget::pane {
        background-color: #0d0d12;
        border: 1px solid #252538;
        border-radius: 10px;
        top: -1px;
    }

    QTabBar::tab {
        background-color: #151520;
        color: #9090a8;
        border: 1px solid #252538;
        border-bottom: none;
        padding: 12px 24px;
        margin-right: 4px;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        font-weight: 500;
        font-size: 13px;
    }

    QTabBar::tab:selected {
        background-color: #0d0d12;
        color: #00d4ff;
        border-color: #00a8e8;
        border-bottom: 2px solid #0d0d12;
    }

    QTabBar::tab:hover:!selected {
        background-color: #1a1a28;
        color: #c0c0d8;
    }

    /* ========================================
       SCROLLBARS - Minimal design
       ======================================== */

    QScrollBar:vertical {
        background-color: transparent;
        width: 10px;
        margin: 0;
    }

    QScrollBar::handle:vertical {
        background-color: #2a2a40;
        border-radius: 5px;
        min-height: 40px;
        margin: 2px;
    }

    QScrollBar::handle:vertical:hover {
        background-color: #3a3a58;
    }

    QScrollBar::handle:vertical:pressed {
        background-color: #00a8e8;
    }

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
        height: 0;
        border: none;
    }

    QScrollBar:horizontal {
        background-color: transparent;
        height: 10px;
        margin: 0;
    }

    QScrollBar::handle:horizontal {
        background-color: #2a2a40;
        border-radius: 5px;
        min-width: 40px;
        margin: 2px;
    }

    QScrollBar::handle:horizontal:hover {
        background-color: #3a3a58;
    }

    QScrollBar::handle:horizontal:pressed {
        background-color: #00a8e8;
    }

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: none;
        width: 0;
        border: none;
    }

    /* ========================================
       SPLITTER
       ======================================== */

    QSplitter::handle {
        background-color: #1a1a28;
    }

    QSplitter::handle:horizontal {
        width: 3px;
    }

    QSplitter::handle:vertical {
        height: 3px;
    }

    QSplitter::handle:hover {
        background-color: #00a8e8;
    }

    /* ========================================
       FRAMES
       ======================================== */

    QFrame {
        border: none;
    }

    QFrame[frameShape="4"] {
        background-color: #252538;
        max-height: 1px;
    }

    QFrame[frameShape="5"] {
        background-color: #252538;
        max-width: 1px;
    }

    /* ========================================
       TOOLBAR
       ======================================== */

    QToolBar {
        background-color: #0d0d12;
        border: none;
        border-bottom: 1px solid #1a1a28;
        padding: 6px 10px;
        spacing: 10px;
    }

    QToolBar::separator {
        background-color: #252538;
        width: 1px;
        margin: 6px 10px;
    }

    QToolButton {
        background-color: transparent;
        color: #a0a0b8;
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 10px 16px;
        font-weight: 500;
        font-size: 13px;
    }

    QToolButton:hover {
        background-color: rgba(0, 168, 232, 0.1);
        border-color: rgba(0, 168, 232, 0.3);
        color: #00d4ff;
    }

    QToolButton:pressed {
        background-color: rgba(0, 168, 232, 0.2);
    }

    /* ========================================
       MENUBAR & MENUS
       ======================================== */

    QMenuBar {
        background-color: #0a0a10;
        color: #a0a0b8;
        border-bottom: 1px solid #1a1a28;
        padding: 4px 0;
    }

    QMenuBar::item {
        background: transparent;
        padding: 10px 18px;
        border-radius: 6px;
        margin: 2px 4px;
    }

    QMenuBar::item:selected {
        background-color: rgba(0, 168, 232, 0.12);
        color: #00d4ff;
    }

    QMenu {
        background-color: #12121c;
        color: #d0d0e8;
        border: 1px solid #282840;
        border-radius: 10px;
        padding: 8px;
    }

    QMenu::item {
        padding: 10px 24px 10px 16px;
        margin: 2px 4px;
        border-radius: 6px;
    }

    QMenu::item:selected {
        background-color: rgba(0, 168, 232, 0.2);
        color: #00d4ff;
    }

    QMenu::separator {
        height: 1px;
        background-color: #252538;
        margin: 8px 12px;
    }

    /* ========================================
       DIALOGS & MESSAGE BOXES
       ======================================== */

    QDialog {
        background-color: #0d0d12;
    }

    QMessageBox {
        background-color: #0d0d12;
    }

    QMessageBox QLabel {
        color: #e0e0f0;
        font-size: 13px;
    }

    /* ========================================
       TABLES
       ======================================== */

    QTableWidget, QTableView {
        background-color: #0a0a10;
        alternate-background-color: #0e0e16;
        color: #d0d0e8;
        border: 1px solid #1a1a28;
        border-radius: 10px;
        gridline-color: #1a1a28;
        selection-background-color: rgba(0, 168, 232, 0.25);
    }

    QTableWidget::item, QTableView::item {
        padding: 10px;
        border: none;
    }

    QTableWidget::item:selected, QTableView::item:selected {
        background-color: rgba(0, 168, 232, 0.3);
        color: #ffffff;
    }

    QHeaderView::section {
        background-color: #12121c;
        color: #9090a8;
        border: none;
        border-right: 1px solid #1a1a28;
        border-bottom: 1px solid #1a1a28;
        padding: 12px 14px;
        font-weight: 600;
    }

    QHeaderView::section:hover {
        background-color: #181828;
        color: #00d4ff;
    }

    /* ========================================
       PROGRESS BAR
       ======================================== */

    QProgressBar {
        background-color: #181824;
        border: none;
        border-radius: 6px;
        height: 10px;
        text-align: center;
        color: transparent;
    }

    QProgressBar::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #0080b8, stop:1 #00c8ff);
        border-radius: 6px;
    }

    /* ========================================
       SLIDERS
       ======================================== */

    QSlider::groove:horizontal {
        background-color: #181824;
        height: 8px;
        border-radius: 4px;
    }

    QSlider::handle:horizontal {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #00d4ff, stop:1 #0090c0);
        width: 20px;
        height: 20px;
        margin: -6px 0;
        border-radius: 10px;
        border: 2px solid #0d0d12;
    }

    QSlider::handle:horizontal:hover {
        background: #00e4ff;
    }

    QSlider::sub-page:horizontal {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #005080, stop:1 #00a8e8);
        border-radius: 4px;
    }

    /* ========================================
       CHECKBOXES & RADIO BUTTONS
       ======================================== */

    QCheckBox, QRadioButton {
        color: #c0c0d8;
        spacing: 10px;
        font-size: 13px;
    }

    QCheckBox::indicator {
        width: 20px;
        height: 20px;
        border-radius: 5px;
        background-color: #181824;
        border: 2px solid #2a2a40;
    }

    QCheckBox::indicator:hover {
        border-color: #00a8e8;
    }

    QCheckBox::indicator:checked {
        background-color: #00a8e8;
        border-color: #00a8e8;
    }

    QRadioButton::indicator {
        width: 20px;
        height: 20px;
        border-radius: 10px;
        background-color: #181824;
        border: 2px solid #2a2a40;
    }

    QRadioButton::indicator:hover {
        border-color: #00a8e8;
    }

    QRadioButton::indicator:checked {
        background-color: #00a8e8;
        border: 5px solid #181824;
    }

    /* ========================================
       TOOLTIPS
       ======================================== */

    QToolTip {
        background-color: #181828;
        color: #e0e0f0;
        border: 1px solid #00a8e8;
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 12px;
    }

    /* ========================================
       STATUS BAR
       ======================================== */

    QStatusBar {
        background-color: #0a0a10;
        color: #707088;
        border-top: 1px solid #1a1a28;
        padding: 4px;
    }

    QStatusBar::item {
        border: none;
    }
    """

    app.setStyleSheet(qss)
