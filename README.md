# NeuroFlow

**NeuroFlow** is a professional-grade desktop application for EEG signal analysis, built with Python. It leverages **MNE-Python** for neuroscience computations and **PyQt6** for a modern, responsive user interface.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

---

## Features

### Data Management

| Feature | Description |
|---------|-------------|
| **Multi-Format Support** | Load BrainVision (`.vhdr`), MNE-Python (`.fif`), and European Data Format (`.edf`) files |
| **Automatic Montage** | Detects missing channel locations and applies standard 10-20 montage |
| **Dataset Inspector** | View recording metadata, sampling rate, duration, and event statistics |
| **Sensor Visualization** | Interactive 2D topographic display of electrode positions |
| **Data Export** | Save processed data to `.fif` format for future analysis |

### Signal Processing

| Feature | Description |
|---------|-------------|
| **High-Pass Filter** | Remove slow drifts and DC offsets |
| **Low-Pass Filter** | Eliminate high-frequency noise |
| **Notch Filter** | Suppress power line noise (50/60 Hz) |
| **ICA Decomposition** | FastICA-based artifact identification and removal (EOG, ECG) |

### Analysis Tools

| Feature | Description |
|---------|-------------|
| **Power Spectral Density** | Real-time PSD computation using Welch's method |
| **Event-Related Potentials** | Automatic event extraction with averaged evoked responses |
| **Time-Frequency Analysis** | Morlet wavelet-based oscillatory power visualization |
| **Functional Connectivity** | Weighted Phase Lag Index (wPLI) for brain network analysis |

### Quality Control

| Feature | Description |
|---------|-------------|
| **Manual Epoch Inspection** | Interactive epoch viewer for artifact rejection |
| **Event Statistics** | Tabular view of event counts for data integrity verification |
| **Screenshot Export** | Capture analysis views for reports and documentation |

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| GUI Framework | PyQt6 |
| Signal Processing | MNE-Python |
| Connectivity Analysis | mne-connectivity |
| Numerical Computing | NumPy, SciPy |
| Visualization | Matplotlib |
| Concurrency | QThread Worker Pattern |

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/rzgrozt/neuroflow.git
cd neuroflow
```

**Create a virtual environment (recommended):**

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

**Install dependencies:**

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install mne mne-connectivity PyQt6 PyQt6-Qt6 PyQt6-sip matplotlib numpy scipy scikit-learn
```

---

## Usage

**Run the application:**

```bash
python main.py
```

### Workflow Overview

1. **Load Data** - Select your EEG file (`.vhdr`, `.fif`, or `.edf`)
2. **Verify Setup** - Check sensor positions and inspect dataset metadata
3. **Preprocess** - Apply bandpass and notch filters
4. **Remove Artifacts** - Run ICA to identify and exclude EOG/ECG components
5. **Inspect Epochs** - Manually reject bad epochs using the interactive viewer
6. **Analyze** - Compute ERPs, TFR, or connectivity measures

---

## Project Structure

```
neuroflow/
├── main.py                      # Application entry point
├── requirements.txt             # Python dependencies
├── README.md
└── app/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   └── workers.py           # EEGWorker: MNE processing on background thread
    └── ui/
        ├── __init__.py
        ├── canvas.py            # MplCanvas: Matplotlib-PyQt6 integration
        ├── dialogs.py           # DatasetInfoDialog, ConnectivityDialog, ERPViewer
        └── main_window.py       # MainWindow: Primary application interface
```

### Architecture

The application follows a separation of concerns pattern with multithreading:

- **`EEGWorker`** (Background Thread) - Handles all MNE I/O and heavy computations, communicates via Qt signals
- **`MainWindow`** (Main Thread) - Manages UI layout, user interactions, and plot updates
- **Dialogs** - Modular popup windows for specialized visualizations

---

## Screenshots

<img width="1283" height="899" alt="Main Interface" src="https://github.com/user-attachments/assets/a3105fac-5ff1-48ef-af2f-b0a99ef44839" />

<img width="1287" height="865" alt="ICA Analysis" src="https://github.com/user-attachments/assets/834bd9ad-9cc4-4a96-97ea-6108ba25eb33" />

<img width="807" height="925" alt="ERP Viewer" src="https://github.com/user-attachments/assets/050dfc96-c021-49e2-8429-1fd5f4cfc146" />

<img width="1302" height="874" alt="Connectivity Explorer" src="https://github.com/user-attachments/assets/9c667a99-0c87-4ba4-b40a-36335a70e7f2" />

---

## License

This project is open-source under the MIT License.
