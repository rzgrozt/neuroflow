# NeuroFlow Project Overview

## Purpose
NeuroFlow is a professional-grade desktop application for EEG signal analysis. It provides researchers with tools for preprocessing, artifact removal, and advanced analysis of EEG data.

## Tech Stack
- **Language:** Python 3.10+
- **GUI Framework:** PyQt6 (Qt Widgets, Signals & Slots)
- **EEG Backend:** MNE-Python
- **Connectivity Analysis:** mne-connectivity
- **Numerical:** NumPy, SciPy, scikit-learn
- **Plotting:** Matplotlib (FigureCanvasQTAgg integration)
- **Concurrency:** QThread + QObject Worker Pattern

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

## Architecture
The application follows a separation of concerns pattern with multithreading:

### Core Module (`app/core/`)
- **EEGWorker** (`workers.py`): Runs on QThread, handles all MNE I/O and heavy computations, communicates via pyqtSignal

### UI Module (`app/ui/`)
- **MainWindow** (`main_window.py`): Primary application interface, manages GUI layout and user interactions
- **MplCanvas** (`canvas.py`): Matplotlib figure canvas for PyQt6 integration with dark theme
- **Dialogs** (`dialogs.py`):
  - `DatasetInfoDialog`: Metadata and event statistics viewer
  - `ConnectivityDialog`: Connectivity circle plot popup
  - `ERPViewer`: Interactive ERP butterfly plot and topomap viewer

## Code Style
- Code style: Black formatter
- Type hints used in function signatures
- Docstrings for classes and methods
- Dark theme UI with consistent styling

## Main Entry Point
```bash
python main.py
```

## Key Features
- Multi-format data loading (.vhdr, .fif, .edf)
- Preprocessing pipeline (HP/LP/Notch filters)
- ICA artifact removal
- ERP analysis with manual epoch inspection
- Time-Frequency Representation (TFR)
- Functional Connectivity (wPLI)
