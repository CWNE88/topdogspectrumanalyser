"""Base classes for data sources.

Defines abstract interfaces for sweep and sample-based data sources.
All implementations should follow these interfaces for consistent behavior.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple
import numpy as np
import threading
import time
from utils.signal_processing import TraceAverager


class SweepDataSource(ABC):
    """Base class for sweep-based data sources (e.g., spectrum sweeps)."""

    @abstractmethod
    def start(self, frequency=None):
        """Start the sweep operation.

        Args:
            frequency: Optional frequency range to set before starting.
        """
        pass

    @abstractmethod
    def stop(self):
        """Stop the sweep operation."""
        pass

    @abstractmethod
    def get_data(self):
        """Get sweep data.

        Returns:
            Power data from the sweep.
        """
        pass



class SampleDataSource(ABC):
    """Base class for sample-based data sources (FFT analysis).

    Standardized interface for consistent behavior across hardware implementations.
    All subclasses should use 'sample_count' for FFT size to avoid naming confusion.
    """

    def __init__(self, sample_rate: Optional[int] = None, centre_freq: Optional[int] = None):
        """Initialize the sample data source.

        Args:
            sample_rate: Sample rate in Hz.
            centre_freq: Centre frequency in Hz.
        """
        self.sample_rate = sample_rate
        self.centre_freq = centre_freq
        self._averager = TraceAverager()
        self._last_raw_samples: Optional[np.ndarray] = None
        self.last_data_time: float = 0.0
        self._raw_lock = threading.Lock()

    @abstractmethod
    def start(self, frequency=None):
        """Start sample acquisition.

        Args:
            frequency: Optional frequency range to set before starting.
        """
        pass

    @abstractmethod
    def stop(self):
        """Stop sample acquisition."""
        pass

    @abstractmethod
    def get_power_levels(self) -> Tuple[np.ndarray, np.ndarray]:
        """Get computed power spectrum.

        This is the primary interface for sample sources.

        Returns:
            Tuple of (power_db, frequency_bins):
                - power_db: Power levels in dB
                - frequency_bins: Corresponding frequency values
        """
        pass

    @property
    @abstractmethod
    def sample_count(self) -> int:
        """Get the number of samples used for FFT.

        Standardized property to replace inconsistent num_samples/fft_size naming.

        Returns:
            int: Number of samples for FFT calculation.
        """
        pass

    @sample_count.setter
    @abstractmethod
    def sample_count(self, value: int):
        """Set the number of samples used for FFT.

        Args:
            value: Number of samples for FFT calculation.
        """
        pass

    @abstractmethod
    def update_frequency(self, sample_rate: float, centre_freq: float):
        """Update both sample rate and centre frequency.

        Args:
            sample_rate: New sample rate in Hz.
            centre_freq: New centre frequency in Hz.
        """
        pass

    @abstractmethod
    def update_centre_frequency(self, centre_freq: float):
        """Update the centre frequency only.

        Fixed spelling from 'update_center_frequency' for consistency.

        Args:
            centre_freq: New centre frequency in Hz.
        """
        pass

    def get_raw_samples(self) -> Optional[np.ndarray]:
        with self._raw_lock:
            return self._last_raw_samples

    def read_samples_only(self) -> Optional[np.ndarray]:
        """Read hardware samples without FFT. Override in subclasses."""
        return None

    def _store_raw(self, samples: np.ndarray) -> None:
        """Store raw samples thread-safely and update data timestamp."""
        with self._raw_lock:
            self._last_raw_samples = samples
        self.last_data_time = time.monotonic()

    def set_psd_mode(self, enabled: bool):
        """Enable or disable Power Spectral Density mode.

        Optional method - not all sources need to implement this.

        Args:
            enabled: True to compute PSD (dB/Hz), False for power spectrum (dB).
        """
        pass

    def set_averaging(self, mode: str, n: int) -> None:
        """Set trace averaging mode.

        Args:
            mode: "off", "exp" (exponential), or "lin" (linear running mean).
            n: Decay constant (exp) or frame count cap (lin).
        """
        self._averager.set_mode(mode, n)

    def reset_averaging(self) -> None:
        """Reset the averaging buffer — call on frequency or FFT size change."""
        self._averager.reset()
