
from PyQt6.QtCore import pyqtSignal, QObject



class SampleDataSource:
    centre_freq: float
    sample_rate: float
    gain: float

    def __init__(self, centre_freq: float, sample_rate: float, gain: float) -> None:
        self.centre_freq = centre_freq
        self.sample_rate = sample_rate
        self.gain = gain

    @staticmethod
    def find_devices():
        pass

    def device_init(self, index=0):
        pass

    def set_centre_freq(self, freq_hz: int):
        pass

    def read_samples(self, sample_size):
        raise NotImplementedError

    def cleanup(self):
        raise NotImplementedError
    
class SweepDataSource(QObject):
    sweep_signal = pyqtSignal()
    start_freq: int
    stop_freq: int

    def __init__(self, start_freq: int, stop_freq: int):
        super().__init__()
        self.start_freq = start_freq
        self.stop_freq = stop_freq
        
    
