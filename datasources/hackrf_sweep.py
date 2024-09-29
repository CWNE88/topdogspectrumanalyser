import struct
import subprocess
import numpy as np
import threading


from . import SweepDataSource

class HackRFSweepDataSourceOld(SweepDataSource):
    def __init__(self, on_sweep_callback, start_freq=2.4e9, stop_freq=2.5e9, bin_size=500e3):
        super().__init__(on_sweep_callback)

        self.start_freq = start_freq
        self.stop_freq = stop_freq
        self.bin_size = bin_size

        self.is_running = False
        self.process = None

        self.bins = np.arange(start_freq, stop_freq, bin_size)
        self.pwr = np.zeros(len(self.bins))

        self.thread = None
        self.sweep_signal.connect(self.on_full_sweep)
        self.run()

    def cleanup(self):
        self.stop()

    def on_full_sweep(self):
        copy = {
            "x": np.array(self.bins),
            "y": np.array(self.pwr)
        }

        self.on_sweep(copy)

    def run(self):
        """Start the hackrf_sweep subprocess and process its output."""
        if self.process is None:
            cmdline = [
                "hackrf_sweep",
                "-f", f"{int(self.start_freq / 1e6)}:{int(self.stop_freq / 1e6)}",
                "-B",
                "-a 1",
                "-g 20",
                "-l 20",
                "-w", str(int(self.bin_size))
            ]
            print(f"Running command: {' '.join(cmdline)}")
            print()
            self.process = subprocess.Popen(
                cmdline, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.is_running = True
            self.sweep_complete = False
            self.thread = threading.Thread(target=self._sweep_loop)
            self.thread.daemon = True
            self.thread.start()

    def _sweep_loop(self):
        """Loop to read and process sweep data."""
        try:
            while self.is_running:
                hackrf_buffer_header = self.process.stdout.read(4)
                if hackrf_buffer_header:
                    record_length, = struct.unpack('I', hackrf_buffer_header)
                    self.record_length = (record_length - 16) / 4

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
            index = self.bins.searchsorted(step_low_frequency, side='left')

            for sample in struct.iter_unpack('<f', hackrf_data[16:]):
                if index >= len(self.pwr):
                    break # HACK: figure out the off by one problem
                self.pwr[index] = sample[0]
                index += 1

            if step_high_frequency >= self.stop_freq:
                self.sweep_signal.emit();


        except (struct.error, ValueError) as e:
            print(f"Data parsing error: {e}")
            return

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



