"""EEG Processing Worker - Handles MNE-Python tasks on a separate thread."""

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
    """Worker for MNE-Python analysis tasks on a separate thread."""
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
    interpolation_done = pyqtSignal(list)  # Emits list of interpolated channels
    report_ready = pyqtSignal(str)  # Emits file path of generated report
    data_updated = pyqtSignal(object, str)  # Emits (raw, info_str) after any pipeline operation

    def __init__(self):
        super().__init__()
        self.raw = None  # Holds the MNE Raw object (working copy)
        self.raw_original = None  # Holds the original unmodified Raw object for comparison
        self.ica = None  # Holds the fitted ICA object
        self.events = None
        self.event_id = None
        self.epochs = None  # Holds the created Epochs object for analysis

    @pyqtSlot(str)
    def load_data(self, file_path: str):
        """Load EEG data from .vhdr, .fif, or .edf files."""
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

            # Store a copy of the original data for comparison
            self.raw_original = self.raw.copy()
            self.log_message.emit("Original data backup created for comparison.")

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
        """Run preprocessing pipeline: Filtering on working copy (cumulative)."""
        if self.raw is None:
            self.error_occurred.emit("No data loaded. Please load a dataset first.")
            return

        self.log_message.emit("Starting preprocessing pipeline...")

        try:
            filter_info = []

            if l_freq > 0 or h_freq > 0:
                lf = l_freq if l_freq > 0 else None
                hf = h_freq if h_freq > 0 else None

                self.log_message.emit(f"Applying Bandpass Filter: HP={lf} Hz, LP={hf} Hz")
                self.raw.filter(l_freq=lf, h_freq=hf, fir_design='firwin', verbose=False)
                filter_info.append(f"Bandpass: {lf}-{hf} Hz")

            if notch_freq > 0:
                self.log_message.emit(f"Applying Notch Filter at {notch_freq} Hz")
                self.raw.notch_filter(
                    freqs=np.array([notch_freq]), fir_design='firwin', verbose=False
                )
                filter_info.append(f"Notch: {notch_freq} Hz")

            if not filter_info:
                filter_info.append("Raw Signal")

            filter_str = " | ".join(filter_info)
            self.log_message.emit(f"Pipeline completed: {filter_str}")
            
            # Emit data_updated signal with current processed data
            self.data_updated.emit(self.raw, filter_str)
            self.finished.emit()

        except Exception as e:
            self.error_occurred.emit(f"Pipeline Error: {str(e)}")
            traceback.print_exc()

    @pyqtSlot()
    def run_ica(self):
        """Fit ICA on the current data."""
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
        """Apply ICA with excluded components to the working copy (cumulative)."""
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

            # Apply ICA directly to self.raw (cumulative, destructive on working copy)
            self.ica.apply(self.raw)

            self.log_message.emit("ICA applied to working data. Artifacts removed.")
            
            # Emit data_updated signal with current processed data
            self.data_updated.emit(self.raw, f"ICA Cleaned | Excl: {excludes}")
            self.finished.emit()

        except ValueError:
            self.error_occurred.emit("Invalid format for components. Use '0, 1, 2'")
        except Exception as e:
            self.error_occurred.emit(f"ICA Apply Error: {str(e)}")
            traceback.print_exc()

    @pyqtSlot(str, float, float, bool)
    def create_epochs(self, event_name: str, tmin: float, tmax: float, apply_baseline: bool = True):
        """Create epochs from raw data around event triggers.

        This method creates epochs and stores them in self.epochs for use by
        analysis methods (ERP, TFR, Connectivity).

        Args:
            event_name: Name of the event to epoch around (or 'All Events').
            tmin: Start time before event (seconds).
            tmax: End time after event (seconds).
            apply_baseline: If True, apply baseline correction from tmin to 0.

        Returns:
            Emits log_message with summary of created epochs.
        """
        if self.raw is None:
            self.error_occurred.emit("No data loaded.")
            return

        if self.events is None or self.event_id is None:
            self.error_occurred.emit("No events found in this dataset.")
            return

        baseline_info = f"baseline=({tmin}, 0)" if apply_baseline else "no baseline"
        self.log_message.emit(
            f"Creating epochs for: {event_name} (tmin={tmin}, tmax={tmax}, {baseline_info})..."
        )

        try:
            # Determine event_id based on selection
            if event_name == "All Events":
                specific_event_id = self.event_id
            else:
                if event_name not in self.event_id:
                    self.error_occurred.emit(f"Event '{event_name}' not found.")
                    return
                specific_event_id = {event_name: self.event_id[event_name]}

            # Create epochs without baseline initially
            epochs = mne.Epochs(
                self.raw, self.events, event_id=specific_event_id,
                tmin=tmin, tmax=tmax, baseline=None, preload=True, verbose=False
            )

            n_total = len(epochs)
            n_dropped = len(epochs.drop_log) - n_total

            # Apply baseline correction if requested
            if apply_baseline:
                epochs.apply_baseline((tmin, 0))
                self.log_message.emit(f"Applied baseline correction: ({tmin}, 0)")

            # Store epochs for later use
            self.epochs = epochs

            summary = f"Created {n_total} epochs."
            if n_dropped > 0:
                summary += f" {n_dropped} dropped due to artifacts."

            self.log_message.emit(summary)
            self.finished.emit()

        except Exception as e:
            self.error_occurred.emit(f"Epoch Creation Error: {str(e)}")
            traceback.print_exc()

    @pyqtSlot()
    def compute_erp(self):
        """Compute ERP by averaging pre-existing epochs.

        Requires epochs to be created first using create_epochs().
        """
        if self.epochs is None:
            self.error_occurred.emit(
                "No epochs available. Please create epochs first using the Segmentation section."
            )
            return

        self.log_message.emit(f"Computing ERP from {len(self.epochs)} epochs...")

        try:
            evoked = self.epochs.average()

            self.log_message.emit(f"ERP Computed. Averaged {len(self.epochs)} epochs.")
            self.erp_ready.emit(evoked)
            self.finished.emit()

        except Exception as e:
            self.error_occurred.emit(f"ERP Error: {str(e)}")
            traceback.print_exc()

    @pyqtSlot(str, float, float, int, str)
    def compute_tfr(self, ch_name: str, l_freq: float, h_freq: float,
                    n_cycles_base: int = 2, baseline_mode: str = 'percent'):
        """Compute Time-Frequency Representation using Morlet wavelets.

        Requires epochs to be created first using create_epochs().

        Args:
            ch_name: Channel name to analyze.
            l_freq: Lower frequency bound (Hz).
            h_freq: Upper frequency bound (Hz).
            n_cycles_base: Divisor for frequency-adaptive n_cycles (n_cycles = freqs / n_cycles_base).
                          Higher values = fewer cycles = better temporal resolution.
                          Lower values = more cycles = better frequency resolution.
            baseline_mode: Baseline correction mode. Options:
                          'percent' - Express power as percent change from baseline
                          'logratio' - Express power as log ratio of baseline
                          'zscore' - Express power as z-score relative to baseline
                          'mean' - Subtract mean baseline power
                          'none' - No baseline correction
        """
        if self.epochs is None:
            self.error_occurred.emit(
                "No epochs available. Please create epochs first using the Segmentation section."
            )
            return

        self.log_message.emit(
            f"Computing TFR for channel {ch_name} (Freqs: {l_freq}-{h_freq}Hz, "
            f"n_cycles=freqs/{n_cycles_base}, baseline={baseline_mode})..."
        )

        try:
            # Pick channel from epochs
            if ch_name not in self.epochs.ch_names:
                self.error_occurred.emit(f"Channel '{ch_name}' not found in epochs.")
                return

            epochs_pick = self.epochs.copy().pick([ch_name])

            freqs = np.arange(l_freq, h_freq + 1, 1.0)
            n_cycles = freqs / n_cycles_base

            self.log_message.emit(f"Using {len(self.epochs)} epochs for TFR analysis...")

            power = epochs_pick.compute_tfr(
                method='morlet',
                freqs=freqs,
                n_cycles=n_cycles,
                return_itc=False,
                average=True,
                verbose=False
            )

            # Apply baseline correction if requested
            if baseline_mode != 'none':
                # Use pre-stimulus period as baseline
                tmin = self.epochs.tmin
                baseline = (tmin, 0)
                power.apply_baseline(baseline, mode=baseline_mode)
                self.log_message.emit(f"Applied baseline correction: mode='{baseline_mode}'")

            self.tfr_ready.emit(power)
            self.finished.emit()

        except Exception as e:
            self.error_occurred.emit(f"TFR Error: {str(e)}")
            traceback.print_exc()

    @pyqtSlot(str)
    def save_data(self, filename: str):
        """Save the current raw object to a .fif file."""
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

    @pyqtSlot(str)
    def save_epochs(self, filename: str):
        """Save the current epochs object to a .fif file."""
        if self.epochs is None:
            self.error_occurred.emit("No epochs to save. Please create epochs first.")
            return

        self.log_message.emit(f"Saving epochs to {filename}...")
        try:
            if not filename.endswith('-epo.fif'):
                if filename.endswith('.fif'):
                    filename = filename[:-4] + '-epo.fif'
                else:
                    filename += '-epo.fif'

            self.epochs.save(filename, overwrite=True)
            self.save_finished.emit(filename)
            self.log_message.emit(f"Epochs saved successfully to {filename}")

        except Exception as e:
            self.error_occurred.emit(f"Save Epochs Error: {str(e)}")
            traceback.print_exc()

    @pyqtSlot()
    def compute_connectivity(self):
        """Compute Functional Connectivity using wPLI in Alpha Band (8-12Hz).

        Requires epochs to be created first using create_epochs().
        """
        if self.epochs is None:
            self.error_occurred.emit(
                "No epochs available. Please create epochs first using the Segmentation section."
            )
            return

        if not HAS_CONNECTIVITY:
            self.error_occurred.emit(
                "mne-connectivity not installed. pip install mne-connectivity"
            )
            return

        self.log_message.emit(f"Computing Alpha Band Connectivity (wPLI) on {len(self.epochs)} epochs...")

        try:
            fmin, fmax = 8.0, 12.0
            sfreq = self.epochs.info['sfreq']

            con = mne_connectivity.spectral_connectivity_epochs(
                self.epochs, method='wpli', mode='multitaper', sfreq=sfreq,
                fmin=fmin, fmax=fmax, faverage=True, mt_adaptive=True,
                n_jobs=1, verbose=False
            )

            self.connectivity_ready.emit(con)
            self.finished.emit()
            self.log_message.emit("Connectivity Computation Complete.")

        except Exception as e:
            self.error_occurred.emit(f"Connectivity Error: {str(e)}")
            traceback.print_exc()


    @pyqtSlot(list)
    def interpolate_bads(self, bad_channels: list):
        """Interpolate bad channels using spherical spline interpolation.
        
        Args:
            bad_channels: List of channel names to mark as bad and interpolate.
        """
        if self.raw is None:
            self.error_occurred.emit("No data loaded. Cannot interpolate channels.")
            return

        if not bad_channels:
            self.log_message.emit("No channels selected for interpolation.")
            self.finished.emit()
            return

        self.log_message.emit(f"Interpolating bad channels: {', '.join(bad_channels)}")

        try:
            # Check if montage is set (required for interpolation)
            if self.raw.get_montage() is None:
                self.error_occurred.emit(
                    "Montage not set. Interpolation requires sensor positions. "
                    "Please load data with a montage or set one manually."
                )
                return

            # Validate that all specified channels exist
            invalid_channels = [ch for ch in bad_channels if ch not in self.raw.ch_names]
            if invalid_channels:
                self.error_occurred.emit(
                    f"Invalid channels: {', '.join(invalid_channels)}. "
                    "These channels do not exist in the dataset."
                )
                return

            # Mark channels as bad
            self.raw.info['bads'] = bad_channels
            self.log_message.emit(f"Marked {len(bad_channels)} channel(s) as bad.")

            # Perform interpolation on working copy (cumulative)
            self.raw.interpolate_bads(reset_bads=True, verbose=True)

            self.log_message.emit(
                f"Successfully interpolated channels: {', '.join(bad_channels)}"
            )
            
            # Emit data_updated signal with current processed data
            self.data_updated.emit(self.raw, f"Interpolated: {', '.join(bad_channels)}")
            self.interpolation_done.emit(bad_channels)
            self.finished.emit()

        except Exception as e:
            self.error_occurred.emit(f"Interpolation Error: {str(e)}")
            traceback.print_exc()


    @pyqtSlot(object, object, object, object, list, dict)
    def generate_report(
        self,
        raw: object,
        ica: object,
        epochs: object,
        evoked: object,
        history_log: list,
        segmentation_params: dict = None,
    ):
        """Generate an HTML analysis report using mne.Report.

        Args:
            raw: The MNE Raw object (cleaned/processed).
            ica: The fitted ICA object (or None).
            epochs: The Epochs object (or None).
            evoked: The Evoked object (or None).
            history_log: List of dicts containing pipeline history.
            segmentation_params: Dict containing tmin, tmax, event_name, baseline_status.
        """
        if raw is None:
            self.error_occurred.emit("No data loaded. Cannot generate report.")
            return

        self.log_message.emit("Generating analysis report...")

        try:
            report = mne.Report(title="NeuroFlow Analysis Report")

            # Add Raw data with PSD
            self.log_message.emit("Adding raw data to report...")
            report.add_raw(raw, title="Raw Data (Cleaned)", psd=True)

            # Add ICA if available
            if ica is not None:
                self.log_message.emit("Adding ICA components to report...")
                report.add_ica(ica, title="ICA Artifact Removal", inst=raw)

            # Add Segmentation Details section
            if segmentation_params:
                self.log_message.emit("Adding segmentation details to report...")
                event_name = segmentation_params.get('event_name', 'N/A')
                tmin = segmentation_params.get('tmin', 'N/A')
                tmax = segmentation_params.get('tmax', 'N/A')
                baseline_status = segmentation_params.get('baseline_status', False)
                baseline_text = "Applied" if baseline_status else "Not Applied"
                
                # Get epoch counts
                total_epochs = 0
                dropped_epochs = 0
                if epochs is not None:
                    total_epochs = len(epochs)
                    drop_log = epochs.drop_log
                    dropped_epochs = sum(1 for log in drop_log if len(log) > 0)
                
                segmentation_html = f"""
                <div style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2>Segmentation Details</h2>
                    <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
                        <tr style="background-color: #f2f2f2;">
                            <td style="padding: 12px; border: 1px solid #ddd;"><strong>Event Trigger</strong></td>
                            <td style="padding: 12px; border: 1px solid #ddd;">{event_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid #ddd;"><strong>Time Window</strong></td>
                            <td style="padding: 12px; border: 1px solid #ddd;">{tmin}s to {tmax}s</td>
                        </tr>
                        <tr style="background-color: #f2f2f2;">
                            <td style="padding: 12px; border: 1px solid #ddd;"><strong>Baseline Correction</strong></td>
                            <td style="padding: 12px; border: 1px solid #ddd;">{baseline_text}</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid #ddd;"><strong>Epoch Count</strong></td>
                            <td style="padding: 12px; border: 1px solid #ddd;">{total_epochs} (Dropped: {dropped_epochs})</td>
                        </tr>
                    </table>
                </div>
                """
                report.add_html(segmentation_html, title="Segmentation Details")

            # Add Epochs if available
            if epochs is not None:
                self.log_message.emit("Adding epochs to report...")
                report.add_epochs(epochs, title="Epochs Check")

            # Add Evoked/ERP if available
            if evoked is not None:
                self.log_message.emit("Adding ERP to report...")
                report.add_evokeds(evoked, titles=["ERP Response"])

            # Add Pipeline History as HTML
            if history_log:
                self.log_message.emit("Adding pipeline history to report...")
                history_html = self._format_history_html(history_log)
                report.add_html(history_html, title="Pipeline History")

            # Save the report
            report_path = "neuroflow_report.html"
            self.log_message.emit(f"Saving report to {report_path}...")
            report.save(report_path, overwrite=True, open_browser=False)

            self.log_message.emit(f"Report generated successfully: {report_path}")
            self.report_ready.emit(report_path)
            self.finished.emit()

        except Exception as e:
            self.error_occurred.emit(f"Report Generation Error: {str(e)}")
            traceback.print_exc()

    def _format_history_html(self, history_log: list) -> str:
        """Convert pipeline history to formatted HTML.

        Args:
            history_log: List of dicts with pipeline step information.

        Returns:
            Formatted HTML string.
        """
        html_parts = [
            "<div style='font-family: Arial, sans-serif; padding: 20px;'>",
            "<h2 style='color: #2c3e50;'>Analysis Pipeline History</h2>",
            "<table style='width: 100%; border-collapse: collapse; margin-top: 10px;'>",
            "<thead>",
            "<tr style='background-color: #3498db; color: white;'>",
            "<th style='padding: 12px; text-align: left; border: 1px solid #ddd;'>Step</th>",
            "<th style='padding: 12px; text-align: left; border: 1px solid #ddd;'>Operation</th>",
            "<th style='padding: 12px; text-align: left; border: 1px solid #ddd;'>Parameters</th>",
            "<th style='padding: 12px; text-align: left; border: 1px solid #ddd;'>Timestamp</th>",
            "</tr>",
            "</thead>",
            "<tbody>",
        ]

        for idx, step in enumerate(history_log, 1):
            # Support both 'action' and 'operation' keys for backwards compatibility
            operation = step.get("action") or step.get("operation", "Unknown")
            # Support both 'params' and 'parameters' keys
            params = step.get("params") or step.get("parameters", {})
            timestamp = step.get("timestamp", "N/A")

            # Format parameters as readable string
            if isinstance(params, dict):
                params_str = ", ".join(f"{k}: {v}" for k, v in params.items()) if params else "N/A"
            else:
                params_str = str(params)

            row_color = "#f9f9f9" if idx % 2 == 0 else "#ffffff"
            html_parts.append(
                f"<tr style='background-color: {row_color};'>"
                f"<td style='padding: 10px; border: 1px solid #ddd;'>{idx}</td>"
                f"<td style='padding: 10px; border: 1px solid #ddd;'>{operation}</td>"
                f"<td style='padding: 10px; border: 1px solid #ddd;'>{params_str}</td>"
                f"<td style='padding: 10px; border: 1px solid #ddd;'>{timestamp}</td>"
                f"</tr>"
            )

        html_parts.extend([
            "</tbody>",
            "</table>",
            "<p style='margin-top: 20px; color: #7f8c8d; font-size: 12px;'>",
            "Generated by NeuroFlow - Professional EEG Analysis",
            "</p>",
            "</div>",
        ])

        return "\n".join(html_parts)
