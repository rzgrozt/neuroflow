"""Theme Module - Modern dark theme and About dialog for NeuroFlow."""

import math
import webbrowser
from pathlib import Path
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
            lambda: webbrowser.open('https://github.com/rzgrozt/neuroflow')
        )

        linkedin_btn = QPushButton("LinkedIn")
        linkedin_btn.setStyleSheet(btn_style)
        linkedin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        linkedin_btn.clicked.connect(
            lambda: webbrowser.open('https://linkedin.com/in/rzgrozt')
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
    qss_path = Path(__file__).parent / "theme.qss"
    app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
