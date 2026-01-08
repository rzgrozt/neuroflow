"""
Sidebar Components Module for NeuroFlow

Contains styled sidebar widgets with "Neural Elegance" theme:
- SectionCard: Card-style container for grouped controls
- ParamRow: Clean parameter input row
- ActionButton: Styled action buttons with states
- CollapsibleBox: Collapsible section with triangle toggle icons
- StyledSidebar: Complete sidebar widget assembly
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QComboBox, QDoubleSpinBox, QTextEdit,
    QScrollArea, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont


# =============================================================================
# STYLE CONSTANTS - Single source of truth for consistent styling
# =============================================================================

# Layout constants
LABEL_WIDTH = 50  # Fixed label width for all param rows
WIDGET_SPACING = 6  # Standard spacing between widgets
CONTENT_MARGINS = (8, 6, 8, 8)  # Standard content margins (left, top, right, bottom)
CARD_MARGINS = (10, 10, 10, 10)  # Card internal margins

# Label style - shared across all param widgets
LABEL_STYLE = """
    QLabel {
        color: #9090a8;
        font-size: 12px;
        font-weight: 500;
        background: transparent;
    }
"""


class SectionHeader(QWidget):
    """
    Modern section header with icon and title.
    Replaces QGroupBox titles with a cleaner design.
    """

    def __init__(self, title: str, icon: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(8)

        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    color: #00c8ff;
                    background: transparent;
                }
            """)
            layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                font-weight: 600;
                color: #00c8ff;
                background: transparent;
                letter-spacing: 0.5px;
            }
        """)
        layout.addWidget(title_label)
        layout.addStretch()


class SectionCard(QFrame):
    """
    Card-style container for grouped controls.
    Provides a subtle elevated surface with proper spacing.
    """

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

        # Content layout for child widgets
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(WIDGET_SPACING)
        self.main_layout.addLayout(self.content_layout)

    def _setup_style(self):
        self.setStyleSheet("""
            #sectionCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(26, 26, 40, 0.95),
                    stop:1 rgba(20, 20, 32, 0.95));
                border: 1px solid #252538;
                border-radius: 12px;
            }
        """)

    def addWidget(self, widget):
        # Ensure widgets expand horizontally to fill the card width
        widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            widget.sizePolicy().verticalPolicy()
        )
        self.content_layout.addWidget(widget)

    def addLayout(self, layout):
        self.content_layout.addLayout(layout)


class ParamRow(QWidget):
    """
    Clean parameter input row with label and input field.
    Used for filter parameters, time ranges, etc.
    """

    valueChanged = pyqtSignal(str)

    def __init__(self, label: str, default: str = "", placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(WIDGET_SPACING)

        # Label
        self.label = QLabel(label)
        self.label.setFixedWidth(LABEL_WIDTH)
        self.label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(self.label)

        # Input
        self.input = QLineEdit(default)
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
    """
    Horizontal row with fixed-width label and flexible QComboBox.
    Matches ParamRow structure for consistent responsive behavior.
    """

    currentIndexChanged = pyqtSignal(int)

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(WIDGET_SPACING)

        # Label
        self.label = QLabel(label)
        self.label.setFixedWidth(LABEL_WIDTH)
        self.label.setStyleSheet(LABEL_STYLE)
        layout.addWidget(self.label)

        # ComboBox (flexible width)
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self.currentIndexChanged.emit)
        layout.addWidget(self.combo)

    def setEnabled(self, enabled: bool):
        self.combo.setEnabled(enabled)


class ParamSpinRow(QWidget):
    """
    Parameter row with double spin boxes for range inputs.
    """

    def __init__(self, label: str, min_val: float, max_val: float,
                 default_min: float, default_max: float, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Label
        lbl = QLabel(label)
        lbl.setFixedWidth(LABEL_WIDTH)
        lbl.setStyleSheet(LABEL_STYLE)
        layout.addWidget(lbl)

        # Min spin
        self.spin_min = QDoubleSpinBox()
        self.spin_min.setRange(min_val, max_val)
        self.spin_min.setValue(default_min)
        layout.addWidget(self.spin_min)

        # Separator
        sep = QLabel("–")
        sep.setStyleSheet("color: #606080; background: transparent;")
        sep.setFixedWidth(12)
        sep.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sep)

        # Max spin
        self.spin_max = QDoubleSpinBox()
        self.spin_max.setRange(min_val, max_val)
        self.spin_max.setValue(default_max)
        layout.addWidget(self.spin_max)

    def values(self) -> tuple:
        return (self.spin_min.value(), self.spin_max.value())


class ActionButton(QPushButton):
    """
    Styled action button with primary/secondary variants.
    """

    def __init__(self, text: str, primary: bool = False, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._primary = primary
        self._apply_style()

    def _apply_style(self):
        if self._primary:
            self.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #0080b8, stop:1 #00a8e8);
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-weight: 600;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #0090cc, stop:1 #00b8f8);
                }
                QPushButton:pressed {
                    background: #0070a0;
                }
                QPushButton:disabled {
                    background: #1a1a28;
                    color: #454560;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #1c1c28;
                    color: #c8c8e0;
                    border: 1px solid #2a2a40;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-weight: 500;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #252538;
                    border-color: #00a8e8;
                    color: #ffffff;
                }
                QPushButton:pressed {
                    background-color: #00a8e8;
                    color: #ffffff;
                }
                QPushButton:disabled {
                    background-color: #141420;
                    color: #404058;
                    border-color: #1a1a28;
                }
            """)


class StatusLog(QFrame):
    """
    Styled status log area with header.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusLog")
        self._setup_style()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header = QLabel("Status Log")
        header.setStyleSheet("""
            QLabel {
                color: #707088;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1px;
                background: transparent;
                padding-left: 4px;
            }
        """)
        layout.addWidget(header)

        # Log area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMinimumHeight(120)
        self.log_area.setStyleSheet("""
            QTextEdit {
                background-color: #08080c;
                color: #8080a0;
                border: 1px solid #1a1a28;
                border-radius: 8px;
                padding: 10px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.log_area)

    def _setup_style(self):
        self.setStyleSheet("""
            #statusLog {
                background: transparent;
            }
        """)

    def append(self, text: str):
        self.log_area.append(text)

    def clear(self):
        self.log_area.clear()


class CollapsibleBox(QFrame):
    """
    Collapsible accordion section with triangle toggle icons.
    Provides a compact, inspector-panel style collapsible container.
    """

    expanded = pyqtSignal(object)  # Emits self when expanded

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

        # Header button with triangle icon
        self.header = QPushButton()
        self.header.setObjectName("collapsibleHeader")
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.clicked.connect(self._toggle)
        self._update_header_text()
        self._style_header()
        self.main_layout.addWidget(self.header)

        # Content container
        self.content = QWidget()
        self.content.setObjectName("collapsibleContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(*CONTENT_MARGINS)
        self.content_layout.setSpacing(WIDGET_SPACING)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main_layout.addWidget(self.content)

        # Set initial visibility
        self.content.setVisible(self._expanded)
        self._update_header_style()

    def _update_header_text(self):
        """Update header text with appropriate triangle icon."""
        triangle = "▼" if self._expanded else "▶"
        icon_part = f" {self._icon}" if self._icon else ""
        self.header.setText(f"  {triangle}{icon_part}  {self._title}")

    def _style_header(self):
        """Apply base header styling."""
        self.header.setStyleSheet("""
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
        """)

    def _update_header_style(self):
        """Update header styling based on expanded state."""
        if self._expanded:
            self.header.setStyleSheet("""
                #collapsibleHeader {
                    background: #2d2d2d;
                    color: #00d4ff;
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
            """)
        else:
            self._style_header()

    def _toggle(self):
        """Toggle content visibility."""
        self._expanded = not self._expanded
        self.content.setVisible(self._expanded)
        self._update_header_text()
        self._update_header_style()
        if self._expanded:
            self.expanded.emit(self)  # Notify when opened

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
    """
    App title widget for sidebar header.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 16)
        layout.setSpacing(4)

        # App name
        title = QLabel("NeuroFlow")
        title.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: 700;
                color: #00d4ff;
                background: transparent;
                letter-spacing: -0.5px;
            }
        """)
        layout.addWidget(title)

        # Tagline
        tagline = QLabel("Professional EEG Analysis")
        tagline.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #606078;
                background: transparent;
                letter-spacing: 0.5px;
            }
        """)
        layout.addWidget(tagline)


def create_styled_sidebar():
    """
    Factory function to create the base styled sidebar frame.
    Returns the frame, layout, and scroll area.
    """
    # Main sidebar frame
    sidebar = QFrame()
    sidebar.setObjectName("styledSidebar")
    sidebar.setFixedWidth(300)
    sidebar.setStyleSheet("""
        #styledSidebar {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #0d0d14,
                stop:1 #0a0a10);
            border-right: 1px solid #1a1a28;
            border-radius: 0px;
        }
    """)

    main_layout = QVBoxLayout(sidebar)
    main_layout.setContentsMargins(4, 8, 4, 8)
    main_layout.setSpacing(8)

    return sidebar, main_layout
