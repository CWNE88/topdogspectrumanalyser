#!/usr/bin/env python3
"""Tests for PresetManager: slot operations and capture/apply round-trips.

Verifies that each manager's capture_preset() and apply_preset() use
matching key names, and that the coordinator correctly delegates.
No Qt or hardware required.
"""

import sys
from unittest.mock import MagicMock

# Mock hardware before any app import
for mod in ('hackrf', 'rtlsdr', 'sounddevice', 'scipy', 'scipy.signal',
            'scipy.fft', 'pyqtgraph', 'pyqtgraph.opengl'):
    sys.modules.setdefault(mod, MagicMock())

import numpy as np
import tempfile
import core.preset_manager as pm_module
from core.preset_manager import PresetManager, NUM_SLOTS

# Redirect PRESET_FILE to a temp file so tests don't touch real saved presets
_tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
_tmp.close()
pm_module.PRESET_FILE = _tmp.name


# ---------------------------------------------------------------------------
# Minimal stubs
# ---------------------------------------------------------------------------

class _FakeSource:
    sample_count = 1024
    window_type  = 'hamming'
    bin_size     = None

class _FakeFreq:
    start = 88e6
    stop  = 108e6

class _FakeFrequencyManager:
    def __init__(self, mw):
        self._mw = mw
    def change_entry_mode(self, mode): pass
    def capture_preset(self):
        f = self._mw.frequency
        return {'freq_start': float(f.start), 'freq_stop': float(f.stop)}
    def apply_preset(self, s):
        self._mw.frequency.start = s.get('freq_start', self._mw.frequency.start)
        self._mw.frequency.stop  = s.get('freq_stop',  self._mw.frequency.stop)

class _FakeMarkerManager:
    active_marker = None
    markers = {}
    def clear_all(self): pass
    def _sync_display(self, name): pass
    def _refresh_status(self): pass
    def capture_preset(self):
        return {'markers': {}, 'active_marker': None}
    def apply_preset(self, s): pass

class _FakeSourceManager:
    SOURCE_CLASSES = {}
    SOURCE_DISPLAY_NAMES = {}
    last_source_type = 'rtl_samples'
    def capture_preset(self):
        return {'source_type': self.last_source_type,
                'fft_size': 1024, 'window_type': 'hamming', 'sweep_bin_size': None}
    def apply_preset(self, s): pass

class _FakeDisplayManager:
    persistence_mode   = 'off'
    live_trace_visible = True
    constellation_modulation = 'qpsk'
    constellation_range      = 1.5
    constellation_points     = 2000

    def __init__(self, mw):
        self._mw = mw

    def capture_preset(self):
        mw = self._mw
        return {
            'ref_level': mw.ref_level, 'range_db': mw.range_db,
            'log_scale': mw.log_scale, 'log_freq': mw.log_freq,
            'avg_mode': mw.avg_mode, 'avg_n': mw.avg_n,
            'persistence_mode': self.persistence_mode,
            'threshold_enabled': mw.threshold_enabled,
            'peak_threshold': mw.peak_threshold, 'peak_excursion': mw.peak_excursion,
            'display_line_enabled': mw.display_line_enabled,
            'display_line_level': mw.display_line_level,
            'display_mode': 0, 'analysis_mode': mw.analysis_mode,
            'display_format': 0, 'duty_cycle_enabled': mw.duty_cycle_enabled,
            'peak_search_enabled': mw.peak_search_enabled,
            'max_hold_enabled': mw.max_peak_search_enabled,
            'wf_floor': -100.0, 'wf_ceiling': -20.0,
            'wf_time_span': 60.0, 'wf_colourmap': 'magma',
            'two_d_fill_type': 'off', 'two_d_colour': 'green',
            'density_colourmap': 'magma', 'density_decay': 'medium',
            'three_d_history_lines': 300, 'three_d_grid_visible': True,
            'three_d_auto_rotate': False,
        }

    def apply_preset(self, s):
        mw = self._mw
        mw.ref_level = s.get('ref_level', mw.ref_level)
        mw.range_db  = s.get('range_db',  mw.range_db)
        mw.log_scale = s.get('log_scale', mw.log_scale)
        self.persistence_mode = s.get('persistence_mode', self.persistence_mode)
        mw.avg_mode = s.get('avg_mode', mw.avg_mode)
        mw.avg_n    = s.get('avg_n',    mw.avg_n)


class _FakeWindow:
    def __init__(self):
        self.frequency             = _FakeFreq()
        self.ref_level             = 0.0
        self.range_db              = 100.0
        self.log_scale             = True
        self.log_freq              = False
        self.avg_mode              = 'off'
        self.avg_n                 = 1
        self.threshold_enabled     = False
        self.peak_threshold        = -100.0
        self.peak_excursion        = 6.0
        self.display_line_enabled  = False
        self.display_line_level    = -50.0
        self.analysis_mode         = 'fft'
        self.duty_cycle_enabled    = False
        self.peak_search_enabled   = False
        self.max_peak_search_enabled = False
        self.status_label          = type('L', (), {'setText': lambda s, t: None})()
        self.input_value           = type('I', (), {'setText': lambda s, t: None})()
        self.source_manager        = _FakeSourceManager()
        self.frequency_manager     = _FakeFrequencyManager(self)
        self.marker_manager        = _FakeMarkerManager()
        self.display_manager       = _FakeDisplayManager(self)

    def set_window_type(self, wt): pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_slot_label_empty():
    print("### slot labels — empty slots ###")
    pm = PresetManager(_FakeWindow())
    for i in range(1, NUM_SLOTS + 1):
        label = pm.slot_label(i)
        assert 'Empty' in label or str(i) in label, f"Unexpected label: {label!r}"
    print(f"  {NUM_SLOTS} empty slot labels OK  ✓")


def test_save_and_recall_name():
    print("### save preserves name, recall restores it ###")
    mw = _FakeWindow()
    pm = PresetManager(mw)
    pm.set_pending_op('save')
    pm.execute_slot(1)
    assert pm.slot_label(1) != f"Slot 1\nEmpty"
    pm.set_pending_op('name')
    pm.execute_slot(1)
    pm.confirm_name(1, "FM Radio")
    assert "FM Radio" in pm.slot_label(1), f"Name not stored: {pm.slot_label(1)!r}"
    print("  save + name round-trip OK  ✓")


def test_delete():
    print("### delete empties slot ###")
    mw = _FakeWindow()
    pm = PresetManager(mw)
    pm.set_pending_op('save')
    pm.execute_slot(3)
    assert 'Empty' not in pm.slot_label(3)
    pm.set_pending_op('delete')
    pm.execute_slot(3)
    assert 'Empty' in pm.slot_label(3), f"Slot not empty after delete: {pm.slot_label(3)!r}"
    print("  delete clears slot  ✓")


def test_capture_apply_key_consistency():
    """Every key written by capture_preset must be readable by apply_preset
    without KeyError — i.e. apply uses .get() with defaults."""
    print("### capture/apply key consistency ###")
    mw = _FakeWindow()
    pm = PresetManager(mw)

    captured = pm._capture()
    # Verify all expected keys are present
    required = {
        'source_type', 'fft_size', 'window_type', 'sweep_bin_size',
        'freq_start', 'freq_stop',
        'ref_level', 'range_db', 'log_scale', 'log_freq',
        'avg_mode', 'avg_n', 'persistence_mode',
        'threshold_enabled', 'peak_threshold', 'peak_excursion',
        'display_line_enabled', 'display_line_level',
        'display_mode', 'analysis_mode', 'display_format', 'duty_cycle_enabled',
        'peak_search_enabled', 'max_hold_enabled',
        'wf_floor', 'wf_ceiling', 'wf_time_span', 'wf_colourmap',
        'two_d_fill_type', 'two_d_colour',
        'density_colourmap', 'density_decay',
        'three_d_history_lines', 'three_d_grid_visible', 'three_d_auto_rotate',
        'markers', 'active_marker',
    }
    missing = required - set(captured.keys())
    assert not missing, f"capture_preset() missing keys: {missing}"
    print(f"  {len(captured)} keys captured  ✓")

    # Apply should not raise with a complete dict
    try:
        pm._apply(captured)
    except Exception as e:
        raise AssertionError(f"apply_preset raised on full capture: {e}") from e
    print("  apply_preset accepts full capture without error  ✓")


def test_apply_with_missing_keys():
    """apply_preset must tolerate an empty dict gracefully (all defaults)."""
    print("### apply_preset with empty dict ###")
    mw = _FakeWindow()
    pm = PresetManager(mw)
    try:
        pm._apply({})
    except Exception as e:
        raise AssertionError(f"apply_preset raised on empty dict: {e}") from e
    print("  apply_preset handles empty dict  ✓")


def test_round_trip_values():
    """Values captured should be restored correctly."""
    print("### round-trip value fidelity ###")
    mw = _FakeWindow()
    mw.ref_level = -10.0
    mw.range_db  = 80.0
    mw.avg_mode  = 'exp'
    mw.avg_n     = 8

    pm = PresetManager(mw)
    captured = pm._capture()

    # Mutate state
    mw.ref_level = 0.0
    mw.range_db  = 100.0
    mw.avg_mode  = 'off'
    mw.avg_n     = 1

    pm._apply(captured)

    assert mw.ref_level == -10.0, f"ref_level not restored: {mw.ref_level}"
    assert mw.range_db  == 80.0,  f"range_db not restored:  {mw.range_db}"
    assert mw.avg_mode  == 'exp',  f"avg_mode not restored:  {mw.avg_mode}"
    assert mw.avg_n     == 8,      f"avg_n not restored:     {mw.avg_n}"
    print("  ref_level, range_db, avg_mode, avg_n restored correctly  ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("PresetManager Tests")
    print("=" * 60)
    test_slot_label_empty()
    test_save_and_recall_name()
    test_delete()
    test_capture_apply_key_consistency()
    test_apply_with_missing_keys()
    test_round_trip_values()
    print("\nAll tests passed.")
