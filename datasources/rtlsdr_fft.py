from . import SampleDataSource
from rtlsdr import RtlSdr

class RtlSdrDataSource(SampleDataSource):

    @staticmethod
    def find_devices():
        pass

    def __init__(self, centre_frequency, sample_rate=2097152, gain=46.4, bias_tee=False):
        super().__init__(centre_frequency, sample_rate, gain)

        self.sdr = RtlSdr()
        self.sdr.center_freq = centre_frequency
        self.sdr.sample_rate = sample_rate
        self.sdr.gain = gain
        self.bias_tee=bias_tee

        self.sdr.set_bias_tee(self.bias_tee)

    def set_bias_tee(self, enabled):
        """Set the bias tee state and update the internal attribute."""
        self.bias_tee = enabled
        self.sdr.set_bias_tee(self.bias_tee)
        
    
    def set_centre_freq(self, freq_hz):
        self.sdr.center_freq = freq_hz
        self.centre_freq = freq_hz
        

    def read_samples(self, sample_size):
        return self.sdr.read_samples(sample_size)
    
        

    def cleanup(self):
        self.sdr.close()