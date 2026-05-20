# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running and Installing

```bash
pip install -r requirements.txt
python3 main.py
```

## Tests

Tests are standalone scripts in the project root (no pytest/unittest runner):

```bash
python3 test_fft_size_detection.py
python3 test_frequency_range.py
python3 test_rbw_calculation.py
python3 test_span_limits.py
python3 test_fft_size_changes.py
```

No linting or formatting tooling is configured.

## Architecture

The application is a PyQt6 GUI spectrum analyser supporting HackRF, RTL-SDR, and microphone backends with real-time FFT-based visualisation.

### Data flow

```
Hardware / mic  →  datasource  →  main.py process_samples()
                                      ↓
                               DSP (FFT, windowing, dB)
                                      ↓
                            DisplayManager  →  plot widgets
```

**Sweep sources** (`rtl_sweep.py`, `hackrf_sweep.py`) wrap external CLI tools (`rtl_power`, `hackrf_sweep`) and return pre-binned power data directly to the display — no local FFT.

**Sample sources** (`rtl_samples.py`, `hackrf_samples.py`, `audio_samples.py`) return raw IQ samples; `MainWindow.process_samples()` applies a window function and FFT via `utils/signal_processing.py` before passing data to `DisplayManager`.

### Key modules

| Path | Role |
|------|------|
| `main.py` | `MainWindow` — app state, event routing, coordinates all managers |
| `core/display_manager.py` | Plot updates, peak search, max hold, tare, display mode switching |
| `core/frequency_manager.py` | Keeps centre/start/stop/span in sync; updates status labels |
| `core/source_manager.py` | Instantiates and switches data sources; clamps frequencies to hardware limits |
| `core/popout_window.py` | Pops display widget into a separate window (clones OpenGL widgets; reparents Qt widgets) |
| `datasources/base.py` | Abstract `SweepDataSource` and `SampleDataSource` interfaces |
| `displays/` | PyQtGraph 2D, waterfall, and OpenGL 3D/surface plot widgets |
| `utils/signal_processing.py` | FFT, windowing, magnitude, dB conversion, PSD, IIR filter |
| `utils/frequency_selector.py` | `FrequencyRange` — single source of truth for frequency state |
| `utils/constants.py` | Enums, hardware limits, UI constants |
| `menu/menu_manager.py` | Soft-button (F1–F8) hierarchical menu system |

### UI

The window layout is defined in `main_window_horizontal.ui` / `main_window_vertical.ui` (Qt Designer files). Soft buttons `btn_soft_1`–`btn_soft_8` are dynamically relabelled by the menu system. Pop-out is triggered with **Alt+Enter**; OpenGL-based displays (3D, Surface) are cloned rather than reparented.

### Conventions

- British English spelling throughout (initialise, centre, analyse).
- FFT size must be a power of 2 between 512 and 8192.
- RBW = `sample_rate / fft_size` for sample sources; bin size reported directly for sweep sources.
- Debug-level logging is used extensively — module-level `logging.getLogger(__name__)`.

### Known limitations (from README)

- Frequency changes may cause plot failures; Surface plot is not fully integrated.
- Max hold remnants visible on reactivation; peak search does not work with max hold.
- Waterfall colour map options are non-functional.
