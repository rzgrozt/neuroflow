"""Dialog Components - Dataset info, connectivity plots, and ERP viewer."""

import os
from typing import List, Tuple

import mne

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PyQt6.QtWidgets import (
    QDialog, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QSplitter, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QApplication,
    QListWidget, QListWidgetItem, QFrame
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from .canvas import MplCanvas


class ConnectivityDialog(QDialog):
    """Popup window for displaying connectivity plots."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connectivity Explorer")
        self.resize(800, 800)
        self.layout = QVBoxLayout(self)
        self.canvas = None

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        self.layout.addWidget(self.btn_close)

    def plot(self, fig):
        """Display the given Matplotlib Figure."""
        if self.canvas:
            self.layout.removeWidget(self.canvas)
            self.canvas.deleteLater()

        self.canvas = FigureCanvasQTAgg(fig)
        self.layout.insertWidget(0, self.canvas)

        fig.patch.set_facecolor('#1e1e1e')
        self.canvas.draw()


class DatasetInfoDialog(QDialog):
    """Dialog displaying dataset metadata and event statistics."""

    def __init__(self, raw: mne.io.BaseRaw, parent=None, pipeline_history: list = None):
        super().__init__(parent)
        self.setWindowTitle("Dataset Inspector")
        self.resize(550, 500)
        self.raw = raw
        self.pipeline_history = pipeline_history or []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #252538;
                border-radius: 0px;
                top: -1px; 
            }
            QTabBar::tab {
                min-width: 120px;
            }
        """)

        # General Info Tab
        tab_general = QWidget()
        form_layout = QVBoxLayout(tab_general)
        form_layout.setSpacing(16)
        form_layout.setContentsMargins(24, 24, 24, 24)

        info_pairs = self._get_general_info()
        for label_text, value_text in info_pairs:
            row = QHBoxLayout()
            label = QLabel(f"{label_text}:")
            label.setFixedWidth(130)
            label.setStyleSheet("color: #9090a8; font-weight: 600; font-size: 13px;")
            
            value = QLabel(value_text)
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            value.setStyleSheet("color: #e0e0f0; font-size: 13px;")
            
            row.addWidget(label)
            row.addWidget(value, 1)
            form_layout.addLayout(row)

        form_layout.addStretch()
        tabs.addTab(tab_general, "General Info")

        # Event Statistics Tab
        tab_events = QWidget()
        events_layout = QVBoxLayout(tab_events)
        events_layout.setContentsMargins(0, 0, 0, 0)

        self.event_table = self._create_event_table()
        self.event_table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: #0a0a10;
            }
            QHeaderView::section {
                background-color: #12121c;
                border: none;
                border-bottom: 1px solid #252538;
                padding: 8px;
            }
        """)
        events_layout.addWidget(self.event_table)

        tabs.addTab(tab_events, "Event Statistics")

        # Processing History Tab
        tab_history = QWidget()
        history_layout = QVBoxLayout(tab_history)
        history_layout.setContentsMargins(16, 16, 16, 16)
        history_layout.setSpacing(12)

        import json
        history_text = QTextEdit()
        history_text.setReadOnly(True)
        history_text.setFont(QFont("JetBrains Mono", 12))
        history_text.setStyleSheet("""
            QTextEdit {
                background-color: #08080c;
                border: 1px solid #252538;
                border-radius: 8px;
                padding: 12px;
                color: #a0a0b8;
            }
        """)
        
        if self.pipeline_history:
            history_text.setPlainText(json.dumps(self.pipeline_history, indent=2))
        else:
            history_text.setPlainText("No processing steps recorded yet.")
        history_layout.addWidget(history_text)

        tabs.addTab(tab_history, "Processing History")

        layout.addWidget(tabs)

        # Bottom Bar
        bottom_bar = QWidget()
        bottom_bar.setStyleSheet("background-color: #151520; border-top: 1px solid #252538;")
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(16, 12, 16, 12)
        bottom_layout.addStretch()

        btn_close = QPushButton("Close")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setFixedWidth(100)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #0080b8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0090cc;
            }
            QPushButton:pressed {
                background-color: #0070a0;
            }
        """)
        btn_close.clicked.connect(self.accept)
        bottom_layout.addWidget(btn_close)
        
        layout.addWidget(bottom_bar)

    def _get_general_info(self) -> List[Tuple[str, str]]:
        """Extract general metadata from the raw object."""
        info = self.raw.info
        info_pairs = []

        filenames = self.raw.filenames
        if filenames:
            filename = os.path.basename(filenames[0])
        else:
            filename = "Unknown"
        info_pairs.append(("File", filename))

        meas_date = info.get("meas_date")
        if meas_date is not None:
            date_str = meas_date.strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_str = "Not recorded"
        info_pairs.append(("Meas Date", date_str))

        duration_sec = self.raw.times[-1]
        minutes = int(duration_sec // 60)
        seconds = int(duration_sec % 60)
        info_pairs.append(("Duration", f"{minutes:02d}:{seconds:02d} ({duration_sec:.1f}s)"))

        sfreq = info.get("sfreq", 0)
        info_pairs.append(("Sampling Rate", f"{sfreq:.1f} Hz"))

        ch_types_count = {}
        for ch in info["chs"]:
            ch_type = mne.channel_type(info, info["ch_names"].index(ch["ch_name"]))
            ch_types_count[ch_type] = ch_types_count.get(ch_type, 0) + 1

        total_chs = len(info["ch_names"])
        type_summary = ", ".join(f"{count} {t.upper()}" for t, count in ch_types_count.items())
        info_pairs.append(("Channels", f"{total_chs} ({type_summary})"))

        highpass = info.get("highpass", 0)
        lowpass = info.get("lowpass", 0)
        info_pairs.append(("High-pass", f"{highpass:.2f} Hz" if highpass else "DC"))
        info_pairs.append(("Low-pass", f"{lowpass:.1f} Hz" if lowpass else "None"))

        return info_pairs

    def _create_event_table(self):
        """Create table widget displaying event type counts."""
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Event Type/ID", "Count"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)

        try:
            events, event_id = mne.events_from_annotations(self.raw, verbose=False)
            event_counts = {}
            for event in events:
                eid = event[2]
                event_counts[eid] = event_counts.get(eid, 0) + 1

            id_to_name = {v: k for k, v in event_id.items()}

            table.setRowCount(len(event_counts))
            for row, (eid, count) in enumerate(sorted(event_counts.items())):
                name = id_to_name.get(eid, f"Unknown ({eid})")
                table.setItem(row, 0, QTableWidgetItem(name))
                table.setItem(row, 1, QTableWidgetItem(str(count)))

        except Exception:
            table.setRowCount(1)
            table.setItem(0, 0, QTableWidgetItem("No events found"))
            table.setItem(0, 1, QTableWidgetItem("-"))

        return table


class ERPViewer(QMainWindow):
    """Interactive ERP analysis window with butterfly plot and topomap."""

    def __init__(self, evoked, parent=None):
        super().__init__(parent)
        self.evoked = evoked
        self.setWindowTitle("Interactive ERP Explorer")
        self.resize(800, 900)
        self.apply_dark_theme()

        self.times = self.evoked.times
        self.tmin = self.times[0]
        self.tmax = self.times[-1]
        self.current_time = 0.0
        self.vline = None

        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.timeout.connect(self.update_topomap_heavy)

        self.init_ui()
        self.plot_initial_state()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #0d0d12; }
            QLabel { color: #ffffff; font-size: 14px; font-weight: bold; }
            QSlider::groove:horizontal {
                border: 1px solid #282840;
                height: 8px;
                background: #181824;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #00d4ff, stop:1 #0090c0);
                border: 1px solid #282840;
                width: 18px;
                height: 18px;
                margin: -7px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #00e4ff;
            }
            QSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #005080, stop:1 #00a8e8);
                border-radius: 4px;
            }
        """)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.butterfly_canvas = MplCanvas(self, width=5, height=4)
        splitter.addWidget(self.butterfly_canvas)

        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)

        self.topomap_canvas = MplCanvas(self, width=5, height=4)
        bottom_layout.addWidget(self.topomap_canvas)

        controls_layout = QHBoxLayout()

        self.lbl_time = QLabel("Time: 0 ms")
        self.lbl_time.setFixedWidth(100)

        min_ms = int(self.tmin * 1000)
        max_ms = int(self.tmax * 1000)

        self.slider_time = QSlider(Qt.Orientation.Horizontal)
        self.slider_time.setRange(min_ms, max_ms)
        self.slider_time.setValue(0)
        self.slider_time.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_time.setTickInterval(50)
        self.slider_time.valueChanged.connect(self.on_time_changed)

        controls_layout.addWidget(self.lbl_time)
        controls_layout.addWidget(self.slider_time)

        bottom_layout.addLayout(controls_layout)
        splitter.addWidget(bottom_widget)

        main_layout.addWidget(splitter)

    def plot_initial_state(self):
        """Draw the static butterfly plot and initial topomap."""
        ax = self.butterfly_canvas.axes
        ax.clear()

        self.evoked.plot(axes=ax, spatial_colors=True, show=False, time_unit='s')

        ax.set_title("Global Field Power (Butterfly Plot)", color='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(colors='white')

        self.vline = ax.axvline(x=0, color='white', linestyle='--', linewidth=1.5, alpha=0.8)
        self.butterfly_canvas.draw()

        self.update_topomap_heavy()

    def on_time_changed(self, value):
        time_sec = value / 1000.0
        self.current_time = time_sec
        self.lbl_time.setText(f"Time: {value} ms")

        if self.vline:
            self.vline.set_xdata([time_sec, time_sec])
            self.butterfly_canvas.draw()

        self.debounce_timer.start(100)

    def update_topomap_heavy(self):
        t = self.current_time

        ax = self.topomap_canvas.axes
        ax.clear()

        try:
            self.evoked.plot_topomap(
                times=[t], axes=ax, show=False, colorbar=False,
                outlines='head', sphere='auto'
            )

            ax.set_title(f"Topography at {t*1000:.0f} ms", color='white', fontsize=12)
            self.topomap_canvas.draw()
        except Exception as e:
            print(f"Topomap Error: {e}")



class ChannelManagerDialog(QDialog):
    """Dialog for managing and interpolating bad EEG channels."""
    
    interpolate_requested = pyqtSignal(list)  # Emits list of channels to interpolate

    def __init__(self, raw: mne.io.BaseRaw, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Channel Manager")
        self.resize(450, 550)
        self.raw = raw
        self.setModal(True)
        
        self._init_ui()
        self._populate_channels()

    def _init_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setStyleSheet("background-color: #151520; border-bottom: 1px solid #252538;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        
        title = QLabel("Channel Manager")
        title.setStyleSheet("color: #e0e0f0; font-size: 16px; font-weight: 600;")
        header_layout.addWidget(title)
        
        subtitle = QLabel("Select channels to mark as bad and interpolate using spherical spline interpolation.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #8080a0; font-size: 12px;")
        header_layout.addWidget(subtitle)
        
        layout.addWidget(header)

        # Channel List Container
        list_container = QWidget()
        list_container.setStyleSheet("background-color: #0a0a10;")
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(16, 16, 16, 16)
        list_layout.setSpacing(12)

        # Info label
        info_label = QLabel("Channels:")
        info_label.setStyleSheet("color: #9090a8; font-size: 13px; font-weight: 600;")
        list_layout.addWidget(info_label)

        # Channel list widget
        self.channel_list = QListWidget()
        self.channel_list.setStyleSheet("""
            QListWidget {
                background-color: #12121c;
                border: 1px solid #252538;
                border-radius: 8px;
                padding: 8px;
                color: #e0e0f0;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
            }
            QListWidget::item:hover {
                background-color: #1a1a28;
            }
            QListWidget::item:selected {
                background-color: #252540;
            }
        """)
        self.channel_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        list_layout.addWidget(self.channel_list)

        # Selection info
        self.selection_label = QLabel("0 channel(s) selected")
        self.selection_label.setStyleSheet("color: #6080a0; font-size: 12px;")
        list_layout.addWidget(self.selection_label)
        
        # Connect selection change
        self.channel_list.itemSelectionChanged.connect(self._on_selection_changed)

        layout.addWidget(list_container, 1)

        # Button Bar
        button_bar = QWidget()
        button_bar.setStyleSheet("background-color: #151520; border-top: 1px solid #252538;")
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(16, 12, 16, 12)
        button_layout.setSpacing(12)

        # Select All / Deselect All buttons
        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_select_all.setStyleSheet(self._get_secondary_button_style())
        self.btn_select_all.clicked.connect(self._select_all)
        button_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deselect_all.setStyleSheet(self._get_secondary_button_style())
        self.btn_deselect_all.clicked.connect(self._deselect_all)
        button_layout.addWidget(self.btn_deselect_all)

        button_layout.addStretch()

        # Cancel button
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.setFixedWidth(90)
        self.btn_cancel.setStyleSheet(self._get_secondary_button_style())
        self.btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(self.btn_cancel)

        # Interpolate button
        self.btn_interpolate = QPushButton("Interpolate")
        self.btn_interpolate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_interpolate.setFixedWidth(120)
        self.btn_interpolate.setStyleSheet(self._get_primary_button_style())
        self.btn_interpolate.clicked.connect(self._on_interpolate_clicked)
        self.btn_interpolate.setEnabled(False)
        button_layout.addWidget(self.btn_interpolate)

        layout.addWidget(button_bar)

    def _populate_channels(self):
        """Populate the channel list with all channels from the raw object."""
        if self.raw is None:
            return

        current_bads = self.raw.info.get('bads', [])
        
        for ch_name in self.raw.ch_names:
            item = QListWidgetItem(ch_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            
            # Mark already known bad channels as selected
            if ch_name in current_bads:
                item.setSelected(True)
                item.setText(f"{ch_name} (marked bad)")
            
            self.channel_list.addItem(item)

    def _on_selection_changed(self):
        """Update selection label and button state when selection changes."""
        selected_count = len(self.channel_list.selectedItems())
        self.selection_label.setText(f"{selected_count} channel(s) selected")
        self.btn_interpolate.setEnabled(selected_count > 0)

    def _select_all(self):
        """Select all channels in the list."""
        self.channel_list.selectAll()

    def _deselect_all(self):
        """Deselect all channels in the list."""
        self.channel_list.clearSelection()

    def _on_interpolate_clicked(self):
        """Emit signal with selected channels and close dialog."""
        selected_channels = []
        for item in self.channel_list.selectedItems():
            # Extract channel name (remove " (marked bad)" suffix if present)
            ch_name = item.text().replace(" (marked bad)", "")
            selected_channels.append(ch_name)
        
        if selected_channels:
            self.interpolate_requested.emit(selected_channels)
            self.accept()

    def get_selected_channels(self) -> list:
        """Return list of selected channel names."""
        selected_channels = []
        for item in self.channel_list.selectedItems():
            ch_name = item.text().replace(" (marked bad)", "")
            selected_channels.append(ch_name)
        return selected_channels

    def _get_primary_button_style(self) -> str:
        """Return stylesheet for primary action buttons."""
        return """
            QPushButton {
                background-color: #0080b8;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #0090cc;
            }
            QPushButton:pressed {
                background-color: #0070a0;
            }
            QPushButton:disabled {
                background-color: #404060;
                color: #808090;
            }
        """

    def _get_secondary_button_style(self) -> str:
        """Return stylesheet for secondary action buttons."""
        return """
            QPushButton {
                background-color: #252538;
                color: #c0c0d0;
                border: 1px solid #353550;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #303048;
                border-color: #454560;
            }
            QPushButton:pressed {
                background-color: #202030;
            }
        """
