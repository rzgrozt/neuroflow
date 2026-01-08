# Pipeline History System Design

## Purpose
Implement a traceability system that logs every preprocessing step so EEG analyses can be reproduced. This addresses the scientific need for reproducibility in research workflows.

## Design Decisions
- **Timestamps**: Each operation includes an ISO timestamp
- **Auto-reset**: History clears when a new dataset is loaded
- **UI location**: History displayed in Dataset Info dialog
- **Drop log format**: Summary only (kept/rejected counts)
- **History filename**: Based on source filename, not save path

## Data Structure

```python
self.pipeline_history = []
self.source_filename = None  # e.g., "subject01" (without extension)

# Entry format:
{
    "timestamp": "2026-01-08T14:32:15",
    "action": "data_loaded" | "filter" | "ica_exclusion" | "manual_epoch_rejection",
    "params": { ... }
}
```

### Action Types

1. **data_loaded**
   ```json
   {"timestamp": "...", "action": "data_loaded", "params": {"filename": "subject01.vhdr"}}
   ```

2. **filter**
   ```json
   {"timestamp": "...", "action": "filter", "params": {"highpass": 0.1, "lowpass": 40.0, "notch": 50.0}}
   ```

3. **ica_exclusion**
   ```json
   {"timestamp": "...", "action": "ica_exclusion", "params": {"excluded_components": [0, 2, 5]}}
   ```

4. **manual_epoch_rejection**
   ```json
   {"timestamp": "...", "action": "manual_epoch_rejection", "params": {"event": "stimulus", "tmin": -0.2, "tmax": 0.5, "kept": 85, "rejected": 15}}
   ```

## Implementation Changes

### MainWindow (`app/ui/main_window.py`)

#### `__init__`
- Add `self.pipeline_history = []`
- Add `self.source_filename = None`

#### `on_data_loaded`
- Reset: `self.pipeline_history = []`
- Extract and store source filename (without extension)
- Log `data_loaded` entry with timestamp

#### `launch_pipeline` (or via signal callback)
- After successful filtering, log `filter` entry
- Need mechanism to know when worker's `run_pipeline` succeeds

#### `apply_ica_click`
- After successful ICA apply (signal received), log `ica_exclusion` entry

#### `inspect_epochs_click`
- After `epochs.drop_bad()`, log `manual_epoch_rejection` entry with counts

#### `on_save_finished`
- After `.fif` saved, write `{source_filename}_history.json` to same directory
- Log success message including both files

#### `show_dataset_info`
- Pass `self.pipeline_history` to `DatasetInfoDialog`

### DatasetInfoDialog (`app/ui/dialogs.py`)

#### Constructor
- Accept new parameter: `pipeline_history: list`

#### UI Changes
- Add separator/label: "Processing History"
- Add `QTextEdit` (read-only) showing `json.dumps(history, indent=2)`
- Add "Copy to Clipboard" `QPushButton`
- Connect button to copy JSON to clipboard

## Export Behavior

When user saves clean data:
1. Worker saves `{user_chosen_path}.fif`
2. `on_save_finished` receives the saved path
3. Create `{source_filename}_history.json` in the same directory
4. Show status: "Saved data and processing history"

Example: User loads `subject01.vhdr`, processes it, saves as `cleaned.fif`:
- Created: `cleaned.fif`
- Created: `subject01_history.json` (in same directory)

## UI Mockup

```
┌─────────────────────────────────────────────┐
│  Dataset Information                    [X] │
├─────────────────────────────────────────────┤
│  Filename: subject01.vhdr                   │
│  Channels: 64                               │
│  Sampling Rate: 512 Hz                      │
│  Duration: 5.2 minutes                      │
│  ...existing info...                        │
│                                             │
│  ─────────── Processing History ─────────── │
│  ┌────────────────────────────────────────┐ │
│  │ [                                      │ │
│  │   {                                    │ │
│  │     "timestamp": "2026-01-08T14:32:15",│ │
│  │     "action": "data_loaded",           │ │
│  │     ...                                │ │
│  │   }                                    │ │
│  │ ]                                      │ │
│  └────────────────────────────────────────┘ │
│                         [Copy to Clipboard] │
└─────────────────────────────────────────────┘
```
