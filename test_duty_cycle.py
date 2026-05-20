#!/usr/bin/env python3
"""Tests for DutyCycleAnalyser logic (no Qt required)."""

import numpy as np
from core.duty_cycle import DutyCycleAnalyser


def test_duty_cycle_all_on():
    """When all frames exceed threshold, duty cycle is 100%."""
    print("### duty cycle all ON ###")
    dc = DutyCycleAnalyser()
    data = np.full(512, -30.0)  # all above -60 dBm
    for _ in range(50):
        dc.update_from_power(data)
    assert abs(dc.duty_pct - 100.0) < 0.1, f"duty_pct={dc.duty_pct}"
    assert dc.on_power_dbm is not None
    assert dc.off_power_dbm is None
    print(f"  duty={dc.duty_pct:.1f}%  ✓")


def test_duty_cycle_all_off():
    """When all frames are below threshold, duty cycle is 0%."""
    print("### duty cycle all OFF ###")
    dc = DutyCycleAnalyser()
    data = np.full(512, -90.0)  # all below -60 dBm
    for _ in range(50):
        dc.update_from_power(data)
    assert abs(dc.duty_pct - 0.0) < 0.1, f"duty_pct={dc.duty_pct}"
    assert dc.on_power_dbm is None
    assert dc.off_power_dbm is not None
    print(f"  duty={dc.duty_pct:.1f}%  ✓")


def test_duty_cycle_fifty_fifty():
    """50% on / 50% off produces approximately 50% duty cycle."""
    print("### duty cycle 50/50 ###")
    dc = DutyCycleAnalyser()
    on_data  = np.full(512, -30.0)
    off_data = np.full(512, -90.0)
    for i in range(100):
        dc.update_from_power(on_data if i % 2 == 0 else off_data)
    assert abs(dc.duty_pct - 50.0) < 2.0, f"duty_pct={dc.duty_pct}"
    print(f"  duty={dc.duty_pct:.1f}%  ✓")


def test_duty_cycle_reset():
    """reset() clears all accumulated state."""
    print("### duty cycle reset ###")
    dc = DutyCycleAnalyser()
    data = np.full(512, -30.0)
    for _ in range(50):
        dc.update_from_power(data)
    dc.reset()
    assert dc.duty_pct == 0.0
    assert dc.on_power_dbm is None
    assert dc.off_power_dbm is None
    print("  reset cleared state  ✓")


def test_duty_cycle_readout():
    """get_readout() returns non-empty HTML when data is available."""
    print("### duty cycle get_readout ###")
    dc = DutyCycleAnalyser()
    data = np.linspace(-80, -20, 512)
    for _ in range(20):
        dc.update_from_power(data)
    readout = dc.get_readout()
    assert readout, "get_readout() returned empty string"
    assert "Duty" in readout
    assert "%" in readout
    print(f"  readout contains expected text  ✓")


def test_threshold_attribute():
    """threshold_dbm attribute is updated when update_from_power is called with a threshold."""
    print("### threshold_dbm attribute ###")
    dc = DutyCycleAnalyser()
    assert dc.threshold_dbm == -60.0
    dc.update_from_power(np.full(512, -30.0), threshold_dbm=-40.0)
    assert dc.threshold_dbm == -40.0
    print("  threshold_dbm updated  ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("DutyCycleAnalyser Tests")
    print("=" * 60)
    test_duty_cycle_all_on()
    test_duty_cycle_all_off()
    test_duty_cycle_fifty_fifty()
    test_duty_cycle_reset()
    test_duty_cycle_readout()
    test_threshold_attribute()
    print("\nAll tests passed.")
