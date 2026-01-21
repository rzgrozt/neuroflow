<div align="center">

<!-- Neural-inspired header with passion -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1b2a,50:1b4965,100:5fa8d3&height=200&section=header&text=NeuroFlow&fontSize=80&fontColor=bee9e8&fontAlignY=35&desc=Where%20Neurons%20Meet%20Algorithms&descSize=20&descAlignY=55&descAlign=50&animation=fadeIn" width="100%"/>

<br/>

<!-- Poetic tagline -->
<em>
<strong>"The brain is the last and grandest biological frontier"</strong> — James D. Watson
</em>

<br/><br/>

<!-- Stylized description -->
<p>
<img src="https://img.shields.io/badge/⚡_Professional_Grade-EEG_Signal_Analysis-0d1b2a?style=for-the-badge&labelColor=1b4965" alt="Professional Grade"/>
</p>

<p>
A desktop application born from the intersection of <strong>cognitive neuroscience</strong> and <strong>elegant code</strong>.<br/>
Built with <strong>MNE-Python</strong> for rigorous signal processing and <strong>PyQt6</strong> for a refined experience.
</p>

<!-- Badges with cohesive styling -->
<p>
<a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-bee9e8?style=flat-square&labelColor=0d1b2a" alt="License: MIT"/></a>
<a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.10+-5fa8d3?style=flat-square&labelColor=0d1b2a&logo=python&logoColor=bee9e8" alt="Python 3.10+"/></a>
<a href="https://github.com/psf/black"><img src="https://img.shields.io/badge/Code_Style-Black-bee9e8?style=flat-square&labelColor=0d1b2a" alt="Code Style: Black"/></a>
<a href="https://mne.tools/"><img src="https://img.shields.io/badge/Powered_by-MNE--Python-5fa8d3?style=flat-square&labelColor=0d1b2a" alt="MNE-Python"/></a>
</p>

</div>

---

<div align="center">
<h2>🧠 The Vision</h2>
</div>

> **NeuroFlow** exists because understanding the brain shouldn't require fighting with your tools.
>
> Every oscillation tells a story. Every ERP reveals cognition in action. This application is designed for researchers, clinicians, and students who share the profound curiosity about what makes us *think*, *feel*, and *perceive*.

---

## ✦ Core Capabilities

### 📂 Data Management

- **Multi-Format I/O** — BrainVision `.vhdr` • MNE `.fif` • EDF `.edf` • Epoched `-epo.fif`
- **Smart Montage** — Auto-detects missing locations, applies standard 10-20
- **Dataset Inspector** — Metadata, sampling rate, duration, event statistics
- **Sensor Topology** — Interactive 2D electrode visualization
- **Session Persistence** — Save complete `.nflow` sessions with full state

### ⚡ Signal Processing

- **High-Pass Filter** — Remove DC offsets and slow drifts
- **Low-Pass Filter** — Eliminate high-frequency noise
- **Notch Filter** — Suppress 50/60 Hz power line interference
- **Interpolation** — Spherical spline repair for bad channels
- **ICA Decomposition** — FastICA artifact removal (EOG, ECG)

### 📊 Analysis Suite

- **Power Spectral Density** — Welch's method with μV²/Hz display
- **Event-Related Potentials** — Configurable baseline correction
- **Time-Frequency** — Morlet wavelets with multiple normalization modes
- **Connectivity** — Weighted Phase Lag Index (wPLI)

### 🔬 Quality & Reproducibility

- **Epoch Inspector** — Interactive artifact rejection
- **Pipeline History** — Timestamped preprocessing log
- **Screenshot Export** — Capture views for documentation
- **HTML Reports** — Professional MNE Report generation

### ⚡ Batch Processing

- **Multi-File Automation** — Process entire folders of EEG files automatically
- **Smart Auto-ICA** — Intelligent EOG detection with Fp1/Fp2 fallback for blink removal
- **Configurable Pipeline** — Toggle filtering, ICA, epoching, and report generation
- **Progress Tracking** — Real-time progress dialog with per-file status logging
- **Batch Reports** — Generate individual HTML reports for each processed file

---

<div align="center">
<h2>🎨 Visual Tour</h2>
<em>Clinical-grade visualization meets intuitive design</em>
</div>

<br/>

<p align="center">
<img width="90%" alt="Main Interface" src="https://github.com/user-attachments/assets/b68bb39c-87c1-4b69-92ab-b4d72b06a1d6"/>
</p>

<details>
<summary><strong>📸 More Screenshots</strong></summary>
<br/>

<p align="center">
<img width="60%" alt="Dataset Inspector" src="https://github.com/user-attachments/assets/512036e6-6feb-4138-a579-f5cadd0cfdf2"/>
</p>

<p align="center">
<img width="50%" alt="Connectivity Analysis" src="https://github.com/user-attachments/assets/960faf1f-7cc6-4cd9-a9f7-1c081cb0cfa6"/>
</p>

<p align="center">
<img width="90%" alt="Time-Frequency Analysis" src="https://github.com/user-attachments/assets/8b5bdb40-2609-4c35-917d-d94223242fa5"/>
</p>

<p align="center">
<img width="90%" alt="ERP Visualization" src="https://github.com/user-attachments/assets/f7f64847-214c-4e64-97c1-1a5f7067d152"/>
</p>

<p align="center">
<img width="90%" alt="Power Spectral Density" src="https://github.com/user-attachments/assets/ad09c2a3-50e7-48a8-8c61-59c275dbbdc7"/>
</p>

</details>

---

## 🛠 Technology

<div align="center">

| Layer | Technology | Purpose |
|:-----:|:-----------|:--------|
| 🐍 | **Python 3.10+** | Core language |
| 🖥️ | **PyQt6** | Modern desktop GUI |
| 🧠 | **MNE-Python** | Neuroscience signal processing |
| 🔗 | **mne-connectivity** | Functional connectivity analysis |
| 🔢 | **NumPy / SciPy** | Numerical computing backbone |
| 📈 | **Matplotlib** | Publication-quality visualization |
| ⚙️ | **QThread** | Non-blocking background processing |

</div>

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/rzgrozt/neuroflow.git
cd neuroflow

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

<details>
<summary><strong>📦 Manual dependency installation</strong></summary>

```bash
pip install mne mne-connectivity PyQt6 PyQt6-Qt6 PyQt6-sip matplotlib numpy scipy scikit-learn
```

</details>

### Launch

```bash
python main.py
```

---

## 🔄 Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   📁 LOAD          🔍 VERIFY         ⚡ PREPROCESS       🧹 ARTIFACTS       │
│   ───────          ────────          ────────────       ───────────        │
│   .vhdr .fif       Sensors &         Bandpass &         ICA for            │
│   .edf files       Metadata          Notch filters      EOG/ECG            │
│                                                                             │
│         │               │                  │                  │            │
│         └───────────────┴──────────────────┴──────────────────┘            │
│                                    ▼                                        │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                         📊 ANALYZE                                   │  │
│   │   ─────────────────────────────────────────────────────────────     │  │
│   │   Create Epochs → Inspect & Reject → ERP / TFR / Connectivity       │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Architecture

```
neuroflow/
├── main.py                      # Application entry point
├── requirements.txt             # Dependencies
└── app/
    ├── core/
    │   └── workers.py           # EEGWorker: Background MNE processing
    └── ui/
        ├── canvas.py            # Matplotlib-PyQt6 integration
        ├── dialogs.py           # Specialized visualization dialogs
        └── main_window.py       # Primary application interface
```

<div align="center">

| Component | Thread | Responsibility |
|:----------|:------:|:---------------|
| **EEGWorker** | Background | MNE I/O, heavy computation, Qt signals |
| **MainWindow** | Main | UI layout, user interaction, plot updates |
| **Dialogs** | Main | Modular popup visualizations |

</div>

---

<div align="center">

## 🤝 Contributing

Contributions are welcome! Whether you're fixing bugs, adding features, or improving documentation—<br/>
every contribution helps advance open neuroscience tools.

</div>

---

<div align="center">

## 📜 License & Citation

<table>
<tr>
<td align="center">

<br/>

**MIT License**

*Free to use, modify, and distribute.*

<br/>

</td>
<td align="center">

<br/>

**Cite This Work**

Ozturk, R. (2025). *NeuroFlow* [Software].<br/>
https://github.com/rzgrozt/neuroflow

<br/>

</td>
</tr>
</table>

<details>
<summary><strong>📋 BibTeX</strong></summary>
<br/>

```bibtex
@software{neuroflow,
  author       = {Ruzgar Ozturk},
  title        = {NeuroFlow: Professional EEG Signal Analysis},
  year         = {2025},
  url          = {https://github.com/rzgrozt/neuroflow}
}
```

</details>

<br/>

*Built with 💙 for the neuroscience community.*

---

<br/>

<em>
"What we know is a drop, what we don't know is an ocean."<br/>
— Isaac Newton
</em>

<br/><br/>

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1b2a,50:1b4965,100:5fa8d3&height=100&section=footer" width="100%"/>

</div>
