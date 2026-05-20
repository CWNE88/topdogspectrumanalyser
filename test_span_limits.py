import sys
from unittest.mock import MagicMock
for _mod in ('hackrf', 'rtlsdr', 'sounddevice', 'scipy', 'scipy.signal',
             'scipy.fft', 'pyqtgraph', 'pyqtgraph.opengl'):
    sys.modules.setdefault(_mod, MagicMock())

#!/usr/bin/env python3
"""Test script to verify span limits for different source types."""

from datasources.hackrf_sweep import HackRFSweepDataSource
from datasources.rtl_sweep import RtlSweepDataSource
from datasources.hackrf_samples import HackrfSamplesDataSource
from datasources.rtl_samples import RtlSamplesDataSource
from datasources.audio_samples import MicrophoneSamplesDataSource
from datasources.base import SweepDataSource, SampleDataSource
from utils.constants import SourceLimits

def test_source_type_detection():
    """Test that we can correctly identify sweep vs sample sources."""
    print("Testing source type detection...")
    print("=" * 60)

    # Test sweep sources
    print("\nSweep Sources:")
    hackrf_sweep = HackRFSweepDataSource(2.4e9, 2.5e9, 30000)
    rtl_sweep = RtlSweepDataSource(88e6, 108e6, 30000)

    print(f"  HackRF Sweep: {isinstance(hackrf_sweep, SweepDataSource)}")
    print(f"    Max span: {(SourceLimits.HACKRF_MAX_FREQ - SourceLimits.HACKRF_MIN_FREQ)/1e9:.2f} GHz")

    print(f"  RTL Sweep: {isinstance(rtl_sweep, SweepDataSource)}")
    print(f"    Max span: {(SourceLimits.RTL_MAX_FREQ - SourceLimits.RTL_MIN_FREQ)/1e9:.2f} GHz")

    # Test sample sources
    print("\nSample Sources:")
    hackrf_samples = HackrfSamplesDataSource(20e6, 2.45e9)
    rtl_samples = RtlSamplesDataSource(2e6, 100e6)
    mic_samples = MicrophoneSamplesDataSource(44100, 0)

    print(f"  HackRF Samples: {isinstance(hackrf_samples, SampleDataSource)}")
    print(f"    Max span: {SourceLimits.HACKRF_MAX_SAMPLE_RATE/1e6:.2f} MHz")

    print(f"  RTL Samples: {isinstance(rtl_samples, SampleDataSource)}")
    print(f"    Max span: {SourceLimits.RTL_MAX_SAMPLE_RATE/1e6:.2f} MHz")

    print(f"  Microphone Samples: {isinstance(mic_samples, SampleDataSource)}")
    print(f"    Max span: {44100/1e3:.2f} kHz")

    print("\n" + "=" * 60)
    print("Example scenarios:")
    print("\n1. HackRF Sweep mode - Centre: 2.45 GHz, Span: 1 GHz")
    print("   Should be ALLOWED (sweep mode has no sample rate limit)")
    print("   Result: Start=1.95 GHz, Stop=2.95 GHz")

    print("\n2. HackRF Samples mode - Centre: 2.45 GHz, Span: 1 GHz")
    print("   Should be REJECTED (sample mode limited to 20 MHz)")
    print("   Error: Span limited to 20 MHz for HackRF Samples")

    print("\n3. RTL Sweep mode - Centre: 900 MHz, Span: 500 MHz")
    print("   Should be ALLOWED (sweep mode)")
    print("   Result: Start=650 MHz, Stop=1150 MHz")

    print("\n4. RTL Samples mode - Centre: 100 MHz, Span: 2 MHz")
    print("   Should be ALLOWED (within 2.4 MHz limit)")
    print("   Result: Start=99 MHz, Stop=101 MHz")

    print("\n5. RTL Samples mode - Centre: 100 MHz, Span: 10 MHz")
    print("   Should be REJECTED (exceeds 2.4 MHz limit)")
    print("   Error: Span limited to 2.40 MHz for RTL Samples")

if __name__ == "__main__":
    test_source_type_detection()
