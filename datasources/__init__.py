
from PyQt6.QtCore import pyqtSignal, QObject



class DataSource:
    @staticmethod
    def find_devices():
        pass

    def device_init(self, index=0):
        pass

    def read_samples(self, sample_size):
        raise NotImplementedError

    def cleanup(self):
        raise NotImplementedError
    
class SweepDataSource(QObject):
    sweep_signal = pyqtSignal()
    def __init__(self, on_sweep_callback):
        super().__init__()
        self.on_sweep = on_sweep_callback
        
    