from . import DataSource
from rtlsdr import RtlSdr
import numpy as np

class RtlSdrDataSource(DataSource):

    @staticmethod
    def find_devices():
        pass

    def __init__(self, centre_frequency, sample_rate=2097152, gain=36.4):
        super().__init__(centre_frequency, sample_rate, gain)

        self.sdr = RtlSdr()
        self.sdr.center_freq = centre_frequency
        self.sdr.sample_rate = sample_rate
        self.sdr.gain = gain

    def read_samples(self, sample_size):
        return self.sdr.read_samples(sample_size)
    
        

    def cleanup(self):
        self.sdr.close()