# Unified UX & Accordion Design

**Goal:** Refactor the MainWindow UI to enforce layout consistency, implement exclusive section expansion (accordion), and clean up the toolbar.

**Architecture:** Three focused changes - fix widget sizing in SectionCard, add accordion signal/handler, migrate toolbar to menu bar.

---

## Section 1: Visual Consistency Fix (SectionCard)

**Problem:** `SectionCard.addWidget()` passes widgets through without expansion policy. Widgets like `QLabel` and `QComboBox` don't expand by default, causing misaligned layouts.

**Fix:** Modify `SectionCard.addWidget()` to set expanding size policy:

```python
def addWidget(self, widget):
    widget.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        widget.sizePolicy().verticalPolicy()
    )
    self.content_layout.addWidget(widget)
```

**File:** `app/ui/sidebar.py` - `SectionCard.addWidget()` method

---

## Section 2: Accordion Behavior

**Goal:** When user expands a section, all other sections collapse automatically.

**Implementation:**

1. Add `expanded` signal to `CollapsibleBox` that emits when expanded
2. Track sections in `MainWindow.sidebar_sections` list
3. Connect handler that collapses other sections

**Files:**
- `app/ui/sidebar.py` - Add `expanded` signal
- `app/ui/main_window.py` - Add section tracking and handler

---

## Section 3: Toolbar to Menu Bar

**Goal:** Remove toolbar, move actions to File menu with keyboard shortcuts.

**Implementation:**

1. Expand `create_menu()` with File menu (Save, Screenshot, Exit)
2. Add keyboard shortcuts (Ctrl+S, Ctrl+Shift+S, Ctrl+Q)
3. Delete `init_toolbar()` method and its call

**File:** `app/ui/main_window.py`
