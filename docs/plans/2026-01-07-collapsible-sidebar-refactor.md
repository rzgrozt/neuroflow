# Collapsible Sidebar Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace QToolBox sidebar with a compact, scrollable Inspector Panel using custom CollapsibleBox widgets with triangle toggle icons.

**Architecture:** Create a new `CollapsibleBox` widget class that provides collapsible sections with header buttons featuring triangle icons (▶/▼). Replace the QToolBox in MainWindow with a QScrollArea containing vertically-stacked CollapsibleBox widgets, aligned to top with minimal spacing. Update QSS theme for seamless integration.

**Tech Stack:** PyQt6 (QWidget, QPushButton, QScrollArea, QVBoxLayout, QFrame)

---

## Task 1: Create CollapsibleBox Widget Class

**Files:**
- Modify: `app/ui/sidebar.py:316-408` (replace existing CollapsibleSection)

**Step 1: Write the CollapsibleBox class**

Replace the existing `CollapsibleSection` class with the new `CollapsibleBox` implementation:

```python
class CollapsibleBox(QFrame):
    """
    Collapsible accordion section with triangle toggle icons.
    Provides a compact, inspector-panel style collapsible container.
    """

    def __init__(self, title: str, icon: str = "", expanded: bool = True, parent=None):
        super().__init__(parent)
        self.setObjectName("collapsibleBox")
        self._expanded = expanded
        self._title = title
        self._icon = icon

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header button with triangle icon
        self.header = QPushButton()
        self.header.setObjectName("collapsibleHeader")
        self.header.setCursor(Qt.CursorShape.PointingHandCursor)
        self.header.clicked.connect(self._toggle)
        self._update_header_text()
        self._style_header()
        self.main_layout.addWidget(self.header)

        # Content container
        self.content = QWidget()
        self.content.setObjectName("collapsibleContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(12, 8, 12, 12)
        self.content_layout.setSpacing(10)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.main_layout.addWidget(self.content)

        # Set initial visibility
        self.content.setVisible(self._expanded)
        self._update_header_style()

    def _update_header_text(self):
        """Update header text with appropriate triangle icon."""
        triangle = "▼" if self._expanded else "▶"
        icon_part = f" {self._icon}" if self._icon else ""
        self.header.setText(f"  {triangle}{icon_part}  {self._title}")

    def _style_header(self):
        """Apply base header styling."""
        self.header.setStyleSheet("""
            #collapsibleHeader {
                background: #2d2d2d;
                color: #ffffff;
                border: none;
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: 600;
                font-size: 13px;
                text-align: left;
            }
            #collapsibleHeader:hover {
                background: #3a3a3a;
            }
        """)

    def _update_header_style(self):
        """Update header styling based on expanded state."""
        if self._expanded:
            self.header.setStyleSheet("""
                #collapsibleHeader {
                    background: #2d2d2d;
                    color: #00d4ff;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 12px;
                    font-weight: 600;
                    font-size: 13px;
                    text-align: left;
                }
                #collapsibleHeader:hover {
                    background: #3a3a3a;
                }
            """)
        else:
            self._style_header()

    def _toggle(self):
        """Toggle content visibility."""
        self._expanded = not self._expanded
        self.content.setVisible(self._expanded)
        self._update_header_text()
        self._update_header_style()

    def addWidget(self, widget):
        """Add a widget to the content area."""
        self.content_layout.addWidget(widget)

    def addLayout(self, layout):
        """Add a layout to the content area."""
        self.content_layout.addLayout(layout)

    def setExpanded(self, expanded: bool):
        """Programmatically set expanded state."""
        if self._expanded != expanded:
            self._toggle()

    def isExpanded(self) -> bool:
        """Return current expanded state."""
        return self._expanded
```

**Step 2: Verify CollapsibleBox class is syntactically correct**

Run: `python -c "from app.ui.sidebar import CollapsibleBox; print('CollapsibleBox imported successfully')"`
Expected: `CollapsibleBox imported successfully`

**Step 3: Commit**

```bash
git add app/ui/sidebar.py
git commit -m "feat(sidebar): add CollapsibleBox widget with triangle toggle icons

- Replace CollapsibleSection with CollapsibleBox
- Header button with ▶/▼ triangle icons based on state
- Compact content margins (12px horizontal, 8px top, 12px bottom)
- Dark background header (#2d2d2d) with cyan highlight when expanded
- setVisible() toggle for instant show/hide

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Update sidebar.py Exports

**Files:**
- Modify: `app/ui/sidebar.py` (update module docstring and ensure CollapsibleBox is exported)

**Step 1: Update module docstring**

Replace the module docstring at lines 1-9 to include CollapsibleBox:

```python
"""
Sidebar Components Module for NeuroFlow

Contains styled sidebar widgets with "Neural Elegance" theme:
- SectionCard: Card-style container for grouped controls
- ParamRow: Clean parameter input row
- ActionButton: Styled action buttons with states
- CollapsibleBox: Collapsible section with triangle toggle icons
- StyledSidebar: Complete sidebar widget assembly
"""
```

**Step 2: Verify exports**

Run: `python -c "from app.ui.sidebar import CollapsibleBox, SectionCard, ActionButton, ParamRow; print('All exports OK')"`
Expected: `All exports OK`

**Step 3: Commit**

```bash
git add app/ui/sidebar.py
git commit -m "docs(sidebar): update module docstring for CollapsibleBox

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: Create Scrollable Sidebar Container

**Files:**
- Modify: `app/ui/main_window.py:142-175` (replace QToolBox setup with QScrollArea)

**Step 1: Update imports in init_ui**

Change the import statement inside `init_ui` to include `CollapsibleBox`:

```python
        # Import sidebar components
        from .sidebar import (
            SidebarTitle, SectionCard, ParamRow, ParamSpinRow,
            ActionButton, StatusLog, CollapsibleBox
        )
```

**Step 2: Replace QToolBox with QScrollArea setup**

Replace the QToolBox creation (around line 172: `toolbox = QToolBox()`) with this QScrollArea setup:

```python
        # Scrollable sidebar container (replaces QToolBox)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setObjectName("sidebarScrollArea")

        # Container widget for scroll area
        scroll_content = QWidget()
        scroll_content.setObjectName("sidebarScrollContent")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(8, 8, 8, 8)
        scroll_layout.setSpacing(5)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
```

**Step 3: Verify syntax**

Run: `python -c "from app.ui.main_window import MainWindow; print('MainWindow imports OK')"`
Expected: `MainWindow imports OK`

**Step 4: Commit**

```bash
git add app/ui/main_window.py
git commit -m "refactor(main_window): set up QScrollArea container for sidebar

- Import CollapsibleBox from sidebar module
- Create QScrollArea with transparent frame
- Configure scroll content with AlignTop and 5px spacing
- Disable horizontal scrollbar

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: Refactor Data & Preprocessing Section

**Files:**
- Modify: `app/ui/main_window.py:183-228` (convert page_data to CollapsibleBox)

**Step 1: Replace page_data creation with CollapsibleBox**

Remove the `create_page()` helper and `page_data` creation. Replace with:

```python
        # ====== SECTION 1: Data & Preprocessing ======
        section_data = CollapsibleBox("Data & Preprocessing", "📂", expanded=True)

        # Dataset Card
        card_dataset = SectionCard("Dataset", "💾")
        self.btn_load = ActionButton("Load EEG Data")
        self.btn_load.clicked.connect(self.browse_file)
        card_dataset.addWidget(self.btn_load)

        self.btn_sensors = ActionButton("Check Sensors")
        self.btn_sensors.setEnabled(False)
        self.btn_sensors.clicked.connect(self.check_sensors)
        card_dataset.addWidget(self.btn_sensors)

        self.btn_dataset_info = ActionButton("Dataset Info")
        self.btn_dataset_info.setEnabled(False)
        self.btn_dataset_info.clicked.connect(self.show_dataset_info)
        self.btn_dataset_info.setToolTip("View dataset metadata and event statistics")
        card_dataset.addWidget(self.btn_dataset_info)
        section_data.addWidget(card_dataset)

        # Signal Pipeline Card
        card_pipeline = SectionCard("Signal Pipeline", "⚡")

        self.param_hp = ParamRow("HP (Hz):", "1.0")
        card_pipeline.addWidget(self.param_hp)
        self.input_hp = self.param_hp.input

        self.param_lp = ParamRow("LP (Hz):", "40.0")
        card_pipeline.addWidget(self.param_lp)
        self.input_lp = self.param_lp.input

        self.param_notch = ParamRow("Notch:", "50.0")
        card_pipeline.addWidget(self.param_notch)
        self.input_notch = self.param_notch.input

        self.btn_run = ActionButton("Run Pipeline", primary=True)
        self.btn_run.clicked.connect(self.launch_pipeline)
        self.btn_run.setEnabled(False)
        card_pipeline.addWidget(self.btn_run)
        section_data.addWidget(card_pipeline)

        scroll_layout.addWidget(section_data)
```

**Step 2: Verify syntax**

Run: `python -c "from app.ui.main_window import MainWindow; print('MainWindow imports OK')"`
Expected: `MainWindow imports OK`

**Step 3: Commit**

```bash
git add app/ui/main_window.py
git commit -m "refactor(main_window): convert Data & Preprocessing to CollapsibleBox

- Replace page_data with section_data CollapsibleBox
- Add Dataset and Signal Pipeline cards to collapsible section
- Wire up existing button connections

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Refactor Artifact Removal Section

**Files:**
- Modify: `app/ui/main_window.py` (convert page_ica to CollapsibleBox)

**Step 1: Replace page_ica creation with CollapsibleBox**

```python
        # ====== SECTION 2: Artifact Removal ======
        section_ica = CollapsibleBox("Artifact Removal", "🧹", expanded=False)

        card_ica = SectionCard("Independent Component Analysis", "🔬")

        self.btn_calc_ica = ActionButton("1. Calculate ICA")
        self.btn_calc_ica.clicked.connect(self.run_ica_click)
        self.btn_calc_ica.setEnabled(False)
        card_ica.addWidget(self.btn_calc_ica)

        exclude_label = QLabel("Exclude Components:")
        exclude_label.setStyleSheet("color: #9090a8; font-size: 12px; background: transparent;")
        card_ica.addWidget(exclude_label)

        self.input_ica_exclude = QLineEdit()
        self.input_ica_exclude.setPlaceholderText("e.g. 0, 2 (comma separated)")
        card_ica.addWidget(self.input_ica_exclude)

        self.btn_apply_ica = ActionButton("2. Apply ICA")
        self.btn_apply_ica.clicked.connect(self.apply_ica_click)
        self.btn_apply_ica.setEnabled(False)
        card_ica.addWidget(self.btn_apply_ica)

        section_ica.addWidget(card_ica)
        scroll_layout.addWidget(section_ica)
```

**Step 2: Verify syntax**

Run: `python -c "from app.ui.main_window import MainWindow; print('MainWindow imports OK')"`
Expected: `MainWindow imports OK`

**Step 3: Commit**

```bash
git add app/ui/main_window.py
git commit -m "refactor(main_window): convert Artifact Removal to CollapsibleBox

- Replace page_ica with section_ica CollapsibleBox
- Start collapsed (expanded=False) for compact initial view
- Add ICA card with all controls

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: Refactor ERP Analysis Section

**Files:**
- Modify: `app/ui/main_window.py` (convert page_erp to CollapsibleBox)

**Step 1: Replace page_erp creation with CollapsibleBox**

```python
        # ====== SECTION 3: ERP Analysis ======
        section_erp = CollapsibleBox("ERP Analysis", "📊", expanded=False)

        card_erp = SectionCard("Event-Related Potentials", "📈")

        event_label = QLabel("Trigger Event:")
        event_label.setStyleSheet("color: #9090a8; font-size: 12px; background: transparent;")
        card_erp.addWidget(event_label)

        self.combo_events = QComboBox()
        card_erp.addWidget(self.combo_events)

        time_row = ParamSpinRow("Time:", -5.0, 5.0, -0.2, 0.5)
        self.spin_tmin = time_row.spin_min
        self.spin_tmax = time_row.spin_max
        card_erp.addWidget(time_row)

        self.btn_inspect_epochs = ActionButton("Inspect & Reject Epochs")
        self.btn_inspect_epochs.clicked.connect(self.inspect_epochs_click)
        self.btn_inspect_epochs.setEnabled(False)
        self.btn_inspect_epochs.setToolTip("Visually inspect epochs and manually reject artifacts")
        card_erp.addWidget(self.btn_inspect_epochs)

        self.btn_erp = ActionButton("Compute & Plot ERP", primary=True)
        self.btn_erp.clicked.connect(self.compute_erp_click)
        self.btn_erp.setEnabled(False)
        card_erp.addWidget(self.btn_erp)

        section_erp.addWidget(card_erp)
        scroll_layout.addWidget(section_erp)
```

**Step 2: Verify syntax**

Run: `python -c "from app.ui.main_window import MainWindow; print('MainWindow imports OK')"`
Expected: `MainWindow imports OK`

**Step 3: Commit**

```bash
git add app/ui/main_window.py
git commit -m "refactor(main_window): convert ERP Analysis to CollapsibleBox

- Replace page_erp with section_erp CollapsibleBox
- Start collapsed for compact initial view
- Add ERP card with event selector and time controls

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: Refactor Advanced Analysis Section

**Files:**
- Modify: `app/ui/main_window.py` (convert page_adv to CollapsibleBox)

**Step 1: Replace page_adv creation with CollapsibleBox**

```python
        # ====== SECTION 4: Advanced Analysis ======
        section_advanced = CollapsibleBox("Advanced Analysis", "🔮", expanded=False)

        # TFR Card
        card_tfr = SectionCard("Time-Frequency (TFR)", "🌊")

        chan_label = QLabel("Channel:")
        chan_label.setStyleSheet("color: #9090a8; font-size: 12px; background: transparent;")
        card_tfr.addWidget(chan_label)

        self.combo_channels = QComboBox()
        card_tfr.addWidget(self.combo_channels)

        freq_row = ParamSpinRow("Freqs:", 0.1, 100.0, 4.0, 30.0)
        self.spin_tfr_l = freq_row.spin_min
        self.spin_tfr_h = freq_row.spin_max
        card_tfr.addWidget(freq_row)

        self.btn_tfr = ActionButton("Compute TFR", primary=True)
        self.btn_tfr.clicked.connect(self.compute_tfr_click)
        self.btn_tfr.setEnabled(False)
        card_tfr.addWidget(self.btn_tfr)
        section_advanced.addWidget(card_tfr)

        # Connectivity Card
        card_conn = SectionCard("Connectivity (wPLI)", "🔗")

        self.btn_conn = ActionButton("Alpha Band (8-12Hz)")
        self.btn_conn.clicked.connect(self.compute_connectivity_click)
        self.btn_conn.setEnabled(False)
        card_conn.addWidget(self.btn_conn)
        section_advanced.addWidget(card_conn)

        scroll_layout.addWidget(section_advanced)
```

**Step 2: Verify syntax**

Run: `python -c "from app.ui.main_window import MainWindow; print('MainWindow imports OK')"`
Expected: `MainWindow imports OK`

**Step 3: Commit**

```bash
git add app/ui/main_window.py
git commit -m "refactor(main_window): convert Advanced Analysis to CollapsibleBox

- Replace page_adv with section_advanced CollapsibleBox
- Add TFR and Connectivity cards
- Start collapsed for compact initial view

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 8: Finalize Sidebar Layout

**Files:**
- Modify: `app/ui/main_window.py` (connect scroll area and remove old toolbox references)

**Step 1: Connect scroll area to sidebar**

Replace the line `sidebar_layout.addWidget(toolbox)` with:

```python
        # Set scroll content and add to sidebar
        scroll_area.setWidget(scroll_content)
        sidebar_layout.addWidget(scroll_area)
```

**Step 2: Add QFrame import if not present**

Ensure `QFrame` is imported at the top of the file. Check the existing imports and add if missing:

```python
from PyQt6.QtWidgets import (
    # ... existing imports ...
    QFrame,
)
```

**Step 3: Remove create_page helper function**

Delete the `create_page()` helper function that was used for QToolBox pages (no longer needed).

**Step 4: Verify the application launches**

Run: `python main.py`
Expected: Application launches with collapsible sidebar sections

**Step 5: Commit**

```bash
git add app/ui/main_window.py
git commit -m "refactor(main_window): complete sidebar migration to QScrollArea

- Connect scroll_area to sidebar_layout
- Remove obsolete create_page helper
- Ensure QFrame import is present

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 9: Update Theme QSS for Scroll Area

**Files:**
- Modify: `app/ui/theme.py` (add QScrollArea styles)

**Step 1: Add QScrollArea styles to the QSS**

Add these styles after the QToolBox section (around line 675) in the `apply_modern_theme` function:

```python
    /* ========================================
       SCROLL AREA (Sidebar)
       ======================================== */

    #sidebarScrollArea {
        background: transparent;
        border: none;
    }

    #sidebarScrollContent {
        background: transparent;
    }

    /* ========================================
       COLLAPSIBLE BOX
       ======================================== */

    #collapsibleBox {
        background: transparent;
        border: none;
        margin-bottom: 2px;
    }

    #collapsibleHeader {
        background: #2d2d2d;
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 8px 12px;
        font-weight: 600;
        font-size: 13px;
        text-align: left;
    }

    #collapsibleHeader:hover {
        background: #3a3a3a;
    }

    #collapsibleContent {
        background: transparent;
    }
```

**Step 2: Verify the theme applies**

Run: `python main.py`
Expected: Collapsible sections have dark headers with proper styling

**Step 3: Commit**

```bash
git add app/ui/theme.py
git commit -m "style(theme): add QSS styles for collapsible sidebar

- Add transparent QScrollArea background
- Style collapsible headers (#2d2d2d background)
- Ensure content areas are transparent

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 10: Visual Verification and Polish

**Files:**
- All sidebar-related files for visual testing

**Step 1: Launch application and verify all sections**

Run: `python main.py`

Verify the following:
- [ ] All 4 collapsible sections are visible (Data & Preprocessing, Artifact Removal, ERP Analysis, Advanced Analysis)
- [ ] Triangle icons display correctly (▼ when expanded, ▶ when collapsed)
- [ ] Clicking headers toggles section visibility
- [ ] First section starts expanded, others start collapsed
- [ ] Sections stack vertically without gaps
- [ ] Scroll bar appears when content exceeds viewport height
- [ ] All buttons and inputs are functional

**Step 2: Adjust compact input height if needed**

If inputs appear too tall, update the QSS in `theme.py` to ensure 28px height:

```python
    /* Compact inputs for sidebar */
    #collapsibleContent QLineEdit,
    #collapsibleContent QComboBox,
    #collapsibleContent QSpinBox,
    #collapsibleContent QDoubleSpinBox {
        height: 28px;
        min-height: 28px;
        max-height: 28px;
    }
```

**Step 3: Final commit**

```bash
git add .
git commit -m "style(sidebar): polish collapsible sidebar styling

- Verify all sections toggle correctly
- Ensure compact input heights
- Visual QA pass complete

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 11: Cleanup - Remove Old CollapsibleSection

**Files:**
- Modify: `app/ui/sidebar.py` (remove old CollapsibleSection class if still present)

**Step 1: Remove CollapsibleSection class**

If the old `CollapsibleSection` class is still in the file alongside `CollapsibleBox`, remove it entirely. Keep only `CollapsibleBox`.

**Step 2: Verify no references to old class**

Run: `grep -r "CollapsibleSection" app/`
Expected: No matches (or only in comments/docs)

**Step 3: Commit if changes were made**

```bash
git add app/ui/sidebar.py
git commit -m "refactor(sidebar): remove deprecated CollapsibleSection class

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Summary

This plan refactors the NeuroFlow sidebar from a QToolBox-based layout to a compact, scrollable Inspector Panel with:

1. **CollapsibleBox widget** - Custom collapsible sections with ▶/▼ triangle toggle icons
2. **QScrollArea container** - Replaces QToolBox with AlignTop alignment and 5px spacing
3. **Updated QSS theme** - Transparent scroll area, dark (#2d2d2d) headers, compact inputs

The result is a modern, professional sidebar that:
- Eliminates wasted vertical space from QToolBox page expansion
- Provides instant toggle animation (setVisible)
- Uses compact margins and spacing throughout
- Maintains the existing "Neural Elegance" dark theme aesthetic
