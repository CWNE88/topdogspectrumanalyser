import numpy as np
from rtlsdr import RtlSdr
from scipy import fft
from frequencyselector import FrequencyRange
from . import SampleDataSource
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class RtlSamplesDataSource(SampleDataSource):
    def __init__(self, sample_rate: int, centre_freq: int):
        super().__init__(sample_rate, centre_freq)
        self.fft_size = 1024
        self.sdr = None
        self.window = np.hanning(self.fft_size)
        self.running = False
        self.last_sample_rate = sample_rate
        logging.debug(f"Initialised RtlSamplesDataSource with sample_rate={sample_rate}, centre_freq={centre_freq}")

    def start(self, frequency: FrequencyRange = None):
        if frequency:
            self.centre_freq = int(frequency.centre)
            self.sample_rate = int(frequency.span)
            
        if self.running:
            logging.debug("RTL-SDR already running, skipping start")
            return
            
        try:
            logging.debug("Attempting to initialise RTL-SDR")
            self.sdr = RtlSdr()
            self.sdr.sample_rate = self.sample_rate
            self.sdr.center_freq = self.centre_freq
            self.sdr.gain = 'auto'
            self.last_sample_rate = self.sample_rate
            self.running = True
            logging.debug(f"RTL-SDR started successfully at {self.centre_freq/1e6:.2f} MHz with {self.sample_rate/1e6:.2f} MHz sample rate")
        except Exception as e:
            self.running = False
            logging.error(f"RTL-SDR initialisation failed: {str(e)}")
            raise RuntimeError(f"RTL-SDR initialisation failed: {str(e)}")

    def stop(self):
        if self.sdr:
            try:
                self.sdr.close()
                logging.debug("RTL-SDR closed successfully")
            except Exception as e:
                logging.error(f"Error closing RTL-SDR: {str(e)}")
            self.sdr = None
        self.running = False
        logging.debug("RTL-SDR stopped")

    def update_center_frequency(self, centre_freq: float):
        """Update just the center frequency without restarting the device"""
        if not self.running:
            logging.warning("RTL-SDR not running, cannot update center frequency")
            return
            
        centre_freq = int(centre_freq)
        if centre_freq == self.centre_freq:
            logging.debug("Center frequency unchanged, skipping update")
            return
            
        self.centre_freq = centre_freq
        try:
            self.sdr.center_freq = centre_freq
            logging.debug(f"Updated center frequency to {centre_freq/1e6:.2f} MHz without reinitialization")
        except Exception as e:
            logging.error(f"Error updating center frequency: {str(e)}")
            raise RuntimeError(f"Error updating center frequency: {str(e)}")

    def update_sample_rate(self, sample_rate: float):
        """Update the sample rate (requires restart)"""
        sample_rate = int(sample_rate)
        if sample_rate == self.last_sample_rate:
            logging.debug("Sample rate unchanged, skipping update")
            return
            
        self.sample_rate = sample_rate
        if self.running:
            self.stop()
            self.start()

    def update_frequency(self, sample_rate: float, centre_freq: float):
        """Update both sample rate and center frequency efficiently"""
        sample_rate = int(sample_rate)
        centre_freq = int(centre_freq)
        
        # Only update sample rate if it changed (requires restart)
        if sample_rate != self.last_sample_rate:
            self.sample_rate = sample_rate
            if self.running:
                self.stop()
                self.start()
            return
            
        # If only center freq changed, update it directly
        if centre_freq != self.centre_freq:
            self.update_center_frequency(centre_freq)

    def get_power_levels(self) -> tuple[np.ndarray, np.ndarray]:
        if not self.running:
            logging.warning("RTL-SDR not running, returning zero data")
            return np.zeros(self.fft_size), np.linspace(
                self.centre_freq - self.sample_rate / 2,
                self.centre_freq + self.sample_rate / 2,
                self.fft_size
            )

        try:
            samples = self.sdr.read_samples(self.fft_size)
            samples = samples * self.window
            spectrum = fft.fft(samples, n=self.fft_size)
            power = np.abs(spectrum) ** 2
            power_db = 10 * np.log10(power + 1e-10)
            freq_bins = np.linspace(
                self.centre_freq - self.sample_rate / 2,
                self.centre_freq + self.sample_rate / 2,
                self.fft_size
            )
            logging.debug("Computed power levels successfully")
            return power_db, freq_bins
        except Exception as e:
            logging.error(f"Error computing power levels: {str(e)}")
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
        logging.debug(f"Set window type to {window_type}")

    def set_fft_size(self, fft_size: int):
        if fft_size == self.fft_size:
            return
            
        self.fft_size = fft_size
        self.window = np.hanning(self.fft_size)
        logging.debug(f"Set FFT size to {fft_size}")
