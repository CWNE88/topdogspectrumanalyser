import numpy as np
import time
try:
    from rtlsdr import RtlSdr
    _RTL_AVAILABLE = True
except (ImportError, OSError):
    _RTL_AVAILABLE = False
    RtlSdr = None
from scipy import fft
from utils.frequency_selector import FrequencyRange
from utils.constants import DSPConstants
from . import SampleDataSource
import logging

logger = logging.getLogger(__name__)

class RtlSamplesDataSource(SampleDataSource):
    def __init__(self, sample_rate: int, centre_freq: int):
        super().__init__(sample_rate, centre_freq)
        self.fft_size = 1024
        self.sdr = None
        self.window = np.hanning(self.fft_size)
        self.running = False
        self.last_sample_rate = sample_rate
        self.use_psd = False  # Flag to enable PSD mode
        self._gain = 'auto'
        self._flush_reads_remaining = 0
        logger.debug(f"Initialised RtlSamplesDataSource with sample_rate={sample_rate}, centre_freq={centre_freq}")

    def start(self, frequency: FrequencyRange = None):
        if not _RTL_AVAILABLE:
            raise RuntimeError("RTL-SDR library (librtlsdr) not available on this system")
        if frequency:
            self.centre_freq = int(frequency.centre)
            self.sample_rate = int(frequency.span)

        if self.running:
            logger.debug("RTL-SDR already running, skipping start")
            return
            
        try:
            logger.debug("Attempting to initialise RTL-SDR")
            self.sdr = RtlSdr()
            self.sdr.sample_rate = self.sample_rate
            self.sdr.center_freq = self.centre_freq
            self.sdr.gain = self._gain

            # Read back the actual sample rate from hardware (may differ slightly)
            actual_sample_rate = self.sdr.get_sample_rate()
            self.sample_rate = actual_sample_rate
            self.last_sample_rate = actual_sample_rate

            self.running = True
            logger.debug(f"RTL-SDR started successfully at {self.centre_freq/1e6:.2f} MHz with {actual_sample_rate/1e6:.6f} MHz sample rate")
        except Exception as e:
            self.running = False
            logger.error(f"RTL-SDR initialisation failed: {str(e)}")
            raise RuntimeError(f"RTL-SDR initialisation failed: {str(e)}")

    def pause(self):
        """Pause the device without closing it (for quick resume)."""
        self.running = False
        logger.debug("RTL-SDR paused (device still initialized)")

    def resume(self):
        """Resume the paused device without reinitializing."""
        if self.sdr is None:
            logger.warning("Cannot resume: RTL-SDR device not initialized")
            return
        self.running = True
        logger.debug("RTL-SDR resumed (no reinitialization needed)")

    def stop(self):
        if self.sdr:
            try:
                self.sdr.close()
                logger.debug("RTL-SDR closed successfully")
            except Exception as e:
                logger.error(f"Error closing RTL-SDR: {str(e)}")
            self.sdr = None
        self.running = False
        logger.debug("RTL-SDR stopped")

    def update_centre_frequency(self, centre_freq: float):
        """Update just the centre frequency without restarting the device"""
        if not self.running:
            logger.warning("RTL-SDR not running, cannot update centre frequency")
            return

        centre_freq = int(centre_freq)
        if centre_freq == self.centre_freq:
            logger.debug("Centre frequency unchanged, skipping update")
            return

        self.centre_freq = centre_freq
        try:
            self.sdr.center_freq = centre_freq
            # Flush enough reads to cover PLL lock time (~5ms) plus USB FIFO.
            # Done all at once in get_power_levels() so live display recovers immediately.
            self._flush_reads_remaining = max(3, int(0.006 * self.sample_rate / self.fft_size))
            logger.debug(f"Updated centre frequency to {centre_freq/1e6:.2f} MHz without reinitialisation")
        except Exception as e:
            logger.error(f"Error updating centre frequency: {str(e)}")
            raise RuntimeError(f"Error updating centre frequency: {str(e)}")

    def update_sample_rate(self, sample_rate: float):
        """Update the sample rate without restarting the device"""
        sample_rate = int(sample_rate)
        if sample_rate == self.last_sample_rate:
            logger.debug("Sample rate unchanged, skipping update")
            return

        if self.running and self.sdr:
            # Change sample rate on running device without restart
            try:
                self.sdr.sample_rate = sample_rate
                # Read back actual rate (hardware may adjust slightly)
                actual_sample_rate = self.sdr.get_sample_rate()
                self.sample_rate = actual_sample_rate
                self.last_sample_rate = actual_sample_rate

                # CRITICAL: Re-set centre frequency after sample rate change
                # RTL-SDR may shift centre when sample rate changes
                self.sdr.center_freq = self.centre_freq
                actual_centre = self.sdr.get_center_freq()
                self.centre_freq = actual_centre

                logger.debug(f"Updated sample rate to {actual_sample_rate/1e6:.6f} MHz, centre={actual_centre/1e6:.2f} MHz")
            except Exception as e:
                logger.error(f"Error updating sample rate: {str(e)}")
                raise RuntimeError(f"Error updating sample rate: {str(e)}")
        else:
            self.sample_rate = sample_rate

    def update_frequency(self, sample_rate: float, centre_freq: float):
        """Update both sample rate and center frequency efficiently without restarting"""
        sample_rate = int(sample_rate)
        centre_freq = int(centre_freq)

        # Update sample rate if it changed (no restart needed)
        if sample_rate != self.last_sample_rate:
            self.update_sample_rate(sample_rate)

        # Update centre frequency if it changed (no restart needed)
        if centre_freq != self.centre_freq:
            self.update_centre_frequency(centre_freq)

    def get_power_levels(self) -> tuple[np.ndarray, np.ndarray]:
        if not self.running:
            logger.warning("RTL-SDR not running, returning zero data")
            return np.zeros(self.fft_size), np.linspace(
                self.centre_freq - self.sample_rate / 2,
                self.centre_freq + self.sample_rate / 2,
                self.fft_size
            )

        try:
            # CRITICAL: Always use actual hardware values for all calculations
            actual_fs = self.sdr.get_sample_rate()
            actual_fc = self.sdr.get_center_freq()

            if self._flush_reads_remaining > 0:
                for _ in range(self._flush_reads_remaining):
                    self.sdr.read_samples(self.fft_size)
                self._flush_reads_remaining = 0

            samples = self.sdr.read_samples(self.fft_size)
            self._store_raw(samples.copy())
            samples = samples * self.window
            spectrum = fft.fft(samples, n=self.fft_size)

            # CRITICAL: FFT output needs to be shifted to put DC in the center
            spectrum = fft.fftshift(spectrum)

            if self.use_psd:
                # Compute Power Spectral Density (dB/Hz) - use actual_fs
                psd = (np.abs(spectrum) ** 2) / (actual_fs * self.fft_size)
                psd = self._averager.process(psd)
                power_db = 10 * np.log10(psd + DSPConstants.LOG_FLOOR)
            else:
                # Standard power spectrum (dB)
                power = np.abs(spectrum) ** 2
                power = self._averager.process(power)
                power_db = 10 * np.log10(power + DSPConstants.POWER_LOG_FLOOR)

            # CRITICAL: Use fftshift to create properly ordered frequency bins
            # This matches the shifted FFT output
            freq_bins = fft.fftshift(fft.fftfreq(self.fft_size, 1/actual_fs)) + actual_fc

            return power_db, freq_bins
        except Exception as e:
            logger.error(f"Error computing power levels: {str(e)}")
            return np.zeros(self.fft_size), np.linspace(
                self.centre_freq - self.sample_rate / 2,
                self.centre_freq + self.sample_rate / 2,
                self.fft_size
            )

    def set_window_type(self, window_type: str):
        window_funcs = {
            'hanning': np.hanning,
            'hamming': np.hamming,
            'rectangle': np.ones
        }
        self.window = window_funcs.get(window_type.lower(), np.hanning)(self.fft_size)
        logger.debug(f"Set window type to {window_type}")

    def set_fft_size(self, fft_size: int):
        if fft_size == self.fft_size:
            return

        self.fft_size = fft_size
        self.window = np.hanning(self.fft_size)
        self._averager.reset()
        logger.debug(f"Set FFT size to {fft_size}")

    @property
    def sample_count(self) -> int:
        """Get the number of samples used for FFT."""
        return self.fft_size

    @sample_count.setter
    def sample_count(self, value: int):
        """Set the number of samples used for FFT."""
        self.set_fft_size(value)

    def read_samples_only(self) -> np.ndarray | None:
        if not self.running or self.sdr is None:
            return None
        try:
            samples = self.sdr.read_samples(self.fft_size)
            self._store_raw(samples.copy())
            return self._last_raw_samples
        except Exception as e:
            logger.error(f"Error reading samples: {e}")
            return None

    def set_gain(self, gain) -> None:
        """Set tuner gain. Pass 'auto' for AGC or a numeric dB value."""
        self._gain = gain
        if self.sdr is not None and self.running:
            try:
                self.sdr.gain = gain
                logger.info(f"RTL-SDR gain set to {gain}")
            except Exception as e:
                logger.error(f"Error setting RTL-SDR gain: {e}")

    def set_psd_mode(self, enabled: bool):
        """Enable or disable PSD (Power Spectral Density) mode.

        Args:
            enabled: True to compute PSD (dB/Hz), False for standard power spectrum (dB).
        """
        self.use_psd = enabled
        logger.debug(f"PSD mode {'enabled' if enabled else 'disabled'}")
