# NeuroFlow - EEG Signal Analysis MVP

**NeuroFlow** (MVP) is a professional-grade desktop application for EEG signal analysis, built with Python. It leverages **MNE-Python** for powerful neuroscience computations and **PyQt6** for a modern, responsive user interface.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

This project demonstrates a strict **Model-View-Controller (MVC)** architecture with **multithreading** to ensure a seamless user experience, preventing GUI freezes during heavy signal processing tasks.

## 🚀 Key Features

*   **Key Features:**
    *   **Advanced Spectral Analysis:**
        *   **Time-Frequency Representation (TFR):** Visualize global or channel-specific oscillatory power changes over time (Morlet Wavelets).
        *   **Functional Connectivity:** Compute and visualize brain network interactions using **Weighted Phase Lag Index (wPLI)** (Alpha band).
    *   **Multi-Format Data Loading:** Support for **BrainVision (.vhdr)**, **.fif**, and **.edf** EEG datasets.
    *   **Robust Montage Handling:** Automatically detects missing channel locations (common in vhdr) and applies a standard '10-20' montage for consistent analysis.
    *   **Interactive Topomap:** "**Check Sensors**" feature to visualize electrode positions 2D topographically to verify channel mapping.
    *   **Preprocessing Pipeline:**
        *   **High-Pass Filter:** Remove slow drifts and DC offsets.
        *   **Low-Pass Filter:** Eliminate high-frequency noise.
        *   **Notch Filter:** Suppress line noise (50/60 Hz).
    *   **Independent Component Analysis (ICA):** Powerful artifact removal tool using FastICA to identify and exclude blinks (`EOG`) and heartbeats (`ECG`) from the data.
    *   **Event-Related Potentials (ERP):** Automatically extracts events and computes averaged evoked responses (ERP), visualized as a global "Butterfly Plot".
    *   **Spectral Analysis:** Real-time computation and visualization of **Power Spectral Density (PSD)** using Welch's method.
    *   **File & Export:**
        *   **Save Clean Data:** Save your processed/filtered EEG data to standard `.fif` format for future use.
        *   **Analyst Snapshots:** One-click **Screenshot** logic to capture high-quality images of your current analysis view for reports.
    *   **Modern Accordion UI:** A sleek, properly organized sidebar using `QToolBox` to manage complex workflows efficiently.

## 🛠️ Tech Stack

*   **Language:** Python 3.10+
*   **GUI:** PyQt6 (Qt Widgets, Signals & Slots)
*   **Backend:** MNE-Python (Neuroscience/EEG Analysis)
*   **Connectivity:** `mne-connectivity`
*   **Numerical:** NumPy, SciPy
*   **Plotting:** Matplotlib (integrated via FigureCanvasQTAgg)
*   **Concurrency:** `QThread` + `QObject` Worker Pattern

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/rzgrozt/neuroflow.git
    cd neuroflow
    ```

2.  **Create a virtual environment (Optional but Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install mne mne-connectivity PyQt6 PyQt6-Qt6 PyQt6-sip matplotlib numpy scipy scikit-learn
    ```

## 🖥️ Usage

1.  **Run the Application:**
    ```bash
    python neuroflow.py
    ```

2.  **Workflow:**
    *   **Load Data (Data & Preprocessing):** Click `Load EEG Data` and select your file (e.g., `subject_01.vhdr`).
    *   **Verify Sensors:** Click `📍 Check Sensors` to ensure your channels are mapped correctly.
    *   **Set Filters:** Input your desired High-pass, Low-pass, and Notch frequencies (default: 1.0 - 40.0 Hz, Notch 50.0 Hz).
    *   **ICA Artifact Removal (Page 2):**
        *   Click `Calculate ICA` to decompose the signal into independent components.
        *   Inspect the topomaps in the popup window. Identify blink/heartbeat artifacts (e.g., Component 0).
        *   Enter the ID (e.g., `0`) in the "Exclude" box and click `Apply ICA`. The PSD plot will update to show the cleaned signal.
    *   **ERP Analysis (Page 3):**
        *   Select a stimulus trigger from the "Select Event Trigger" dropdown (auto-populated).
        *   Set your epoch window (e.g., `tmin: -0.2`, `tmax: 0.5`).
        *   Click `Compute & Plot ERP` to view the averaged evoked response (Butterfly Plot) in a dedicated interactive viewer.
    *   **Advanced Analysis (Page 4):**
        *   **TFR:** Select a channel and click `Compute TFR` to see the Time-Frequency heatmap.
        *   **Connectivity:** Click `Alpha Band (8-12Hz)` to launch the **Connectivity Explorer** popup and visualize the functional brain network.

## 📂 Architecture

The application is structured to decouple UI from Logic:

*   **`AnalysisWorker` (Model/Controller Logic):**
    *   Runs on a separate `QThread`.
    *   Handles all MNE I/O and heavy computations.
    *   Communicates results back to the main thread via `pyqtSignal`.
*   **`MainWindow` (View):**
    *   Manages the GUI layout and user interactions.
    *   Updates the log and plots based on signals from the Worker.

## 📸 Screenshots

<img width="1283" height="899" alt="ss1" src="https://github.com/user-attachments/assets/a3105fac-5ff1-48ef-af2f-b0a99ef44839" />

<img width="1287" height="865" alt="ss2" src="https://github.com/user-attachments/assets/834bd9ad-9cc4-4a96-97ea-6108ba25eb33" />

<img width="807" height="925" alt="ss3" src="https://github.com/user-attachments/assets/050dfc96-c021-49e2-8429-1fd5f4cfc146" />

<img width="1302" height="874" alt="ss4" src="https://github.com/user-attachments/assets/9c667a99-0c87-4ba4-b40a-36335a70e7f2" />


## 📄 License

This project is open-source and available for educational and portfolio purposes.
