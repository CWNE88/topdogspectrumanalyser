#!/usr/bin/env python3
"""Smoke tests — no Qt, no hardware required.

Hardware modules (hackrf, rtlsdr, sounddevice) are mocked via sys.modules
before any application code is imported, so this suite runs on any machine
without SDR devices attached.

Covers:
- Utility functions (format_hz, clamp_centre_span, EntryMode, validators)
- Signal processing (TraceAverager)
- FrequencyRange
- Data processor and export manager structure
- TareState dataclass
- Menu system (MenuItem, MenuManager)
- Constants completeness
- Preset manager file I/O
"""

import sys
import traceback
from unittest.mock import MagicMock

# ------------------------------------------------------------------
# Mock hardware modules before any application import
# ------------------------------------------------------------------
_HW_MOCKS = {
    'hackrf':      MagicMock(),
    'rtlsdr':      MagicMock(),
    'sounddevice': MagicMock(),
    'scipy':       MagicMock(),
    'scipy.signal':MagicMock(),
    'scipy.fft':   MagicMock(),
    'pyqtgraph':   MagicMock(),
    'pyqtgraph.opengl': MagicMock(),
}
for name, mock in _HW_MOCKS.items():
    sys.modules.setdefault(name, mock)

import numpy as np

PASS = "  ✓"
FAIL = "  ✗"
errors: list = []


def check(label: str, fn):
    try:
        fn()
        print(f"{PASS} {label}")
    except Exception as e:
        print(f"{FAIL} {label}")
        print(f"      {type(e).__name__}: {e}")
        errors.append((label, traceback.format_exc()))


# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------
print("\n── Utilities ──")


def _test_format_hz():
    from utils.frequency_helpers import format_hz
    assert format_hz(440)    == "440.0 Hz"
    assert format_hz(22e3)   == "22 kHz"
    assert format_hz(98.8e6) == "98.8 MHz"
    assert format_hz(1.4e9)  == "1.4 GHz"
    assert format_hz(2.45e9) == "2.45 GHz"

check("format_hz produces correct units", _test_format_hz)


def _test_clamp_centre_span():
    from utils.validators import clamp_centre_span
    limits = {'rtl': {'min': 24e6, 'max': 1766e6, 'max_span': 2.4e6}}
    c, s = clamp_centre_span(98e6, 1e6, 'rtl', limits)
    assert c == 98e6 and s == 1e6, "nominal case changed"
    # span clamped to max_span
    c, s = clamp_centre_span(98e6, 5e6, 'rtl', limits)
    assert s == 2.4e6, f"span not clamped: {s}"
    # centre slid when window would overshoot min
    c, s = clamp_centre_span(24e6, 2e6, 'rtl', limits)
    assert c >= 24e6, f"centre below hw_min: {c}"
    # unknown source type: pass-through
    c2, s2 = clamp_centre_span(500e6, 10e6, 'unknown', limits)
    assert c2 == 500e6 and s2 == 10e6

check("clamp_centre_span clamps span and slides window", _test_clamp_centre_span)


def _test_entry_mode_enum():
    from utils.constants import EntryMode
    assert EntryMode.CENTRE == 'centre'
    assert EntryMode.WF_FLOOR == 'wf_floor'
    assert EntryMode.MARKER == 'marker'
    # str inheritance: membership tests work with raw strings
    assert EntryMode.CENTRE in {'centre', 'start', 'stop'}

check("EntryMode backward-compatible with str comparisons", _test_entry_mode_enum)


def _test_source_type_enum():
    from utils.constants import SourceType
    assert SourceType.RTL_SAMPLES.value   == 'rtl_samples'
    assert SourceType.HACKRF_SWEEP.value  == 'hackrf_sweep'
    assert SourceType.MICROPHONE_SAMPLES.value == 'microphone_samples'

check("SourceType values are snake_case strings", _test_source_type_enum)


def _test_display_mode_enum():
    from utils.constants import DisplayMode
    assert DisplayMode.TWO_D     == 0
    assert DisplayMode.WATERFALL == 2
    assert DisplayMode.LOGO      == 4
    assert DisplayMode.DENSITY   == 9

check("DisplayMode indices unchanged after refactor", _test_display_mode_enum)


def _test_validate_fft():
    from utils.validators import validate_fft_size
    assert validate_fft_size(1024) == 1024
    assert validate_fft_size(512)  == 512
    nearest = validate_fft_size(700)
    assert nearest in (512, 1024), f"unexpected nearest: {nearest}"

check("validate_fft_size returns valid power-of-2 size", _test_validate_fft)


# ------------------------------------------------------------------
# Signal processing
# ------------------------------------------------------------------
print("\n── Signal processing ──")


def _test_trace_averager_passthrough():
    from utils.signal_processing import TraceAverager
    ta = TraceAverager()
    data = np.ones(128, dtype=np.float64)
    assert ta.is_active == False
    out = ta.process(data)
    assert np.allclose(out, data)

check("TraceAverager passthrough when inactive", _test_trace_averager_passthrough)


def _test_trace_averager_exp():
    from utils.signal_processing import TraceAverager
    ta = TraceAverager()
    ta.set_mode('exp', 4)
    assert ta.is_active
    data_low  = np.ones(64, dtype=np.float64) * 10.0
    data_high = np.ones(64, dtype=np.float64) * 20.0
    # First frame initialises buffer — copy because _buffer is returned in-place
    val_after_low = ta.process(data_low).copy()[0]
    assert val_after_low == 10.0, f"first frame should equal input, got {val_after_low}"
    # Second frame blends toward higher value
    val_after_high = ta.process(data_high).copy()[0]
    assert val_after_high > val_after_low, (
        f"blended value {val_after_high} should exceed initial {val_after_low}")

check("TraceAverager exponential blending moves toward new input", _test_trace_averager_exp)


def _test_trace_averager_reset():
    from utils.signal_processing import TraceAverager
    ta = TraceAverager()
    ta.set_mode('exp', 4)
    ta.process(np.full(64, np.nan))   # NaN first frame
    ta.reset()                         # explicit reset
    out = ta.process(np.ones(64) * 5.0)
    assert not np.any(np.isnan(out)), "NaN persisted after reset"

check("TraceAverager reset clears NaN buffer", _test_trace_averager_reset)


# ------------------------------------------------------------------
# FrequencyRange
# ------------------------------------------------------------------
print("\n── FrequencyRange ──")


def _test_frequency_range_basics():
    from utils.frequency_selector import FrequencyRange
    fr = FrequencyRange(88e6, 108e6)
    assert abs(fr.centre - 98e6) < 1,  f"centre: {fr.centre}"
    assert abs(fr.span   - 20e6) < 1,  f"span:   {fr.span}"
    fr.set_centre(100e6)
    assert abs(fr.centre - 100e6) < 1, f"new centre: {fr.centre}"
    assert abs(fr.span   - 20e6)  < 1, f"span after centre shift: {fr.span}"

check("FrequencyRange centre/span symmetric around midpoint", _test_frequency_range_basics)


def _test_frequency_range_set_span():
    from utils.frequency_selector import FrequencyRange
    fr = FrequencyRange(88e6, 108e6)
    fr.set_span(10e6)
    assert abs(fr.span   - 10e6) < 1, f"span: {fr.span}"
    assert abs(fr.centre - 98e6) < 1, f"centre after span change: {fr.centre}"

check("FrequencyRange set_span preserves centre", _test_frequency_range_set_span)


def _test_frequency_range_set_start():
    from utils.frequency_selector import FrequencyRange
    fr = FrequencyRange(88e6, 108e6)
    fr.set_start(90e6)
    assert abs(fr.start - 90e6) < 1
    assert abs(fr.stop  - 108e6) < 1  # stop unchanged

check("FrequencyRange set_start moves start, preserves stop", _test_frequency_range_set_start)


# ------------------------------------------------------------------
# Data processor structure
# ------------------------------------------------------------------
print("\n── Data processor ──")


def _test_data_processor_methods():
    from core.display_data_processor import DataProcessor
    methods = set(dir(DataProcessor))
    required = {
        'update_data', '_process_sample_data', '_process_sweep_data',
        '_process_constellation_data', '_process_zero_span_data',
        '_find_top_peaks', '_nan_safe', '_apply_tare', '_apply_cal_offset',
        '_update_max_hold', '_update_min_hold', '_update_duty_cycle',
        '_update_peak_list', 'reset_sweep_averager',
        '_dispatch_widget_data', '_refresh_display',
    }
    missing = required - methods
    assert not missing, f"Missing DataProcessor methods: {missing}"

check("DataProcessor has all required methods", _test_data_processor_methods)


def _test_find_top_peaks():
    from core.display_data_processor import DataProcessor
    freq  = np.linspace(88e6, 108e6, 1000)
    power = np.full(1000, -80.0)
    # Plant three proper peaks with a Gaussian shape so local maxima exist
    for centre_hz, amp in [(91e6, -50.0), (98e6, -45.0), (105e6, -55.0)]:
        idx = int((centre_hz - 88e6) / 20e6 * 1000)
        for k in range(-8, 9):
            if 0 <= idx + k < 1000:
                power[idx + k] = amp - (k * k) * 0.3  # Gaussian drop-off

    peaks = DataProcessor._find_top_peaks(
        freq, power, n=5, min_sep_bins=30, min_excursion_db=5.0
    )
    assert len(peaks) == 3, f"Expected 3 peaks, got {len(peaks)}: {peaks}"
    peak_freqs = sorted(f for f, _ in peaks)
    assert abs(peak_freqs[0] - 91e6) < 1e6, f"Peak 1 at {peak_freqs[0]/1e6:.1f} MHz"
    assert abs(peak_freqs[1] - 98e6) < 1e6, f"Peak 2 at {peak_freqs[1]/1e6:.1f} MHz"
    assert abs(peak_freqs[2] - 105e6) < 1e6, f"Peak 3 at {peak_freqs[2]/1e6:.1f} MHz"

check("_find_top_peaks locates three planted Gaussian peaks", _test_find_top_peaks)


def _test_nan_safe():
    from core.display_data_processor import DataProcessor
    arr = np.array([1.0, np.nan, 3.0])
    out = DataProcessor._nan_safe(arr, -999.0)
    assert out[1] == -999.0
    assert not np.any(np.isnan(out))
    # Clean arrays returned without copy
    clean = np.array([1.0, 2.0, 3.0])
    assert DataProcessor._nan_safe(clean, 0.0) is clean

check("_nan_safe replaces NaN, passes clean arrays through", _test_nan_safe)


def _test_export_manager_methods():
    from core.export_manager import ExportManager
    methods = set(dir(ExportManager))
    for m in ['export_display', 'export_window', '_ensure_ext', '_save_pixmap']:
        assert m in methods, f"Missing ExportManager.{m}"

check("ExportManager has all required methods", _test_export_manager_methods)


def _test_ensure_ext():
    from core.export_manager import ExportManager
    assert ExportManager._ensure_ext("foo", ".png")  == "foo.png"
    assert ExportManager._ensure_ext("foo.png", ".png") == "foo.png"
    assert ExportManager._ensure_ext("FOO.PNG", ".png") == "FOO.PNG"

check("ExportManager._ensure_ext appends extension only when missing", _test_ensure_ext)


# ------------------------------------------------------------------
# TareState
# ------------------------------------------------------------------
print("\n── TareState ──")


def _test_tare_state():
    from core.display_manager import TareState
    ts = TareState()
    assert not ts.collecting
    assert ts.buffer is None
    assert ts.count == 0
    ts2 = TareState(collecting=True)
    assert ts2.collecting
    assert ts2.buffer is None  # buffer independent of collecting flag

check("TareState initialises correctly", _test_tare_state)


# ------------------------------------------------------------------
# Menu system
# ------------------------------------------------------------------
print("\n── Menu system ──")


def _test_menu_item():
    from menu.menu_manager import MenuItem
    item = MenuItem("btnTest", "Test\nLabel")
    assert item.id    == "btnTest"
    assert item.label == "Test\nLabel"
    assert item.sub_menu == []
    # With sub_menu
    child = MenuItem("btnChild", "Child")
    parent = MenuItem("btnParent", "Parent", sub_menu=[child])
    assert len(parent.sub_menu) == 1

check("MenuItem constructs with and without sub_menu", _test_menu_item)


# ------------------------------------------------------------------
# Constants completeness
# ------------------------------------------------------------------
print("\n── Constants ──")


def _test_menu_button_id_coverage():
    from utils.constants import MenuButtonId
    values = {e.value for e in MenuButtonId}
    spot = [
        'btnCentreFrequency', 'btnSpan', 'btnFullSpan',
        'btnRtlSamples', 'btnHackrfSamples', 'btnMicrophoneSamples',
        'btnAvgOff', 'btnAvgExp2', 'btnAvgLin64',
        'btnMarkerF1', 'btnPeakList',
        'btnBwNotAvailable', 'btnGainNotAvailable',
        'btnExportDisplayPng', 'btnExportWindowJpeg',
    ]
    missing = [v for v in spot if v not in values]
    assert not missing, f"Missing MenuButtonId values: {missing}"

check("MenuButtonId spot-check covers all expected IDs", _test_menu_button_id_coverage)


def _test_source_limits_completeness():
    from core.source_manager import SourceManager
    from utils.constants import SourceType
    required = {
        SourceType.RTL_SWEEP.value,
        SourceType.HACKRF_SWEEP.value,
        SourceType.RTL_SAMPLES.value,
        SourceType.HACKRF_SAMPLES.value,
        SourceType.MICROPHONE_SAMPLES.value,
    }
    limits = SourceManager._SOURCE_LIMITS
    missing = required - set(limits.keys())
    assert not missing, f"Missing source limits for: {missing}"
    for src, lim in limits.items():
        assert 'min' in lim and 'max' in lim and 'max_span' in lim, \
            f"Incomplete limits for {src}: {lim}"
        assert lim['max'] > lim['min'], f"Invalid range for {src}"

check("SourceManager._SOURCE_LIMITS covers all source types with valid ranges",
      _test_source_limits_completeness)


def _test_full_span_dict():
    from core.display_manager import DisplayManager
    from utils.constants import SourceType
    fs = DisplayManager._FULL_SPAN
    assert SourceType.HACKRF_SWEEP.value in fs
    assert SourceType.RTL_SWEEP.value    in fs
    for key, (start, stop, label) in fs.items():
        assert stop > start, f"Invalid range for {key}: {start} – {stop}"
        assert isinstance(label, str) and len(label) > 0

check("DisplayManager._FULL_SPAN has valid ranges for all sweep sources",
      _test_full_span_dict)


# ------------------------------------------------------------------
# Preset manager (file I/O, no Qt)
# ------------------------------------------------------------------
print("\n── Preset manager ──")


def _test_preset_manager_slots():
    from core.preset_manager import PresetManager, NUM_SLOTS

    class _FakeMW:
        pass

    assert NUM_SLOTS == 8
    pm = PresetManager(_FakeMW())
    for i in range(1, NUM_SLOTS + 1):
        label = pm.slot_label(i)
        assert isinstance(label, str) and len(label) > 0, \
            f"slot_label({i}) returned empty or non-string: {label!r}"

check("PresetManager loads and all slot labels are non-empty strings",
      _test_preset_manager_slots)


# ------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------
total = 22
print(f"\n{'=' * 60}")
if errors:
    print(f"FAILED: {len(errors)} / {total} test(s)")
    for label, tb in errors:
        print(f"\n  ✗ {label}")
        for line in tb.strip().split('\n'):
            print(f"    {line}")
    sys.exit(1)
else:
    print(f"All {total} smoke tests passed.")
