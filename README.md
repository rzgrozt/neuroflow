# NeuroFlow - EEG Signal Analysis MVP

**NeuroFlow** (MVP) is a professional-grade desktop application for EEG signal analysis, built with Python. It leverages **MNE-Python** for powerful neuroscience computations and **PyQt6** for a modern, responsive user interface.

This project demonstrates a strict **Model-View-Controller (MVC)** architecture with **multithreading** to ensure a seamless user experience, preventing GUI freezes during heavy signal processing tasks.

## 🚀 Key Features

*   **Multi-Format Data Loading:** Support for **BrainVision (.vhdr)**, **.fif**, and **.edf** EEG datasets.
*   **Robust Montage Handling:** Automatically detects missing channel locations (common in vhdr) and applies a standard '10-20' montage for consistent analysis.
*   **Interactive Topomap:** "**Check Sensors**" feature to visualize electrode positions 2D topographically to verify channel mapping.
*   **Preprocessing Pipeline:**
    *   **High-Pass Filter:** Remove slow drifts and DC offsets.
    *   **Low-Pass Filter:** Eliminate high-frequency noise.
    *   **Notch Filter:** Suppress line noise (50/60 Hz).
*   **Spectral Analysis:** Real-time computation and visualization of **Power Spectral Density (PSD)** using Welch's method.
*   **Modern Dark UI:** A sleek, VS Code-inspired dark theme optimized for long research sessions.

## 🛠️ Tech Stack

*   **Language:** Python 3.10+
*   **GUI:** PyQt6 (Qt Widgets, Signals & Slots)
*   **Backend:** MNE-Python (Neuroscience/EEG Analysis)
*   **Numerical:** NumPy, SciPy
*   **Plotting:** Matplotlib (integrated via FigureCanvasQTAgg)
*   **Concurrency:** `QThread` + `QObject` Worker Pattern

## 📦 Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/StartYourFork/neuroflow.git
    cd neuroflow
    ```

2.  **Create a virtual environment (Optional but Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install mne PyQt6 PyQt6-Qt6 PyQt6-sip matplotlib numpy scipy
    ```

## 🖥️ Usage

1.  **Run the Application:**
    ```bash
    python neuroflow.py
    ```

2.  **Workflow:**
    *   **Load Data:** Click `Load EEG Data` and select your file (e.g., `subject_01.vhdr`).
    *   **Verify Sensors:** Click `📍 Check Sensors` to ensure your channels are mapped correctly.
    *   **Set Filters:** Input your desired High-pass, Low-pass, and Notch frequencies (default: 1.0 - 40.0 Hz, Notch 50.0 Hz).
    *   **Process:** Click `Run Pipeline`. The PSD plot on the right will update to show the frequency power distribution of your processed data.

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

*(Add screenshots of your application here to showcase the Dark UI and PSD plots)*

## 📄 License

This project is open-source and available for educational and portfolio purposes.
