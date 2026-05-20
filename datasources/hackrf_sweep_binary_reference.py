# Reference copy of the binary (-B flag) parsing methods from hackrf_sweep.py.
# Not used by the application — kept for notes only.
# Replaced with CSV text parsing for Windows compatibility (Windows CRT text mode
# corrupts binary pipe output by inserting 0x0D before every 0x0A byte).

import struct
import numpy as np


def _sweep_loop_binary(self):
    """Read binary records from hackrf_sweep -B stdout."""
    try:
        while self.is_running:
            hackrf_buffer_header = self.process.stdout.read(4)
            if hackrf_buffer_header:
                record_length, = struct.unpack('I', hackrf_buffer_header)
                hackrf_buffer_data = self.process.stdout.read(record_length)
                _parse_binary(self, hackrf_buffer_data)
            else:
                break
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error during sweep loop: {str(e)}")
    finally:
        self.is_running = False
        self.sweep_complete = True


def _parse_binary(self, hackrf_data):
    """Parse a single binary record.

    Binary record format (hackrf_sweep -B):
      4 bytes  uint32  record_length  (already consumed by caller)
      8 bytes  uint64  step_low_freq  (Hz)
      8 bytes  uint64  step_high_freq (Hz)
      N bytes  float32 power values   (dBm, little-endian)
    """
    try:
        step_low_freq, step_high_freq = struct.unpack('QQ', hackrf_data[:16])
        step_data = np.frombuffer(hackrf_data[16:], dtype='<f4')
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
    except (struct.error, ValueError) as e:
        import logging
        logging.getLogger(__name__).error(f"Data parsing error: {str(e)}")
