import struct
import subprocess
import numpy as np
import threading
from frequencyselector import FrequencyRange

class HackRFSweep:
    def __init__(self):
        self.is_running = False
        self.sweep_complete = False
        self.process = None
        self.full_power_array = np.array([])
        self.lock = threading.Lock()
        self.stop_flag = threading.Event()
        self.thread = None

    def start(self, range: FrequencyRange):
        """Start the hackrf_sweep subprocess and process its output."""
        if self.is_running:
            self.stop()

        self.start_freq = int(range.start / 1e6)  # MHz
        self.stop_freq = int(range.stop / 1e6)    # MHz
        self.bin_size = int(range.res_bw)         # Hz

        cmdline = [
            "hackrf_sweep",
            "-f", f"{self.start_freq}:{self.stop_freq}",
            "-B",  # Binary output
            "-a", "1",  # Enable amp
            "-g", "20",  # Gain
            "-l", "20",  # LNA gain
            "-w", str(self.bin_size)
        ]
        print(f"Running command: {' '.join(cmdline)}")
        try:
            self.process = subprocess.Popen(
                cmdline,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0  # Unbuffered
            )
            self.is_running = True
            self.sweep_complete = False
            self.stop_flag.clear()
            self.thread = threading.Thread(target=self._sweep_loop)
            self.thread.start()
        except FileNotFoundError:
            print("Error: hackrf_sweep binary not found")
            self.is_running = False

    def _sweep_loop(self):
        """Loop to read and process sweep data."""
        try:
            while self.is_running and not self.stop_flag.is_set():
                hackrf_buffer_header = self.process.stdout.read(4)
                if not hackrf_buffer_header:
                    break
                record_length, = struct.unpack('I', hackrf_buffer_header)
                hackrf_buffer_data = self.process.stdout.read(record_length)
                if hackrf_buffer_data:
                    self.parse(hackrf_buffer_data)
        except Exception as e:
            print(f"Error during sweep loop: {e}")
        finally:
            self.stop()
            self.sweep_complete = True

    def parse(self, hackrf_data):
        """Parse the data and store it in full_power_array."""
        try:
            step_low_freq, step_high_freq = struct.unpack('QQ', hackrf_data[:16])
            step_data = np.frombuffer(hackrf_data[16:], dtype='<f4')
            if step_data.size == 0:
                return

            with self.lock:
                step_bandwidth = (step_high_freq - step_low_freq) / len(step_data)
                step_frequency_bins = np.arange(
                    step_low_freq + step_bandwidth / 2,
                    step_high_freq,
                    step_bandwidth
                )

                if step_low_freq / 1e6 <= self.start_freq:
                    self.full_power_array = np.array([])

                # Append data
                if self.full_power_array.size == 0:
                    self.full_power_array = step_data
                else:
                    self.full_power_array = np.concatenate((self.full_power_array, step_data))

                # Sort and trim when sweep completes
                if step_high_freq / 1e6 >= self.stop_freq:
                    self.full_power_array = self.full_power_array[:int((self.stop_freq - self.start_freq) * 1e6 / self.bin_size)]

        except (struct.error, ValueError) as e:
            print(f"Data parsing error: {e}")

    def stop(self):
        """Stop the subprocess and cleanup."""
        with self.lock:
            self.is_running = False
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

        self.stop_flag.set()
        if self.thread and self.thread.is_alive():
            print("Stopping sweep thread...")
            self.thread.join(timeout=5)
            self.thread = None

    def get_data(self):
        """Return the full sweep data (power levels)."""
        with self.lock:
            return self.full_power_array.copy()  # Return a copy to avoid race conditions

    def get_number_of_points(self):
        """Return the number of data points."""
        with self.lock:
            return len(self.full_power_array)

    def is_sweep_complete(self):
        """Check if the sweep has completed."""
        return self.sweep_complete
