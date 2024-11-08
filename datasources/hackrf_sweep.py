from . import SweepDataSource
from hackrf_sweep import HackRFSweep  

class HackRFSweepDataSource(SweepDataSource):

    def __init__(self, start_freq: int, stop_freq: int, bin_size):
        super().__init__(start_freq=start_freq, stop_freq=stop_freq, bin_size=bin_size)

        start_freq = self.start_freq//1e6   # Required in MHz
        stop_freq = self.stop_freq//1e6     # Required in MHz
        bin_size = self.bin_size//1e3       # Required in kHz

        self.object=HackRFSweep()
        self.object.setup(start_freq, stop_freq, bin_size)
        #self.object.run()
        self.object.get_number_of_points()

 