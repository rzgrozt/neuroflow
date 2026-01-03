import sys
import os
import traceback
import logging
from typing import Optional, Tuple

import mne
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QFrame,
    QTextEdit, QMessageBox, QGroupBox
)
from PyQt6.QtCore import (
    Qt, QObject, QThread, pyqtSignal, pyqtSlot
)

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NeuroFlow")

# -----------------------------------------------------------------------------
# ARCHITECTURE: AnalysisWorker (Model / Controller Logic on Thread)
# -----------------------------------------------------------------------------

class AnalysisWorker(QObject):
    """
    Worker class for handling heavy MNE-Python analysis tasks on a separate thread.
    This ensures the GUI remains responsive during data loading and signal processing.
    """
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    log_message = pyqtSignal(str)
    data_loaded = pyqtSignal(object)  # Emits the MNE Raw object
    psd_ready = pyqtSignal(object, object, str)  # Emits (freqs, psd, filter_info_str)

    def __init__(self):
        super().__init__()
        self.raw = None  # Holds the MNE Raw object

    @pyqtSlot(str)
    def load_data(self, file_path: str):
        """
        Loads EEG data from .vhdr (BrainVision), .fif, or .edf files.
        Applies standard montage if channel positions are missing.
        """
        filename = os.path.basename(file_path)
        self.log_message.emit(f"Function: load_data | Loading: {filename}")
        
        try:
            # 1. Load Data based on extension
            if file_path.endswith('.vhdr'):
                # BrainVision (.vhdr header file)
                self.raw = mne.io.read_raw_brainvision(file_path, preload=True)
            elif file_path.endswith('.fif'):
                self.raw = mne.io.read_raw_fif(file_path, preload=True)
            elif file_path.endswith('.edf'):
                self.raw = mne.io.read_raw_edf(file_path, preload=True)
            else:
                self.error_occurred.emit(f"Unsupported format: {filename}. Please use .vhdr, .fif, or .edf")
                return

            # 2. Neuroscience Logic: Standardizing Electrode Positions
            # BrainVision and other raw formats often lack 3D sensor locations.
            # We strictly check if montage is missing before setting a standard one.
            if self.raw.get_montage() is None:
                self.log_message.emit("Montage is missing. Applying standard_1020 montage...")
                try:
                    montage = mne.channels.make_standard_montage('standard_1020')
                    self.raw.set_montage(montage, on_missing='ignore')
                    self.log_message.emit("Successfully applied standard_1020 montage.")
                except Exception as e:
                    self.log_message.emit(f"Warning: Could not set montage: {e}")
            else:
                self.log_message.emit("Dataset already contains montage information.")

            self.data_loaded.emit(self.raw)
            self.log_message.emit(f"Successfully loaded {len(self.raw.ch_names)} channels, {self.raw.times[-1]:.2f}s duration.")
            self.finished.emit()

        except NotImplementedError:
             self.error_occurred.emit("MNE Error: Feature not implemented for this file type.")
        except Exception as e:
            self.error_occurred.emit(f"Data Loading Error: {str(e)}")
            traceback.print_exc()

    @pyqtSlot(float, float, float)
    def run_pipeline(self, l_freq: float, h_freq: float, notch_freq: float):
        """
        Runs the preprocessing pipeline: Filtering -> PSD Calculation.
        
        FIXED LOGIC:
        - l_freq: Lower pass-band edge (High-pass filter value).
        - h_freq: Upper pass-band edge (Low-pass filter value).
        """
        if self.raw is None:
            self.error_occurred.emit("No data loaded. Please load a dataset first.")
            return

        self.log_message.emit("Starting preprocessing pipeline...")
        
        # Operate on a copy to preserve original data state
        result_raw = self.raw.copy()

        try:
            # 1. Filtering
            filter_info = []
            
            # Apply Bandpass (Low-pass + High-pass)
            # l_freq = High-pass cutoff (e.g., 1.0 Hz)
            # h_freq = Low-pass cutoff (e.g., 40.0 Hz)
            if l_freq > 0 or h_freq > 0:
                lf = l_freq if l_freq > 0 else None
                hf = h_freq if h_freq > 0 else None
                
                self.log_message.emit(f"Applying Bandpass Filter: HP={lf} Hz, LP={hf} Hz")
                result_raw.filter(l_freq=lf, h_freq=hf, fir_design='firwin', verbose=False)
                filter_info.append(f"Bandpass: {lf}-{hf} Hz")

            # Apply Notch
            if notch_freq > 0:
                self.log_message.emit(f"Applying Notch Filter at {notch_freq} Hz")
                result_raw.notch_filter(freqs=np.array([notch_freq]), fir_design='firwin', verbose=False)
                filter_info.append(f"Notch: {notch_freq} Hz")

            if not filter_info:
                filter_info.append("Raw Signal")

            # 2. PSD Calculation
            self.log_message.emit("Computing Power Spectral Density (PSD)...")
            
            # Use Welch's method
            spectrum = result_raw.compute_psd(fmax=100)
            psds, freqs = spectrum.get_data(return_freqs=True)
            
            # Average across channels
            psd_mean = psds.mean(axis=0)
            
            filter_str = " | ".join(filter_info)
            self.psd_ready.emit(freqs, psd_mean, filter_str)
            self.log_message.emit("Pipeline completed successfully.")
            self.finished.emit()

        except Exception as e:
            self.error_occurred.emit(f"Pipeline Error: {str(e)}")
            traceback.print_exc()


# -----------------------------------------------------------------------------
# UI COMPONENTS: Canvas
# -----------------------------------------------------------------------------

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # Neural Data Visualization Theme
        plt.style.use('dark_background')
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        self.fig.patch.set_facecolor('#1e1e1e') # Match app background
        self.axes.set_facecolor('#1e1e1e')
        
        super(MplCanvas, self).__init__(self.fig)


# -----------------------------------------------------------------------------
# MAIN WINDOW: View / UI Logic
# -----------------------------------------------------------------------------

class MainWindow(QMainWindow):
    # Signals to communicate with worker
    request_load_data = pyqtSignal(str)
    # Signal sending: (High-pass/l_freq, Low-pass/h_freq, Notch)
    request_run_pipeline = pyqtSignal(float, float, float)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NeuroFlow - Professional EEG Analysis")
        self.resize(1200, 800)
        self.raw_data = None # Store reference to plot sensors logic
        
        # Initialize Threading
        self.thread = QThread()
        self.worker = AnalysisWorker()
        self.worker.moveToThread(self.thread)
        
        # Connect Signals
        self.worker.log_message.connect(self.log_status)
        self.worker.error_occurred.connect(self.show_error)
        self.worker.data_loaded.connect(self.on_data_loaded)
        self.worker.psd_ready.connect(self.update_plot)
        
        # Connect worker slots
        self.request_load_data.connect(self.worker.load_data)
        self.request_run_pipeline.connect(self.worker.run_pipeline)
        
        self.thread.start()
        
        # UI Setup
        self.apply_dark_theme()
        self.init_ui()

    def apply_dark_theme(self):
        """Applies a Modern Dark Theme using QSS."""
        qss = """
        QMainWindow {
            background-color: #2b2b2b;
        }
        QWidget {
            color: #ffffff;
            font-family: 'Segoe UI', 'Roboto', sans-serif;
            font-size: 14px;
        }
        QGroupBox {
            border: 1px solid #444;
            border-radius: 6px;
            margin-top: 12px;
            font-weight: bold;
            color: #ccc;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
        QPushButton {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 8px 16px;
            color: white;
        }
        QPushButton:hover {
            background-color: #4c4c4c;
            border-color: #007acc;
        }
        QPushButton:pressed {
            background-color: #007acc;
        }
        QLineEdit {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px;
            color: white;
            selection-background-color: #007acc;
        }
        QLineEdit:focus {
            border: 1px solid #007acc;
        }
        QTextEdit {
            background-color: #1e1e1e;
            border: 1px solid #444;
            color: #dcdcdc;
            font-family: 'Consolas', 'Courier New', monospace;
        }
        QLabel {
            color: #cccccc;
        }
        """
        self.setStyleSheet(qss)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # ----------------------
        # LEFT SIDEBAR
        # ----------------------
        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        sidebar.setFixedWidth(320)
        sidebar.setStyleSheet("background-color: #252526; border-radius: 8px;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(15)

        # Title
        title_label = QLabel("NeuroFlow")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #007acc; margin-bottom: 10px;")
        sidebar_layout.addWidget(title_label)

        # 1. Data Loading Section
        gb_data = QGroupBox("Dataset")
        gb_data_layout = QVBoxLayout()
        
        self.btn_load = QPushButton("Load EEG Data")
        self.btn_load.setToolTip("Supports .vhdr (BrainVision), .fif, .edf")
        self.btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load.clicked.connect(self.browse_file)
        
        # New "Check Sensors" Button
        self.btn_sensors = QPushButton("📍 Check Sensors")
        self.btn_sensors.setToolTip("View 2D Topomap of sensor positions")
        self.btn_sensors.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sensors.setEnabled(False) # Disabled until data loads
        self.btn_sensors.clicked.connect(self.check_sensors)

        gb_data_layout.addWidget(self.btn_load)
        gb_data_layout.addWidget(self.btn_sensors)
        gb_data.setLayout(gb_data_layout)
        sidebar_layout.addWidget(gb_data)

        # 2. Preprocessing Section
        gb_proc = QGroupBox("Preprocessing Pipeline")
        gb_proc_layout = QVBoxLayout()

        # High Pass
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("High-pass (Hz):"))
        self.input_hp = QLineEdit("1.0")
        h_layout.addWidget(self.input_hp)
        gb_proc_layout.addLayout(h_layout)

        # Low Pass
        l_layout = QHBoxLayout()
        l_layout.addWidget(QLabel("Low-pass (Hz):"))
        self.input_lp = QLineEdit("40.0")
        l_layout.addWidget(self.input_lp)
        gb_proc_layout.addLayout(l_layout)

        # Notch
        n_layout = QHBoxLayout()
        n_layout.addWidget(QLabel("Notch (Hz):"))
        self.input_notch = QLineEdit("50.0")
        n_layout.addWidget(self.input_notch)
        gb_proc_layout.addLayout(n_layout)

        self.btn_run = QPushButton("Run Pipeline")
        self.btn_run.setStyleSheet("background-color: #007acc; font-weight: bold;")
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.clicked.connect(self.launch_pipeline)
        self.btn_run.setEnabled(False)
        
        gb_proc_layout.addSpacing(10)
        gb_proc_layout.addWidget(self.btn_run)
        
        gb_proc.setLayout(gb_proc_layout)
        sidebar_layout.addWidget(gb_proc)

        # Spacer to push log to bottom
        sidebar_layout.addStretch()

        # 3. Logs
        sidebar_layout.addWidget(QLabel("Status Log:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFixedHeight(200)
        sidebar_layout.addWidget(self.log_area)

        # Add Sidebar to Main
        main_layout.addWidget(sidebar)

        # ----------------------
        # MAIN CONTENT AREA
        # ----------------------
        content_frame = QFrame()
        content_frame.setStyleSheet("background-color: #1e1e1e; border-radius: 8px;")
        content_layout = QVBoxLayout(content_frame)

        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        content_layout.addWidget(self.canvas)

        # Initial plot placeholder
        self.canvas.axes.text(0.5, 0.5, 'NeuroFlow Ready\nLoad BrainVision (.vhdr) or others\nto begin analysis', 
                              color='gray', ha='center', va='center', fontsize=12)
        self.canvas.draw()

        main_layout.addWidget(content_frame)
        
        # Stretch factors
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 3)

    # -------------------------------------------------------------------------
    # UI Interactions
    # -------------------------------------------------------------------------

    def log_status(self, message):
        """Appends message to the sidebar status log."""
        self.log_area.append(f">> {message}")
        self.log_area.verticalScrollBar().setValue(self.log_area.verticalScrollBar().maximum())

    def show_error(self, message):
        """Displays error message box and logs it."""
        self.log_status(f"ERROR: {message}")
        QMessageBox.critical(self, "Error", message)

    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            "Open EEG Data", 
            "", 
            "EEG Data (*.vhdr *.fif *.edf);;All Files (*)"
        )
        if file_name:
            self.log_status(f"Selected file: {file_name}")
            self.request_load_data.emit(file_name)
        else:
            self.log_status("File selection cancelled.")

    def on_data_loaded(self, raw):
        """Called when worker successfully loads data."""
        self.raw_data = raw # Store reference
        self.btn_run.setEnabled(True)
        self.btn_sensors.setEnabled(True)
        QMessageBox.information(self, "Success", "EEG Data Loaded Successfully.")

    def check_sensors(self):
        """Visualize sensor positions."""
        if self.raw_data:
            self.log_status("Visualizing sensor positions...")
            # block=False ensures the GUI doesn't freeze
            self.raw_data.plot_sensors(show_names=True, kind='topomap', block=False)

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
            
            # Corrections:
            # GUI "High-pass" -> MNE l_freq (Lower pass-band edge)
            # GUI "Low-pass"  -> MNE h_freq (Upper pass-band edge)
            l_freq = hp
            h_freq = lp
            
            self.request_run_pipeline.emit(l_freq, h_freq, notch)
            
        except ValueError:
            self.show_error("Invalid Filter Parameters. Please enter numeric values.")

    def update_plot(self, freqs, psd_mean, filter_info_str):
        """Updates the Matplotlib canvas with the new PSD data."""
        self.canvas.axes.clear()
        
        # PSD Plot Logic
        # 10*np.log10 to convert to dB
        self.canvas.axes.plot(freqs, 10 * np.log10(psd_mean), color='#007acc', linewidth=1.5)
        
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

# -----------------------------------------------------------------------------
# MAIN ENTRY POINT
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
