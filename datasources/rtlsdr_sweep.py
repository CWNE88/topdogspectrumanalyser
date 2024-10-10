from . import SampleDataSource

class RtlSweepDataSource(SampleDataSource):
    def __init__(self, centre_frequency, sample_rate=2097152, gain=30):
        # Initialise RTL Sweep specific parameters
        pass

    def read_samples(self, sample_size):
        # Implement the logic to read samples for RTL Sweep
        pass

    def cleanup(self):
        # Cleanup RTL Sweep resources
        pass


# Paul did some work

import shlex
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
        self.databuffer = {"timestamp": "", "x": [], "y": []}
        self.last_timestamp = ""
        self.lnb_lo = 0  # Assuming lnb_lo needs to be managed; adjust if necessary

    def setup(self, start_freq=2400, stop_freq=2450, bin_size=1000000, gain=10, interval=1):
        """Set up the sweep parameters."""
        self.params = {
            "start_freq": start_freq,  # MHz
            "stop_freq": stop_freq,    # MHz
            "bin_size": bin_size,      # kHz
            "interval": interval,      # Time between samples in seconds
            "gain": gain
        }

    def run(self):
        """Start the sweep process."""
        if not self.process and self.params:
            cmdline = [
                "rtl_power",
                "-f", (
                    f"{int(self.params['start_freq'])}M:"
                    f"{int(self.params['stop_freq'])}M:"
                    f"{int(self.params['bin_size'])}k"
                ),
                "-i", str(int(self.params['interval'])),
                "-g", str(self.params['gain']),
                
            ]
            print('Starting backend:')
            print(' '.join(cmdline))
            print()

            self.process = subprocess.Popen(
                cmdline,
                stdout=subprocess.PIPE,
                universal_newlines=True
            )
            self.is_running = True

            # Read lines from stdout and parse them
            for line in self.process.stdout:
                self.parse_output(line.strip())

            self.stop()  # Ensure stop is called to clean up

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

    def parse_output(self, line):
        """Parse one line of output from rtl_power."""
        try:
            # Split the line by commas and strip whitespace
            columns = [col.strip() for col in line.split(",")]

            # Extract and parse the relevant fields
            timestamp = " ".join(columns[:2])  # Combine date and time
            start_freq = int(columns[2])  # Starting frequency in Hz
            stop_freq = int(columns[3])  # Stopping frequency in Hz
            step = float(columns[4])  # Frequency step size in Hz
            
            # Generate frequency axis (x-axis) and power values (y-axis)
            y_axis = [float(y) for y in columns[6:]]
            x_axis = list(np.linspace(start_freq, stop_freq, len(y_axis)))
            
            # Update data buffer based on timestamp
            if timestamp != self.last_timestamp:

                print ("x data " + str(self.databuffer["x"]))
                print ("y data " + str(self.databuffer["y"]))
                self.last_timestamp = timestamp
                self.databuffer = {
                    "timestamp": timestamp,
                    "x": x_axis,
                    "y": y_axis
                }
            else:
                self.databuffer["x"].extend(x_axis)
                self.databuffer["y"].extend(y_axis)
            
        except ValueError as e:
            print(f"ValueError encountered: {e} - check the input data format.")
        except Exception as e:
            print(f"Unexpected error encountered: {e}")

    def get_data(self):
        """Return the full sweep data."""
        return np.array(self.databuffer["y"])
