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
    QTextEdit, QMessageBox, QGroupBox, QComboBox, QDoubleSpinBox,
    QSplitter, QSlider, QWidget
)
from PyQt6.QtCore import (
    Qt, QObject, QThread, pyqtSignal, pyqtSlot, QTimer
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
    psd_ready = pyqtSignal(object, object, str)  # Emits (freqs, psd, filter_info_str)
    ica_ready = pyqtSignal(object) # Emits the fitted ICA object for plotting on Main Thread
    events_loaded = pyqtSignal(dict)  # Emits event_id mapping
    erp_ready = pyqtSignal(object)    # Emits evoked object

    def __init__(self):
        super().__init__()
        self.raw = None  # Holds the MNE Raw object
        self.raw = None  # Holds the MNE Raw object
        self.ica = None  # Holds the fitted ICA object
        self.events = None
        self.event_id = None

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


            # 2. Auto-Detect & Set Channel Types (EOG/ECG)
            # This must be done BEFORE setting the montage to avoid "overlapping positions" errors
            # if EOG/EEG sensors map to the same default location.
            ch_types = {}
            for ch_name in self.raw.ch_names:
                name_lower = ch_name.lower()
                if any(x in name_lower for x in ['eog', 'heog', 'veog']):
                    ch_types[ch_name] = 'eog'
                elif any(x in name_lower for x in ['ecg', 'ekg']):
                    ch_types[ch_name] = 'ecg'
            
            if ch_types:
                self.log_message.emit(f"Setting channel types: {ch_types}")
                self.raw.set_channel_types(ch_types)

            # 3. Neuroscience Logic: Standardizing Electrode Positions
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
            
            # 4. Extract Events (Annotations -> Events)
            try:
                events, event_id = mne.events_from_annotations(self.raw, verbose=False)
                self.events = events
                self.event_id = event_id
                self.log_message.emit(f"Events found: {len(events)} events extracted.")
                self.events_loaded.emit(event_id)
            except Exception:
                self.log_message.emit("No events found in annotations.")
                self.events_loaded.emit({}) # Emit empty dict

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
    @pyqtSlot()
    def run_ica(self):
        """
        Fits ICA on the CURRENTLY filtered data (or raw if no filter).
        Use standard settings: n_components=15, method='fastica'.
        """
        if self.raw is None:
            self.error_occurred.emit("No data loaded. Cannot run ICA.")
            return

        self.log_message.emit("Fitting ICA (n_components=15, fastica)... This may take a moment.")
        
        try:
            # We usually recommend 1Hz high-pass for ICA. 
            # We will use self.raw. In a real app, we should ensure self.raw is filtered.
            # Here we assume the user has run the pipeline or we assume raw is OK.
            # Important: fitting on a copy to be safe, though ICA fit doesn't alter data inplace unless asked?
            # MNE ICA fit takes a Raw object.
            
            # Create ICA object
            self.ica = mne.preprocessing.ICA(n_components=15, method='fastica', random_state=97, max_iter='auto')
            
            # Fit on a copy of data (MNE recommends high-pass filtered data for fitting)
            # We'll validly assume the user might have filtered 'self.raw' in place? 
            # Wait, 'run_pipeline' operates on 'self.raw.copy()'. 'self.raw' is always the ORIGINAL raw loaded.
            # NOTE: Ideally ICA should be fitted on the *filtered* data. 
            # TO FIX: The 'run_pipeline' method currently DOES NOT update 'self.raw', it creates 'result_raw'.
            # If we want to support the workflow "Filter -> ICA", we need to store the filtered result or allow fitting on raw.
            # Given the USER REQUEST: "Ensure ICA is only run after the data is loaded and filtered (High-pass > 1Hz is recommended for ICA)."
            # We don't have a persistent "filtered" object in the current class design (it was 'result_raw').
            # COMPROMISE: We will Fit on 'self.raw' but Warn the user, OR (better) we should have stored the filtered version.
            # Let's modify 'run_pipeline' to Update 'self.current_processed_raw' or similar?
            # Or just fit on self.raw for MVP and rely on user to have filtered?
            # Wait, if 'run_pipeline' just emits PSD and doesn't save the filtered raw, we can't fit ICA on it!
            # Let's filter a temporary copy here for fitting if needed, or assume self.raw is what we use.
            # Re-reading: "Ensure ICA is only run after the data is loaded and filtered"
            # -> This implies we NEED the filtered data.
            # Let's change this to: Fit on a COPY of self.raw that we apply a 1Hz HP filter to specifically for ICA fitting, 
            # OR we change architecture to store processed data.
            # Best approach for MVP integrity: Apply a 1Hz High-pass strictly for the ICA fit here.
            
            raw_for_ica = self.raw.copy()
            # Apply 1.0Hz Highpass for stable ICA if not already done? 
            # The prompt says "Ensure... High-pass > 1Hz is recommended". 
            # We'll just filter this copy to be safe.
            raw_for_ica.filter(l_freq=1.0, h_freq=None, verbose=False) 
            
            self.ica.fit(raw_for_ica, verbose=False)
            self.log_message.emit("ICA Fit Complete. Emitting signal to plot components...")
            
            # Plot components immediately
            # self.ica.plot_components(show=True) -> MOVED TO MAIN THREAD
            self.ica_ready.emit(self.ica)
            self.finished.emit()

        except Exception as e:
            self.error_occurred.emit(f"ICA Fit Error: {str(e)}")
            traceback.print_exc()

    @pyqtSlot(str)
    def apply_ica(self, exclude_str: str):
        """
        Apply ICA with excluded components and re-compute PSD.
        """
        if self.ica is None:
            self.error_occurred.emit("ICA has not been calculated yet.")
            return
            
        try:
            # Parse excludes
            if not exclude_str.strip():
                excludes = []
            else:
                excludes = [int(x.strip()) for x in exclude_str.split(',') if x.strip().isdigit()]
            
            self.log_message.emit(f"Applying ICA exclusion: {excludes}")
            self.ica.exclude = excludes
            
            # Apply to a COPY of raw
            # We want to show the Cleaner signal PSD.
            # So: Raw -> Apply ICA -> Compute PSD
            
            clean_raw = self.raw.copy()
            self.ica.apply(clean_raw)
            
            # Now we compute PSD on this clean_raw
            # We should probably apply the SAME High/Low pass filters the user had?
            # We don't know what they were unless we store them. 
            # For this 'Apply ICA' step, let's just show the PSD of the ICA-cleaned raw (maybe just 1-40Hz default or raw).
            # To be consistent, let's just do a quick PSD of the cleaned data.
            # Better: Apply default filters (1-40) to look nice? Or just raw.
            # Let's just do Raw -> ICA -> PSD (0-100Hz).
            
            self.log_message.emit(f"Computing PSD on ICA-cleaned data...")
            spectrum = clean_raw.compute_psd(fmax=100)
            psds, freqs = spectrum.get_data(return_freqs=True)
            psd_mean = psds.mean(axis=0)
            
            self.psd_ready.emit(freqs, psd_mean, f"ICA Cleaned | Excl: {excludes}")
            self.finished.emit()
            
        except ValueError:
             self.error_occurred.emit("Invalid format for components. Use '0, 1, 2'")
        except Exception as e:
            self.error_occurred.emit(f"ICA Apply Error: {str(e)}")
            traceback.print_exc()

    @pyqtSlot(str, float, float)
    def compute_erp(self, event_name: str, tmin: float, tmax: float):
        """
        Epochs the data around a specific event trigger and averages them to create an ERP.
        """
        if self.raw is None:
            self.error_occurred.emit("No data loaded.")
            return

        if self.events is None or self.event_id is None:
             self.error_occurred.emit("No events found in this dataset.")
             return
             
        if event_name not in self.event_id:
            self.error_occurred.emit(f"Event '{event_name}' not found.")
            return

        self.log_message.emit(f"Computing ERP for: {event_name} (tmin={tmin}, tmax={tmax})...")
        
        try:
            # Select specific event ID
            specific_event_id = {event_name: self.event_id[event_name]}
            
            # Create Epochs
            # baseline=(None, 0) applies baseline correction from start of epoch to 0 (stimulus onset)
            epochs = mne.Epochs(self.raw, self.events, event_id=specific_event_id, 
                                tmin=tmin, tmax=tmax, baseline=(tmin, 0), preload=True, verbose=False)
            
            # Compute Evoked (Average)
            evoked = epochs.average()
            
            self.log_message.emit(f"ERP Computed. Averaged {len(epochs)} epochs.")
            self.erp_ready.emit(evoked)
            self.finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(f"ERP Error: {str(e)}")
            traceback.print_exc()

# -----------------------------------------------------------------------------
# UI COMPONENTS: ERP Viewer Window
# -----------------------------------------------------------------------------

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
        
        # Data properties
        self.times = self.evoked.times
        self.tmin = self.times[0]
        self.tmax = self.times[-1]
        self.current_time = 0.0
        self.vline = None # Reference to the vertical line on plot
        
        # Debounce Timer for smoother sliding
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
        
        # Splitter for adjustable heights
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # 1. TOP PLOT : Butterfly
        self.butterfly_canvas = MplCanvas(self, width=5, height=4)
        splitter.addWidget(self.butterfly_canvas)
        
        # 2. BOTTOM AREA : Topomap + Controls
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        # Topomap Canvas
        self.topomap_canvas = MplCanvas(self, width=5, height=4)
        bottom_layout.addWidget(self.topomap_canvas)
        
        # Controls Row
        controls_layout = QHBoxLayout()
        
        self.lbl_time = QLabel("Time: 0 ms")
        self.lbl_time.setFixedWidth(100)
        
        # Slider setup
        # Convert time range to milliseconds for integer slider
        min_ms = int(self.tmin * 1000)
        max_ms = int(self.tmax * 1000)
        
        self.slider_time = QSlider(Qt.Orientation.Horizontal)
        self.slider_time.setRange(min_ms, max_ms)
        self.slider_time.setValue(0) # Start at 0ms (stimulus onset)
        self.slider_time.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider_time.setTickInterval(50) # Tick every 50ms
        self.slider_time.valueChanged.connect(self.on_time_changed)
        # sliderReleased removed in favor of debounced valueChanged
        # self.slider_time.sliderReleased.connect(self.update_topomap_heavy)

        controls_layout.addWidget(self.lbl_time)
        controls_layout.addWidget(self.slider_time)
        
        bottom_layout.addLayout(controls_layout)
        splitter.addWidget(bottom_widget)
        
        main_layout.addWidget(splitter)

    def plot_initial_state(self):
        """Draws the static Butterfly plot and initial Topomap."""
        # --- Plot Butterfly ---
        ax = self.butterfly_canvas.axes
        ax.clear()
        
        # MNE plot onto our axes
        # spatial_colors=True colors lines by sensor position
        self.evoked.plot(axes=ax, spatial_colors=True, show=False, time_unit='s')
        
        # Customize look to match simple dark theme if MNE overrode it, 
        # but MNE plot usually handles its own styling. 
        # We just ensure the facecolor matches.
        # Note: MNE's plot() might change title/labels.
        ax.set_title("Global Field Power (Butterfly Plot)", color='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.tick_params(colors='white')
        
        # Add interactive vertical line at t=0
        self.vline = ax.axvline(x=0, color='white', linestyle='--', linewidth=1.5, alpha=0.8)
        self.butterfly_canvas.draw()
        
        # --- Plot Initial Topomap using the 'heavy' update logic ---
        self.update_topomap_heavy()

    def on_time_changed(self, value):
        """Called repeatedly while dragging slider."""
        time_sec = value / 1000.0
        self.current_time = time_sec
        self.lbl_time.setText(f"Time: {value} ms")
        
        # Update Vertical Line position efficiently (blit would be better but simple redraw is OK for this scale)
        if self.vline:
            self.vline.set_xdata([time_sec, time_sec])
            self.butterfly_canvas.draw() # Redraw just to move line
            
        # NOTE: We can skip full topomap redraw here if it's too slow, 
        # and only do it on release.
        # But let's try to see if MNE's topomap is fast enough for continuous scrubbing.
        # Usually it is NOT fast enough for 60fps, so we might throttle or only do on release.
        # User requirement: "consider updating only on sliderReleased or use a slight delay".
        # We will Implement the 'sliderReleased' approach for the heavy topomap, 
        # but maybe doing it here makes it 'feel' better if data is small. 
        # For safety/performance, we will ONLY move the line here and trigger the timer.
        # Topomap updates when timer fires (user stopped moving or paused).
        
        self.debounce_timer.start(100) # Reset timer to 100ms
    
    def update_topomap_heavy(self):
        """
        Re-plots the topomap. 
        Called on sliderReleased OR manual trigger.
        Allows for smoother UI during dragging.
        """
        # Get current time from stored state (updated by slider move)
        t = self.current_time
        
        ax = self.topomap_canvas.axes
        ax.clear()
        
        # Plot topomap
        # times=[t] plots a single map
        # colorbar=True adds a colorbar, slightly squishing the plot
        try:
            self.evoked.plot_topomap(times=[t], axes=ax, show=False, colorbar=False,
                                     outlines='head', sphere='auto')
            
            ax.set_title(f"Topography at {t*1000:.0f} ms", color='white', fontsize=12)
            self.topomap_canvas.draw()
        except Exception as e:
            print(f"Topomap Error: {e}")

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
    request_run_ica = pyqtSignal()
    request_run_ica = pyqtSignal()
    request_apply_ica = pyqtSignal(str)
    request_compute_erp = pyqtSignal(str, float, float)

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
        self.worker.psd_ready.connect(self.update_plot)
        self.worker.ica_ready.connect(self.display_ica_components)
        self.worker.events_loaded.connect(self.populate_event_dropdown)
        self.worker.erp_ready.connect(self.handle_erp_ready)
        
        # Connect worker slots
        self.request_load_data.connect(self.worker.load_data)
        self.request_run_pipeline.connect(self.worker.run_pipeline)
        self.request_run_ica.connect(self.worker.run_ica)
        self.request_run_ica.connect(self.worker.run_ica)
        self.request_apply_ica.connect(self.worker.apply_ica)
        self.request_compute_erp.connect(self.worker.compute_erp)
        
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

        # 3. ICA Section
        gb_ica = QGroupBox("ICA Artifact Removal")
        gb_ica_layout = QVBoxLayout()
        
        self.btn_calc_ica = QPushButton("1. Calculate ICA")
        self.btn_calc_ica.setToolTip("Fit ICA and show component maps")
        self.btn_calc_ica.clicked.connect(self.run_ica_click)
        self.btn_calc_ica.setEnabled(False)
        
        l_ica = QLabel("Exclude Components (IDs):")
        self.input_ica_exclude = QLineEdit()
        self.input_ica_exclude.setPlaceholderText("e.g. 0, 2")
        
        self.btn_apply_ica = QPushButton("2. Apply ICA & Re-plot")
        self.btn_apply_ica.clicked.connect(self.apply_ica_click)
        self.btn_apply_ica.setEnabled(False) # Enabled after Calc? Or just always allow checking
        
        gb_ica_layout.addWidget(self.btn_calc_ica)
        gb_ica_layout.addWidget(l_ica)
        gb_ica_layout.addWidget(self.input_ica_exclude)
        gb_ica_layout.addWidget(self.btn_apply_ica)
        
        gb_ica.setLayout(gb_ica_layout)
        sidebar_layout.addWidget(gb_ica)

        # 4. ERP Analysis Section
        gb_erp = QGroupBox("ERP Analysis")
        gb_erp_layout = QVBoxLayout()

        gb_erp_layout.addWidget(QLabel("Select Event Trigger:"))
        self.combo_events = QComboBox()
        gb_erp_layout.addWidget(self.combo_events)

        # Time range inputs
        t_layout = QHBoxLayout()
        t_layout.addWidget(QLabel("tmin:"))
        self.spin_tmin = QDoubleSpinBox()
        self.spin_tmin.setRange(-5.0, 5.0)
        self.spin_tmin.setValue(-0.2)
        self.spin_tmin.setSingleStep(0.1)
        t_layout.addWidget(self.spin_tmin)
        
        t_layout.addWidget(QLabel("tmax:"))
        self.spin_tmax = QDoubleSpinBox()
        self.spin_tmax.setRange(-5.0, 5.0)
        self.spin_tmax.setValue(0.5)
        self.spin_tmax.setSingleStep(0.1)
        t_layout.addWidget(self.spin_tmax)
        
        gb_erp_layout.addLayout(t_layout)

        self.btn_erp = QPushButton("Compute & Plot ERP")
        self.btn_erp.clicked.connect(self.compute_erp_click)
        self.btn_erp.setEnabled(False) # Enable when events loaded
        gb_erp_layout.addWidget(self.btn_erp)

        gb_erp.setLayout(gb_erp_layout)
        sidebar_layout.addWidget(gb_erp)

        # Spacer to push log to bottom
        sidebar_layout.addStretch()

        # 3. Logs
        sidebar_layout.addWidget(QLabel("Status Log:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        # self.log_area.setFixedHeight(200) # Remove fixed height to let it fill available space if needed, or keep small
        self.log_area.setMinimumHeight(150) # Use min height instead
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
        self.btn_calc_ica.setEnabled(True) # Enable ICA
        self.btn_apply_ica.setEnabled(True)
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

    def run_ica_click(self):
        self.request_run_ica.emit()

    def apply_ica_click(self):
        excludes = self.input_ica_exclude.text()
        self.request_apply_ica.emit(excludes)

    def populate_event_dropdown(self, event_id_dict):
        """Populates the event dropdown with unique events found in the data."""
        self.combo_events.clear()
        if not event_id_dict:
            self.log_status("No events found for ERP analysis.")
            self.btn_erp.setEnabled(False)
            return

        self.combo_events.addItems(list(event_id_dict.keys()))
        self.btn_erp.setEnabled(True)
        self.log_status(f"Populated ERP dropdown with {len(event_id_dict)} events.")

    def compute_erp_click(self):
        event_name = self.combo_events.currentText()
        if not event_name:
            return
        tmin = self.spin_tmin.value()
        tmax = self.spin_tmax.value()
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
