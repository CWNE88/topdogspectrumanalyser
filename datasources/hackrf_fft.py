from . import SampleDataSource
from hackrf import *
from numpy import complexfloating, ndarray as NDArray
import numpy as np
from scipy.signal import butter, filtfilt

class HackRFDataSource(SampleDataSource):
    samples: NDArray[complexfloating]

    @staticmethod
    def find_devices():
        devices = hackrf_device_list()
        return devices

    def __init__(self, centre_frequency=298e6, sample_rate=10e6, amplifier=True, lna_gain=20, vga_gain=20):
        super().__init__(centre_frequency, sample_rate, lna_gain)

        self.device = HackRF()
        self.device.set_sample_rate(sample_rate)

        #if amplifier:
        #    self.device.enable_amp()
        self.device.enable_amp()

        self.device.set_lna_gain(lna_gain)
        self.device.set_vga_gain(vga_gain)
        self.device.set_freq(centre_frequency)

    def set_centre_freq(self, freq_hz: int):
        self.device.set_freq(freq_hz)

    def read_samples(self, sample_size):
        self.samples = self.device.read_samples()
        mean_value = np.mean(self.samples)
        neutralised_samples = self.samples - mean_value
        return neutralised_samples
        # return self.samples
    
        

    def cleanup(self):
        self.device.close()