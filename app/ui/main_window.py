"""Main Window - Primary application window for NeuroFlow."""

import traceback

import mne
import numpy as np

import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFileDialog, QFrame, QMessageBox, QProgressDialog,
    QTabWidget, QApplication, QSplitter,
    QScrollArea, QSizePolicy, QLabel, QSpinBox
)
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QMetaObject, Q_ARG

from app.core.workers import EEGWorker
from .canvas import MplCanvas
from .dialogs import DatasetInfoDialog, ConnectivityDialog, ERPViewer, ChannelManagerDialog
from .theme import ModernAboutDialog
from .sidebar import (
    SidebarTitle, SectionCard, ParamRow, ParamComboRow, ParamSpinRow,
    ActionButton, StatusLog, CollapsibleBox, EEGNavigationBar, ParamCheckRow
)


class MainWindow(QMainWindow):
    """Main application window for NeuroFlow EEG analysis."""

    request_load_data = pyqtSignal(str)
    request_run_pipeline = pyqtSignal(float, float, float)
    request_run_ica = pyqtSignal()
    request_apply_ica = pyqtSignal(str)
    request_create_epochs = pyqtSignal(str, float, float, bool)
    request_compute_erp = pyqtSignal()
    request_compute_tfr = pyqtSignal(str, float, float, int, str)
    request_compute_connectivity = pyqtSignal()
    request_save_data = pyqtSignal(str)
    request_save_epochs = pyqtSignal(str)
    request_interpolate_bads = pyqtSignal(list)
    request_generate_report = pyqtSignal(object, object, object, object, list, dict)
    request_save_session = pyqtSignal(str, dict)
    request_load_session = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NeuroFlow - Professional EEG Analysis")
        self.setWindowIcon(QIcon("assets/neuroflow_icon.png"))
        self.resize(1300, 850)
        self.raw_data = None
        self.raw_original = None  # Backup of original data for overlay comparison
        self.epochs_data = None  # Holds loaded epochs data (from -epo.fif files)
        self.epochs = None  # Holds epochs for manual inspection
        self.epochs_inspected = False  # Flag to track if epochs have been inspected

        # Pipeline history for traceability
        self.pipeline_history = []
        self.source_filename = None  # Base filename without extension
        
        # Current processing info for plot title
        self.current_filter_info = "Raw Signal"

        # Current project file path for save functionality
        self.current_project_path = None  # Path to current .nflow file

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
        self.worker.interpolation_done.connect(self.on_interpolation_done)
        self.worker.report_ready.connect(self.on_report_ready)
        self.worker.data_updated.connect(self.on_data_updated)
        self.worker.session_loaded.connect(self._restore_session_state)

        # Batch processing signals
        self.worker.batch_progress.connect(self._on_batch_progress)
        self.worker.batch_log.connect(self._on_batch_log)
        self.worker.batch_finished.connect(self._on_batch_finished)
        self.worker.batch_error.connect(self._on_batch_error)

        self.request_load_data.connect(self.worker.load_data)
        self.request_run_pipeline.connect(self.worker.run_pipeline)
        self.request_run_ica.connect(self.worker.run_ica)
        self.request_apply_ica.connect(self.worker.apply_ica)
        self.request_create_epochs.connect(self.worker.create_epochs)
        self.request_compute_erp.connect(self.worker.compute_erp)
        self.request_compute_tfr.connect(self.worker.compute_tfr)
        self.request_compute_connectivity.connect(self.worker.compute_connectivity)
        self.request_save_data.connect(self.worker.save_data)
        self.request_save_epochs.connect(self.worker.save_epochs)
        self.request_interpolate_bads.connect(self.worker.interpolate_bads)
        self.request_generate_report.connect(self.worker.generate_report)
        self.request_save_session.connect(self.worker.save_session)
        self.request_load_session.connect(self.worker.load_session)

        self.thread.start()

        self.init_ui()
        self.create_menu()

    def create_menu(self):
        """Create the menu bar."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")

        # Project Session Actions (primary save/open)
        save_project_action = QAction("💾 &Save Project", self)
        save_project_action.setShortcut("Ctrl+S")
        save_project_action.setStatusTip("Save analysis session to .nflow file")
        save_project_action.triggered.connect(self.on_save_project)
        file_menu.addAction(save_project_action)

        save_project_as_action = QAction("📁 Save Project &As...", self)
        save_project_as_action.setShortcut("Ctrl+Shift+S")
        save_project_as_action.setStatusTip("Save analysis session to a new .nflow file")
        save_project_as_action.triggered.connect(self.on_save_project_as)
        file_menu.addAction(save_project_as_action)

        open_project_action = QAction("📂 &Open Project (.nflow)", self)
        open_project_action.setShortcut("Ctrl+O")
        open_project_action.setStatusTip("Open a saved analysis session from .nflow file")
        open_project_action.triggered.connect(self.on_open_project)
        file_menu.addAction(open_project_action)

        file_menu.addSeparator()

        # Export actions
        save_action = QAction("Export &Clean Data (.fif)", self)
        save_action.setStatusTip("Export the processed data to .fif format")
        save_action.triggered.connect(self.on_save_clean_data)
        file_menu.addAction(save_action)

        save_epochs_action = QAction("Export &Epoched Data (.fif)", self)
        save_epochs_action.setShortcut("Ctrl+Shift+E")
        save_epochs_action.setStatusTip("Export the epoched data to .fif format")
        save_epochs_action.triggered.connect(self.save_epochs_click)
        file_menu.addAction(save_epochs_action)

        file_menu.addSeparator()

        screenshot_action = QAction("Scree&nshot", self)
        screenshot_action.setStatusTip("Take a screenshot of the application")
        screenshot_action.triggered.connect(self.on_take_screenshot)
        file_menu.addAction(screenshot_action)

        report_action = QAction("&Generate Analysis Report", self)
        report_action.setShortcut("Ctrl+R")
        report_action.setStatusTip("Generate an HTML report of the analysis pipeline")
        report_action.triggered.connect(self.run_report_generation)
        file_menu.addAction(report_action)

        file_menu.addSeparator()

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menu_bar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.setStatusTip("Show About dialog")
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_about_dialog(self):
        """Show the About dialog."""
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

    def save_epochs_click(self):
        """Handle Save Epoched Data menu action."""
        # Use worker.epochs as the single source of truth
        if self.worker.epochs is None:
            QMessageBox.warning(
                self, "No Epochs", "Please create epochs first before saving."
            )
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Epoched Data", "", "MNE FIF (*.fif)"
        )
        if filename:
            self.request_save_epochs.emit(filename)

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
        """Handle save completion and save pipeline history."""
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

    def on_save_project(self):
        """Handle Save Project menu action - save to current file or prompt for new."""
        if self.worker.raw is None and self.worker.epochs is None:
            QMessageBox.warning(self, "No Data", "Please load a dataset first before saving a project.")
            return

        # If we have a current project path, save directly to it
        if self.current_project_path:
            state_payload = self._collect_session_state()
            self.request_save_session.emit(self.current_project_path, state_payload)
        else:
            # No current project, use Save As behavior
            self.on_save_project_as()

    def on_save_project_as(self):
        """Handle Save Project As menu action - always prompt for new file."""
        if self.worker.raw is None and self.worker.epochs is None:
            QMessageBox.warning(self, "No Data", "Please load a dataset first before saving a project.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            f"{self.source_filename or 'project'}.nflow",
            "NeuroFlow Project (*.nflow)"
        )

        if file_path:
            # Update the current project path
            self.current_project_path = file_path
            state_payload = self._collect_session_state()
            self.request_save_session.emit(file_path, state_payload)

    def on_open_project(self):
        """Handle Open Project menu action - load session from .nflow file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "NeuroFlow Project (*.nflow)"
        )

        if file_path:
            # Security warning before loading untrusted session files
            reply = QMessageBox.warning(
                self,
                "Security Warning",
                "Loading project files executes code. Only load files from trusted sources.\n\nDo you want to continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                return
            
            # Store the project path for future saves
            self.current_project_path = file_path
            self.request_load_session.emit(file_path)

    def _collect_session_state(self) -> dict:
        """Collect all application state for session persistence.

        Returns:
            Dictionary containing all state needed to restore the session.
        """
        # Gather UI state from input widgets
        ui_params = {
            'hp': self.input_hp.text(),
            'lp': self.input_lp.text(),
            'notch': self.input_notch.text(),
            'ica_exclude': self.input_ica_exclude.text(),
            'event_selected': self.combo_events.currentText(),
            'event_index': self.combo_events.currentIndex(),
            'tmin': self.spin_tmin.value(),
            'tmax': self.spin_tmax.value(),
            'baseline_checked': self.chk_erp_baseline.isChecked(),
            'tfr_channel': self.combo_channels.currentText(),
            'tfr_channel_index': self.combo_channels.currentIndex(),
            'tfr_freq_low': self.spin_tfr_l.value(),
            'tfr_freq_high': self.spin_tfr_h.value(),
            'tfr_cycles': self.spin_tfr_cycles.value(),
            'tfr_baseline_mode': self.combo_tfr_baseline.currentText(),
            'tfr_baseline_index': self.combo_tfr_baseline.currentIndex(),
        }

        # Build the complete state payload
        state_payload = {
            # Backend MNE objects
            'raw': self.worker.raw,
            'raw_original': self.worker.raw_original,
            'ica': self.worker.ica,
            'epochs': self.worker.epochs,  # Created epochs (single source of truth)
            'epochs_data': self.epochs_data,  # Loaded epoch files (-epo.fif)
            'events': self.worker.events,
            'event_id': self.worker.event_id,
            # Metadata
            'pipeline_history': self.pipeline_history,
            'source_filename': self.source_filename,
            'current_filter_info': self.current_filter_info,
            'epochs_inspected': self.epochs_inspected,
            # UI state
            'ui_params': ui_params,
            # Event dropdown items for restoration
            'event_items': [self.combo_events.itemText(i) for i in range(self.combo_events.count())],
            # Channel dropdown items for restoration
            'channel_items': [self.combo_channels.itemText(i) for i in range(self.combo_channels.count())],
        }

        return state_payload

    def _restore_session_state(self, state: dict):
        """Restore application state from a loaded session.

        Args:
            state: Dictionary containing the saved session state.
        """
        # Store pipeline history BEFORE calling on_data_loaded (which resets it)
        saved_pipeline_history = state.get('pipeline_history', [])
        saved_source_filename = state.get('source_filename')
        saved_filter_info = state.get('current_filter_info', 'Raw Signal')
        saved_epochs_inspected = state.get('epochs_inspected', False)

        # Restore UI state first (before on_data_loaded overwrites dropdowns)
        ui_params = state.get('ui_params', {})

        # Restore filter parameters
        if 'hp' in ui_params:
            self.input_hp.setText(ui_params['hp'])
        if 'lp' in ui_params:
            self.input_lp.setText(ui_params['lp'])
        if 'notch' in ui_params:
            self.input_notch.setText(ui_params['notch'])
        if 'ica_exclude' in ui_params:
            self.input_ica_exclude.setText(ui_params['ica_exclude'])

        # Restore epoch parameters
        if 'tmin' in ui_params:
            self.spin_tmin.setValue(ui_params['tmin'])
        if 'tmax' in ui_params:
            self.spin_tmax.setValue(ui_params['tmax'])
        if 'baseline_checked' in ui_params:
            self.chk_erp_baseline.setChecked(ui_params['baseline_checked'])

        # Restore TFR parameters
        if 'tfr_freq_low' in ui_params:
            self.spin_tfr_l.setValue(ui_params['tfr_freq_low'])
        if 'tfr_freq_high' in ui_params:
            self.spin_tfr_h.setValue(ui_params['tfr_freq_high'])
        if 'tfr_cycles' in ui_params:
            self.spin_tfr_cycles.setValue(ui_params['tfr_cycles'])

        # Determine what data we have
        raw_data = state.get('raw')
        epochs_data = state.get('epochs')
        
        # Restore local references
        self.raw_data = raw_data
        self.raw_original = state.get('raw_original')
        
        # Sync epochs: set both self.epochs and epochs_data for consistency
        self.epochs = epochs_data
        self.epochs_data = state.get('epochs_data')  # For loaded -epo.fif files

        # Call on_data_loaded WITHOUT showing message box (we'll show our own)
        # We need to manually do what on_data_loaded does but skip the message
        if raw_data is not None:
            self._restore_ui_for_data(raw_data, is_epochs=False)
        elif epochs_data is not None:
            self._restore_ui_for_data(epochs_data, is_epochs=True)
        elif self.epochs_data is not None:
            self._restore_ui_for_data(self.epochs_data, is_epochs=True)

        # Restore dropdowns AFTER _restore_ui_for_data (which clears them)
        event_items = state.get('event_items', [])
        self.combo_events.clear()
        self.combo_events.addItems(event_items)
        if 'event_index' in ui_params and ui_params['event_index'] >= 0:
            self.combo_events.setCurrentIndex(ui_params['event_index'])

        channel_items = state.get('channel_items', [])
        self.combo_channels.clear()
        self.combo_channels.addItems(channel_items)
        if 'tfr_channel_index' in ui_params and ui_params['tfr_channel_index'] >= 0:
            self.combo_channels.setCurrentIndex(ui_params['tfr_channel_index'])

        # Restore TFR baseline mode
        if 'tfr_baseline_index' in ui_params:
            self.combo_tfr_baseline.setCurrentIndex(ui_params['tfr_baseline_index'])

        # RESTORE saved state that on_data_loaded would have overwritten
        self.pipeline_history = saved_pipeline_history
        self.source_filename = saved_source_filename
        self.current_filter_info = saved_filter_info
        self.epochs_inspected = saved_epochs_inspected

        # Enable epoch-related buttons if epochs exist
        if self.worker.epochs is not None:
            self.btn_inspect_epochs.setEnabled(True)
            self.btn_erp.setEnabled(True)
            self.btn_create_epochs.setEnabled(True)

        # Update plot
        self.update_time_series_plot()

        # Show single success message
        from pathlib import Path
        project_name = Path(self.current_project_path).stem if self.current_project_path else saved_source_filename
        QMessageBox.information(
            self,
            "Project Loaded",
            f"Project '{project_name or 'Unknown'}' loaded successfully.\n"
            f"Pipeline history: {len(self.pipeline_history)} steps restored."
        )

    def _restore_ui_for_data(self, data, is_epochs: bool):
        """Restore UI state for loaded data without showing message boxes.
        
        This is a helper for _restore_session_state that does what on_data_loaded
        does but without resetting pipeline_history or showing dialogs.
        
        Args:
            data: The MNE Raw or Epochs object.
            is_epochs: True if data is Epochs, False if Raw.
        """
        if is_epochs:
            self.epochs_data = data
            self.raw_data = None
            self.raw_original = None
        else:
            self.raw_data = data
            self.raw_original = self.worker.raw_original
            self.epochs_data = None

        # Enable buttons based on data type
        self.btn_run.setEnabled(True)
        self.btn_sensors.setEnabled(True)
        self.btn_dataset_info.setEnabled(True)
        self.btn_calc_ica.setEnabled(not is_epochs)
        self.btn_apply_ica.setEnabled(not is_epochs)
        self.btn_channel_manager.setEnabled(True)
        self.btn_tfr.setEnabled(True)
        self.btn_conn.setEnabled(True)

        # Initialize navigation controls
        if is_epochs:
            self.total_duration = data.times[-1] - data.times[0]
        else:
            self.total_duration = data.times[-1]
        self.current_start_time = 0.0

        if hasattr(self, 'nav_bar'):
            self.nav_bar.set_duration_range(self.total_duration)

    def init_ui(self) -> None:
        """Initialize the user interface by delegating to helper methods."""
        self._setup_central_widget()
        self._setup_sidebar()
        self._setup_content_area()
        self._connect_sidebar_signals()


    def _setup_central_widget(self) -> None:
        """Set up the central widget with main layout and splitter."""
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)
        self._main_layout = QHBoxLayout(self._central_widget)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # Create Splitter
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setHandleWidth(0)
        self._splitter.setChildrenCollapsible(False)
        self._main_layout.addWidget(self._splitter)

    def _setup_sidebar(self) -> None:
        """Set up the sidebar with all sections: Data, ICA, Epochs, ERP, Advanced, Batch."""
        # Sidebar container
        sidebar_widget = QWidget()
        sidebar_widget.setFixedWidth(330)
        
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # App Title
        title_widget = SidebarTitle()
        sidebar_layout.addWidget(title_widget)

        # Scrollable sidebar container
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setObjectName("sidebarScrollArea")

        # Container widget for scroll area
        scroll_content = QWidget()
        scroll_content.setObjectName("sidebarScrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(4, 4, 4, 4)
        scroll_layout.setSpacing(5)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Create sidebar sections
        self._create_data_section(scroll_layout)
        self._create_ica_section(scroll_layout)
        self._create_epochs_section(scroll_layout)
        self._create_erp_section(scroll_layout)
        self._create_advanced_section(scroll_layout)
        self._create_batch_section(scroll_layout)

        # Set scroll content and add to sidebar
        scroll_area.setWidget(scroll_content)
        sidebar_layout.addWidget(scroll_area)

        # Status Log
        self.status_log = StatusLog()
        self.log_area = self.status_log.log_area
        sidebar_layout.addWidget(self.status_log)

        # Add Sidebar to Splitter
        self._splitter.addWidget(sidebar_widget)

    def _create_data_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the Data & Preprocessing section."""
        section_data = CollapsibleBox("Data & Preprocessing", "📂", expanded=False)

        # Dataset Card
        card_dataset = SectionCard("Dataset", "💾")
        self.btn_load = ActionButton("Load EEG Data")
        card_dataset.addWidget(self.btn_load)

        self.btn_sensors = ActionButton("Check Sensors")
        self.btn_sensors.setEnabled(False)
        card_dataset.addWidget(self.btn_sensors)

        self.btn_dataset_info = ActionButton("Dataset Info")
        self.btn_dataset_info.setEnabled(False)
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
        self.btn_run.setEnabled(False)
        card_pipeline.addWidget(self.btn_run)
        section_data.addWidget(card_pipeline)

        # Channel Manager Card
        card_channels = SectionCard("Channel Manager", "🔧")

        self.btn_channel_manager = ActionButton("Manage & Repair Channels")
        self.btn_channel_manager.setEnabled(False)
        self.btn_channel_manager.setToolTip("Mark bad channels and interpolate using spherical spline")
        card_channels.addWidget(self.btn_channel_manager)
        section_data.addWidget(card_channels)

        parent_layout.addWidget(section_data)
        self._section_data = section_data

    def _create_ica_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the Artifact Removal (ICA) section."""
        section_ica = CollapsibleBox("Artifact Removal", "🧹", expanded=False)

        card_ica = SectionCard("Independent Component Analysis", "🔬")

        self.btn_calc_ica = ActionButton("1. Calculate ICA")
        self.btn_calc_ica.setEnabled(False)
        card_ica.addWidget(self.btn_calc_ica)

        self.param_ica_exclude = ParamRow("Exclude:", "", "e.g. 0, 2 (comma separated)")
        self.input_ica_exclude = self.param_ica_exclude.input
        card_ica.addWidget(self.param_ica_exclude)

        self.btn_apply_ica = ActionButton("2. Apply ICA")
        self.btn_apply_ica.setEnabled(False)
        card_ica.addWidget(self.btn_apply_ica)

        section_ica.addWidget(card_ica)
        parent_layout.addWidget(section_ica)
        self._section_ica = section_ica

    def _create_epochs_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the Segmentation (Epoching) section."""
        section_epochs = CollapsibleBox("Segmentation (Epoching)", "✂️", expanded=False)

        card_epochs = SectionCard("Epoch Creation", "📐")

        self.param_events = ParamComboRow("Trigger Event:")
        self.combo_events = self.param_events.combo
        card_epochs.addWidget(self.param_events)

        time_row = ParamSpinRow("Time Window:", -5.0, 5.0, -0.2, 0.5)
        self.spin_tmin = time_row.spin_min
        self.spin_tmax = time_row.spin_max
        card_epochs.addWidget(time_row)

        # Baseline correction checkbox
        self.chk_erp_baseline = ParamCheckRow("Apply Baseline Correction (tmin to 0)", checked=True)
        self.chk_erp_baseline.setToolTip("Subtract mean of baseline period (tmin to 0) from each epoch")
        card_epochs.addWidget(self.chk_erp_baseline)

        self.btn_create_epochs = ActionButton("✂️ Create Epochs", primary=True)
        self.btn_create_epochs.setEnabled(False)
        self.btn_create_epochs.setToolTip("Create epochs from continuous data using selected event trigger")
        card_epochs.addWidget(self.btn_create_epochs)

        self.btn_inspect_epochs = ActionButton("🔍 Inspect & Reject Epochs")
        self.btn_inspect_epochs.setEnabled(False)
        self.btn_inspect_epochs.setToolTip("Visually inspect epochs and manually reject artifacts")
        card_epochs.addWidget(self.btn_inspect_epochs)

        section_epochs.addWidget(card_epochs)
        parent_layout.addWidget(section_epochs)
        self._section_epochs = section_epochs

    def _create_erp_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the ERP Analysis section."""
        section_erp = CollapsibleBox("ERP Analysis", "📊", expanded=False)

        card_erp = SectionCard("Event-Related Potentials", "📈")

        self.btn_erp = ActionButton("Compute & Plot ERP", primary=True)
        self.btn_erp.setEnabled(False)
        self.btn_erp.setToolTip("Compute ERP by averaging epochs (create epochs first)")
        card_erp.addWidget(self.btn_erp)

        section_erp.addWidget(card_erp)
        parent_layout.addWidget(section_erp)
        self._section_erp = section_erp

    def _create_advanced_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the Advanced Analysis section."""
        section_advanced = CollapsibleBox("Advanced Analysis", "🔮", expanded=False)

        # TFR Card
        card_tfr = SectionCard("Time-Frequency (TFR)", "🌊")

        self.param_channels = ParamComboRow("Channel:")
        self.combo_channels = self.param_channels.combo
        card_tfr.addWidget(self.param_channels)

        freq_row = ParamSpinRow("Freqs:", 0.1, 100.0, 4.0, 30.0)
        self.spin_tfr_l = freq_row.spin_min
        self.spin_tfr_h = freq_row.spin_max
        card_tfr.addWidget(freq_row)

        # TFR n_cycles parameter (frequency divisor)
        tfr_cycles_row = QWidget()
        tfr_cycles_layout = QHBoxLayout(tfr_cycles_row)
        tfr_cycles_layout.setContentsMargins(0, 0, 0, 0)
        tfr_cycles_layout.setSpacing(8)
        tfr_cycles_label = QLabel("Cycles:")
        tfr_cycles_label.setFixedWidth(55)
        tfr_cycles_label.setStyleSheet("color: #9498a8; font-size: 12px;")
        tfr_cycles_layout.addWidget(tfr_cycles_label)
        self.spin_tfr_cycles = QSpinBox()
        self.spin_tfr_cycles.setRange(1, 10)
        self.spin_tfr_cycles.setValue(2)
        self.spin_tfr_cycles.setToolTip("n_cycles = freqs / this value. Higher = better temporal resolution")
        self.spin_tfr_cycles.setStyleSheet("""
            QSpinBox {
                background: #0a0c14;
                color: #e8eaf0;
                border: 1px solid #1e2233;
                border-radius: 6px;
                padding: 5px 8px;
                font-size: 12px;
            }
            QSpinBox:focus { border-color: #00b4d8; }
        """)
        tfr_cycles_layout.addWidget(self.spin_tfr_cycles)
        card_tfr.addWidget(tfr_cycles_row)

        # TFR baseline mode combobox
        self.param_tfr_baseline = ParamComboRow("Baseline:")
        self.combo_tfr_baseline = self.param_tfr_baseline.combo
        self.combo_tfr_baseline.addItems(['percent', 'logratio', 'zscore', 'mean', 'none'])
        self.combo_tfr_baseline.setToolTip("Baseline correction mode for TFR power normalization")
        card_tfr.addWidget(self.param_tfr_baseline)

        self.btn_tfr = ActionButton("Compute TFR", primary=True)
        self.btn_tfr.setEnabled(False)
        card_tfr.addWidget(self.btn_tfr)
        section_advanced.addWidget(card_tfr)

        # Connectivity Card
        card_conn = SectionCard("Connectivity (wPLI)", "🔗")

        self.btn_conn = ActionButton("Alpha Band (8-12Hz)")
        self.btn_conn.setEnabled(False)
        card_conn.addWidget(self.btn_conn)
        section_advanced.addWidget(card_conn)

        parent_layout.addWidget(section_advanced)
        self._section_advanced = section_advanced


    def _create_batch_section(self, parent_layout: QVBoxLayout) -> None:
        """Create the Batch Processing section."""
        section_batch = CollapsibleBox("Batch Processing", "⚡", expanded=False)

        # Batch Folders Card
        card_folders = SectionCard("Folders", "📁")

        # Input folder selection
        self.batch_input_folder = ""
        self.btn_batch_input = ActionButton("Select Input Folder")
        self.btn_batch_input.setToolTip("Select folder containing EEG files (.vhdr, .fif, .edf)")
        card_folders.addWidget(self.btn_batch_input)

        self.lbl_batch_input = QLabel("No folder selected")
        self.lbl_batch_input.setStyleSheet("""
            QLabel {
                color: #5c6070;
                font-size: 10px;
                font-style: italic;
                padding: 2px 4px;
            }
        """)
        self.lbl_batch_input.setWordWrap(True)
        card_folders.addWidget(self.lbl_batch_input)

        # Output folder selection
        self.batch_output_folder = ""
        self.btn_batch_output = ActionButton("Select Output Folder")
        self.btn_batch_output.setToolTip("Select folder for saving processed files and reports")
        card_folders.addWidget(self.btn_batch_output)

        self.lbl_batch_output = QLabel("No folder selected")
        self.lbl_batch_output.setStyleSheet("""
            QLabel {
                color: #5c6070;
                font-size: 10px;
                font-style: italic;
                padding: 2px 4px;
            }
        """)
        self.lbl_batch_output.setWordWrap(True)
        card_folders.addWidget(self.lbl_batch_output)

        section_batch.addWidget(card_folders)

        # Batch Options Card
        card_options = SectionCard("Pipeline Options", "⚙️")

        self.chk_batch_filter = ParamCheckRow("Enable Filtering", checked=True)
        card_options.addWidget(self.chk_batch_filter)

        self.chk_batch_ica = ParamCheckRow("Enable Auto-ICA (Remove Blinks)", checked=True)
        card_options.addWidget(self.chk_batch_ica)

        self.chk_batch_epoch = ParamCheckRow("Enable Epoching", checked=True)
        card_options.addWidget(self.chk_batch_epoch)

        self.chk_batch_report = ParamCheckRow("Generate Reports", checked=True)
        card_options.addWidget(self.chk_batch_report)

        section_batch.addWidget(card_options)

        # Start Button Card
        card_start = SectionCard()
        self.btn_start_batch = ActionButton("🚀 Start Batch Processing", primary=True)
        self.btn_start_batch.setEnabled(False)
        self.btn_start_batch.setToolTip("Process all EEG files in the input folder")
        card_start.addWidget(self.btn_start_batch)

        section_batch.addWidget(card_start)

        parent_layout.addWidget(section_batch)
        self._section_batch = section_batch

    def _setup_content_area(self) -> None:
        """Set up the main content area with tabs, navigation bar, and canvas."""
        # Main Content
        self.tabs = QTabWidget()

        self.tab_signal = QWidget()
        tab1_layout = QVBoxLayout(self.tab_signal)
        tab1_layout.setContentsMargins(12, 12, 12, 12)
        tab1_layout.setSpacing(10)

        # EEG Navigation Bar (Clinical Controls)
        self.nav_bar = EEGNavigationBar()
        tab1_layout.addWidget(self.nav_bar)

        # Canvas for plotting
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

        self._splitter.addWidget(self.tabs)
        
        # Splitter Stretch
        self._splitter.setStretchFactor(1, 4)
        
        # Initialize navigation state
        self.current_start_time = 0.0
        self.total_duration = 0.0

    def _connect_sidebar_signals(self) -> None:
        """Connect all sidebar widget signals to their respective slots."""
        # Accordion behavior for sections
        self.sidebar_sections = [
            self._section_data, self._section_ica, self._section_epochs,
            self._section_erp, self._section_advanced, self._section_batch
        ]
        for section in self.sidebar_sections:
            section.expanded.connect(self._on_section_expanded)

        # Data & Preprocessing signals
        self.btn_load.clicked.connect(self.browse_file)
        self.btn_sensors.clicked.connect(self.check_sensors)
        self.btn_dataset_info.clicked.connect(self.show_dataset_info)
        self.btn_run.clicked.connect(self.launch_pipeline)
        self.btn_channel_manager.clicked.connect(self.open_channel_manager)

        # ICA signals
        self.btn_calc_ica.clicked.connect(self.run_ica_click)
        self.btn_apply_ica.clicked.connect(self.apply_ica_click)

        # Epochs signals
        self.btn_create_epochs.clicked.connect(self.create_epochs_click)
        self.btn_inspect_epochs.clicked.connect(self.inspect_epochs_click)

        # ERP signals
        self.btn_erp.clicked.connect(self.compute_erp_click)

        # Advanced analysis signals
        self.btn_tfr.clicked.connect(self.compute_tfr_click)
        self.btn_conn.clicked.connect(self.compute_connectivity_click)

        # Navigation bar signals
        self.nav_bar.time_changed.connect(self._on_nav_time_changed)
        self.nav_bar.duration_changed.connect(self._on_nav_duration_changed)
        self.nav_bar.scale_changed.connect(self._on_nav_scale_changed)
        self.nav_bar.overlay_toggled.connect(self._on_nav_overlay_toggled)

        # Batch processing signals
        self.btn_batch_input.clicked.connect(self._on_select_batch_input)
        self.btn_batch_output.clicked.connect(self._on_select_batch_output)
        self.btn_start_batch.clicked.connect(self._on_start_batch_click)

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

    def on_data_loaded(self, data):
        """Called when worker successfully loads data."""
        from mne import BaseEpochs
        
        # Determine if we loaded epochs or raw data
        is_epochs = isinstance(data, BaseEpochs)
        
        if is_epochs:
            self.epochs_data = data
            self.raw_data = None
            self.raw_original = None
            # Also set worker.epochs so analysis functions can use it
            self.worker.epochs = data
            # Enable epoch-related buttons immediately for loaded epochs
            self.btn_inspect_epochs.setEnabled(True)
            self.btn_erp.setEnabled(True)
            self.btn_create_epochs.setEnabled(True)  # Can still "use" epochs
        else:
            self.raw_data = data  # Store reference
            self.raw_original = self.worker.raw_original  # Store original for overlay comparison
            self.epochs_data = None
            
        self.btn_run.setEnabled(True)
        self.btn_sensors.setEnabled(True)
        self.btn_dataset_info.setEnabled(True)
        self.btn_calc_ica.setEnabled(not is_epochs)  # ICA typically on raw data
        self.btn_apply_ica.setEnabled(not is_epochs)
        self.btn_channel_manager.setEnabled(True)  # Enable Channel Manager

        # Reset pipeline history for new dataset
        self.pipeline_history = []
        self.current_filter_info = "Epoched Data" if is_epochs else "Raw Signal"
        
        # Extract and store source filename
        if is_epochs:
            if hasattr(data, 'filename') and data.filename:
                from pathlib import Path
                self.source_filename = Path(data.filename).stem
            else:
                self.source_filename = "unknown_epochs"
        elif self.worker.raw is not None and hasattr(self.worker.raw, 'filenames'):
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
            "params": {"filename": self.source_filename, "type": "epochs" if is_epochs else "raw"}
        })

        # Populate Channels for TFR
        self.combo_channels.clear()
        self.combo_channels.addItems(data.ch_names)
        self.btn_tfr.setEnabled(True)
        self.btn_conn.setEnabled(True)

        # Initialize navigation controls for the loaded data
        if is_epochs:
            # For epochs, total duration = n_epochs * single_epoch_duration
            epoch_duration = data.times[-1] - data.times[0]
            n_epochs = len(data)
            self.total_duration = n_epochs * epoch_duration
        else:
            self.total_duration = data.times[-1]
        self.current_start_time = 0.0
        
        # Update nav bar with recording duration
        if hasattr(self, 'nav_bar'):
            self.nav_bar.set_duration_range(self.total_duration)

        # Display initial time-series plot
        self.update_time_series_plot()

        data_type = "Epoched" if is_epochs else "Raw"
        QMessageBox.information(self, "Success", f"{data_type} EEG Data Loaded Successfully.")

    def check_sensors(self):
        """Visualize sensor positions."""
        data = self.raw_data or self.epochs_data
        if data:
            self.log_status("Visualizing sensor positions...")
            # block=False ensures the GUI doesn't freeze
            data.plot_sensors(show_names=True, kind='topomap', block=False)

    def show_dataset_info(self):
        """Display comprehensive dataset metadata in a dialog."""
        data = self.raw_data or self.epochs_data
        if data is None:
            QMessageBox.warning(
                self,
                "No Data",
                "Please load an EEG dataset first."
            )
            return

        dialog = DatasetInfoDialog(data, parent=self, pipeline_history=self.pipeline_history)
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
            self.btn_create_epochs.setEnabled(False)
            return

        event_names = list(event_id_dict.keys())

        # Populate ERP dropdown with "All Events" option first
        self.combo_events.addItem("All Events")
        self.combo_events.addItems(event_names)
        self.btn_create_epochs.setEnabled(True)
        self.btn_inspect_epochs.setEnabled(False)  # Enabled after epochs are created
        self.btn_erp.setEnabled(False)  # Enabled after epochs are created

        self.log_status(f"Populated event dropdown with {len(event_id_dict)} events.")

    def create_epochs_click(self):
        """Create epochs from continuous data using selected event trigger.
        
        If epoched data is already loaded (from -epo.fif file), use that directly
        instead of trying to create new epochs from raw data.
        """
        # Check if we already have loaded epochs (from -epo.fif file)
        if self.epochs_data is not None or self.worker.epochs is not None:
            # Epochs already exist - use them directly
            if self.worker.epochs is None and self.epochs_data is not None:
                # Transfer loaded epochs to worker
                self.worker.epochs = self.epochs_data
            
            self.log_status("Using pre-loaded epochs from file.")
            self.btn_inspect_epochs.setEnabled(True)
            self.btn_erp.setEnabled(True)
            self.btn_tfr.setEnabled(True)
            self.btn_conn.setEnabled(True)
            self.epochs_inspected = False
            QMessageBox.information(
                self, "Epochs Ready", 
                f"Using {len(self.worker.epochs)} pre-loaded epochs.\n"
                "You can now inspect epochs or compute ERP/TFR."
            )
            return

        # No pre-loaded epochs - need to create from raw data
        if self.worker.raw is None:
            self.show_error("No raw data loaded. Cannot create epochs.\n\n"
                          "If you loaded an epoched file, epochs are already available.\n"
                          "Use 'Inspect Epochs' or 'Compute ERP' directly.")
            return

        event_name = self.combo_events.currentText()
        if not event_name:
            self.show_error("Please select an event trigger first.")
            return

        tmin = self.spin_tmin.value()
        tmax = self.spin_tmax.value()
        apply_baseline = self.chk_erp_baseline.isChecked()

        self.log_status(f"Creating epochs for event: {event_name}...")
        self.request_create_epochs.emit(event_name, tmin, tmax, apply_baseline)

        # Enable inspection and analysis buttons after epochs are created
        self.btn_inspect_epochs.setEnabled(True)
        self.btn_erp.setEnabled(True)
        self.btn_tfr.setEnabled(True)
        self.btn_conn.setEnabled(True)
        self.epochs_inspected = False

    def inspect_epochs_click(self):
        """
        Gold Standard manual QC: Opens MNE's interactive epoch viewer.
        User can click epochs to mark them as 'bad'. On close, bad epochs are dropped.
        This MUST run on Main Thread since epochs.plot() creates a GUI window.
        """
        # Check if epochs have been created
        if self.worker.epochs is None:
            self.show_error("No epochs available. Please create epochs first.")
            return

        self.log_status("Opening interactive epoch viewer...")

        try:
            # Copy epochs from worker to main window for inspection
            self.epochs = self.worker.epochs.copy()

            n_epochs_before = len(self.epochs)
            self.log_status(
                f"Loaded {n_epochs_before} epochs. Opening interactive viewer..."
            )
            self.log_status("Click epochs to mark as bad. Close window when done.")

            # Open the interactive epoch viewer
            # Force light style via matplotlib to make traces visible on dark theme
            import matplotlib.pyplot as plt
            original_style = plt.rcParams.copy()
            plt.style.use('default')
            mne.viz.set_browser_backend('matplotlib')

            n_channels = min(30, len(self.epochs.ch_names))

            # Use block=False to avoid event loop conflict with PyQt
            # Then wait for the figure to close using PyQt's event processing
            fig = self.epochs.plot(
                block=False,
                show=True,
                scalings='auto',
                n_epochs=10,
                n_channels=n_channels,
                title=f"Epoch Inspection (Click to reject)"
            )

            # Store reference and connect to close event
            self._epoch_fig = fig
            self._n_epochs_before = n_epochs_before
            self._original_style = original_style

            # Connect to the figure's close event
            fig.canvas.mpl_connect('close_event', self._on_epoch_fig_closed)

            self.log_status("Epoch viewer opened. Click epochs to reject, then close the window.")

        except Exception as e:
            self.show_error(f"Epoch inspection error: {str(e)}")
            traceback.print_exc()

    def _on_epoch_fig_closed(self, event):
        """Handle epoch figure close event - sync and drop bad epochs."""
        import matplotlib.pyplot as plt

        try:
            fig = self._epoch_fig
            n_epochs_before = self._n_epochs_before

            # Get bad epochs from figure before closing
            if hasattr(fig, 'mne') and hasattr(fig.mne, 'bad_epochs'):
                bad_epochs = list(fig.mne.bad_epochs)
                if bad_epochs:
                    self.log_status(f"Marked epochs for rejection: {bad_epochs}")

            # Close figure to trigger MNE's internal sync
            plt.close(fig)

            # Restore original style
            plt.rcParams.update(self._original_style)

            # Drop the marked bad epochs
            self.epochs.drop_bad()

            n_epochs_after = len(self.epochs)
            n_rejected = n_epochs_before - n_epochs_after

            # Update worker's epochs with the inspected/cleaned epochs
            self.worker.epochs = self.epochs

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

            # Clean up references
            self._epoch_fig = None
            self._n_epochs_before = None
            self._original_style = None

        except Exception as e:
            self.log_status(f"Error processing epoch rejections: {str(e)}")
            traceback.print_exc()

    def compute_erp_click(self):
        """
        Compute ERP using pre-existing epochs from the worker.
        """
        # Check if epochs exist
        if self.worker.epochs is None:
            self.show_error("No epochs available. Please create epochs first using the Segmentation section.")
            return

        self.log_status("Computing ERP...")
        self.request_compute_erp.emit()

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

    def compute_tfr_click(self):
        # Check if epochs exist
        if self.worker.epochs is None:
            self.show_error("No epochs available. Please create epochs first using the Segmentation section.")
            return

        ch = self.combo_channels.currentText()
        if not ch:
            self.show_error("Please select a channel for TFR analysis.")
            return
        l_freq = self.spin_tfr_l.value()
        h_freq = self.spin_tfr_h.value()
        n_cycles_base = self.spin_tfr_cycles.value()
        baseline_mode = self.combo_tfr_baseline.currentText()
        self.request_compute_tfr.emit(ch, l_freq, h_freq, n_cycles_base, baseline_mode)
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
        # Check if epochs exist
        if self.worker.epochs is None:
            self.show_error("No epochs available. Please create epochs first using the Segmentation section.")
            return

        # Trigger connectivity (Alpha band 8-12Hz)
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

            data = self.raw_data or self.epochs_data
            node_names = data.ch_names

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
        """Updates the Matplotlib canvas with the new PSD data.

        PSD is displayed in linear power (μV²/Hz) for better scientific interpretation.
        MNE returns V²/Hz, so we multiply by 1e12 to convert to μV²/Hz.
        """
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

        # PSD Plot Logic - Linear Power in μV²/Hz
        # MNE returns V²/Hz, multiply by 1e12 to convert to μV²/Hz
        psd_uv2 = psd_mean * 1e12
        self.canvas.axes.plot(
            freqs, psd_uv2, color='#007acc', linewidth=1.5
        )

        title = f"Power Spectral Density (Welch)\n[{filter_info_str}]"
        self.canvas.axes.set_title(title, color='white', pad=20, fontsize=10)
        self.canvas.axes.set_xlabel("Frequency (Hz)", color='white')
        self.canvas.axes.set_ylabel("Power (μV²/Hz)", color='white')
        self.canvas.axes.tick_params(axis='x', colors='white')
        self.canvas.axes.tick_params(axis='y', colors='white')
        self.canvas.axes.grid(True, linestyle='--', alpha=0.3)
        self.canvas.axes.set_facecolor('#1e1e1e')

        self.canvas.draw()

    def update_time_series_plot(self, _state=None):
        """Update the Signal Monitor with clinical stacked time-series plot.
        
        Args:
            _state: Optional state value from checkbox/slider signals (ignored).
        """
        from mne import BaseEpochs
        import numpy as np
        
        data = self.raw_data or getattr(self, 'epochs_data', None)
        if data is None:
            return
        
        # Handle epochs data: flatten 3D (n_epochs, n_channels, n_times) to 2D for visualization
        plot_data = data
        if isinstance(data, BaseEpochs):
            import mne
            # Get 3D array: (n_epochs, n_channels, n_times)
            epochs_array = data.get_data()
            # Transpose to (n_channels, n_epochs, n_times) then reshape to (n_channels, n_total_samples)
            n_epochs, n_channels, n_times = epochs_array.shape
            # Concatenate epochs along time axis: result is (n_channels, n_epochs * n_times)
            flattened = epochs_array.transpose(1, 0, 2).reshape(n_channels, -1)
            # Create temporary RawArray for plotting
            info = data.info.copy()
            plot_data = mne.io.RawArray(flattened, info, verbose=False)
        
        # Determine if overlay is requested (only for raw data)
        overlay_data = None
        if self.raw_data is not None and hasattr(self, 'nav_bar') and self.nav_bar.is_overlay_enabled():
            overlay_data = self.raw_original
        
        # Get navigation parameters from nav_bar
        start_time = self.current_start_time
        duration = self.nav_bar.get_duration() if hasattr(self, 'nav_bar') else 10.0
        scale = self.nav_bar.get_scale() if hasattr(self, 'nav_bar') else 50.0
        
        title = f"EEG Time-Series (Clinical View)\n[{self.current_filter_info}]"
        self.canvas.plot_time_series(
            plot_data, 
            title, 
            overlay_data=overlay_data,
            start_time=start_time,
            duration=duration,
            scale=scale
        )

    def on_data_updated(self, raw, info_str):
        """Handle data_updated signal from worker after pipeline operations."""
        self.raw_data = raw
        self.current_filter_info = info_str
        
        # Log filter operation if pending
        if hasattr(self, '_pending_filter_params') and self._pending_filter_params is not None:
            from datetime import datetime
            self.pipeline_history.append({
                "timestamp": datetime.now().isoformat(timespec='seconds'),
                "action": "filter",
                "params": self._pending_filter_params
            })
            self._pending_filter_params = None

        # Log ICA exclusion if pending
        if hasattr(self, '_pending_ica_excludes') and self._pending_ica_excludes is not None:
            from datetime import datetime
            self.pipeline_history.append({
                "timestamp": datetime.now().isoformat(timespec='seconds'),
                "action": "ica_exclusion",
                "params": {"excluded_components": self._pending_ica_excludes}
            })
            self._pending_ica_excludes = None
        
        # Update the time-series plot
        self.update_time_series_plot()

    def _on_nav_time_changed(self, time_sec):
        """Handle time changes from navigation bar."""
        if self.raw_data is None and getattr(self, 'epochs_data', None) is None:
            return
        self.current_start_time = time_sec
        self.update_time_series_plot()
    
    def _on_nav_duration_changed(self, duration):
        """Handle duration changes from navigation bar."""
        if self.raw_data is None and getattr(self, 'epochs_data', None) is None:
            return
        # Update slider range when duration changes
        if hasattr(self, 'nav_bar'):
            self.nav_bar.set_duration_range(self.total_duration)
        self.update_time_series_plot()
    
    def _on_nav_scale_changed(self, scale):
        """Handle scale changes from navigation bar."""
        if self.raw_data is None and getattr(self, 'epochs_data', None) is None:
            return
        self.update_time_series_plot()
    
    def _on_nav_overlay_toggled(self, enabled):
        """Handle overlay toggle from navigation bar."""
        if self.raw_data is None and getattr(self, 'epochs_data', None) is None:
            return
        self.update_time_series_plot()
    
    def on_nav_controls_changed(self, _value=None):
        """Legacy handler - now handled by nav_bar signals."""
        pass

    def open_channel_manager(self):
        """Open the Channel Manager dialog for bad channel interpolation."""
        data = self.raw_data or getattr(self, 'epochs_data', None)
        if data is None:
            self.show_error("No data loaded. Please load a dataset first.")
            return

        dialog = ChannelManagerDialog(data, parent=self)
        dialog.interpolate_requested.connect(self._on_interpolate_channels)
        dialog.exec()

    def _on_interpolate_channels(self, channels: list):
        """Handle interpolation request from Channel Manager dialog."""
        if not channels:
            return
        
        self.log_status(f"Starting interpolation for channels: {', '.join(channels)}")
        self.request_interpolate_bads.emit(channels)

    def on_interpolation_done(self, channels: list):
        """Handle successful channel interpolation."""
        channel_str = ", ".join(channels)
        self.log_status(f"Successfully interpolated channels: {channel_str}")
        
        # Update raw_data reference
        self.raw_data = self.worker.raw
        
        # Add to pipeline history
        from datetime import datetime
        self.pipeline_history.append({
            "timestamp": datetime.now().isoformat(timespec='seconds'),
            "action": "channel_interpolation",
            "params": {
                "channels": channels,
                "method": "spherical_spline"
            }
        })
        
        # Update the time-series plot to reflect changes
        self.current_filter_info = f"Interpolated: {channel_str}"
        self.update_time_series_plot()


    def run_report_generation(self):
        """Trigger report generation on the worker thread."""
        data = self.raw_data or getattr(self, 'epochs_data', None)
        if data is None:
            QMessageBox.warning(
                self,
                "No Data Loaded",
                "Please load a dataset before generating a report."
            )
            return

        self.log_status("Starting report generation...")

        # Gather evoked data if available
        evoked = getattr(self, 'evoked', None)

        # Collect segmentation parameters from GUI
        segmentation_params = {
            'event_name': self.combo_events.currentText() if self.combo_events.currentText() else "N/A",
            'tmin': self.spin_tmin.value(),
            'tmax': self.spin_tmax.value(),
            'baseline_status': self.chk_erp_baseline.isChecked(),
        }

        # Emit signal to worker thread
        self.request_generate_report.emit(
            data,
            self.worker.ica,
            self.epochs,
            evoked,
            self.pipeline_history,
            segmentation_params
        )

    def on_report_ready(self, report_path: str):
        """Handle successful report generation."""
        import webbrowser
        import os

        abs_path = os.path.abspath(report_path)
        self.log_status(f"Report generated: {abs_path}")

        reply = QMessageBox.question(
            self,
            "Report Generated",
            f"Report generated successfully at:\n{abs_path}\n\nOpen in browser now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        if reply == QMessageBox.StandardButton.Yes:
            webbrowser.open(f"file://{abs_path}")

    def closeEvent(self, event):
        """Clean up thread on close."""
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        event.accept()


    # ==================== Batch Processing Methods ====================

    def _on_select_batch_input(self) -> None:
        """Handle input folder selection for batch processing."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Input Folder", "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.batch_input_folder = folder
            # Show truncated path if too long
            display_path = folder if len(folder) < 40 else f"...{folder[-37:]}"
            self.lbl_batch_input.setText(display_path)
            self.lbl_batch_input.setToolTip(folder)
            self._update_batch_button_state()
            self.log_status(f"Batch input folder: {folder}")

    def _on_select_batch_output(self) -> None:
        """Handle output folder selection for batch processing."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", "",
            QFileDialog.Option.ShowDirsOnly
        )
        if folder:
            self.batch_output_folder = folder
            # Show truncated path if too long
            display_path = folder if len(folder) < 40 else f"...{folder[-37:]}"
            self.lbl_batch_output.setText(display_path)
            self.lbl_batch_output.setToolTip(folder)
            self._update_batch_button_state()
            self.log_status(f"Batch output folder: {folder}")

    def _update_batch_button_state(self) -> None:
        """Enable/disable start batch button based on folder selection."""
        enabled = bool(self.batch_input_folder and self.batch_output_folder)
        self.btn_start_batch.setEnabled(enabled)

    def _on_start_batch_click(self) -> None:
        """Start batch processing with current parameters."""
        if not self.batch_input_folder or not self.batch_output_folder:
            self.show_error("Please select both input and output folders.")
            return

        # Validate folders exist
        if not os.path.isdir(self.batch_input_folder):
            self.show_error(f"Input folder does not exist: {self.batch_input_folder}")
            return
        if not os.path.isdir(self.batch_output_folder):
            self.show_error(f"Output folder does not exist: {self.batch_output_folder}")
            return

        # Collect parameters from UI
        params = {
            'filter': self.chk_batch_filter.isChecked(),
            'l_freq': float(self.input_hp.text() or 1.0),
            'h_freq': float(self.input_lp.text() or 40.0),
            'notch_freq': float(self.input_notch.text() or 0.0),
            'ica': self.chk_batch_ica.isChecked(),
            'epoch': self.chk_batch_epoch.isChecked(),
            'event_id': self.combo_events.currentText() if self.combo_events.count() > 0 else "All Events",
            'tmin': self.spin_tmin.value(),
            'tmax': self.spin_tmax.value(),
            'baseline': self.chk_erp_baseline.isChecked(),
            'report': self.chk_batch_report.isChecked(),
        }

        self.log_status("Starting batch processing...")

        # Create and show progress dialog
        self.batch_progress_dialog = QProgressDialog(
            "Initializing batch processing...",
            "Cancel",
            0, 100,
            self
        )
        self.batch_progress_dialog.setWindowTitle("Batch Processing")
        self.batch_progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.batch_progress_dialog.setMinimumDuration(0)
        self.batch_progress_dialog.setValue(0)
        self.batch_progress_dialog.canceled.connect(self._on_batch_canceled)
        self.batch_progress_dialog.show()

        # Disable batch controls during processing
        self.btn_start_batch.setEnabled(False)
        self.btn_batch_input.setEnabled(False)
        self.btn_batch_output.setEnabled(False)

        # Start batch processing
        QMetaObject.invokeMethod(
            self.worker, "run_batch_job",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, self.batch_input_folder),
            Q_ARG(str, self.batch_output_folder),
            Q_ARG(dict, params)
        )

    def _on_batch_progress(self, current: int, total: int, filename: str) -> None:
        """Update batch progress dialog."""
        if hasattr(self, 'batch_progress_dialog') and self.batch_progress_dialog:
            progress = int((current / total) * 100)
            self.batch_progress_dialog.setValue(progress)
            self.batch_progress_dialog.setLabelText(
                f"Processing file {current}/{total}:\n{filename}"
            )

    def _on_batch_log(self, message: str) -> None:
        """Handle batch log messages."""
        self.log_status(message)

    def _on_batch_finished(self, summary: str) -> None:
        """Handle batch processing completion."""
        if hasattr(self, 'batch_progress_dialog') and self.batch_progress_dialog:
            self.batch_progress_dialog.close()
            self.batch_progress_dialog = None

        # Re-enable batch controls
        self.btn_start_batch.setEnabled(True)
        self.btn_batch_input.setEnabled(True)
        self.btn_batch_output.setEnabled(True)

        self.log_status(summary)
        QMessageBox.information(self, "Batch Processing Complete", summary)

    def _on_batch_error(self, filename: str, error: str) -> None:
        """Handle per-file batch errors."""
        self.log_status(f"Error processing {filename}: {error}")

    def _on_batch_canceled(self) -> None:
        """Handle batch cancellation."""
        self.log_status("Batch processing was canceled by user.")
        # Re-enable batch controls
        self.btn_start_batch.setEnabled(True)
        self.btn_batch_input.setEnabled(True)
        self.btn_batch_output.setEnabled(True)
