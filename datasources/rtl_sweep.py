import subprocess
import shlex
import numpy as np
import logging
import select
import os
from threading import Thread
from datasources.base import SweepDataSource
from frequencyselector import FrequencyRange

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class RtlSweepDataSource(SweepDataSource):
    """Data source for RTL-SDR frequency sweep using rtl_power binary."""
    
    def __init__(self, start_freq: float, stop_freq: float, bin_size: float):
        super().__init__()
        self.start_freq = max(24e6, min(start_freq, 1766e6))  # RTL range: 24–1766 MHz
        self.stop_freq = max(24e6, min(stop_freq, 1766e6))
        self.bin_size = 10e3  # 10 kHz for finer resolution
        self.interval = 1.0  # Update interval in seconds
        self.gain = -1  # Auto gain
        self.ppm = 0  # Frequency correction
        self.crop = 0  # No cropping
        self.device = 0  # Default device index
        self.lnb_lo = 0  # No LNB offset
        self.process = None
        self.stdout_thread = None
        self.stderr_thread = None
        self.databuffer = {}
        self.last_timestamp = ""
        self.running = False
        logging.debug(f"Initialized RtlSweepDataSource: start={self.start_freq/1e6:.2f} MHz, "
                     f"stop={self.stop_freq/1e6:.2f} MHz, bin_size={self.bin_size/1e3:.2f} kHz")

    def start(self, frequency: FrequencyRange):
        """Start the rtl_power process with the given frequency range."""
        try:
            self.start_freq = max(24e6, min(frequency.start, 1766e6))
            self.stop_freq = max(24e6, min(frequency.stop, 1766e6))
            if self.start_freq >= self.stop_freq:
                raise ValueError("Start frequency must be less than stop frequency")
            
            if self.running:
                self.stop()
            
            # Kill any stray RTL-SDR processes to free the device
            try:
                subprocess.run(["pkill", "-f", "rtl_power"], check=False)
                subprocess.run(["pkill", "-f", "rtl_test"], check=False)
                logging.debug("Terminated stray rtl_power and rtl_test processes")
            except subprocess.SubprocessError as e:
                logging.warning(f"Failed to kill stray processes: {str(e)}")
            
            cmdline = shlex.split("rtl_power")
            cmdline.extend([
                "-f", f"{int(self.start_freq/1e6)}M:{int(self.stop_freq/1e6)}M:{int(self.bin_size/1e3)}k",
                "-i", f"{self.interval}",
                "-d", f"{self.device}",
                "-p", f"{self.ppm}",
                "-c", f"{self.crop}"
            ])
            if self.gain >= 0:
                cmdline.extend(["-g", f"{self.gain}"])
            
            logging.debug(f"Starting rtl_power: {' '.join(cmdline)}")
            for attempt in range(3):  # Retry up to 3 times
                try:
                    self.process = subprocess.Popen(
                        cmdline,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True,
                        bufsize=1
                    )
                    # Check if process started
                    if self.process.poll() is None:
                        break
                    logging.warning(f"rtl_power attempt {attempt+1} failed, retrying...")
                except subprocess.SubprocessError as e:
                    logging.error(f"rtl_power attempt {attempt+1} failed: {str(e)}")
                    if attempt == 2:
                        raise RuntimeError(f"Failed to start rtl_power after 3 attempts: {str(e)}")
            
            self.running = True
            self.databuffer = {}
            self.last_timestamp = ""
            
            # Start threads for stdout and stderr
            self.stdout_thread = Thread(target=self._read_stdout, daemon=True)
            self.stderr_thread = Thread(target=self._read_stderr, daemon=True)
            self.stdout_thread.start()
            self.stderr_thread.start()
            logging.debug("rtl_power process started successfully")
        except Exception as e:
            self.running = False
            logging.error(f"Failed to start rtl_power: {str(e)}")
            self.stop()
            raise

    def stop(self):
        """Stop the rtl_power process and clean up."""
        try:
            self.running = False
            if self.process:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    logging.warning("rtl_power process killed after timeout")
                self.process = None
            self.stdout_thread = None
            self.stderr_thread = None
            self.databuffer = {}
            self.last_timestamp = ""
            logging.debug("rtl_power process stopped")
        except Exception as e:
            logging.error(f"Error stopping rtl_power: {str(e)}")

    def get_data(self) -> np.ndarray:
        """Return the latest power levels from the databuffer."""
        try:
            if not self.running or not self.databuffer or "y" not in self.databuffer:
                logging.debug("No data available in databuffer")
                return np.array([])
            power_levels = np.array(self.databuffer["y"], dtype=np.float32)
            logging.debug(f"Retrieved {len(power_levels)} power levels")
            return power_levels
        except Exception as e:
            logging.error(f"Error getting data: {str(e)}")
            return np.array([])

    def _read_stdout(self):
        """Read and parse rtl_power stdout."""
        try:
            while self.running and self.process:
                rlist, _, _ = select.select([self.process.stdout], [], [], 1.0)
                if not rlist:
                    continue
                line = self.process.stdout.readline().strip()
                if not line:
                    if self.process.poll() is not None:
                        break
                    continue
                logging.debug(f"Raw rtl_power output: {line}")
                self._parse_output(line)
        except Exception as e:
            logging.error(f"Error reading rtl_power stdout: {str(e)}")
        finally:
            if self.running:
                self.stop()

    def _read_stderr(self):
        """Read rtl_power stderr for errors."""
        try:
            while self.running and self.process:
                rlist, _, _ = select.select([self.process.stderr], [], [], 1.0)
                if not rlist:
                    continue
                line = self.process.stderr.readline().strip()
                if line:
                    logging.error(f"rtl_power stderr: {line}")
        except Exception as e:
            logging.error(f"Error reading rtl_power stderr: {str(e)}")

    def _parse_output(self, line: str):
        """Parse one line of rtl_power output."""
        try:
            line = [col.strip() for col in line.split(",")]
            if len(line) < 6:
                logging.warning(f"Invalid rtl_power output: {line}")
                return
            timestamp = " ".join(line[:2])
            start_freq = int(line[2])
            stop_freq = int(line[3])
            step = float(line[4])
            samples = float(line[5])
            y_axis = [float(y) for y in line[6:] if y]
            
            x_axis = list(np.linspace(
                start_freq + self.lnb_lo,
                stop_freq + self.lnb_lo,
                round((stop_freq - start_freq) / step)
            ))
            
            if len(x_axis) != len(y_axis):
                logging.warning(f"Length mismatch: x_axis={len(x_axis)}, y_axis={len(y_axis)}")
                if len(x_axis) > len(y_axis):
                    x_axis = x_axis[:len(y_axis)]
                else:
                    y_axis = y_axis[:len(x_axis)]
            
            if timestamp != self.last_timestamp:
                self.last_timestamp = timestamp
                self.databuffer = {
                    "timestamp": timestamp,
                    "x": x_axis,
                    "y": y_axis
                }
            else:
                self.databuffer["x"].extend(x_axis)
                self.databuffer["y"].extend(y_axis)
            
            # Update when the full sweep is complete
            if stop_freq >= (self.stop_freq - self.lnb_lo) - step:
                logging.debug(f"Full sweep completed: {len(self.databuffer['y'])} points")
        except Exception as e:
            logging.error(f"Error parsing rtl_power output: {str(e)}")