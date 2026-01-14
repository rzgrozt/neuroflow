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
| **Channel Interpolation** | Repair bad channels using spherical spline interpolation |
| **ICA Decomposition** | FastICA-based artifact identification and removal (EOG, ECG) |

### Visualization

| Feature | Description |
|---------|-------------|
| **Clinical Time-Series View** | Stacked channel display with adjustable scale and duration |
| **Time Navigation** | Slider-based scrolling through recordings with real-time updates |
| **Original Data Overlay** | Compare processed vs. original data with transparency overlay |
| **Cumulative Pipeline** | Destructive editing on working copy preserves original for comparison |

### Analysis Tools

| Feature | Description |
|---------|-------------|
| **Power Spectral Density** | Real-time PSD computation using Welch's method with linear power display (μV²/Hz) |
| **Event-Related Potentials** | Automatic event extraction with configurable baseline correction (tmin to 0) |
| **Time-Frequency Analysis** | Morlet wavelet-based oscillatory power with adjustable n_cycles and baseline normalization modes (percent, logratio, zscore, mean) |
| **Functional Connectivity** | Weighted Phase Lag Index (wPLI) for brain network analysis |

### Quality Control

| Feature | Description |
|---------|-------------|
| **Manual Epoch Inspection** | Interactive epoch viewer for artifact rejection |
| **Event Statistics** | Tabular view of event counts for data integrity verification |
| **Screenshot Export** | Capture analysis views for reports and documentation |
| **Pipeline History** | Automatic logging of all preprocessing steps with timestamps for reproducibility |
| **HTML Report Generation** | Export complete analysis pipeline to a professional HTML report using MNE Report |

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
5. **Create Epochs** - Segment continuous data around event triggers with configurable time windows
6. **Inspect Epochs** - Manually reject bad epochs using the interactive viewer
7. **Analyze** - Compute ERPs, TFR, or connectivity measures using the created epochs

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

<img width="1299" height="887" alt="image" src="https://github.com/user-attachments/assets/b68bb39c-87c1-4b69-92ab-b4d72b06a1d6" />

<img width="644" height="789" alt="image" src="https://github.com/user-attachments/assets/512036e6-6feb-4138-a579-f5cadd0cfdf2" />

<img width="555" height="483" alt="image" src="https://github.com/user-attachments/assets/960faf1f-7cc6-4cd9-a9f7-1c081cb0cfa6" />

<img width="1302" height="877" alt="image" src="https://github.com/user-attachments/assets/8b5bdb40-2609-4c35-917d-d94223242fa5" />

<img width="1278" height="863" alt="image" src="https://github.com/user-attachments/assets/f7f64847-214c-4e64-97c1-1a5f7067d152" />

<img width="1299" height="874" alt="image" src="https://github.com/user-attachments/assets/ad09c2a3-50e7-48a8-8c61-59c275dbbdc7" />

---

## License

This project is open-source under the MIT License.
