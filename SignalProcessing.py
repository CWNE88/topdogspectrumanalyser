import numpy as np
from scipy.signal import butter, filtfilt, spectrogram, welch
from scipy.fft import fft

class process:
    
    def do_fft(self, samples):
        self.fft_result = fft(samples)
        return self.fft_result
    
    def do_centre_fft(self, X):
        self.fft_centred = np.fft.fftshift(X)
        return self.fft_centred
    
    def get_magnitude(self, fft):
        self.magnitude = np.abs(fft)
        return self.magnitude
    
    def get_log_magnitude(self, magnitude):
        self.log_magnitude = 20 * np.log10(magnitude + 1e-12)   # check the 20*
        return self.log_magnitude

    # Low pass filter
    def butter_lowpass(cutoff, fs, order=5):
        nyq = 0.5 * fs
        normal_cutoff = cutoff / nyq
        b, a = butter(order, normal_cutoff, btype='low', analog=False)
        return b, a

    def lowpass_filter(self, data, cutoff, fs, order=5):
        b, a = self.butter_lowpass(cutoff, fs, order=order)   # is self.bu... right?
        y = filtfilt(b, a, data)
        return y
    
    def create_window(self, size, window_type='hamming'):
            if window_type == 'hamming':
                window = np.hamming(size)
            elif window_type == 'hanning':
                window = np.hanning(size)
            elif window_type == 'blackman':
                window = np.blackman(size)
            else:
                raise ValueError("Unknown window type.")
            return (window)

    
    # Spectrogram:
    # Compute a spectrogram to visualise how the frequency content of a signal changes over time.
    def compute_spectrogram(self, samples, fs):
        f, t, Sxx = spectrogram(samples, fs)
        return f, t, Sxx

    #Phase Information:
    #Extract phase information from the FFT results, which can be useful for certain applications.
        
    def get_phase(self, fft):
        return np.angle(fft)

    # Power Spectral Density (PSD):
    # Estimate the power spectral density to analyze the power distribution of the signal across frequencies.

    def compute_psd(self, samples, sample_rate):
        f, Pxx = welch(samples, sample_rate)
        return f, Pxx

    # Calculate cross-correlation between two signals to find similarities or delays.
    def cross_correlation(self, signal1, signal2):
        return np.correlate(signal1, signal2, mode='full')

    # Implement an envelope detector to find the amplitude envelope of an RF signal.
    def envelope_detection(self, samples):
        analytic_signal = np.hilbert(samples)
        return np.abs(analytic_signal)

    # Normalise the samples or FFT results to a specific range or scale.
    def normalise(self, samples):
        return (samples - np.min(samples)) / (np.max(samples) - np.min(samples))
