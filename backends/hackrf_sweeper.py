import struct
import subprocess
import numpy as np
import threading

class HackRFSweep:
    def __init__(self):
        self.is_running = False
        self.sweep_complete = False
        self.process = None
        self.full_power_array = np.array([])
        self.sweep_data = {
            "x": [],
            "y": []
        }
        self.lock = threading.Lock()
        self.thread = None

    def setup(self, start_freq=2400, stop_freq=2500, bin_size=5000):
        """Set up the sweep parameters."""
        if start_freq >= stop_freq:
            raise ValueError("Start frequency must be less than stop frequency.")
        self.start_freq = start_freq
        self.stop_freq = stop_freq
        self.bin_size = bin_size

    def run(self):
        """Start the hackrf_sweep subprocess and process its output."""
        if self.process is None:
            cmdline = [
                "hackrf_sweep",
                "-f", f"{self.start_freq}:{self.stop_freq}",
                "-B",
                "-w", str(self.bin_size)
            ]
            print(f"Running command: {' '.join(cmdline)}")
            self.process = subprocess.Popen(
                cmdline, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.is_running = True
            self.sweep_complete = False
            self.thread = threading.Thread(target=self._sweep_loop)
            self.thread.start()

    def _sweep_loop(self):
        """Loop to read and process sweep data."""
        try:
            while self.is_running:
                hackrf_buffer_header = self.process.stdout.read(4)
                if hackrf_buffer_header:
                    record_length, = struct.unpack('I', hackrf_buffer_header)
                    hackrf_buffer_data = self.process.stdout.read(record_length)
                    self.parse(hackrf_buffer_data)
                else:
                    break
        finally:
            self.stop()
            self.sweep_complete = True

    def parse(self, hackrf_data):
        """Parse the data and store it in full_power_array."""
        try:
            step_low_frequency, step_high_frequency = struct.unpack('QQ', hackrf_data[:16])
            step_data = np.frombuffer(hackrf_data[16:], dtype='<f4')
        except (struct.error, ValueError) as e:
            print(f"Data parsing error: {e}")
            return

        with self.lock:
            if step_low_frequency / 1e6 <= self.start_freq:
                self.sweep_data = {"x": [], "y": []}

            step_bandwidth = (step_high_frequency - step_low_frequency) / len(step_data)
            step_frequency_bins = np.arange(
                step_low_frequency + step_bandwidth / 2,
                step_high_frequency,
                step_bandwidth
            )

            self.sweep_data["x"].extend(step_frequency_bins)
            self.sweep_data["y"].extend(step_data)

            if step_high_frequency / 1e6 >= self.stop_freq:
                sorted_indices = np.argsort(self.sweep_data["x"])
                self.full_power_array = np.array(self.sweep_data["y"])[sorted_indices]
            #print(self.full_power_array)

    def stop(self):
        """Stop the subprocess."""
        if self.process:
            try:
                print("Terminating subprocess...")
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("Process did not terminate in time. Killing...")
                self.process.kill()
            finally:
                self.process = None
        self.is_running = False

    def get_data(self):
        """Return the full sweep data."""
        with self.lock:
            return np.array(self.full_power_array)
    
    def get_number_of_points(self):
        return len(self.full_power_array)

    def is_sweep_complete(self):
        """Check if the sweep has completed."""
        return self.sweep_complete
