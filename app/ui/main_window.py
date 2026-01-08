"""
Main Window Module

Contains the MainWindow class - the primary application window.
"""

import traceback

import mne
import numpy as np

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QFileDialog, QFrame,
    QMessageBox, QComboBox, QDoubleSpinBox,
    QTabWidget, QToolBar, QApplication, QSplitter,
    QScrollArea, QSizePolicy
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize

from app.core.workers import EEGWorker
from .canvas import MplCanvas
from .dialogs import DatasetInfoDialog, ConnectivityDialog, ERPViewer
from .theme import ModernAboutDialog


class MainWindow(QMainWindow):
    """
    Main application window for NeuroFlow EEG analysis.
    """
    # Signals to communicate with worker
    request_load_data = pyqtSignal(str)
    # Signal sending: (High-pass/l_freq, Low-pass/h_freq, Notch)
    request_run_pipeline = pyqtSignal(float, float, float)
    request_run_ica = pyqtSignal()
    request_apply_ica = pyqtSignal(str)
    request_compute_erp = pyqtSignal(str, float, float)
    request_compute_tfr = pyqtSignal(str, float, float)
    request_compute_connectivity = pyqtSignal()
    request_save_data = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NeuroFlow - Professional EEG Analysis")
        self.resize(1300, 850)
        self.raw_data = None
        self.epochs = None  # Holds epochs for manual inspection
        self.epochs_inspected = False  # Flag to track if epochs have been inspected

        # Pipeline history for traceability
        self.pipeline_history = []
        self.source_filename = None  # Base filename without extension

        self.thread = QThread()
        self.worker = EEGWorker()
        self.worker.moveToThread(self.thread)

        self.worker.log_message.connect(self.log_status)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.data_loaded.connect(self.on_data_loaded)
        self.worker.psd_ready.connect(self.update_plot)
        self.worker.ica_ready.connect(self.display_ica_components)
        self.worker.events_loaded.connect(self.populate_event_dropdown)
        self.worker.erp_ready.connect(self.handle_erp_ready)
        self.worker.tfr_ready.connect(self.plot_tfr)
        self.worker.connectivity_ready.connect(self.plot_connectivity)
        self.worker.save_finished.connect(self.on_save_finished)

        self.request_load_data.connect(self.worker.load_data)
        self.request_run_pipeline.connect(self.worker.run_pipeline)
        self.request_run_ica.connect(self.worker.run_ica)
        self.request_apply_ica.connect(self.worker.apply_ica)
        self.request_compute_erp.connect(self.worker.compute_erp)
        self.request_compute_tfr.connect(self.worker.compute_tfr)
        self.request_compute_connectivity.connect(self.worker.compute_connectivity)
        self.request_save_data.connect(self.worker.save_data)

        self.thread.start()

        self.init_ui()
        self.create_menu()

    def create_menu(self):
        """Creates the Menu Bar."""
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")

        save_action = QAction("&Save Clean Data", self)
        save_action.setShortcut("Ctrl+S")
        save_action.setStatusTip("Save the processed data to .fif")
        save_action.triggered.connect(self.on_save_clean_data)
        file_menu.addAction(save_action)

        screenshot_action = QAction("S&creenshot", self)
        screenshot_action.setShortcut("Ctrl+Shift+S")
        screenshot_action.setStatusTip("Take a screenshot of the application")
        screenshot_action.triggered.connect(self.on_take_screenshot)
        file_menu.addAction(screenshot_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Help Menu
        help_menu = menu_bar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.setStatusTip("Show About dialog")
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_about_dialog(self):
        """Shows the modern About dialog."""
        dialog = ModernAboutDialog(self)
        dialog.exec()

    def on_save_clean_data(self):
        if not self.worker.raw:
            QMessageBox.warning(self, "No Data", "Please load a dataset first.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Clean Data", "", "MNE FIF (*.fif)"
        )
        if filename:
            self.request_save_data.emit(filename)

    def on_take_screenshot(self):
        screen = QApplication.primaryScreen()
        if not screen:
            self.log_status("Error: No screen detected.")
            return

        screenshot = screen.grabWindow(self.winId())

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Screenshot", "neuroflow_screenshot.png",
            "PNG Files (*.png);;All Files (*)"
        )
        if filename:
            screenshot.save(filename)
            self.log_status(f"Screenshot saved to {filename}")

    def on_save_finished(self, filename):
        # Save pipeline history JSON alongside the data file
        import json
        from pathlib import Path
        
        history_saved = False
        history_path = None
        
        if self.source_filename and self.pipeline_history:
            history_filename = f"{self.source_filename}_history.json"
            history_path = Path(filename).parent / history_filename
            
            try:
                with open(history_path, 'w') as f:
                    json.dump(self.pipeline_history, f, indent=4)
                history_saved = True
            except Exception as e:
                self.log_status(f"Warning: Could not save history file: {e}")
        
        if history_saved:
            QMessageBox.information(
                self, 
                "Save Successful", 
                f"Data saved to:\n{filename}\n\nProcessing history saved to:\n{history_path}"
            )
        else:
            QMessageBox.information(self, "Save Successful", f"Data saved to:\n{filename}")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Import sidebar components
        from .sidebar import (
            SidebarTitle, SectionCard, ParamRow, ParamSpinRow,
            ActionButton, StatusLog, CollapsibleBox
        )

        # Create Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)
        main_layout.addWidget(splitter)

        # ====== SIDEBAR WIDGET ======
        sidebar_widget = QWidget()
        sidebar_widget.setMinimumWidth(250)
        sidebar_widget.setMaximumWidth(350)
        
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # App Title
        title_widget = SidebarTitle()
        sidebar_layout.addWidget(title_widget)

        # Scrollable sidebar container (replaces QToolBox)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setObjectName("sidebarScrollArea")

        # Container widget for scroll area
        scroll_content = QWidget()
        scroll_content.setObjectName("sidebarScrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(8, 8, 8, 8)
        scroll_layout.setSpacing(5)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # ====== SECTION 1: Data & Preprocessing ======
        section_data = CollapsibleBox("Data & Preprocessing", "📂", expanded=True)

        # Dataset Card
        card_dataset = SectionCard("Dataset", "💾")
        self.btn_load = ActionButton("Load EEG Data")
        self.btn_load.clicked.connect(self.browse_file)
        card_dataset.addWidget(self.btn_load)

        self.btn_sensors = ActionButton("Check Sensors")
        self.btn_sensors.setEnabled(False)
        self.btn_sensors.clicked.connect(self.check_sensors)
        card_dataset.addWidget(self.btn_sensors)

        self.btn_dataset_info = ActionButton("Dataset Info")
        self.btn_dataset_info.setEnabled(False)
        self.btn_dataset_info.clicked.connect(self.show_dataset_info)
        self.btn_dataset_info.setToolTip("View dataset metadata and event statistics")
        card_dataset.addWidget(self.btn_dataset_info)
        section_data.addWidget(card_dataset)

        # Signal Pipeline Card
        card_pipeline = SectionCard("Signal Pipeline", "⚡")

        self.param_hp = ParamRow("HP (Hz):", "1.0")
        card_pipeline.addWidget(self.param_hp)
        self.input_hp = self.param_hp.input

        self.param_lp = ParamRow("LP (Hz):", "40.0")
        card_pipeline.addWidget(self.param_lp)
        self.input_lp = self.param_lp.input

        self.param_notch = ParamRow("Notch:", "50.0")
        card_pipeline.addWidget(self.param_notch)
        self.input_notch = self.param_notch.input

        self.btn_run = ActionButton("Run Pipeline", primary=True)
        self.btn_run.clicked.connect(self.launch_pipeline)
        self.btn_run.setEnabled(False)
        card_pipeline.addWidget(self.btn_run)
        section_data.addWidget(card_pipeline)

        scroll_layout.addWidget(section_data)

        # ====== SECTION 2: Artifact Removal ======
        section_ica = CollapsibleBox("Artifact Removal", "🧹", expanded=False)

        card_ica = SectionCard("Independent Component Analysis", "🔬")

        self.btn_calc_ica = ActionButton("1. Calculate ICA")
        self.btn_calc_ica.clicked.connect(self.run_ica_click)
        self.btn_calc_ica.setEnabled(False)
        card_ica.addWidget(self.btn_calc_ica)

        exclude_label = QLabel("Exclude Components:")
        exclude_label.setStyleSheet("color: #9090a8; font-size: 12px; background: transparent;")
        card_ica.addWidget(exclude_label)

        self.input_ica_exclude = QLineEdit()
        self.input_ica_exclude.setPlaceholderText("e.g. 0, 2 (comma separated)")
        card_ica.addWidget(self.input_ica_exclude)

        self.btn_apply_ica = ActionButton("2. Apply ICA")
        self.btn_apply_ica.clicked.connect(self.apply_ica_click)
        self.btn_apply_ica.setEnabled(False)
        card_ica.addWidget(self.btn_apply_ica)

        section_ica.addWidget(card_ica)
        scroll_layout.addWidget(section_ica)

        # ====== SECTION 3: ERP Analysis ======
        section_erp = CollapsibleBox("ERP Analysis", "📊", expanded=False)

        card_erp = SectionCard("Event-Related Potentials", "📈")

        event_label = QLabel("Trigger Event:")
        event_label.setStyleSheet("color: #9090a8; font-size: 12px; background: transparent;")
        card_erp.addWidget(event_label)

        self.combo_events = QComboBox()
        card_erp.addWidget(self.combo_events)

        time_row = ParamSpinRow("Time:", -5.0, 5.0, -0.2, 0.5)
        self.spin_tmin = time_row.spin_min
        self.spin_tmax = time_row.spin_max
        card_erp.addWidget(time_row)

        self.btn_inspect_epochs = ActionButton("Inspect & Reject Epochs")
        self.btn_inspect_epochs.clicked.connect(self.inspect_epochs_click)
        self.btn_inspect_epochs.setEnabled(False)
        self.btn_inspect_epochs.setToolTip("Visually inspect epochs and manually reject artifacts")
        card_erp.addWidget(self.btn_inspect_epochs)

        self.btn_erp = ActionButton("Compute & Plot ERP", primary=True)
        self.btn_erp.clicked.connect(self.compute_erp_click)
        self.btn_erp.setEnabled(False)
        card_erp.addWidget(self.btn_erp)

        section_erp.addWidget(card_erp)
        scroll_layout.addWidget(section_erp)

        # ====== SECTION 4: Advanced Analysis ======
        section_advanced = CollapsibleBox("Advanced Analysis", "🔮", expanded=False)

        # TFR Card
        card_tfr = SectionCard("Time-Frequency (TFR)", "🌊")

        chan_label = QLabel("Channel:")
        chan_label.setStyleSheet("color: #9090a8; font-size: 12px; background: transparent;")
        card_tfr.addWidget(chan_label)

        self.combo_channels = QComboBox()
        card_tfr.addWidget(self.combo_channels)

        freq_row = ParamSpinRow("Freqs:", 0.1, 100.0, 4.0, 30.0)
        self.spin_tfr_l = freq_row.spin_min
        self.spin_tfr_h = freq_row.spin_max
        card_tfr.addWidget(freq_row)

        self.btn_tfr = ActionButton("Compute TFR", primary=True)
        self.btn_tfr.clicked.connect(self.compute_tfr_click)
        self.btn_tfr.setEnabled(False)
        card_tfr.addWidget(self.btn_tfr)
        section_advanced.addWidget(card_tfr)

        # Connectivity Card
        card_conn = SectionCard("Connectivity (wPLI)", "🔗")

        self.btn_conn = ActionButton("Alpha Band (8-12Hz)")
        self.btn_conn.clicked.connect(self.compute_connectivity_click)
        self.btn_conn.setEnabled(False)
        card_conn.addWidget(self.btn_conn)
        section_advanced.addWidget(card_conn)

        scroll_layout.addWidget(section_advanced)

        # ====== ACCORDION BEHAVIOR ======
        # Track all sections for exclusive expansion
        self.sidebar_sections = [section_data, section_ica, section_erp, section_advanced]
        for section in self.sidebar_sections:
            section.expanded.connect(self._on_section_expanded)

        # Set scroll content and add to sidebar
        scroll_area.setWidget(scroll_content)
        sidebar_layout.addWidget(scroll_area)

        # ====== STATUS LOG ======
        self.status_log = StatusLog()
        self.log_area = self.status_log.log_area
        sidebar_layout.addWidget(self.status_log)

        # Add Sidebar to Splitter
        splitter.addWidget(sidebar_widget)

        # ====== MAIN CONTENT CONTENT ======
        self.tabs = QTabWidget()

        self.tab_signal = QWidget()
        tab1_layout = QVBoxLayout(self.tab_signal)
        tab1_layout.setContentsMargins(10, 10, 0, 0)

        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        tab1_layout.addWidget(self.canvas)

        # Initial plot placeholder
        self.canvas.axes.text(
            0.5, 0.5,
            'NeuroFlow Ready\nLoad BrainVision (.vhdr) or others\nto begin analysis',
            color='#606080', ha='center', va='center', fontsize=14,
            fontweight='medium'
        )
        self.canvas.draw()

        self.tabs.addTab(self.tab_signal, "Signal Monitor")

        self.tab_advanced = QWidget()
        self.tab2_layout = QVBoxLayout(self.tab_advanced)
        self.tab2_layout.setContentsMargins(10, 10, 0, 0)

        self.canvas_advanced = MplCanvas(self, width=5, height=4, dpi=100)
        self.canvas_advanced.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tab2_layout.addWidget(self.canvas_advanced)

        self.tabs.addTab(self.tab_advanced, "Advanced Analysis")

        splitter.addWidget(self.tabs)
        
        # Splitter Stretch
        splitter.setStretchFactor(1, 4)

    # -------------------------------------------------------------------------
    # UI Interactions
    # -------------------------------------------------------------------------

    def _on_section_expanded(self, expanded_section):
        """Collapse all sections except the one being expanded (accordion behavior)."""
        for section in self.sidebar_sections:
            if section is not expanded_section:
                section.setExpanded(False)

    def log_status(self, message):
        """Appends message to the sidebar status log."""
        self.log_area.append(f">> {message}")
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )

    def show_error(self, message):
        """Displays error message box and logs it."""
        self.log_status(f"ERROR: {message}")
        QMessageBox.critical(self, "Error", message)

    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open EEG Data",
            "",
            "EEG Data (*.vhdr *.VHDR *.ahdr *.AHDR *.fif *.FIF *.edf *.EDF *.bdf *.BDF);;All Files (*)"
        )
        if file_name:
            self.log_status(f"Selected file: {file_name}")
            self.request_load_data.emit(file_name)
        else:
            self.log_status("File selection cancelled.")

    def on_data_loaded(self, raw):
        """Called when worker successfully loads data."""
        self.raw_data = raw  # Store reference
        self.btn_run.setEnabled(True)
        self.btn_sensors.setEnabled(True)
        self.btn_dataset_info.setEnabled(True)
        self.btn_calc_ica.setEnabled(True)  # Enable ICA
        self.btn_apply_ica.setEnabled(True)

        # Reset pipeline history for new dataset
        self.pipeline_history = []
        
        # Extract and store source filename
        if self.worker.raw is not None and hasattr(self.worker.raw, 'filenames'):
            from pathlib import Path
            source_path = self.worker.raw.filenames[0]
            self.source_filename = Path(source_path).stem
        else:
            self.source_filename = "unknown"
        
        # Log data loaded event
        from datetime import datetime
        self.pipeline_history.append({
            "timestamp": datetime.now().isoformat(timespec='seconds'),
            "action": "data_loaded",
            "params": {"filename": self.source_filename}
        })

        # Populate Channels for TFR
        self.combo_channels.clear()
        self.combo_channels.addItems(self.raw_data.ch_names)
        self.btn_tfr.setEnabled(True)
        self.btn_conn.setEnabled(True)

        QMessageBox.information(self, "Success", "EEG Data Loaded Successfully.")

    def check_sensors(self):
        """Visualize sensor positions."""
        if self.raw_data:
            self.log_status("Visualizing sensor positions...")
            # block=False ensures the GUI doesn't freeze
            self.raw_data.plot_sensors(show_names=True, kind='topomap', block=False)

    def show_dataset_info(self):
        """Display comprehensive dataset metadata in a dialog."""
        if self.raw_data is None:
            QMessageBox.warning(
                self,
                "No Data",
                "Please load an EEG dataset first."
            )
            return

        dialog = DatasetInfoDialog(self.raw_data, parent=self, pipeline_history=self.pipeline_history)
        dialog.exec()

    def launch_pipeline(self):
        """Reads inputs and signals worker to start processing."""
        try:
            # Inputs
            text_hp = self.input_hp.text()
            text_lp = self.input_lp.text()
            text_notch = self.input_notch.text()

            hp = float(text_hp) if text_hp else 0.0
            lp = float(text_lp) if text_lp else 0.0
            notch = float(text_notch) if text_notch else 0.0

            l_freq = hp
            h_freq = lp

            # Store pending filter params for history logging
            self._pending_filter_params = {
                "highpass": hp if hp > 0 else None,
                "lowpass": lp if lp > 0 else None,
                "notch": notch if notch > 0 else None
            }

            self.request_run_pipeline.emit(l_freq, h_freq, notch)

        except ValueError:
            self.show_error("Invalid Filter Parameters. Please enter numeric values.")

    def run_ica_click(self):
        self.request_run_ica.emit()

    def apply_ica_click(self):
        excludes = self.input_ica_exclude.text()
        
        # Store pending ICA params for history logging
        if not excludes.strip():
            self._pending_ica_excludes = []
        else:
            self._pending_ica_excludes = [
                int(x.strip()) for x in excludes.split(',') if x.strip().isdigit()
            ]
        
        self.request_apply_ica.emit(excludes)

    def populate_event_dropdown(self, event_id_dict):
        """Populates the event dropdown with unique events found in the data."""
        self.combo_events.clear()
        self.epochs = None  # Reset epochs when new data is loaded
        self.epochs_inspected = False
        if not event_id_dict:
            self.log_status("No events found for ERP analysis.")
            self.btn_erp.setEnabled(False)
            self.btn_inspect_epochs.setEnabled(False)
            return

        self.combo_events.addItems(list(event_id_dict.keys()))
        self.btn_inspect_epochs.setEnabled(True)  # Enable inspection button
        self.btn_erp.setEnabled(True)  # Allow ERP without inspection (optional workflow)
        self.log_status(f"Populated ERP dropdown with {len(event_id_dict)} events.")

    def inspect_epochs_click(self):
        """
        Gold Standard manual QC: Opens MNE's interactive epoch viewer.
        User can click epochs to mark them as 'bad'. On close, bad epochs are dropped.
        This MUST run on Main Thread since epochs.plot() creates a GUI window.
        """
        event_name = self.combo_events.currentText()
        if not event_name:
            self.show_error("Please select an event trigger first.")
            return

        # Access worker data (events and raw)
        if self.worker.raw is None:
            self.show_error("No data loaded. Please load and preprocess data first.")
            return

        if self.worker.events is None or self.worker.event_id is None:
            self.show_error("No events found in this dataset.")
            return

        if event_name not in self.worker.event_id:
            self.show_error(f"Event '{event_name}' not found in data.")
            return

        tmin = self.spin_tmin.value()
        tmax = self.spin_tmax.value()

        self.log_status(f"Creating epochs for '{event_name}' (tmin={tmin}, tmax={tmax})...")

        try:
            # Create epochs on main thread using worker's data
            specific_event_id = {event_name: self.worker.event_id[event_name]}
            self.epochs = mne.Epochs(
                self.worker.raw,
                self.worker.events,
                event_id=specific_event_id,
                tmin=tmin,
                tmax=tmax,
                baseline=(tmin, 0),
                preload=True,
                verbose=False
            )

            n_epochs_before = len(self.epochs)
            self.log_status(
                f"Created {n_epochs_before} epochs. Opening interactive viewer..."
            )
            self.log_status("Click epochs to mark as bad. Close window when done.")

            # Open the interactive epoch viewer (blocks until window closes)
            # scalings='auto' adapts to data, n_epochs=10 shows 10 at a time
            # Force light style via matplotlib to make traces visible on dark theme
            import matplotlib.pyplot as plt
            original_style = plt.rcParams.copy()
            plt.style.use('default')
            mne.viz.set_browser_backend('matplotlib')

            n_channels = min(30, len(self.epochs.ch_names))
            try:
                self.epochs.plot(
                    block=True,
                    scalings='auto',
                    n_epochs=10,
                    n_channels=n_channels,
                    title=f"Epoch Inspection: {event_name} (Click to reject)"
                )
            finally:
                # Restore original style
                plt.rcParams.update(original_style)

            # After the plot window is closed, drop the marked bad epochs
            self.epochs.drop_bad()

            n_epochs_after = len(self.epochs)
            n_rejected = n_epochs_before - n_epochs_after

            self.epochs_inspected = True
            self.log_status(
                f"Manual inspection complete. Removed {n_rejected} epochs. "
                f"Remaining: {n_epochs_after}."
            )

            # Log manual epoch rejection to pipeline history
            from datetime import datetime
            self.pipeline_history.append({
                "timestamp": datetime.now().isoformat(timespec='seconds'),
                "action": "manual_epoch_rejection",
                "params": {
                    "event": event_name,
                    "tmin": tmin,
                    "tmax": tmax,
                    "kept": n_epochs_after,
                    "rejected": n_rejected
                }
            })

            if n_epochs_after == 0:
                self.show_error("All epochs were rejected! Cannot compute ERP.")
                self.btn_erp.setEnabled(False)
            else:
                self.btn_erp.setEnabled(True)
                self.log_status("Ready to compute ERP with cleaned epochs.")

        except Exception as e:
            self.show_error(f"Epoch inspection error: {str(e)}")
            traceback.print_exc()

    def compute_erp_click(self):
        """
        Compute ERP. If epochs were manually inspected, use those.
        Otherwise, request fresh epochs from the worker.
        """
        event_name = self.combo_events.currentText()
        if not event_name:
            return
        tmin = self.spin_tmin.value()
        tmax = self.spin_tmax.value()

        # If epochs were already inspected and cleaned, compute ERP locally
        if self.epochs is not None and self.epochs_inspected:
            self.log_status(f"Computing ERP from {len(self.epochs)} inspected epochs...")
            try:
                evoked = self.epochs.average()
                self.log_status(
                    f"ERP Computed from inspected epochs. Averaged {len(self.epochs)} epochs."
                )
                self.handle_erp_ready(evoked)
            except Exception as e:
                self.show_error(f"ERP Error: {str(e)}")
                traceback.print_exc()
        else:
            # No inspection performed, use worker-based computation
            self.log_status("Computing ERP (no manual inspection performed)...")
            self.request_compute_erp.emit(event_name, tmin, tmax)

    def handle_erp_ready(self, evoked):
        """Plots the ERP using the new Interactive Viewer."""
        self.log_status("Launching Interactive ERP Viewer...")
        try:
            # We keep a reference to the window to prevent it from being garbage collected
            self.erp_viewer = ERPViewer(evoked, self)
            self.erp_viewer.show()
            self.log_status("ERP Viewer Opened.")
        except Exception as e:
            self.show_error(f"Plotting Error: {e}")

    def display_ica_components(self, ica_solution):
        """
        Slot to plot ICA components on the Main Thread.
        This fixes the 'Matplotlib GUI outside main thread' crash.
        """
        self.log_status("Opening ICA Components Window...")
        try:
            # Standard MNE Plot (creates a new Qt Window)
            ica_solution.plot_components(show=True)
        except Exception as e:
            self.show_error(f"Plotting Error: {e}")

    # -------------------------------------------------------------------------
    # Advanced Analysis Slots
    # -------------------------------------------------------------------------

    def compute_tfr_click(self):
        ch = self.combo_channels.currentText()
        if not ch:
            return
        l_freq = self.spin_tfr_l.value()
        h_freq = self.spin_tfr_h.value()
        self.request_compute_tfr.emit(ch, l_freq, h_freq)
        self.tabs.setCurrentWidget(self.tab_advanced)

    def plot_tfr(self, tfr_power):
        """Plots TFR Heatmap on the Advanced Canvas."""
        self.canvas_advanced.axes.clear()
        self.canvas_advanced.axes.set_facecolor('black')

        try:
            data = tfr_power.data[0]  # Single channel
            times = tfr_power.times
            freqs = tfr_power.freqs

            # Apply baseline correction (percent change relative to pre-stimulus)
            # Baseline is from start of epoch to time 0
            baseline_mask = times < 0
            if baseline_mask.any():
                baseline = data[:, baseline_mask].mean(axis=1, keepdims=True)
                # Percent change: (data - baseline) / baseline * 100
                data = (data - baseline) / (baseline + 1e-10) * 100

            # Spectrogram Plot with baseline-corrected data
            # Gouraud shading for smoothness
            self.canvas_advanced.axes.pcolormesh(
                times, freqs, data, shading='gouraud', cmap='viridis'
            )

            self.canvas_advanced.axes.set_title(
                f"Time-Frequency: {tfr_power.ch_names[0]}", color='white'
            )
            self.canvas_advanced.axes.set_xlabel("Time (s)", color='white')
            self.canvas_advanced.axes.set_ylabel("Frequency (Hz)", color='white')
            self.canvas_advanced.axes.tick_params(colors='white')

            self.canvas_advanced.draw()
            self.log_status("TFR Plot Updated.")

        except Exception as e:
            self.show_error(f"TFR Plot Error: {e}")

    def compute_connectivity_click(self):
        # Trigger connectivity (Alpha band 8-12Hz)
        if hasattr(self, 'btn_conn'):
            self.request_compute_connectivity.emit()
            self.tabs.setCurrentWidget(self.tab_advanced)

    def plot_connectivity(self, con):
        """
        Visualizes connectivity using mne_connectivity.viz.plot_connectivity_circle.
        Uses a Popup Dialog to display the result.
        """
        self.log_status("Connectivity Calculated. Visualizing...")

        try:
            from mne_connectivity.viz import plot_connectivity_circle
        except ImportError:
            self.show_error("mne_connectivity not found.")
            return

        try:
            # Extract data
            con_data = con.get_data(output='dense')

            # Handling dimensions
            if con_data.ndim == 3:
                con_data = con_data[:, :, 0]  # Squeeze freq dimension if 1

            node_names = self.raw_data.ch_names

            # Create Figure with show=False to prevent immediate popup
            # plot_connectivity_circle returns fig, ax
            fig, ax = plot_connectivity_circle(
                con_data, node_names, n_lines=50,
                fontsize_names=8, title='Alpha Band Connectivity (wPLI)',
                show=False
            )

            # Launch Popup Dialog
            self.connectivity_dialog = ConnectivityDialog(self)
            self.connectivity_dialog.plot(fig)
            self.connectivity_dialog.show()

            self.log_status("Connectivity Explorer Opened.")

        except Exception as e:
            self.show_error(f"Connectivity Plot Error: {e}")
            traceback.print_exc()

    def update_plot(self, freqs, psd_mean, filter_info_str):
        """Updates the Matplotlib canvas with the new PSD data."""
        self.canvas.axes.clear()

        # Log filter operation if pending (from launch_pipeline, not ICA)
        if hasattr(self, '_pending_filter_params') and self._pending_filter_params is not None:
            from datetime import datetime
            self.pipeline_history.append({
                "timestamp": datetime.now().isoformat(timespec='seconds'),
                "action": "filter",
                "params": self._pending_filter_params
            })
            self._pending_filter_params = None  # Clear pending

        # Log ICA exclusion if pending (from apply_ica_click)
        if hasattr(self, '_pending_ica_excludes') and self._pending_ica_excludes is not None:
            from datetime import datetime
            self.pipeline_history.append({
                "timestamp": datetime.now().isoformat(timespec='seconds'),
                "action": "ica_exclusion",
                "params": {"excluded_components": self._pending_ica_excludes}
            })
            self._pending_ica_excludes = None  # Clear pending

        # PSD Plot Logic
        # 10*np.log10 to convert to dB
        self.canvas.axes.plot(
            freqs, 10 * np.log10(psd_mean), color='#007acc', linewidth=1.5
        )

        title = f"Power Spectral Density (Welch)\n[{filter_info_str}]"
        self.canvas.axes.set_title(title, color='white', pad=20, fontsize=10)
        self.canvas.axes.set_xlabel("Frequency (Hz)", color='white')
        self.canvas.axes.set_ylabel("Power Spectral Density (dB)", color='white')
        self.canvas.axes.tick_params(axis='x', colors='white')
        self.canvas.axes.tick_params(axis='y', colors='white')
        self.canvas.axes.grid(True, linestyle='--', alpha=0.3)
        self.canvas.axes.set_facecolor('#1e1e1e')

        self.canvas.draw()

    def closeEvent(self, event):
        """Clean up thread on close."""
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        event.accept()
