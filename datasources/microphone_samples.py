import numpy as np
import sounddevice as sd
from scipy import fft
from frequencyselector import FrequencyRange
from . import SampleDataSource
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class MicrophoneSamplesDataSource(SampleDataSource):
    def __init__(self, sample_rate: int = 44100, centre_freq: int = 0):
        super().__init__(sample_rate, centre_freq)
        self.fft_size = 1024
        self.window_type = 'hanning'
        self.stream = None
        self.running = False
        self.set_window()
        logging.debug(f"Initialised MicrophoneSamplesDataSource with sample_rate={sample_rate}, centre_freq={centre_freq}")

    def set_window(self):
        window_funcs = {'hanning': np.hanning, 'hamming': np.hamming}
        self.window = window_funcs.get(self.window_type, np.hanning)(self.fft_size)
        logging.debug(f"Set window type: {self.window_type}")

    def set_fft_size(self, fft_size: int):
        self.fft_size = fft_size
        self.set_window()
        logging.debug(f"Set FFT size: {fft_size}")
        if self.running:
            self.stop()
            self.start(None)

    def set_window_type(self, window_type: str):
        self.window_type = window_type
        self.set_window()
        logging.debug(f"Set window type: {window_type}")
        if self.running:
            self.stop()
            self.start(None)

    def start(self, frequency: FrequencyRange):
        if self.running:
            logging.debug("Microphone already running, skipping start")
            return
        try:
            logging.debug("Attempting to initialise microphone")
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                blocksize=self.fft_size,
                dtype=np.float32
            )
            self.stream.start()
            self.running = True
            logging.debug("Microphone started successfully")
        except Exception as e:
            self.running = False
            logging.error(f"Microphone initialisation failed: {str(e)}")
            raise RuntimeError(f"Microphone initialisation failed: {str(e)}")

    def stop(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                logging.debug("Microphone closed successfully")
            except Exception as e:
                logging.error(f"Error stopping microphone: {str(e)}")
            self.stream = None
        self.running = False
        logging.debug("Microphone stopped")

    def get_power_levels(self) -> tuple[np.ndarray, np.ndarray]:
        if not self.running:
            logging.warning("Microphone not running, returning zero data")
            return np.zeros(self.fft_size), fft.fftfreq(self.fft_size, 1 / self.sample_rate)
        try:
            samples, _ = self.stream.read(self.fft_size)
            samples = samples.flatten() * self.window
            spectrum = fft.fft(samples, n=self.fft_size)
            power = np.abs(spectrum) ** 2
            power_db = 10 * np.log10(power + 1e-10)
            freq_bins = fft.fftfreq(self.fft_size, 1 / self.sample_rate)
            logging.debug("Computed microphone power levels successfully")
            return power_db, freq_bins
        except Exception as e:
            logging.error(f"Error computing power levels: {str(e)}")
            return np.zeros(self.fft_size), fft.fftfreq(self.fft_size, 1 / self.sample_rate)

    def update_frequency(self, sample_rate: float, centre_freq: float):
        self.sample_rate = int(sample_rate)
        self.centre_freq = int(centre_freq)
        logging.debug(f"Updated microphone frequency: sample_rate={self.sample_rate}, centre_freq={self.centre_freq}")
        if self.running:
            self.stop()
            self.start(None)
