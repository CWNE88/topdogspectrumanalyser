from dataclasses import dataclass
from typing import Optional

@dataclass
class SourceCapabilities:
    # Mode type: either 'sweep' or 'fft'
    mode: str  # "sweep" | "fft"

    # Frequency range
    min_freq: float  # Hz
    max_freq: float  # Hz

    # Maximum span supported (Hz)
    max_span: Optional[float] = None

    # RBW capabilities
    min_rbw: Optional[float] = None  # Hz
    max_rbw: Optional[float] = None  # Hz
    default_rbw: Optional[float] = None  # Hz (bin_size or FFT resolution)

    # Sample / FFT info (for sample sources)
    sample_rate: Optional[float] = None  # Hz
    fft_size: Optional[int] = None  # number of samples used for FFT

    # Flags for optional features
    supports_psd: bool = False
    sweep_rate_available: bool = False

