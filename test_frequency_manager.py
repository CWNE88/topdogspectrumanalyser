#!/usr/bin/env python3
"""Tests for FrequencyManager and FrequencyRange logic."""

from utils.frequency_selector import FrequencyRange


def test_frequency_range_centre_span():
    """FrequencyRange correctly computes centre and span from start/stop."""
    print("### FrequencyRange: centre and span ###")
    fr = FrequencyRange(88e6, 108e6)
    assert abs(fr.centre - 98e6) < 1, f"centre wrong: {fr.centre}"
    assert abs(fr.span - 20e6) < 1, f"span wrong: {fr.span}"
    print(f"  centre={fr.centre/1e6:.3f} MHz, span={fr.span/1e6:.3f} MHz  ✓")


def test_frequency_range_set_centre():
    """set_centre preserves span."""
    print("### FrequencyRange: set_centre ###")
    fr = FrequencyRange(88e6, 108e6)
    fr.set_centre(100e6)
    assert abs(fr.span - 20e6) < 1, f"span changed after set_centre: {fr.span}"
    assert abs(fr.start - 90e6) < 1, f"start wrong: {fr.start}"
    assert abs(fr.stop - 110e6) < 1, f"stop wrong: {fr.stop}"
    print(f"  start={fr.start/1e6:.3f} MHz, stop={fr.stop/1e6:.3f} MHz  ✓")


def test_frequency_range_set_span():
    """set_span preserves centre."""
    print("### FrequencyRange: set_span ###")
    fr = FrequencyRange(88e6, 108e6)
    fr.set_span(10e6)
    assert abs(fr.centre - 98e6) < 1, f"centre changed after set_span: {fr.centre}"
    assert abs(fr.span - 10e6) < 1, f"span wrong: {fr.span}"
    print(f"  centre={fr.centre/1e6:.3f} MHz, span={fr.span/1e6:.3f} MHz  ✓")


def test_frequency_range_set_start_stop():
    """set_start_stop updates both endpoints and derived values."""
    print("### FrequencyRange: set_start_stop ###")
    fr = FrequencyRange(0, 1)
    fr.set_start_stop(2.4e9, 2.5e9)
    assert abs(fr.centre - 2.45e9) < 1, f"centre wrong: {fr.centre}"
    assert abs(fr.span - 100e6) < 1, f"span wrong: {fr.span}"
    print(f"  centre={fr.centre/1e9:.4f} GHz, span={fr.span/1e6:.1f} MHz  ✓")


def test_validators():
    """Validators clamp and validate correctly."""
    print("### Validators ###")
    from utils.validators import clamp_frequency, clamp_ref_level, clamp_range_db, validate_fft_size

    assert clamp_frequency(100e6, 24e6, 1.766e9) == 100e6
    assert clamp_frequency(1e6, 24e6, 1.766e9) == 24e6
    assert clamp_frequency(2e9, 24e6, 1.766e9) == 1.766e9
    print("  clamp_frequency  ✓")

    assert clamp_ref_level(0) == 0
    assert clamp_ref_level(200) == 100
    assert clamp_ref_level(-300) == -200
    print("  clamp_ref_level  ✓")

    assert validate_fft_size(1024) == 1024
    assert validate_fft_size(700) in (512, 1024)
    print("  validate_fft_size  ✓")


if __name__ == "__main__":
    print("=" * 60)
    print("FrequencyManager / Validators Tests")
    print("=" * 60)
    test_frequency_range_centre_span()
    test_frequency_range_set_centre()
    test_frequency_range_set_span()
    test_frequency_range_set_start_stop()
    test_validators()
    print("\nAll tests passed.")
