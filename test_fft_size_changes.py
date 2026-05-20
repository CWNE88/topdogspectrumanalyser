import sys
from unittest.mock import MagicMock
for _mod in ('hackrf', 'rtlsdr', 'sounddevice', 'scipy', 'scipy.signal',
             'scipy.fft', 'pyqtgraph', 'pyqtgraph.opengl'):
    sys.modules.setdefault(_mod, MagicMock())

#!/usr/bin/env python3
"""Test script to verify FFT size changes and RBW updates."""

from datasources.hackrf_samples import HackrfSamplesDataSource
from datasources.rtl_samples import RtlSamplesDataSource
from datasources.audio_samples import MicrophoneSamplesDataSource

def test_fft_size_changes():
    """Test that FFT size changes work correctly and update RBW."""
    print("Testing FFT Size Changes and RBW Updates")
    print("=" * 70)

    # Test HackRF Samples (uses set_num_samples)
    print("\n### HackRF Samples (uses set_num_samples) ###\n")
    hackrf = HackrfSamplesDataSource(20e6, 2.45e9)
    print(f"Initial state:")
    print(f"  Sample rate: {hackrf.sample_rate/1e6:.2f} MHz")
    print(f"  num_samples: {hackrf.num_samples}")
    print(f"  RBW = {hackrf.sample_rate/1e6:.2f} MHz / {hackrf.num_samples} = {(hackrf.sample_rate/hackrf.num_samples)/1e3:.2f} kHz")

    for size in [512, 1024, 2048, 4096]:
        hackrf.set_num_samples(size)
        rbw = hackrf.sample_rate / hackrf.num_samples
        print(f"\nAfter set_num_samples({size}):")
        print(f"  num_samples: {hackrf.num_samples}")
        print(f"  RBW = {hackrf.sample_rate/1e6:.2f} MHz / {size} = {rbw/1e3:.2f} kHz")
        assert hackrf.num_samples == size, f"Expected num_samples={size}, got {hackrf.num_samples}"
        print(f"  ✓ Verified: num_samples changed to {size}")

    # Test RTL Samples (uses set_fft_size)
    print("\n" + "=" * 70)
    print("\n### RTL Samples (uses set_fft_size) ###\n")
    rtl = RtlSamplesDataSource(2e6, 100e6)
    print(f"Initial state:")
    print(f"  Sample rate: {rtl.sample_rate/1e6:.2f} MHz")
    print(f"  fft_size: {rtl.fft_size}")
    print(f"  RBW = {rtl.sample_rate/1e6:.2f} MHz / {rtl.fft_size} = {(rtl.sample_rate/rtl.fft_size)/1e3:.2f} kHz")

    for size in [512, 1024, 2048, 4096]:
        rtl.set_fft_size(size)
        rbw = rtl.sample_rate / rtl.fft_size
        print(f"\nAfter set_fft_size({size}):")
        print(f"  fft_size: {rtl.fft_size}")
        print(f"  Window length: {len(rtl.window)}")
        print(f"  RBW = {rtl.sample_rate/1e6:.2f} MHz / {size} = {rbw/1e3:.2f} kHz")
        assert rtl.fft_size == size, f"Expected fft_size={size}, got {rtl.fft_size}"
        assert len(rtl.window) == size, f"Window size should match FFT size"
        print(f"  ✓ Verified: fft_size changed to {size}, window resized")

    # Test Microphone Samples (uses set_fft_size)
    print("\n" + "=" * 70)
    print("\n### Microphone Samples (uses set_fft_size) ###\n")
    mic = MicrophoneSamplesDataSource(44100, 0)
    print(f"Initial state:")
    print(f"  Sample rate: {mic.sample_rate/1e3:.2f} kHz")
    print(f"  fft_size: {mic.fft_size}")
    print(f"  RBW = {mic.sample_rate/1e3:.2f} kHz / {mic.fft_size} = {(mic.sample_rate/mic.fft_size):.2f} Hz")

    for size in [512, 1024, 2048, 4096]:
        mic.set_fft_size(size)
        rbw = mic.sample_rate / mic.fft_size
        print(f"\nAfter set_fft_size({size}):")
        print(f"  fft_size: {mic.fft_size}")
        print(f"  Window length: {len(mic.window)}")
        print(f"  RBW = {mic.sample_rate/1e3:.2f} kHz / {size} = {rbw:.2f} Hz")
        assert mic.fft_size == size, f"Expected fft_size={size}, got {mic.fft_size}"
        assert len(mic.window) == size, f"Window size should match FFT size"
        print(f"  ✓ Verified: fft_size changed to {size}, window resized")

    # Summary table
    print("\n" + "=" * 70)
    print("\n### RBW Summary for Common FFT Sizes ###\n")
    print("FFT Size | HackRF (20 MHz) | RTL (2 MHz)  | Microphone (44.1 kHz)")
    print("-" * 70)
    for size in [512, 1024, 2048, 4096]:
        hackrf_rbw = 20e6 / size
        rtl_rbw = 2e6 / size
        mic_rbw = 44100 / size
        print(f"{size:8d} | {hackrf_rbw/1e3:14.2f} kHz | {rtl_rbw/1e3:11.2f} kHz | {mic_rbw:18.2f} Hz")

    print("\n" + "=" * 70)
    print("\nKey Insights:")
    print("  • Larger FFT size → Smaller RBW → Better frequency resolution")
    print("  • Smaller FFT size → Larger RBW → Faster processing")
    print("  • All sources support dynamic FFT size changes")
    print("  • Window is automatically resized to match FFT size")
    print("\n✓ All FFT size changes verified!")

if __name__ == "__main__":
    test_fft_size_changes()
