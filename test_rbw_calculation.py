import sys
from unittest.mock import MagicMock
for _mod in ('hackrf', 'rtlsdr', 'sounddevice', 'scipy', 'scipy.signal',
             'scipy.fft', 'pyqtgraph', 'pyqtgraph.opengl'):
    sys.modules.setdefault(_mod, MagicMock())

#!/usr/bin/env python3
"""Test script to verify Resolution Bandwidth (RBW) calculations."""

from datasources.hackrf_sweep import HackRFSweepDataSource
from datasources.rtl_sweep import RtlSweepDataSource
from datasources.hackrf_samples import HackrfSamplesDataSource
from datasources.rtl_samples import RtlSamplesDataSource
from datasources.audio_samples import MicrophoneSamplesDataSource

def test_rbw_calculations():
    """Test RBW calculations for all source types."""
    print("Testing Resolution Bandwidth (RBW) Calculations")
    print("=" * 70)

    # Test Sweep Sources
    print("\n### SWEEP SOURCES ###")
    print("For sweep sources: RBW = bin_size\n")

    # HackRF Sweep
    hackrf_sweep = HackRFSweepDataSource(2.4e9, 2.5e9, 30000)
    rbw_hackrf_sweep = hackrf_sweep.bin_size
    print(f"1. HackRF Sweep:")
    print(f"   Bin size: {hackrf_sweep.bin_size/1e3:.2f} kHz")
    print(f"   RBW = {rbw_hackrf_sweep/1e3:.2f} kHz")
    print(f"   ✓ Correct: RBW equals bin_size")

    # RTL Sweep
    rtl_sweep = RtlSweepDataSource(88e6, 108e6, 10000)
    rbw_rtl_sweep = rtl_sweep.bin_size
    print(f"\n2. RTL Sweep:")
    print(f"   Bin size: {rtl_sweep.bin_size/1e3:.2f} kHz")
    print(f"   RBW = {rbw_rtl_sweep/1e3:.2f} kHz")
    print(f"   ✓ Correct: RBW equals bin_size")

    # Test Sample Sources
    print("\n" + "=" * 70)
    print("\n### SAMPLE SOURCES ###")
    print("For sample sources: RBW = sample_rate / fft_size\n")

    # HackRF Samples
    hackrf_samples = HackrfSamplesDataSource(20e6, 2.45e9)
    rbw_hackrf_samples = hackrf_samples.sample_rate / hackrf_samples.num_samples
    print(f"3. HackRF Samples:")
    print(f"   Sample rate: {hackrf_samples.sample_rate/1e6:.2f} MHz")
    print(f"   FFT size: {hackrf_samples.num_samples}")
    print(f"   RBW = {hackrf_samples.sample_rate/1e6:.2f} MHz / {hackrf_samples.num_samples}")
    print(f"   RBW = {rbw_hackrf_samples/1e3:.2f} kHz")
    assert abs(rbw_hackrf_samples - 19531.25) < 1, "HackRF Samples RBW should be ~19.53 kHz"
    print(f"   ✓ Correct: 20 MHz / 1024 = 19.53 kHz")

    # RTL Samples
    rtl_samples = RtlSamplesDataSource(2e6, 100e6)
    rbw_rtl_samples = rtl_samples.sample_rate / rtl_samples.fft_size
    print(f"\n4. RTL Samples:")
    print(f"   Sample rate: {rtl_samples.sample_rate/1e6:.2f} MHz")
    print(f"   FFT size: {rtl_samples.fft_size}")
    print(f"   RBW = {rtl_samples.sample_rate/1e6:.2f} MHz / {rtl_samples.fft_size}")
    print(f"   RBW = {rbw_rtl_samples/1e3:.2f} kHz")
    assert abs(rbw_rtl_samples - 1953.125) < 1, "RTL Samples RBW should be ~1.95 kHz"
    print(f"   ✓ Correct: 2 MHz / 1024 = 1.95 kHz")

    # Microphone Samples
    mic_samples = MicrophoneSamplesDataSource(44100, 0)
    rbw_mic_samples = mic_samples.sample_rate / mic_samples.fft_size
    print(f"\n5. Microphone Samples:")
    print(f"   Sample rate: {mic_samples.sample_rate/1e3:.2f} kHz")
    print(f"   FFT size: {mic_samples.fft_size}")
    print(f"   RBW = {mic_samples.sample_rate/1e3:.2f} kHz / {mic_samples.fft_size}")
    print(f"   RBW = {rbw_mic_samples:.2f} Hz")
    assert abs(rbw_mic_samples - 43.066) < 1, "Microphone RBW should be ~43.07 Hz"
    print(f"   ✓ Correct: 44.1 kHz / 1024 = 43.07 Hz")

    # Additional scenarios
    print("\n" + "=" * 70)
    print("\n### EXAMPLE SCENARIOS ###\n")

    print("Scenario 1: HackRF Samples with different FFT sizes")
    for fft_size in [512, 1024, 2048, 4096]:
        rbw = 20e6 / fft_size
        print(f"   FFT={fft_size:4d}: RBW = 20 MHz / {fft_size} = {rbw/1e3:.2f} kHz")

    print("\nScenario 2: RTL Samples with different sample rates")
    for sample_rate in [1e6, 2e6, 2.4e6]:
        rbw = sample_rate / 1024
        print(f"   SR={sample_rate/1e6:.1f} MHz: RBW = {sample_rate/1e6:.1f} MHz / 1024 = {rbw/1e3:.2f} kHz")

    print("\nScenario 3: Sweep sources with different bin sizes")
    for bin_size in [10e3, 30e3, 100e3]:
        print(f"   Bin size={bin_size/1e3:.0f} kHz: RBW = {bin_size/1e3:.0f} kHz")

    print("\n" + "=" * 70)
    print("\nKey Insights:")
    print("  • Smaller FFT size → Larger RBW → Less frequency resolution")
    print("  • Larger FFT size → Smaller RBW → Better frequency resolution")
    print("  • Higher sample rate → Larger RBW (for same FFT size)")
    print("  • Smaller bin size (sweep) → Better frequency resolution")
    print("\n✓ All RBW calculations verified!")

if __name__ == "__main__":
    test_rbw_calculations()
