import struct
import subprocess
import threading
from pyqtgraph.Qt import QtCore
import numpy as np

class Sweep(QtCore.QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        self.process = None
        self.params = None
        self._shutdown_lock = threading.Lock()
        self.full_frequency_array = np.array([])
        self.full_power_array = np.array([])
        self.is_buffer_available = False

    def setup(self, start_freq=2400, stop_freq=2450, bin_size=500):
        """Set up the sweep parameters."""
        self.params = {
            "start_freq": start_freq,  # MHz
            "stop_freq": stop_freq,    # MHz
            "bin_size": bin_size       # kHz
        }
        self.sweep_data = {
            "x": [],
            "y": []
        }

    def run(self):
        """Start the sweep process."""
        if self.process is None and self.params:
            cmdline = [
                "hackrf_sweep",
                "-f", f"{int(self.params['start_freq'])}:{int(self.params['stop_freq'])}",
                "-B",
                "-w", str(int(self.params['bin_size'] * 1000))
            ]
            print(cmdline)

            self.process = subprocess.Popen(cmdline, stdout=subprocess.PIPE, bufsize=1, universal_newlines=False)
            self.is_running = True
            
            while self.is_running:
                self.is_buffer_available = False
                hackrf_buffer = self.process.stdout.read(4)

                if hackrf_buffer:
                    self.is_buffer_available = True
                    record_length, = struct.unpack('I', hackrf_buffer)
                    hackrf_buffer = self.process.stdout.read(record_length)
                    if hackrf_buffer:
                        self.parse(hackrf_buffer)
                    else:
                        break
                else:
                    break

            self.stop()
            self.is_running = False

    def stop(self):
        """Terminate the sweep process."""
        with self._shutdown_lock:
            if self.process:
                try:
                    self.process.terminate()
                except ProcessLookupError:
                    pass
                self.process.wait()
                self.process = None
        self.is_running = False
        self.wait()

    def parse(self, hackrf_data):
        """Parse the data from the HackRF sweep."""
        step_low_frequency, step_high_frequency = struct.unpack('QQ', hackrf_data[:16])
        step_data = np.frombuffer(hackrf_data[16:], dtype='<f4')
        step_bandwidth = (step_high_frequency - step_low_frequency) / len(step_data)
        
        if step_low_frequency / 1e6 <= self.params["start_freq"]:
            self.sweep_data = {"x": [], "y": []}

        step_frequency_bins = np.arange(
            step_low_frequency + step_bandwidth / 2,
            step_high_frequency,
            step_bandwidth
        )
        
        self.sweep_data["x"].extend(step_frequency_bins)
        self.sweep_data["y"].extend(step_data)

        if step_high_frequency / 1e6 >= self.params["stop_freq"]:
            sorted_indices = np.argsort(self.sweep_data["x"])
            self.full_frequency_array = np.array(self.sweep_data["x"])[sorted_indices]
            self.full_power_array = np.array(self.sweep_data["y"])[sorted_indices]
        
        print(self.full_frequency_array)
        print(self.full_power_array)

    def get_data(self):
        """Return the full sweep data."""
        return np.array(self.full_power_array)
