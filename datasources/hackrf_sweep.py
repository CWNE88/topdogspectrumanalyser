import struct
import subprocess
import numpy as np
import threading
import logging
from .base import SweepDataSource

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class HackRFSweepDataSource(SweepDataSource):
    def __init__(self, start_freq: float, stop_freq: float, bin_size: int):
        super().__init__()
        self.start_freq = int(start_freq)
        self.stop_freq = int(stop_freq)
        self.bin_size = int(bin_size)
        self.is_running = False
        self.sweep_complete = False
        self.process = None
        self.full_power_array = np.array([])
        self.sweep_data = {"x": [], "y": []}
        self.lock = threading.Lock()
        self.thread = None
        logging.debug(f"Initialized HackRFSweepDataSource: start_freq={self.start_freq/1e6:.2f} MHz, stop_freq={self.stop_freq/1e6:.2f} MHz, bin_size={self.bin_size/1e3:.2f} kHz")

    def start(self, frequency=None):
        if frequency:
            self.start_freq = int(frequency.start)
            self.stop_freq = int(frequency.stop)
            logging.debug(f"Updated frequency range: start_freq={self.start_freq/1e6:.2f} MHz, stop_freq={self.stop_freq/1e6:.2f} MHz")

        # If already running, stop the existing sweep first
        if self.is_running:
            logging.debug("HackRF sweep already running, stopping before restarting")
            self.stop()

        try:
            # Format frequencies as integers (e.g., 2400:2500)
            freq_range = f"{int(self.start_freq/1e6)}:{int(self.stop_freq/1e6)}"
            cmd = [
                "hackrf_sweep",
                "-f", freq_range,
                "-B",  # Binary output
                "-a", "1",  # Enable amplifier
                "-g", "20",  # VGA gain
                "-l", "20",  # LNA gain (leaving as-is since it doesn't prevent running)
                "-w", str(self.bin_size)  # Bin size in Hz
            ]
            logging.debug(f"Starting hackrf_sweep with command: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False  # Handle as binary data
            )
            self.is_running = True
            self.sweep_complete = False
            self.thread = threading.Thread(target=self._sweep_loop)
            self.thread.start()
            # Check stderr for initial errors
            initial_stderr = self.process.stderr.readline()
            if initial_stderr:
                # Decode bytes to string for logging and comparison
                initial_stderr_str = initial_stderr.decode('utf-8', errors='replace')
                logging.error(f"hackrf_sweep stderr: {initial_stderr_str}")
                if "No HackRF device found" in initial_stderr_str:
                    raise RuntimeError("No HackRF device found. Ensure the device is connected and accessible.")
            logging.debug("HackRF sweep started successfully")
        except Exception as e:
            self.is_running = False
            logging.error(f"Failed to start hackrf_sweep: {str(e)}")
            raise RuntimeError(f"Failed to start hackrf_sweep: {str(e)}")

    def _sweep_loop(self):
        try:
            while self.is_running:
                hackrf_buffer_header = self.process.stdout.read(4)
                if hackrf_buffer_header:
                    record_length, = struct.unpack('I', hackrf_buffer_header)
                    hackrf_buffer_data = self.process.stdout.read(record_length)
                    self._parse(hackrf_buffer_data)
                else:
                    logging.debug("No more data from hackrf_sweep, exiting sweep loop")
                    break
        except Exception as e:
            logging.error(f"Error during sweep loop: {str(e)}")
        finally:
            self.is_running = False
            self.sweep_complete = True

    def _parse(self, hackrf_data):
        try:
            step_low_freq, step_high_freq = struct.unpack('QQ', hackrf_data[:16])
            step_data = np.frombuffer(hackrf_data[16:], dtype='<f4')
            if step_data.size == 0:
                logging.warning("No data in step, skipping")
                return

            with self.lock:
                if step_low_freq / 1e6 <= self.start_freq / 1e6:
                    self.sweep_data = {"x": [], "y": []}

                step_bandwidth = (step_high_freq - step_low_freq) / len(step_data)
                step_frequency_bins = np.arange(
                    step_low_freq + step_bandwidth / 2,
                    step_high_freq,
                    step_bandwidth
                )

                self.sweep_data["x"].extend(step_frequency_bins)
                self.sweep_data["y"].extend(step_data)

                if step_high_freq / 1e6 >= self.stop_freq / 1e6:
                    sorted_indices = np.argsort(self.sweep_data["x"])
                    self.full_power_array = np.array(self.sweep_data["y"])[sorted_indices]
                    logging.debug(f"Full sweep completed: {len(self.full_power_array)} points")
        except (struct.error, ValueError) as e:
            logging.error(f"Data parsing error: {str(e)}")

    def stop(self):
        if self.process:
            try:
                logging.debug("Terminating hackrf_sweep subprocess...")
                self.process.terminate()
                self.process.wait(timeout=5)
                # Log any remaining stderr output
                if self.process:
                    stderr_output = self.process.stderr.read()
                    if stderr_output:
                        stderr_output_str = stderr_output.decode('utf-8', errors='replace')
                        logging.error(f"hackrf_sweep stderr on stop: {stderr_output_str}")
            except subprocess.TimeoutExpired:
                logging.warning("hackrf_sweep process did not terminate in time. Killing...")
                self.process.kill()
            except Exception as e:
                logging.error(f"Error terminating hackrf_sweep subprocess: {str(e)}")
            finally:
                self.process = None
        self.is_running = False
        logging.debug("HackRF sweep stopped")

    def get_data(self):
        with self.lock:
            if self.full_power_array.size == 0:
                logging.warning("No sweep data available, returning empty array")
                return np.array([])
            return self.full_power_array.copy()

    def get_number_of_points(self):
        with self.lock:
            return len(self.full_power_array)
