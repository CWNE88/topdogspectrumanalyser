import subprocess
import numpy as np
import threading
import logging
import re
from .base import SweepDataSource

logger = logging.getLogger(__name__)

class HackRFSweepDataSource(SweepDataSource):
    def __init__(self, start_freq: float, stop_freq: float, bin_size: int):
        super().__init__()
        self.start_freq = int(start_freq)
        self.stop_freq = int(stop_freq)
        self.bin_size = int(bin_size)
        self.lna_gain = 20
        self.vga_gain = 20
        self.amp_enabled = True
        self.is_running = False
        self.sweep_complete = False
        self.process = None
        self.full_power_array = np.array([])  # Last complete sweep
        self.current_sweep_data = {"x": [], "y": []}  # In-progress sweep
        self.last_step_freq = 0  # Track last frequency to detect new sweep cycles
        self.lock = threading.Lock()
        self.thread = None
        self.stderr_thread = None
        self.sweep_rate = None  # Sweeps per second
        self._create_frequency_grid()
        logger.debug(f"Initialized HackRFSweepDataSource: start_freq={self.start_freq/1e6:.2f} MHz, stop_freq={self.stop_freq/1e6:.2f} MHz, bin_size={self.bin_size/1e3:.2f} kHz, grid_size={len(self.frequency_grid)}")

    def _create_frequency_grid(self):
        """Create a fixed frequency grid based on start/stop frequencies and bin size."""
        # Calculate number of bins
        num_bins = int((self.stop_freq - self.start_freq) / self.bin_size)
        # Create evenly spaced frequency grid
        self.frequency_grid = np.linspace(self.start_freq, self.stop_freq, num_bins)
        # NaN marks bins not yet swept; displays skip or gap them naturally
        self.full_power_array = np.full(num_bins, np.nan)
        logger.debug(f"Created frequency grid with {num_bins} bins")

    def start(self, frequency=None):
        if frequency:
            self.start_freq = int(frequency.start)
            self.stop_freq = int(frequency.stop)
            logger.debug(f"Updated frequency range: start_freq={self.start_freq/1e6:.2f} MHz, stop_freq={self.stop_freq/1e6:.2f} MHz")
            # Recreate frequency grid for new range
            self._create_frequency_grid()

        # If already running, stop the existing sweep first
        if self.is_running:
            logger.debug("HackRF sweep already running, stopping before restarting")
            self.stop()

        try:
            # Format frequencies as integers (e.g., 2400:2500)
            freq_range = f"{int(self.start_freq/1e6)}:{int(self.stop_freq/1e6)}"
            cmd = [
                "hackrf_sweep",
                "-f", freq_range,
                "-a", "1" if self.amp_enabled else "0",
                "-l", str(self.lna_gain),
                "-g", str(self.vga_gain),
                "-w", str(self.bin_size),
            ]
            logger.debug(f"Starting hackrf_sweep with command: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
            )
            self.is_running = True
            self.sweep_complete = False
            self.sweep_rate = None

            # Start stdout monitoring thread
            self.thread = threading.Thread(target=self._sweep_loop)
            self.thread.start()

            # Start stderr monitoring thread
            self.stderr_thread = threading.Thread(target=self._stderr_monitor_loop)
            self.stderr_thread.start()

            logger.debug("HackRF sweep started successfully")
        except Exception as e:
            self.is_running = False
            logger.error(f"Failed to start hackrf_sweep: {str(e)}")
            raise RuntimeError(f"Failed to start hackrf_sweep: {str(e)}")

    def _sweep_loop(self):
        try:
            for line in self.process.stdout:
                if not self.is_running:
                    break
                line = line.strip()
                if line:
                    self._parse(line)
        except (ValueError, OSError):
            pass  # Pipe closed by stop() — normal shutdown
        except Exception as e:
            logger.error(f"Error during sweep loop: {str(e)}")
        finally:
            self.is_running = False
            self.sweep_complete = True

    def _stderr_monitor_loop(self):
        """Monitor stderr for sweep rate statistics."""
        try:
            # Regex to match lines like "30738 total sweeps completed, 135.24 sweeps/second"
            sweep_rate_pattern = re.compile(r'(\d+\.\d+)\s+sweeps/second')

            while self.is_running:
                line = self.process.stderr.readline()
                if line:
                    line_str = line.strip()
                    if line_str:
                        # Check for sweep rate information
                        match = sweep_rate_pattern.search(line_str)
                        if match:
                            self.sweep_rate = float(match.group(1))
                            logger.debug(f"Updated sweep rate: {self.sweep_rate:.2f} S/s")
                        elif 'gain set to' not in line_str.lower():
                            logger.debug(f"hackrf_sweep stderr: {line_str}")
                else:
                    # No more stderr data
                    break
        except (ValueError, OSError):
            pass  # Pipe closed by stop() — normal shutdown
        except Exception as e:
            logger.error(f"Error during stderr monitoring: {str(e)}")

    def _parse(self, line: str):
        # CSV format: date, time, freq_low, freq_high, bin_width, num_samples, power...
        try:
            fields = [f.strip() for f in line.split(',')]
            if len(fields) < 7:
                return
            step_low_freq = int(fields[2])
            step_high_freq = int(fields[3])
            step_data = np.array([float(v) for v in fields[6:]], dtype=np.float32)
            if step_data.size == 0:
                return

            with self.lock:
                at_start_freq = abs(step_low_freq - self.start_freq) < 1e6

                if at_start_freq and len(self.current_sweep_data["x"]) > 0:
                    sorted_indices = np.argsort(self.current_sweep_data["x"])
                    sweep_freqs = np.array(self.current_sweep_data["x"])[sorted_indices]
                    sweep_powers = np.array(self.current_sweep_data["y"])[sorted_indices]
                    self.full_power_array = np.interp(
                        self.frequency_grid, sweep_freqs, sweep_powers
                    )
                    self.current_sweep_data = {"x": [], "y": []}

                step_bandwidth = (step_high_freq - step_low_freq) / len(step_data)
                step_frequency_bins = np.arange(
                    step_low_freq + step_bandwidth / 2,
                    step_high_freq,
                    step_bandwidth
                )
                self.current_sweep_data["x"].extend(step_frequency_bins)
                self.current_sweep_data["y"].extend(step_data)
        except (ValueError, IndexError) as e:
            logger.error(f"Data parsing error: {str(e)}")

    def set_gains(self, lna_gain=None, vga_gain=None):
        if lna_gain is not None:
            self.lna_gain = int(lna_gain)
        if vga_gain is not None:
            self.vga_gain = int(vga_gain)
        if self.is_running:
            self.stop()
            self.start()

    def set_amplifier(self, enabled: bool):
        self.amp_enabled = bool(enabled)
        if self.is_running:
            self.stop()
            self.start()

    def stop(self):
        self.is_running = False

        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass

            # Close pipes so the reader threads unblock immediately rather than
            # waiting for the process to exit on its own.
            for pipe in (self.process.stdout, self.process.stderr):
                try:
                    if pipe:
                        pipe.close()
                except Exception:
                    pass

            try:
                self.process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                logger.warning("hackrf_sweep did not terminate cleanly, killing...")
                try:
                    self.process.kill()
                    self.process.wait()
                except Exception:
                    pass
            except Exception as e:
                logger.error(f"Error stopping hackrf_sweep: {e}")
            finally:
                self.process = None

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1)
        if self.stderr_thread and self.stderr_thread.is_alive():
            self.stderr_thread.join(timeout=1)

        logger.debug("HackRF sweep stopped")

    def get_data(self):
        with self.lock:
            if self.full_power_array.size == 0:
                logger.warning("No sweep data available, returning empty array")
                return np.array([])
            return self.full_power_array.copy()

    def get_number_of_points(self):
        with self.lock:
            return len(self.full_power_array)
