"""
EEG Processing Worker Module

Contains the EEGWorker class responsible for all MNE-Python processing tasks
running on a separate thread to keep the GUI responsive.
"""

import os
import traceback
import logging

import mne
import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

# Optional mne-connectivity import
try:
    import mne_connectivity
    HAS_CONNECTIVITY = True
except ImportError:
    HAS_CONNECTIVITY = False

logger = logging.getLogger("NeuroFlow")


class EEGWorker(QObject):
    """
    Worker class for handling heavy MNE-Python analysis tasks on a separate thread.
    This ensures the GUI remains responsive during data loading and signal processing.
    """
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    log_message = pyqtSignal(str)
    data_loaded = pyqtSignal(object)  # Emits the MNE Raw object
    psd_ready = pyqtSignal(object, object, str)  # Emits (freqs, psd, filter_info_str)
    ica_ready = pyqtSignal(object)  # Emits the fitted ICA object for plotting on Main Thread
    events_loaded = pyqtSignal(dict)  # Emits event_id mapping
    erp_ready = pyqtSignal(object)  # Emits evoked object
    tfr_ready = pyqtSignal(object)  # Emits TFR object (AverageTFR)
    connectivity_ready = pyqtSignal(object)  # Emits connectivity object (figure or data)
    save_finished = pyqtSignal(str)  # Emits filename when save is complete

    def __init__(self):
        super().__init__()
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
                self.error_occurred.emit(
                    f"Unsupported format: {filename}. Please use .vhdr, .fif, or .edf"
                )
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

            self.log_message.emit(
                f"Successfully loaded {len(self.raw.ch_names)} channels, "
                f"{self.raw.times[-1]:.2f}s duration."
            )
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
                result_raw.notch_filter(
                    freqs=np.array([notch_freq]), fir_design='firwin', verbose=False
                )
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
            self.ica = mne.preprocessing.ICA(
                n_components=15, method='fastica', random_state=97, max_iter='auto'
            )

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
                excludes = [
                    int(x.strip()) for x in exclude_str.split(',') if x.strip().isdigit()
                ]

            self.log_message.emit(f"Applying ICA exclusion: {excludes}")
            self.ica.exclude = excludes

            clean_raw = self.raw.copy()
            self.ica.apply(clean_raw)

            self.log_message.emit("Computing PSD on ICA-cleaned data...")
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

            epochs = mne.Epochs(
                self.raw, self.events, event_id=specific_event_id,
                tmin=tmin, tmax=tmax, baseline=(tmin, 0), preload=True, verbose=False
            )

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
        Uses fixed-length epochs from continuous data for robust computation.
        """
        if self.raw is None:
            self.error_occurred.emit("No data loaded.")
            return

        self.log_message.emit(
            f"Computing TFR for channel {ch_name} (Freqs: {l_freq}-{h_freq}Hz)..."
        )

        try:
            # Verify channel exists
            if ch_name not in self.raw.ch_names:
                self.error_occurred.emit(f"Channel '{ch_name}' not found in data.")
                return

            freqs = np.arange(l_freq, h_freq + 1, 1.0)
            n_cycles = freqs / n_cycles_div

            # Create a copy of raw with only the selected channel for efficiency
            raw_pick = self.raw.copy().pick([ch_name])

            # Use fixed-length epochs for robust TFR computation
            # This avoids issues with event-based epoching
            epoch_duration = 2.0  # 2-second epochs
            epochs = mne.make_fixed_length_epochs(
                raw_pick,
                duration=epoch_duration,
                preload=True,
                verbose=False
            )

            if len(epochs) == 0:
                self.error_occurred.emit(
                    f"TFR Error: Could not create epochs for channel {ch_name}."
                )
                return

            self.log_message.emit(f"Created {len(epochs)} epochs for TFR analysis...")

            # Compute TFR using modern API
            power = epochs.compute_tfr(
                method='morlet',
                freqs=freqs,
                n_cycles=n_cycles,
                return_itc=False,
                average=True,
                verbose=False
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
            self.error_occurred.emit(
                "mne-connectivity not installed. pip install mne-connectivity"
            )
            return

        self.log_message.emit("Computing Alpha Band Connectivity (wPLI)...")

        try:
            tmin, tmax = 0, 4.0

            if self.events is not None:
                epochs = mne.Epochs(
                    self.raw, self.events, event_id=None, tmin=tmin, tmax=tmax,
                    baseline=None, preload=True, verbose=False,
                    event_repeated='drop'
                )
            else:
                epochs = mne.make_fixed_length_epochs(
                    self.raw, duration=4.0, preload=True, verbose=False
                )

            fmin, fmax = 8.0, 12.0
            sfreq = self.raw.info['sfreq']

            con = mne_connectivity.spectral_connectivity_epochs(
                epochs, method='wpli', mode='multitaper', sfreq=sfreq,
                fmin=fmin, fmax=fmax, faverage=True, mt_adaptive=True,
                n_jobs=1, verbose=False
            )

            self.connectivity_ready.emit(con)
            self.finished.emit()
            self.log_message.emit("Connectivity Computation Complete.")

        except Exception as e:
            self.error_occurred.emit(f"Connectivity Error: {str(e)}")
            traceback.print_exc()
