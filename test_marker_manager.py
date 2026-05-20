#!/usr/bin/env python3
"""Tests for MarkerManager logic (no Qt required)."""

import numpy as np
from core.marker_manager import MarkerManager


class _FakeFreq:
    start = 88e6
    stop = 108e6
    centre = 98e6
    span = 20e6


class _FakeFrequencyManager:
    """Minimal frequency_manager stub that tracks entry mode on the window."""
    def __init__(self, window):
        self._window = window

    def change_entry_mode(self, mode: str) -> None:
        self._window.frequency_entry_mode = mode


class _FakeWindow:
    """Minimal main_window stub."""
    def __init__(self):
        self.frequency = _FakeFreq()
        self.frequency_entry_mode = 'centre'
        self.ref_level = 0.0
        self.range_db = 100.0
        self.peak_threshold = -100.0
        self.peak_excursion = 6.0
        self.duty_cycle_enabled = False
        self.frequency_bins = np.linspace(88e6, 108e6, 512)
        self.live_power_levels = np.random.uniform(-80, -40, 512)
        self.marker_readout_label = None
        self.frequency_manager = _FakeFrequencyManager(self)
        # Stub display widgets
        self.two_d_widget = type('W', (), {
            'set_marker': lambda *a, **k: None,
            'clear_marker': lambda *a, **k: None,
        })()
        self.waterfall_widget = type('W', (), {
            'set_marker': lambda *a, **k: None,
            'clear_marker': lambda *a, **k: None,
        })()
        self.status_label = type('L', (), {'setText': lambda s, t: None})()


def test_toggle_marker():
    """Toggling a marker enables it and sets active."""
    print("### toggle_marker ###")
    mw = _FakeWindow()
    mm = MarkerManager(mw)

    assert not mm.markers['F1'].enabled
    mm.toggle_marker('F1')
    assert mm.markers['F1'].enabled
    assert mm.active_marker == 'F1'
    print("  F1 enabled and active  ✓")

    # Toggle off
    mm.toggle_marker('F1')
    assert not mm.markers['F1'].enabled
    assert mm.active_marker is None
    print("  F1 disabled  ✓")


def test_move_active():
    """move_active shifts a frequency marker by span/FREQ_STEPS per step."""
    print("### move_active ###")
    mw = _FakeWindow()
    mm = MarkerManager(mw)
    mm.toggle_marker('F1')
    start_pos = mm.markers['F1'].position
    mm.move_active(1)
    expected_step = mw.frequency.span / 200
    assert abs(mm.markers['F1'].position - (start_pos + expected_step)) < 1, \
        f"position {mm.markers['F1'].position} != {start_pos + expected_step}"
    print(f"  moved +{expected_step/1e3:.2f} kHz  ✓")


def test_reposition_on_frequency_change():
    """Proportional repositioning keeps marker at same relative position."""
    print("### reposition_on_frequency_change ###")
    mw = _FakeWindow()
    mm = MarkerManager(mw)
    mm.toggle_marker('F1')
    # Place at midpoint of old range
    mm.markers['F1'].position = 98e6  # centre of 88–108 MHz
    mm.reposition_on_frequency_change(88e6, 108e6, 90e6, 110e6)
    # Midpoint of new range: 100 MHz
    expected = 100e6
    assert abs(mm.markers['F1'].position - expected) < 1e3, \
        f"repositioned to {mm.markers['F1'].position/1e6:.3f} MHz, expected {expected/1e6:.3f} MHz"
    print(f"  repositioned to {mm.markers['F1'].position/1e6:.3f} MHz  ✓")


def test_clear_all():
    """clear_all disables all markers and clears active."""
    print("### clear_all ###")
    mw = _FakeWindow()
    mm = MarkerManager(mw)
    mm.toggle_marker('F1')
    mm.toggle_marker('F2')
    mm.clear_all()
    assert all(not m.enabled for m in mm.markers.values())
    assert mm.active_marker is None
    print("  all markers cleared  ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("MarkerManager Tests")
    print("=" * 60)
    test_toggle_marker()
    test_move_active()
    test_reposition_on_frequency_change()
    test_clear_all()
    print("\nAll tests passed.")
