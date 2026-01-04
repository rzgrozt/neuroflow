
import sys
import os
import numpy as np
import mne
from PyQt6.QtCore import QObject, pyqtSlot

# Adjust path to import neuroflow properly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from neuroflow import AnalysisWorker

def create_dummy_data():
    """Creates a dummy MNE Raw object with events."""
    sfreq = 100
    times = np.arange(0, 10, 1/sfreq) # 10 seconds
    n_channels = 5
    data = np.random.randn(n_channels, len(times)) * 1e-6
    
    # Add some sine waves for TFR check (10Hz)
    data[0, :] += np.sin(2 * np.pi * 10 * times) * 1e-5
    
    info = mne.create_info(ch_names=[f'EEG {i}' for i in range(n_channels)], 
                           sfreq=sfreq, ch_types='eeg')
    raw = mne.io.RawArray(data, info)
    
    # Add dummy events
    events = np.array([
        [int(1.0*sfreq), 0, 1],
        [int(5.0*sfreq), 0, 1]
    ])
    raw.set_annotations(mne.annotations_from_events(events, sfreq))
    
    return raw

# Mock Listener to catch signals
class SignalListener(QObject):
    def __init__(self, worker):
        super().__init__()
        self.tfr_received = False
        self.conn_received = False
        self.worker = worker
        self.worker.tfr_ready.connect(self.on_tfr)
        self.worker.connectivity_ready.connect(self.on_conn)
        self.worker.error_occurred.connect(self.on_error)
        self.worker.log_message.connect(print)

    @pyqtSlot(object)
    def on_tfr(self, tfr):
        print("SUCCESS: TFR Received!")
        self.tfr_received = True

    @pyqtSlot(object)
    def on_conn(self, con):
        print("SUCCESS: Connectivity Received!")
        self.conn_received = True

    @pyqtSlot(str)
    def on_error(self, msg):
        print(f"ERROR SIGNAL: {msg}")

def run_tests():
    print("--- Starting Backend Verification ---")
    
    # 1. Setup Worker
    worker = AnalysisWorker()
    listener = SignalListener(worker)
    
    # 2. Load Dummy Data
    print("Loading Dummy Data...")
    raw = create_dummy_data()
    worker.raw = raw
    # Manually extract events as load_data would
    events, event_id = mne.events_from_annotations(raw, verbose=False)
    worker.events = events
    worker.event_id = event_id
    
    # 3. Test TFR
    print("\n[TEST] Computing TFR...")
    try:
        worker.compute_tfr("EEG 0", 4.0, 30.0)
    except Exception as e:
        print(f"Exception calling compute_tfr: {e}")

    # 4. Test Connectivity
    print("\n[TEST] Computing Connectivity...")
    try:
        worker.compute_connectivity()
    except Exception as e:
        print(f"Exception calling compute_connectivity: {e}")

    # Check results
    if listener.tfr_received and listener.conn_received:
        print("\n--- PASSED: All signals received. ---")
    else:
        print("\n--- FAILED: Missing signals. ---")
        if not listener.tfr_received: print("- TFR Missing")
        if not listener.conn_received: print("- Connectivity Missing")

if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv) # Needed for signals
    run_tests()
    # No app.exec() needed as we call slots directly and they execute synchronously in this single-thread test setup?
    # MNE signals might process immediately if direct connection.
