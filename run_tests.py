#!/usr/bin/env python3
"""Run all test scripts and report a summary.

Usage:  python3 run_tests.py

Exit code 0 if all tests pass, 1 if any fail.
Tests that require unavailable hardware are skipped gracefully.
"""

import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

TESTS = [
    ("Smoke tests (no hardware)",     "test_smoke.py"),
    ("FFT size detection",            "test_fft_size_detection.py"),
    ("FFT size changes",              "test_fft_size_changes.py"),
    ("Frequency range",               "test_frequency_range.py"),
    ("Frequency manager",             "test_frequency_manager.py"),
    ("RBW calculation",               "test_rbw_calculation.py"),
    ("Span limits",                   "test_span_limits.py"),
    ("Marker manager",                "test_marker_manager.py"),
    ("Preset manager",                "test_preset_manager.py"),
    ("Duty cycle analyser",           "test_duty_cycle.py"),
]

HARDWARE_ERRORS = ("No module named 'hackrf'",
                   "No module named 'rtlsdr'",
                   "No module named 'sounddevice'")

passed = skipped = failed = 0
results = []

print("=" * 62)
print("Top Dog Spectrum Analyser — Test Suite")
print("=" * 62)

for label, script in TESTS:
    path = os.path.join(ROOT, script)
    if not os.path.exists(path):
        results.append(("SKIP", label, f"{script} not found"))
        skipped += 1
        continue

    proc = subprocess.run(
        [sys.executable, path],
        capture_output=True, text=True, cwd=ROOT
    )
    combined = proc.stdout + proc.stderr

    if proc.returncode == 0:
        results.append(("PASS", label, ""))
        passed += 1
    elif any(e in combined for e in HARDWARE_ERRORS):
        results.append(("SKIP", label, "hardware module not available"))
        skipped += 1
    else:
        # Extract last meaningful line as a short reason
        lines = [l.strip() for l in combined.splitlines() if l.strip()]
        reason = lines[-1] if lines else "unknown error"
        results.append(("FAIL", label, reason))
        failed += 1

print()
for status, label, detail in results:
    icon = {"PASS": "✓", "SKIP": "—", "FAIL": "✗"}[status]
    line = f"  {icon} {label}"
    if detail:
        line += f"  ({detail})"
    print(line)

print()
print(f"Results: {passed} passed, {skipped} skipped, {failed} failed")
print("=" * 62)

sys.exit(1 if failed else 0)
