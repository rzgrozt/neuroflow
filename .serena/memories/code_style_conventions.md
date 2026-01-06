# Code Style & Conventions

## Formatting
- **Formatter:** Black
- **Line length:** Default (88 characters)

## Naming Conventions
- Classes: PascalCase (e.g., `MainWindow`, `AnalysisWorker`)
- Methods/Functions: snake_case (e.g., `load_data`, `compute_erp`)
- Variables: snake_case (e.g., `raw_data`, `event_id`)
- Constants: UPPER_SNAKE_CASE (e.g., `HAS_CONNECTIVITY`)
- UI elements: prefixed with type (e.g., `btn_load`, `combo_events`, `input_hp`)

## Type Hints
- Used in function signatures with `typing` module
- Example: `def load_data(self, file_path: str):`

## Docstrings
- Triple-quoted strings for classes and methods
- Brief description of purpose

## PyQt6 Patterns
- Signals defined as class attributes: `log_message = pyqtSignal(str)`
- Slots decorated with `@pyqtSlot(type)`
- Worker pattern: heavy operations in QThread via QObject

## UI Button Patterns
```python
self.btn_name = QPushButton("Label")
self.btn_name.setCursor(Qt.CursorShape.PointingHandCursor)
self.btn_name.setEnabled(False)  # Disable until ready
self.btn_name.clicked.connect(self.handler_method)
```

## Dialog Patterns
- Inherit from QDialog
- Accept parent in __init__
- Use QVBoxLayout or QTabWidget for structure
- Include Close button connected to self.accept()
