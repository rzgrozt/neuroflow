"""Sidebar Components - Styled widgets with Neural Elegance theme."""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit,
    QScrollArea, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QEvent
from PyQt6.QtGui import QColor, QFont


class NoScrollComboBox(QComboBox):
    """ComboBox that ignores wheel events to allow parent scrolling."""
    def wheelEvent(self, event):
        event.ignore()


class NoScrollSpinBox(QDoubleSpinBox):
    """DoubleSpinBox that ignores wheel events to allow parent scrolling."""
    def wheelEvent(self, event):
        event.ignore()


COLORS = {
    'bg_void': '#05060a',
    'bg_deep': '#0a0c14',
    'bg_base': '#0e1018',
    'bg_elevated': '#141620',
    'bg_surface': '#1a1d2a',
    'bg_hover': '#222638',

    'border_subtle': '#1e2233',
    'border_default': '#262b3d',
    'border_focus': '#00b4d8',

    'text_primary': '#e8eaf0',
    'text_secondary': '#9498a8',
    'text_muted': '#5c6070',
    'text_accent': '#00d4ff',

    'accent_primary': '#00b4d8',
    'accent_glow': '#00d4ff',
    'accent_dim': '#0080a0',

    'success': '#00c896',
    'warning': '#f0a030',
    'error': '#e85050',
}

FONTS = {
    'display': 'Segoe UI, SF Pro Display, system-ui',
    'body': 'Segoe UI, SF Pro Text, system-ui',
    'mono': 'JetBrains Mono, Cascadia Code, Consolas, monospace',
}

LABEL_WIDTH = 55
WIDGET_SPACING = 8
CONTENT_MARGINS = (10, 8, 10, 10)
CARD_MARGINS = (12, 12, 12, 14)
BORDER_RADIUS = 10


LABEL_STYLE = f"""
    QLabel {{
        color: {COLORS['text_secondary']};
        font-family: {FONTS['body']};
        font-size: 12px;
        font-weight: 500;
        background: transparent;
        padding: 0;
    }}
"""

INPUT_STYLE = f"""
    QLineEdit {{
        background: {COLORS['bg_deep']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border_subtle']};
        border-radius: 6px;
        padding: 6px 10px;
        font-family: {FONTS['mono']};
        font-size: 12px;
        selection-background-color: {COLORS['accent_dim']};
    }}
    QLineEdit:focus {{
        border-color: {COLORS['accent_primary']};
        background: {COLORS['bg_base']};
    }}
    QLineEdit:disabled {{
        background: {COLORS['bg_void']};
        color: {COLORS['text_muted']};
        border-color: {COLORS['border_subtle']};
    }}
"""

COMBO_STYLE = f"""
    QComboBox {{
        background: {COLORS['bg_deep']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border_subtle']};
        border-radius: 6px;
        padding: 6px 10px;
        font-family: {FONTS['body']};
        font-size: 12px;
        min-height: 18px;
    }}
    QComboBox:hover {{
        border-color: {COLORS['border_default']};
    }}
    QComboBox:focus {{
        border-color: {COLORS['accent_primary']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {COLORS['text_muted']};
        margin-right: 8px;
    }}
    QComboBox:hover::down-arrow {{
        border-top-color: {COLORS['text_secondary']};
    }}
    QComboBox QAbstractItemView {{
        background: {COLORS['bg_elevated']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border_default']};
        border-radius: 6px;
        padding: 4px;
        selection-background-color: {COLORS['accent_dim']};
    }}
"""

SPINBOX_STYLE = f"""
    QDoubleSpinBox {{
        background: {COLORS['bg_deep']};
        color: {COLORS['text_primary']};
        border: 1px solid {COLORS['border_subtle']};
        border-radius: 6px;
        padding: 5px 8px;
        font-family: {FONTS['mono']};
        font-size: 12px;
    }}
    QDoubleSpinBox:focus {{
        border-color: {COLORS['accent_primary']};
    }}
    QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
        background: transparent;
        border: none;
        width: 16px;
    }}
    QDoubleSpinBox::up-arrow {{
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 4px solid {COLORS['text_muted']};
    }}
    QDoubleSpinBox::down-arrow {{
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 4px solid {COLORS['text_muted']};
    }}
    QDoubleSpinBox::up-arrow:hover, QDoubleSpinBox::down-arrow:hover {{
        border-bottom-color: {COLORS['text_secondary']};
        border-top-color: {COLORS['text_secondary']};
    }}
"""


class SectionHeader(QWidget):
    """Section header with icon and title."""

    def __init__(self, title: str, icon: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(10)

        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"""
                QLabel {{
                    font-size: 15px;
                    color: {COLORS['accent_glow']};
                    background: transparent;
                }}
            """)
            layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                font-family: {FONTS['display']};
                font-size: 12px;
                font-weight: 600;
                color: {COLORS['accent_glow']};
                background: transparent;
                letter-spacing: 0.3px;
            }}
        """)
        layout.addWidget(title_label)
        layout.addStretch()


class SectionCard(QFrame):
    """Card-style container with gradient background."""

    def __init__(self, title: str = "", icon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("sectionCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._setup_style()

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(*CARD_MARGINS)
        self.main_layout.setSpacing(WIDGET_SPACING)

        if title:
            header = SectionHeader(title, icon)
            self.main_layout.addWidget(header)

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(WIDGET_SPACING)
        self.main_layout.addLayout(self.content_layout)

    def _setup_style(self):
        self.setStyleSheet(f"""
            #sectionCard {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {COLORS['bg_surface']},
                    stop:1 {COLORS['bg_elevated']});
                border: 1px solid {COLORS['border_subtle']};
                border-radius: {BORDER_RADIUS}px;
            }}
            #sectionCard:hover {{
                border-color: {COLORS['border_default']};
            }}
        """)

    def addWidget(self, widget):
        widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            widget.sizePolicy().verticalPolicy()
        )
        self.content_layout.addWidget(widget)

    def addLayout(self, layout):
        self.content_layout.addLayout(layout)


class ParamRow(QWidget):
    """Parameter input row with fixed-width label."""

    valueChanged = pyqtSignal(str)

    def __init__(self, label: str, default: str = "", placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(WIDGET_SPACING)

        self.label = QLabel(label)
        self.label.setFixedWidth(LABEL_WIDTH)
        self.label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(self.label)

        self.input = QLineEdit(default)
        self.input.setStyleSheet(INPUT_STYLE)
        if placeholder:
            self.input.setPlaceholderText(placeholder)
        self.input.textChanged.connect(self.valueChanged.emit)
        layout.addWidget(self.input)

    def value(self) -> str:
        return self.input.text()

    def setValue(self, value: str):
        self.input.setText(value)

    def setEnabled(self, enabled: bool):
        self.input.setEnabled(enabled)


class ParamComboRow(QWidget):
    """Row with fixed-width label and styled ComboBox."""

    currentIndexChanged = pyqtSignal(int)

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(WIDGET_SPACING)

        self.label = QLabel(label)
        self.label.setFixedWidth(LABEL_WIDTH)
        self.label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(self.label)

        self.combo = NoScrollComboBox()
        self.combo.setStyleSheet(COMBO_STYLE)
        self.combo.currentIndexChanged.connect(self.currentIndexChanged.emit)
        layout.addWidget(self.combo)

    def setEnabled(self, enabled: bool):
        self.combo.setEnabled(enabled)


class ParamSpinRow(QWidget):
    """Parameter row with double spin boxes for range inputs."""

    def __init__(self, label: str, min_val: float, max_val: float,
                 default_min: float, default_max: float, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QLabel(label)
        lbl.setFixedWidth(LABEL_WIDTH)
        lbl.setStyleSheet(LABEL_STYLE)
        layout.addWidget(lbl)

        self.spin_min = NoScrollSpinBox()
        self.spin_min.setRange(min_val, max_val)
        self.spin_min.setValue(default_min)
        self.spin_min.setStyleSheet(SPINBOX_STYLE)
        layout.addWidget(self.spin_min)

        sep = QLabel("–")
        sep.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        sep.setFixedWidth(14)
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sep)

        self.spin_max = NoScrollSpinBox()
        self.spin_max.setRange(min_val, max_val)
        self.spin_max.setValue(default_max)
        self.spin_max.setStyleSheet(SPINBOX_STYLE)
        layout.addWidget(self.spin_max)

    def values(self) -> tuple:
        return (self.spin_min.value(), self.spin_max.value())


class ActionButton(QPushButton):
    """Action button with primary/secondary variants."""

    def __init__(self, text: str, primary: bool = False, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._primary = primary
        self._apply_style()

    def _apply_style(self):
        if self._primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {COLORS['accent_dim']}, stop:1 {COLORS['accent_primary']});
                    color: #ffffff;
                    border: none;
                    border-radius: 7px;
                    padding: 9px 14px;
                    font-family: {FONTS['display']};
                    font-weight: 600;
                    font-size: 12px;
                    text-transform: uppercase;
                    letter-spacing: 0.8px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {COLORS['accent_primary']}, stop:1 {COLORS['accent_glow']});
                }}
                QPushButton:pressed {{
                    background: {COLORS['accent_dim']};
                    padding-top: 10px;
                    padding-bottom: 8px;
                }}
                QPushButton:disabled {{
                    background: {COLORS['bg_elevated']};
                    color: {COLORS['text_muted']};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS['bg_elevated']};
                    color: {COLORS['text_secondary']};
                    border: 1px solid {COLORS['border_subtle']};
                    border-radius: 7px;
                    padding: 9px 14px;
                    font-family: {FONTS['display']};
                    font-weight: 500;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background: {COLORS['bg_hover']};
                    border-color: {COLORS['accent_primary']};
                    color: {COLORS['text_primary']};
                }}
                QPushButton:pressed {{
                    background: {COLORS['accent_dim']};
                    border-color: {COLORS['accent_primary']};
                    color: #ffffff;
                }}
                QPushButton:disabled {{
                    background: {COLORS['bg_base']};
                    color: {COLORS['text_muted']};
                    border-color: {COLORS['border_subtle']};
                }}
            """)


class StatusLog(QFrame):
    """Terminal-style status log display."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusLog")
        self._setup_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(8)

        header = QLabel("◆ STATUS LOG")
        header.setStyleSheet(f"""
            QLabel {{
                color: {COLORS['text_muted']};
                font-family: {FONTS['mono']};
                font-size: 10px;
                font-weight: 600;
                letter-spacing: 1.5px;
                background: transparent;
                padding-left: 2px;
            }}
        """)
        layout.addWidget(header)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(110)
        self.log_area.setStyleSheet(f"""
            QTextEdit {{
                background: {COLORS['bg_void']};
                color: {COLORS['text_muted']};
                border: 1px solid {COLORS['border_subtle']};
                border-radius: 8px;
                padding: 12px;
                font-family: {FONTS['mono']};
                font-size: 11px;
                line-height: 1.5;
            }}
            QTextEdit QScrollBar:vertical {{
                background: {COLORS['bg_deep']};
                width: 8px;
                border-radius: 4px;
            }}
            QTextEdit QScrollBar::handle:vertical {{
                background: {COLORS['border_default']};
                border-radius: 4px;
                min-height: 30px;
            }}
            QTextEdit QScrollBar::handle:vertical:hover {{
                background: {COLORS['text_muted']};
            }}
        """)
        layout.addWidget(self.log_area)

    def _setup_style(self):
        self.setStyleSheet(f"""
            #statusLog {{
                background: transparent;
            }}
        """)

    def append(self, text: str):
        self.log_area.append(text)

    def clear(self):
        self.log_area.clear()


class CollapsibleBox(QFrame):
    """Collapsible accordion section with smooth toggle."""

    expanded = pyqtSignal(object)

    def __init__(self, title: str, icon: str = "", expanded: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("collapsibleBox")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._expanded = expanded
        self._title = title
        self._icon = icon

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header button
        self.header = QPushButton()
        self.header.setObjectName("collapsibleHeader")
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.clicked.connect(self._toggle)
        self._update_header_text()
        self.main_layout.addWidget(self.header)

        # Content container
        self.content = QWidget()
        self.content.setObjectName("collapsibleContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(*CONTENT_MARGINS)
        self.content_layout.setSpacing(WIDGET_SPACING)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main_layout.addWidget(self.content)

        # Set initial state
        self.content.setVisible(self._expanded)
        self._apply_header_style()

    def _update_header_text(self):
        """Update header text with chevron indicator."""
        chevron = "▾" if self._expanded else "▸"
        icon_part = f" {self._icon}" if self._icon else ""
        self.header.setText(f"  {chevron}{icon_part}  {self._title}")

    def _apply_header_style(self):
        """Apply header styling based on state."""
        accent = COLORS['accent_glow'] if self._expanded else COLORS['text_secondary']
        bg = COLORS['bg_surface'] if self._expanded else COLORS['bg_elevated']

        self.header.setStyleSheet(f"""
            #collapsibleHeader {{
                background: {bg};
                color: {accent};
                border: none;
                border-radius: 6px;
                padding: 10px 14px;
                font-family: {FONTS['display']};
                font-weight: 600;
                font-size: 13px;
                text-align: left;
            }}
            #collapsibleHeader:hover {{
                background: {COLORS['bg_hover']};
                color: {COLORS['accent_glow']};
            }}
        """)

    def _toggle(self):
        """Toggle content visibility."""
        self._expanded = not self._expanded
        self.content.setVisible(self._expanded)
        self._update_header_text()
        self._apply_header_style()
        if self._expanded:
            self.expanded.emit(self)

    def addWidget(self, widget):
        """Add a widget to the content area."""
        self.content_layout.addWidget(widget)

    def addLayout(self, layout):
        """Add a layout to the content area."""
        self.content_layout.addLayout(layout)

    def setExpanded(self, expanded: bool):
        """Programmatically set expanded state."""
        if self._expanded != expanded:
            self._toggle()

    def isExpanded(self) -> bool:
        """Return current expanded state."""
        return self._expanded


class SidebarTitle(QWidget):
    """App branding header with NeuroFlow title."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 20)
        layout.setSpacing(6)

        # App name with custom styling
        title = QLabel("NeuroFlow")
        title.setStyleSheet(f"""
            QLabel {{
                font-family: {FONTS['display']};
                font-size: 26px;
                font-weight: 700;
                color: {COLORS['accent_glow']};
                background: transparent;
                letter-spacing: -0.5px;
            }}
        """)
        layout.addWidget(title)

        # Tagline with refined typography
        tagline = QLabel("Professional EEG Analysis")
        tagline.setStyleSheet(f"""
            QLabel {{
                font-family: {FONTS['body']};
                font-size: 11px;
                font-weight: 400;
                color: {COLORS['text_muted']};
                background: transparent;
                letter-spacing: 0.8px;
            }}
        """)
        layout.addWidget(tagline)

        # Subtle separator line
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 transparent,
                stop:0.2 {COLORS['border_subtle']},
                stop:0.8 {COLORS['border_subtle']},
                stop:1 transparent);
        """)
        layout.addWidget(separator)
