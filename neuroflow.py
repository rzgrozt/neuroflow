import sys
import os
import traceback
import logging
from typing import Optional, Tuple, List

import mne
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

try:
    import mne_connectivity
    HAS_CONNECTIVITY = True
except ImportError:
    HAS_CONNECTIVITY = False

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QFrame,
    QTextEdit, QMessageBox, QGroupBox, QComboBox, QDoubleSpinBox,
    QSplitter, QSlider, QWidget, QTabWidget, QScrollArea, QToolBox, QDialog,
    QToolBar, QMenu
)
from PyQt6.QtGui import QAction, QIcon, QPixmap, QScreen
from PyQt6.QtCore import (
    Qt, QObject, QThread, pyqtSignal, pyqtSlot, QTimer, QSize
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NeuroFlow")



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

    def __init__(self, raw: mne.io.BaseRaw, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dataset Inspector")
        self.resize(550, 450)
        self.raw = raw

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
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView

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
    ica_ready = pyqtSignal(object) # Emits the fitted ICA object for plotting on Main Thread
    events_loaded = pyqtSignal(dict)  # Emits event_id mapping
    erp_ready = pyqtSignal(object)    # Emits evoked object
    tfr_ready = pyqtSignal(object)    # Emits TFR object (AverageTFR)
    connectivity_ready = pyqtSignal(object) # Emits connectivity object (figure or data)
    save_finished = pyqtSignal(str) # Emits filename when save is complete

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

            if file_path.endswith('.vhdr'):
                self.raw = mne.io.read_raw_brainvision(file_path, preload=True)
            elif file_path.endswith('.fif'):
                self.raw = mne.io.read_raw_fif(file_path, preload=True)
            elif file_path.endswith('.edf'):
                self.raw = mne.io.read_raw_edf(file_path, preload=True)
            else:
                self.error_occurred.emit(f"Unsupported format: {filename}. Please use .vhdr, .fif, or .edf")
                return


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
            
            try:
                events, event_id = mne.events_from_annotations(self.raw, verbose=False)
                self.events = events
                self.event_id = event_id
                self.log_message.emit(f"Events found: {len(events)} events extracted.")
                self.events_loaded.emit(event_id)
            except Exception:
                self.log_message.emit("No events found in annotations.")
                self.events_loaded.emit({})

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
        
        l_freq: Lower pass-band edge (High-pass filter value).
        h_freq: Upper pass-band edge (Low-pass filter value).
        """
        if self.raw is None:
            self.error_occurred.emit("No data loaded. Please load a dataset first.")
            return

        self.log_message.emit("Starting preprocessing pipeline...")
        
        # Operate on a copy to preserve original data state
        result_raw = self.raw.copy()

        try:
            filter_info = []
            
            if l_freq > 0 or h_freq > 0:
                lf = l_freq if l_freq > 0 else None
                hf = h_freq if h_freq > 0 else None
                
                self.log_message.emit(f"Applying Bandpass Filter: HP={lf} Hz, LP={hf} Hz")
                result_raw.filter(l_freq=lf, h_freq=hf, fir_design='firwin', verbose=False)
                filter_info.append(f"Bandpass: {lf}-{hf} Hz")

            if notch_freq > 0:
                self.log_message.emit(f"Applying Notch Filter at {notch_freq} Hz")
                result_raw.notch_filter(freqs=np.array([notch_freq]), fir_design='firwin', verbose=False)
                filter_info.append(f"Notch: {notch_freq} Hz")

            if not filter_info:
                filter_info.append("Raw Signal")

            self.log_message.emit("Computing Power Spectral Density (PSD)...")
            
            spectrum = result_raw.compute_psd(fmax=100)
            psds, freqs = spectrum.get_data(return_freqs=True)
            
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
        """
        if self.raw is None:
            self.error_occurred.emit("No data loaded. Cannot run ICA.")
            return

        self.log_message.emit("Fitting ICA (n_components=15, fastica)... This may take a moment.")
        
        try:
            self.ica = mne.preprocessing.ICA(n_components=15, method='fastica', random_state=97, max_iter='auto')
            
            raw_for_ica = self.raw.copy()
            raw_for_ica.filter(l_freq=1.0, h_freq=None, verbose=False) 
            
            self.ica.fit(raw_for_ica, verbose=False)
            self.log_message.emit("ICA Fit Complete. Emitting signal to plot components...")
            
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

            if not exclude_str.strip():
                excludes = []
            else:
                excludes = [int(x.strip()) for x in exclude_str.split(',') if x.strip().isdigit()]
            
            self.log_message.emit(f"Applying ICA exclusion: {excludes}")
            self.ica.exclude = excludes
            
            clean_raw = self.raw.copy()
            self.ica.apply(clean_raw)
            
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

            specific_event_id = {event_name: self.event_id[event_name]}
            
            epochs = mne.Epochs(self.raw, self.events, event_id=specific_event_id, 
                                tmin=tmin, tmax=tmax, baseline=(tmin, 0), preload=True, verbose=False)
            
            evoked = epochs.average()
            
            self.log_message.emit(f"ERP Computed. Averaged {len(epochs)} epochs.")
            self.erp_ready.emit(evoked)
            self.finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(f"ERP Error: {str(e)}")
            traceback.print_exc()

    @pyqtSlot(str, float, float)
    def compute_tfr(self, ch_name: str, l_freq: float, h_freq: float, n_cycles_div: int = 2):
        """
        Computes Time-Frequency Representation (TFR) using Morlet wavelets.
        Focuses on a single channel to save performance.
        """
        if self.raw is None:
            self.error_occurred.emit("No data loaded.")
            return

        self.log_message.emit(f"Computing TFR for channel {ch_name} (Freqs: {l_freq}-{h_freq}Hz)...")
        
        try:

            freqs = np.arange(l_freq, h_freq, 1.0)
            n_cycles = freqs / n_cycles_div
            
            if self.events is None:
                self.error_occurred.emit("TFR requires events/epochs to visualize ERD/ERS. No events found.")
                return
                
            picks = [ch_name]
            tmin, tmax = -1.0, 2.0 
            
            event_id_to_use = None
            if self.event_id:
                first_key = list(self.event_id.keys())[0]
                event_id_to_use = {first_key: self.event_id[first_key]}
            
            epochs = mne.Epochs(self.raw, self.events, event_id=event_id_to_use, 
                                tmin=tmin, tmax=tmax, picks=picks,
                                baseline=(tmin, 0), preload=True, verbose=False)
            
            power = mne.time_frequency.tfr_morlet(
                epochs, n_cycles=n_cycles, return_itc=False,
                freqs=freqs, average=True, verbose=False
            )
            
            self.tfr_ready.emit(power)
            self.finished.emit()
            
        except Exception as e:
            self.error_occurred.emit(f"TFR Error: {str(e)}")
            traceback.print_exc()

    @pyqtSlot(str)
    def save_data(self, filename: str):
        """
        Saves the CURRENT raw object to a .fif file.
        Runs in the worker thread to avoid freezing UI.
        """
        if self.raw is None:
            self.error_occurred.emit("No data to save.")
            return

        self.log_message.emit(f"Saving data to {filename}...")
        try:
            if not filename.endswith('.fif'):
                filename += '.fif'
            
            self.raw.save(filename, overwrite=True)
            self.save_finished.emit(filename)
            self.log_message.emit(f"Data saved successfully to {filename}")

        except Exception as e:
            self.error_occurred.emit(f"Save Error: {str(e)}")
            traceback.print_exc()

    @pyqtSlot()
    def compute_connectivity(self):
        """
        Computes Functional Connectivity using wPLI (Weighted Phase Lag Index).
        Targeting Alpha Band (8-12Hz) by default for MVP.
        """
        if self.raw is None:
            self.error_occurred.emit("No data loaded.")
            return

        if not HAS_CONNECTIVITY:
             self.error_occurred.emit("mne-connectivity not installed. pip install mne-connectivity")
             return

        self.log_message.emit("Computing Alpha Band Connectivity (wPLI)...")
        
        try:

            tmin, tmax = 0, 4.0 
            
            if self.events is not None:
                 epochs = mne.Epochs(self.raw, self.events, event_id=None, tmin=tmin, tmax=tmax, 
                                     baseline=None, preload=True, verbose=False)
            else:
                 epochs = mne.make_fixed_length_epochs(self.raw, duration=4.0, preload=True, verbose=False)

            fmin, fmax = 8.0, 12.0
            sfreq = self.raw.info['sfreq']
            
            con = mne_connectivity.spectral_connectivity_epochs(
                epochs, method='wpli', mode='multitaper', sfreq=sfreq,
                fmin=fmin, fmax=fmax, faverage=True, mt_adaptive=True, n_jobs=1, verbose=False
            )
            
            self.connectivity_ready.emit(con)
            self.finished.emit()
            self.log_message.emit("Connectivity Computation Complete.")

        except Exception as e:
            self.error_occurred.emit(f"Connectivity Error: {str(e)}")
            traceback.print_exc()



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
        plt.style.use('dark_background')
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        self.fig.patch.set_facecolor('#1e1e1e')
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
        
        self.thread = QThread()
        self.worker = AnalysisWorker()
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
        
        self.apply_dark_theme()
        self.init_ui()
        self.init_toolbar()
        self.create_menu()

    def init_toolbar(self):
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(self.toolbar)
        
        save_action = QAction("💾 Save Clean Data", self)
        save_action.setStatusTip("Save the processed data to .fif")
        save_action.triggered.connect(self.on_save_clean_data)
        self.toolbar.addAction(save_action)
        
        screenshot_action = QAction("📷 Screenshot", self)
        screenshot_action.setStatusTip("Take a screenshot of the application")
        screenshot_action.triggered.connect(self.on_take_screenshot)
        self.toolbar.addAction(screenshot_action)

    def create_menu(self):
        """Creates the Menu Bar."""
        menu_bar = self.menuBar()
        
        # Help Menu
        help_menu = menu_bar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.setStatusTip("Show About dialog")
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def show_about_dialog(self):
        QMessageBox.about(self, "About NeuroFlow",
                          "NeuroFlow v1.0\n\n"
                          "Developed by Rüzgar Öztürk with love\n"
                          "Powered by MNE-Python & PyQt6")

    def on_save_clean_data(self):
        if not self.worker.raw:
            QMessageBox.warning(self, "No Data", "Please load a dataset first.")
            return
            
        filename, _ = QFileDialog.getSaveFileName(self, "Save Clean Data", "", "MNE FIF (*.fif)")
        if filename:
            self.request_save_data.emit(filename)

    def on_take_screenshot(self):
        screen = QApplication.primaryScreen()
        if not screen:
            self.log_status("Error: No screen detected.")
            return
            
        screenshot = screen.grabWindow(self.winId())
        
        filename, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", "neuroflow_screenshot.png", "PNG Files (*.png);;All Files (*)")
        if filename:
            screenshot.save(filename)
            self.log_status(f"Screenshot saved to {filename}")

    def on_save_finished(self, filename):
        QMessageBox.information(self, "Save Successful", f"Data saved to:\n{filename}")

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
        QToolBox::tab {
            background-color: #383838;
            border: 1px solid #444;
            color: #f0f0f0;
            font-weight: bold;
            padding: 5px;
            border-radius: 4px;
        }
        QToolBox::tab:selected {
            background-color: #444444;
            color: #007acc;
            border-bottom: 2px solid #007acc;
        }
        """
        self.setStyleSheet(qss)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        sidebar.setFixedWidth(350)
        sidebar.setStyleSheet("background-color: #252526; border-radius: 8px;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(10)

        # Title
        title_label = QLabel("NeuroFlow")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #007acc; margin-bottom: 5px;")
        sidebar_layout.addWidget(title_label)
        
        # ToolBox Setup
        self.toolbox = QToolBox()
        
        # --- PAGE 1: Data & Preprocessing ---
        page_data = QWidget()
        layout_data = QVBoxLayout(page_data)
        layout_data.setSpacing(15)
        layout_data.setContentsMargins(10, 15, 10, 10)
        
        layout_data.setContentsMargins(10, 15, 10, 10)
        
        gb_d = QGroupBox("Dataset")
        l_d = QVBoxLayout()
        l_d.setSpacing(8)
        self.btn_load = QPushButton("Load EEG Data")
        self.btn_load.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_load.clicked.connect(self.browse_file)
        
        self.btn_sensors = QPushButton("📍 Check Sensors")
        self.btn_sensors.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sensors.setEnabled(False)
        self.btn_sensors.clicked.connect(self.check_sensors)
        
        self.btn_dataset_info = QPushButton("ℹ️ Dataset Info")
        self.btn_dataset_info.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dataset_info.setEnabled(False)
        self.btn_dataset_info.clicked.connect(self.show_dataset_info)
        self.btn_dataset_info.setToolTip("View dataset metadata and event statistics")

        l_d.addWidget(self.btn_load)
        l_d.addWidget(self.btn_sensors)
        l_d.addWidget(self.btn_dataset_info)
        gb_d.setLayout(l_d)
        layout_data.addWidget(gb_d)
        
        gb_p = QGroupBox("Signal Pipeline")
        l_p = QVBoxLayout()
        l_p.setSpacing(8)
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("HP (Hz):"))
        self.input_hp = QLineEdit("1.0")
        h_layout.addWidget(self.input_hp)
        l_p.addLayout(h_layout)

        l_layout = QHBoxLayout()
        l_layout.addWidget(QLabel("LP (Hz):"))
        self.input_lp = QLineEdit("40.0")
        l_layout.addWidget(self.input_lp)
        l_p.addLayout(l_layout)

        n_layout = QHBoxLayout()
        n_layout.addWidget(QLabel("Notch:"))
        self.input_notch = QLineEdit("50.0")
        n_layout.addWidget(self.input_notch)
        l_p.addLayout(n_layout)
        
        self.btn_run = QPushButton("Run Pipeline")
        self.btn_run.setStyleSheet("background-color: #007acc; font-weight: bold;")
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.clicked.connect(self.launch_pipeline)
        self.btn_run.setEnabled(False)
        l_p.addWidget(self.btn_run)
        gb_p.setLayout(l_p)
        layout_data.addWidget(gb_p)
        
        layout_data.addStretch() # Push up
        self.toolbox.addItem(page_data, "📡 Data & Preprocessing")
        
        # --- PAGE 2: Artifact Removal (ICA) ---
        page_ica = QWidget()
        layout_ica = QVBoxLayout(page_ica)
        layout_ica.setSpacing(15)
        layout_ica.setContentsMargins(10, 15, 10, 10)
        
        gb_ica_inner = QGroupBox("Independent Component Analysis")
        l_ica = QVBoxLayout()
        l_ica.setSpacing(10)
        
        self.btn_calc_ica = QPushButton("1. Calculate ICA")
        self.btn_calc_ica.clicked.connect(self.run_ica_click)
        self.btn_calc_ica.setEnabled(False)
        
        l_exclude = QLabel("Exclude Components (IDs):")
        self.input_ica_exclude = QLineEdit()
        self.input_ica_exclude.setPlaceholderText("e.g. 0, 2 (comma separated)")
        
        self.btn_apply_ica = QPushButton("2. Apply ICA")
        self.btn_apply_ica.clicked.connect(self.apply_ica_click)
        self.btn_apply_ica.setEnabled(False)
        
        l_ica.addWidget(self.btn_calc_ica)
        l_ica.addWidget(l_exclude)
        l_ica.addWidget(self.input_ica_exclude)
        l_ica.addWidget(self.btn_apply_ica)
        gb_ica_inner.setLayout(l_ica)
        
        layout_ica.addWidget(gb_ica_inner)
        layout_ica.addStretch()
        self.toolbox.addItem(page_ica, "👁️ Artifact Removal (ICA)")
        
        # --- PAGE 3: ERP ANALYSIS ---
        page_erp = QWidget()
        layout_erp = QVBoxLayout(page_erp)
        layout_erp.setSpacing(15)
        layout_erp.setContentsMargins(10, 15, 10, 10)
        
        gb_erp_inner = QGroupBox("Event-Related Potentials")
        l_erp = QVBoxLayout()
        l_erp.setSpacing(10)
        
        l_erp.addWidget(QLabel("Trigger Event:"))
        self.combo_events = QComboBox()
        l_erp.addWidget(self.combo_events)
        
        t_row = QHBoxLayout()
        self.spin_tmin = QDoubleSpinBox()
        self.spin_tmin.setRange(-5, 5); self.spin_tmin.setValue(-0.2)
        self.spin_tmax = QDoubleSpinBox()
        self.spin_tmax.setRange(-5, 5); self.spin_tmax.setValue(0.5)
        t_row.addWidget(QLabel("tmin:")); t_row.addWidget(self.spin_tmin)
        t_row.addWidget(QLabel("tmax:")); t_row.addWidget(self.spin_tmax)
        l_erp.addLayout(t_row)

        # Manual epoch inspection button (Gold Standard QC)
        self.btn_inspect_epochs = QPushButton("👁️ Inspect & Reject Epochs")
        self.btn_inspect_epochs.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_inspect_epochs.clicked.connect(self.inspect_epochs_click)
        self.btn_inspect_epochs.setEnabled(False)
        self.btn_inspect_epochs.setToolTip("Visually inspect epochs and manually reject artifacts")
        l_erp.addWidget(self.btn_inspect_epochs)

        self.btn_erp = QPushButton("Compute & Plot ERP")
        self.btn_erp.clicked.connect(self.compute_erp_click)
        self.btn_erp.setEnabled(False)
        l_erp.addWidget(self.btn_erp)
        
        gb_erp_inner.setLayout(l_erp)
        layout_erp.addWidget(gb_erp_inner)
        layout_erp.addStretch()
        self.toolbox.addItem(page_erp, "⚡ ERP Analysis")
        
        # --- PAGE 4: ADVANCED ANALYSIS ---
        page_adv = QWidget()
        layout_adv = QVBoxLayout(page_adv)
        layout_adv.setSpacing(15)
        layout_adv.setContentsMargins(10, 15, 10, 10)
        
        gb_tfr = QGroupBox("Time-Frequency (TFR)")
        l_tfr = QVBoxLayout()
        l_tfr.setSpacing(8)
        
        l_tfr.addWidget(QLabel("Channel:"))
        self.combo_channels = QComboBox()
        l_tfr.addWidget(self.combo_channels)
        
        f_row = QHBoxLayout()
        self.spin_tfr_l = QDoubleSpinBox(); self.spin_tfr_l.setValue(4.0)
        self.spin_tfr_h = QDoubleSpinBox(); self.spin_tfr_h.setValue(30.0)
        f_row.addWidget(QLabel("Freqs:")); f_row.addWidget(self.spin_tfr_l)
        f_row.addWidget(QLabel("-")); f_row.addWidget(self.spin_tfr_h)
        l_tfr.addLayout(f_row)
        
        self.btn_tfr = QPushButton("Compute TFR")
        self.btn_tfr.clicked.connect(self.compute_tfr_click)
        self.btn_tfr.setEnabled(False)
        l_tfr.addWidget(self.btn_tfr)
        gb_tfr.setLayout(l_tfr)
        layout_adv.addWidget(gb_tfr)
        
        gb_conn = QGroupBox("Connectivity (wPLI)")
        l_conn = QVBoxLayout()
        self.btn_conn = QPushButton("Alpha Band (8-12Hz)")
        self.btn_conn.clicked.connect(self.compute_connectivity_click)
        self.btn_conn.setEnabled(False)
        l_conn.addWidget(self.btn_conn)
        gb_conn.setLayout(l_conn)
        layout_adv.addWidget(gb_conn)
        
        layout_adv.addStretch()
        self.toolbox.addItem(page_adv, "🧠 Advanced Analysis")

        # Add ToolBox to sidebar layout
        sidebar_layout.addWidget(self.toolbox)

        # 3. Logs
        sidebar_layout.addWidget(QLabel("Status Log:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        # self.log_area.setFixedHeight(200) # Remove fixed height to let it fill available space if needed, or keep small
        self.log_area.setMinimumHeight(150) # Use min height instead
        sidebar_layout.addWidget(self.log_area)

        main_layout.addWidget(sidebar)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: 0; }")
        
        self.tab_signal = QWidget()
        tab1_layout = QVBoxLayout(self.tab_signal)
        tab1_layout.setContentsMargins(0,0,0,0)
        
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        tab1_layout.addWidget(self.canvas)
        
        # Initial plot placeholder
        self.canvas.axes.text(0.5, 0.5, 'NeuroFlow Ready\nLoad BrainVision (.vhdr) or others\nto begin analysis', 
                              color='gray', ha='center', va='center', fontsize=12)
        self.canvas.draw()
        
        self.tabs.addTab(self.tab_signal, "Signal Monitor")
        
        self.tab_advanced = QWidget()
        self.tab2_layout = QVBoxLayout(self.tab_advanced)
        self.tab2_layout.setContentsMargins(0,0,0,0)
        
        self.canvas_advanced = MplCanvas(self, width=5, height=4, dpi=100)
        self.tab2_layout.addWidget(self.canvas_advanced)
        
        self.tabs.addTab(self.tab_advanced, "Advanced Analysis")

        main_layout.addWidget(self.tabs)
        
        # Stretch factors
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 4)

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
        self.btn_dataset_info.setEnabled(True)
        self.btn_calc_ica.setEnabled(True) # Enable ICA
        self.btn_apply_ica.setEnabled(True)

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

        dialog = DatasetInfoDialog(self.raw_data, parent=self)
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
            self.log_status(f"Created {n_epochs_before} epochs. Opening interactive viewer...")
            self.log_status("Click epochs to mark as bad. Close window when done.")

            # Open the interactive epoch viewer (blocks until window closes)
            # scalings='auto' adapts to data, n_epochs=10 shows 10 at a time
            n_channels = min(30, len(self.epochs.ch_names))
            self.epochs.plot(
                block=True,
                scalings='auto',
                n_epochs=10,
                n_channels=n_channels,
                title=f"Epoch Inspection: {event_name} (Click to reject)"
            )

            # After the plot window is closed, drop the marked bad epochs
            self.epochs.drop_bad()

            n_epochs_after = len(self.epochs)
            n_rejected = n_epochs_before - n_epochs_after

            self.epochs_inspected = True
            self.log_status(
                f"Manual inspection complete. Removed {n_rejected} epochs. "
                f"Remaining: {n_epochs_after}."
            )

            if n_epochs_after == 0:
                self.show_error("All epochs were rejected! Cannot compute ERP.")
                self.btn_erp.setEnabled(False)
            else:
                self.btn_erp.setEnabled(True)
                self.log_status("Ready to compute ERP with cleaned epochs.")

        except Exception as e:
            self.show_error(f"Epoch inspection error: {str(e)}")
            import traceback
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
                self.log_status(f"ERP Computed from inspected epochs. Averaged {len(self.epochs)} epochs.")
                self.handle_erp_ready(evoked)
            except Exception as e:
                self.show_error(f"ERP Error: {str(e)}")
                import traceback
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
        if not ch: return
        l_freq = self.spin_tfr_l.value()
        h_freq = self.spin_tfr_h.value()
        self.request_compute_tfr.emit(ch, l_freq, h_freq)
        self.tabs.setCurrentWidget(self.tab_advanced)

    def plot_tfr(self, tfr_power):
        """Plots TFR Heatmap on the Advanced Canvas."""
        self.canvas_advanced.axes.clear()
        self.canvas_advanced.axes.set_facecolor('black')
        
        try:
            data = tfr_power.data[0] # Single channel
            times = tfr_power.times
            freqs = tfr_power.freqs
            
            # Simple Spectrogram Plot
            # Gouraud shading for smoothness
            im = self.canvas_advanced.axes.pcolormesh(times, freqs, data, shading='gouraud', cmap='viridis')
            
            self.canvas_advanced.axes.set_title(f"Time-Frequency: {tfr_power.ch_names[0]}", color='white')
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
                con_data = con_data[:, :, 0] # Squeeze freq dimension if 1
            
            node_names = self.raw_data.ch_names
            
            # Create Figure with show=False to prevent immediate popup
            # plot_connectivity_circle returns fig, ax
            fig, ax = plot_connectivity_circle(con_data, node_names, n_lines=50, 
                                             fontsize_names=8, title='Alpha Band Connectivity (wPLI)',
                                             show=False)
            
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
