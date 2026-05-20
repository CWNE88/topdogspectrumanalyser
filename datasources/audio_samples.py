import numpy as np
import time
import sounddevice as sd
from scipy import fft
from utils.frequency_selector import FrequencyRange
from utils.constants import DSPConstants
from . import SampleDataSource
import logging

logger = logging.getLogger(__name__)

# Valid channel modes
AUDIO_CHANNELS = ('mono', 'left', 'right', 'stereo')

# Target maximum blocking time per get_power_levels() call.
# The actual read size is capped at fft_size so at high sample rates
# we fall back to reading a full FFT window (original behaviour).
_MAX_READ_MS = 30


class MicrophoneSamplesDataSource(SampleDataSource):
    def __init__(self, sample_rate: int = 44100, centre_freq: int = 0):
        super().__init__(sample_rate, centre_freq)
        self.fft_size = 1024
        self.window_type = 'hanning'
        self.channel_mode = 'mono'  # mono | left | right | stereo
        self.stream = None
        self.running = False
        self.use_psd = False
        self._audio_buffer = np.zeros((self.fft_size, 2), dtype=np.float32)
        self._audio_block  = self.fft_size  # updated in start()
        self.set_window()
        logger.debug(f"Initialised MicrophoneSamplesDataSource sample_rate={sample_rate}")

    def set_window(self):
        window_funcs = {'hanning': np.hanning, 'hamming': np.hamming}
        self.window = window_funcs.get(self.window_type, np.hanning)(self.fft_size)

    def set_fft_size(self, fft_size: int):
        self.fft_size = fft_size
        self.set_window()
        self._averager.reset()
        self._audio_buffer = np.zeros((fft_size, 2), dtype=np.float32)
        self._audio_block  = fft_size
        logger.debug(f"Set FFT size: {fft_size}")
        if self.running:
            self.stop()
            self.start(None)

    @property
    def sample_count(self) -> int:
        return self.fft_size

    @sample_count.setter
    def sample_count(self, value: int):
        self.set_fft_size(value)

    def set_window_type(self, window_type: str):
        self.window_type = window_type
        self.set_window()
        if self.running:
            self.stop()
            self.start(None)

    def set_channel_mode(self, mode: str) -> None:
        if mode not in AUDIO_CHANNELS:
            logger.warning(f"Unknown channel mode: {mode}")
            return
        self.channel_mode = mode
        # Stream always opens as stereo; no restart needed
        logger.debug(f"Audio channel mode: {mode}")

    def start(self, frequency: FrequencyRange):
        if self.running:
            return
        try:
            # Always open stereo so we can select L/R/stereo without restart
            device_info = sd.query_devices(kind='input')
            max_ch = device_info.get('max_input_channels', 1) if isinstance(device_info, dict) else 1
            channels = 2 if max_ch >= 2 else 1
            self._actual_channels = channels
            # Dynamic block size: target _MAX_READ_MS ms per read.
            # At high sample rates this equals fft_size (original behaviour).
            # At low sample rates it is smaller so the display is more responsive.
            target = max(64, int(self.sample_rate * _MAX_READ_MS / 1000))
            self._audio_block = min(self.fft_size, target)
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=channels,
                blocksize=self._audio_block,
                dtype=np.float32
            )
            self.stream.start()
            self._audio_buffer = np.zeros((self.fft_size, 2), dtype=np.float32)
            self.running = True
            logger.debug(f"Microphone started ({channels}ch)")
        except Exception as e:
            self.running = False
            logger.error(f"Microphone initialisation failed: {e}")
            raise RuntimeError(f"Microphone initialisation failed: {e}")

    def stop(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error stopping microphone: {e}")
            self.stream = None
        self.running = False

    # Number of positive-frequency bins from rfft
    @property
    def _rfft_bins(self) -> int:
        return self.fft_size // 2 + 1

    def _freq_bins(self) -> np.ndarray:
        """Positive-only frequency axis: 0 → Nyquist."""
        return np.linspace(0, self.sample_rate / 2, self._rfft_bins)

    def _compute_power(self, signal: np.ndarray) -> np.ndarray:
        """Apply window, rfft, return linear power (one-sided)."""
        signal = signal - signal.mean()
        signal *= self.window
        spectrum = fft.rfft(signal, n=self.fft_size)
        if self.use_psd:
            power = (np.abs(spectrum) ** 2) / (self.sample_rate * self.fft_size)
        else:
            power = np.abs(spectrum) ** 2
        # Double non-DC, non-Nyquist bins to conserve power (one-sided spectrum)
        power[1:-1] *= 2
        return power

    def get_power_levels(self) -> tuple[np.ndarray, np.ndarray]:
        freq_bins = self._freq_bins()

        if not self.running:
            return np.full(self._rfft_bins, -120.0), freq_bins

        try:
            raw, _ = self.stream.read(self._audio_block)
            self._store_raw(raw.copy())

            # Normalise to (N, 2) stereo
            if raw.ndim == 1 or raw.shape[1] == 1:
                raw = raw.reshape(-1, 1)
                raw = np.hstack([raw, raw])

            if self._audio_block < self.fft_size:
                # Low sample rate: roll buffer and compute FFT on full window
                n = len(raw)
                self._audio_buffer = np.concatenate(
                    [self._audio_buffer[n:], raw], axis=0
                )
                left  = self._audio_buffer[:, 0]
                right = self._audio_buffer[:, 1]
            else:
                # High sample rate: read was a full FFT window, use directly
                left  = raw[:, 0]
                right = raw[:, 1]

            mono  = (left + right) * 0.5

            floor = DSPConstants.LOG_FLOOR if self.use_psd else DSPConstants.POWER_LOG_FLOOR

            if self.channel_mode == 'stereo':
                left_power  = self._averager.process(self._compute_power(left))
                right_power = self._compute_power(right)   # separate trace — no shared averager
                left_db  = 10 * np.log10(left_power  + floor)
                right_db = 10 * np.log10(right_power + floor)
                return (left_db, right_db), freq_bins
            elif self.channel_mode == 'left':
                power = self._averager.process(self._compute_power(left))
            elif self.channel_mode == 'right':
                power = self._averager.process(self._compute_power(right))
            else:  # mono
                power = self._averager.process(self._compute_power(mono))

            power_db = 10 * np.log10(power + floor)
            return power_db, freq_bins

        except Exception as e:
            logger.error(f"Error computing power levels: {e}")
            return np.full(self._rfft_bins, -120.0), freq_bins

    def read_samples_only(self) -> np.ndarray | None:
        if not self.running or self.stream is None:
            return None
        try:
            raw, _ = self.stream.read(self.fft_size)
            self._store_raw(raw.copy())
            return self._last_raw_samples
        except Exception as e:
            logger.error(f"Error reading audio samples: {e}")
            return None

    def update_frequency(self, sample_rate: float, centre_freq: float):
        self.sample_rate = int(sample_rate)
        self.centre_freq = int(centre_freq)
        if self.running:
            self.stop()
            self.start(None)

    def update_centre_frequency(self, centre_freq: float):
        self.centre_freq = int(centre_freq)

    def set_psd_mode(self, enabled: bool):
        self.use_psd = enabled
