"""
Dialog Components Module

Contains all dialog and popup windows:
- DatasetInfoDialog: Shows dataset metadata and event statistics
- ConnectivityDialog: Displays connectivity plots
- ERPViewer: Interactive ERP analysis window
"""

import os
from typing import List, Tuple

import mne

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from PyQt6.QtWidgets import (
    QDialog, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSlider, QSplitter, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QApplication
)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QTimer

from .canvas import MplCanvas


class ConnectivityDialog(QDialog):
    """
    Popup Window for displaying Connectivity Plots.
    Uses its own FigureCanvas to show the circular graph.
    """

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
        """Displays the given Matplotlib Figure."""
        if self.canvas:
            self.layout.removeWidget(self.canvas)
            self.canvas.deleteLater()

        self.canvas = FigureCanvasQTAgg(fig)
        self.layout.insertWidget(0, self.canvas)

        fig.patch.set_facecolor('#2b2b2b')
        self.canvas.draw()


class DatasetInfoDialog(QDialog):
    """
    Dialog displaying comprehensive metadata about the loaded EEG dataset.
    Includes General Info and Event Statistics tabs for quality control.
    """

    def __init__(self, raw: mne.io.BaseRaw, parent=None, pipeline_history: list = None):
        super().__init__(parent)
        self.setWindowTitle("Dataset Inspector")
        self.resize(550, 500)
        self.raw = raw
        self.pipeline_history = pipeline_history or []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Tab widget for different info categories
        tabs = QTabWidget()

        # --- Tab 1: General Info ---
        tab_general = QWidget()
        form_layout = QVBoxLayout(tab_general)
        form_layout.setSpacing(12)
        form_layout.setContentsMargins(15, 15, 15, 15)

        info_pairs = self._get_general_info()
        for label_text, value_text in info_pairs:
            row = QHBoxLayout()
            label = QLabel(f"<b>{label_text}:</b>")
            label.setFixedWidth(120)
            value = QLabel(value_text)
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(label)
            row.addWidget(value, 1)
            form_layout.addLayout(row)

        form_layout.addStretch()
        tabs.addTab(tab_general, "General Info")

        # --- Tab 2: Event Statistics ---
        tab_events = QWidget()
        events_layout = QVBoxLayout(tab_events)
        events_layout.setContentsMargins(10, 10, 10, 10)

        self.event_table = self._create_event_table()
        events_layout.addWidget(self.event_table)

        tabs.addTab(tab_events, "Event Statistics")

        # --- Tab 3: Processing History ---
        tab_history = QWidget()
        history_layout = QVBoxLayout(tab_history)
        history_layout.setContentsMargins(10, 10, 10, 10)

        import json
        history_text = QTextEdit()
        history_text.setReadOnly(True)
        history_text.setFont(QFont("Consolas", 9))
        if self.pipeline_history:
            history_text.setPlainText(json.dumps(self.pipeline_history, indent=2))
        else:
            history_text.setPlainText("No processing steps recorded yet.")
        history_layout.addWidget(history_text)

        # Copy to clipboard button
        btn_copy = QPushButton("Copy to Clipboard")
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(history_text.toPlainText()))
        history_layout.addWidget(btn_copy)

        tabs.addTab(tab_history, "Processing History")

        layout.addWidget(tabs)

        # Close button
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _get_general_info(self) -> List[Tuple[str, str]]:
        """Extract general metadata from the raw object."""
        info = self.raw.info
        info_pairs = []

        # File path
        filenames = self.raw.filenames
        if filenames:
            filename = os.path.basename(filenames[0])
        else:
            filename = "Unknown"
        info_pairs.append(("File", filename))

        # Measurement date
        meas_date = info.get("meas_date")
        if meas_date is not None:
            date_str = meas_date.strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_str = "Not recorded"
        info_pairs.append(("Meas Date", date_str))

        # Duration
        duration_sec = self.raw.times[-1]
        minutes = int(duration_sec // 60)
        seconds = int(duration_sec % 60)
        info_pairs.append(("Duration", f"{minutes:02d}:{seconds:02d} ({duration_sec:.1f}s)"))

        # Sampling rate
        sfreq = info.get("sfreq", 0)
        info_pairs.append(("Sampling Rate", f"{sfreq:.1f} Hz"))

        # Channels summary
        ch_types_count = {}
        for ch in info["chs"]:
            ch_type = mne.channel_type(info, info["ch_names"].index(ch["ch_name"]))
            ch_types_count[ch_type] = ch_types_count.get(ch_type, 0) + 1

        total_chs = len(info["ch_names"])
        type_summary = ", ".join(f"{count} {t.upper()}" for t, count in ch_types_count.items())
        info_pairs.append(("Channels", f"{total_chs} ({type_summary})"))

        # Filter settings
        highpass = info.get("highpass", 0)
        lowpass = info.get("lowpass", 0)
        info_pairs.append(("High-pass", f"{highpass:.2f} Hz" if highpass else "DC"))
        info_pairs.append(("Low-pass", f"{lowpass:.1f} Hz" if lowpass else "None"))

        return info_pairs

    def _create_event_table(self):
        """Create a table widget displaying event type counts."""
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Event Type/ID", "Count"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)

        # Get events from annotations
        try:
            events, event_id = mne.events_from_annotations(self.raw, verbose=False)
            event_counts = {}
            for event in events:
                eid = event[2]
                event_counts[eid] = event_counts.get(eid, 0) + 1

            # Invert event_id dict for name lookup
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
    """
    Dedicated Window for Interactive ERP Analysis.
    Displays:
    1. Butterfly Plot (Top) - Temporal view of all sensors.
    2. Topomap (Bottom) - Spatial view at a specific time point.
    Controls:
    - Time Slider to scrub through the epoch.
    """

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
            QMainWindow { background-color: #2b2b2b; }
            QLabel { color: #ffffff; font-size: 14px; font-weight: bold; }
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 8px;
                background: #1e1e1e;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #007acc;
                border: 1px solid #555;
                width: 18px;
                height: 18px;
                margin: -7px 0;
                border-radius: 9px;
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
        """Draws the static Butterfly plot and initial Topomap."""
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
