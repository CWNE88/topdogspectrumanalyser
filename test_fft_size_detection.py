import sys
from unittest.mock import MagicMock
for _mod in ('hackrf', 'rtlsdr', 'sounddevice', 'scipy', 'scipy.signal',
             'scipy.fft', 'pyqtgraph', 'pyqtgraph.opengl'):
    sys.modules.setdefault(_mod, MagicMock())

#!/usr/bin/env python3
"""Test to verify correct FFT size method detection for each source type."""

from datasources.hackrf_samples import HackrfSamplesDataSource
from datasources.rtl_samples import RtlSamplesDataSource
from datasources.audio_samples import MicrophoneSamplesDataSource

def test_attribute_detection():
    """Test that we can correctly detect which attribute each source uses."""
    print("Testing FFT Size Attribute Detection")
    print("=" * 70)

    # HackRF Samples
    print("\n### HackRF Samples ###")
    hackrf = HackrfSamplesDataSource(20e6, 2.45e9)
    print(f"Class name: {hackrf.__class__.__name__}")
    print(f"Has 'num_samples': {hasattr(hackrf, 'num_samples')}")
    print(f"Has 'fft_size': {hasattr(hackrf, 'fft_size')}")
    print(f"Has 'set_num_samples': {hasattr(hackrf, 'set_num_samples')}")
    print(f"Has 'set_fft_size': {hasattr(hackrf, 'set_fft_size')}")

    # Correct detection logic
    source_class_name = hackrf.__class__.__name__
    if hasattr(hackrf, 'num_samples') and 'Hackrf' in source_class_name:
        print(f"✓ Correct: Should use set_num_samples()")
        detected_method = "set_num_samples"
    elif hasattr(hackrf, 'fft_size'):
        print(f"✗ Wrong: Would use set_fft_size()")
        detected_method = "set_fft_size"
    else:
        print(f"✗ Error: No method detected")
        detected_method = "none"

    print(f"Detected method: {detected_method}")
    assert detected_method == "set_num_samples", "HackRF should use set_num_samples()"

    # RTL Samples
    print("\n" + "=" * 70)
    print("\n### RTL Samples ###")
    rtl = RtlSamplesDataSource(2e6, 100e6)
    print(f"Class name: {rtl.__class__.__name__}")
    print(f"Has 'num_samples': {hasattr(rtl, 'num_samples')}")
    print(f"Has 'fft_size': {hasattr(rtl, 'fft_size')}")
    print(f"Has 'set_num_samples': {hasattr(rtl, 'set_num_samples')}")
    print(f"Has 'set_fft_size': {hasattr(rtl, 'set_fft_size')}")

    # Correct detection logic
    source_class_name = rtl.__class__.__name__
    if hasattr(rtl, 'num_samples') and 'Hackrf' in source_class_name:
        print(f"✗ Wrong: Would use set_num_samples()")
        detected_method = "set_num_samples"
    elif hasattr(rtl, 'fft_size'):
        print(f"✓ Correct: Should use set_fft_size()")
        detected_method = "set_fft_size"
    else:
        print(f"✗ Error: No method detected")
        detected_method = "none"

    print(f"Detected method: {detected_method}")
    assert detected_method == "set_fft_size", "RTL should use set_fft_size()"

    # Microphone Samples
    print("\n" + "=" * 70)
    print("\n### Microphone Samples ###")
    mic = MicrophoneSamplesDataSource(44100, 0)
    print(f"Class name: {mic.__class__.__name__}")
    print(f"Has 'num_samples': {hasattr(mic, 'num_samples')}")
    print(f"Has 'fft_size': {hasattr(mic, 'fft_size')}")
    print(f"Has 'set_num_samples': {hasattr(mic, 'set_num_samples')}")
    print(f"Has 'set_fft_size': {hasattr(mic, 'set_fft_size')}")

    # Correct detection logic
    source_class_name = mic.__class__.__name__
    if hasattr(mic, 'num_samples') and 'Hackrf' in source_class_name:
        print(f"✗ Wrong: Would use set_num_samples()")
        detected_method = "set_num_samples"
    elif hasattr(mic, 'fft_size'):
        print(f"✓ Correct: Should use set_fft_size()")
        detected_method = "set_fft_size"
    else:
        print(f"✗ Error: No method detected")
        detected_method = "none"

    print(f"Detected method: {detected_method}")
    assert detected_method == "set_fft_size", "Microphone should use set_fft_size()"

    print("\n" + "=" * 70)
    print("\n✓ All attribute detections correct!")
    print("\nDetection Logic:")
    print("  1. Check if has 'num_samples' AND class name contains 'Hackrf'")
    print("     → Use set_num_samples() (HackRF only)")
    print("  2. Else if has 'fft_size'")
    print("     → Use set_fft_size() (RTL, Microphone)")
    print("\nThis prevents false positives from base class stub methods.")

if __name__ == "__main__":
    test_attribute_detection()
