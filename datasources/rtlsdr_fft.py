from . import DataSource
from rtlsdr import RtlSdr

class RtlSdrDataSource(DataSource):

    @staticmethod
    def find_devices():
        pass

    def __init__(self, centre_frequency, sample_rate=2097152, gain=30):
        self.sdr = RtlSdr()
        self.sdr.center_freq = centre_frequency
        self.sdr.sample_rate = sample_rate
        self.sdr.gain = gain
        self.sample_rate = sample_rate

    def read_samples(self, sample_size):
        return self.sdr.read_samples(sample_size)

    def cleanup(self):
        self.sdr.close()