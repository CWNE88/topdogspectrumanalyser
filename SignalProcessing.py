import numpy as np
from scipy.fft import fft, fftshift
from scipy.signal import butter, filtfilt

class DSP:
    """Digital Signal Processing class for spectrum analyser, focusing on FFT."""

    def do_fft(self, samples: np.ndarray) -> np.ndarray:
        """Compute the FFT of input samples."""
        if not isinstance(samples, np.ndarray) or samples.size == 0:
            raise ValueError("Input samples must be a non-empty NumPy array.")
        return fft(samples)

    def do_centre_fft(self, fft_data: np.ndarray) -> np.ndarray:
        """Centre the FFT result for display (shifts zero frequency to middle)."""
        return fftshift(fft_data)

    def get_magnitude(self, fft_data: np.ndarray) -> np.ndarray:
        """Compute the magnitude of FFT results."""
        return np.abs(fft_data)

    def get_log_magnitude(self, magnitude: np.ndarray) -> np.ndarray:
        """Compute the logarithmic magnitude (dB) of FFT results."""
        return 20 * np.log10(magnitude + 1e-12)  # Avoid log(0)

    @staticmethod
    def butter_lowpass(cutoff: float, fs: float, order: int = 5) -> tuple:
        """Design a Butterworth low-pass filter."""
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        return b, a

    def lowpass_filter(self, data: np.ndarray, cutoff: float, fs: float, order: int = 5) -> np.ndarray:
        """Apply a Butterworth low-pass filter to the data."""
        b, a = self.butter_lowpass(cutoff, fs, order)
        return filtfilt(b, a, data)

    def create_window(self, size: int, window_type: str = 'hamming') -> np.ndarray:
        """Create a window function for signal processing."""
        window_types = {
            'hamming': np.hamming,
            'hanning': np.hanning,
            'blackman': np.blackman
        }
        window_func = window_types.get(window_type.lower())
        if window_func is None:
            window_func = np.hamming  # Default to Hamming
        return window_func(size)

    # Placeholder for future methods (not currently used in FFT scope)
    def compute_spectrogram(self, samples: np.ndarray, fs: float) -> tuple:
        """Compute spectrogram (for future waterfall plots)."""
        from scipy.signal import spectrogram
        f, t, Sxx = spectrogram(samples, fs)
        return f, t, Sxx

    def get_phase(self, fft_data: np.ndarray) -> np.ndarray:
        """Extract phase from FFT (for future use)."""
        return np.angle(fft_data)

    def compute_psd(self, samples: np.ndarray, sample_rate: float) -> tuple:
        """Compute power spectral density (for future use)."""
        from scipy.signal import welch
        f, Pxx = welch(samples, sample_rate)
        return f, Pxx

    def cross_correlation(self, signal1: np.ndarray, signal2: np.ndarray) -> np.ndarray:
        """Compute cross-correlation (for future use)."""
        return np.correlate(signal1, signal2, mode='full')

    def envelope_detection(self, samples: np.ndarray) -> np.ndarray:
        """Detect signal envelope (for future use)."""
        return np.abs(np.hilbert(samples))

    def normalise(self, samples: np.ndarray) -> np.ndarray:
        """Normalise samples to [0, 1] range."""
        min_val, max_val = np.min(samples), np.max(samples)
        if max_val == min_val:
            return np.zeros_like(samples)
        return (samples - min_val) / (max_val - min_val)
