import struct
import subprocess
import numpy as np
import asyncio

class HackRFSweep:
    def __init__(self):
        self.is_running = False
        self.sweep_complete = False
        self.process = None
        self.full_power_array = np.array([])
        self.sweep_data = {"x": [], "y": []}
        self.lock = asyncio.Lock()

    def setup(self, start_freq=2400, stop_freq=2500, bin_size=5000):
        if start_freq >= stop_freq:
            raise ValueError("Start frequency must be less than stop frequency.")
        self.start_freq = start_freq
        self.stop_freq = stop_freq
        self.bin_size = bin_size

    async def run(self):
        if self.process is None:
            cmdline = [
                "hackrf_sweep",
                "-f", f"{self.start_freq}:{self.stop_freq}",
                "-B",
                "-a 1",
                "-g 40",
                "-l 40",
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
            await self._sweep_loop()

    async def _sweep_loop(self):
        try:
            while self.is_running:
                hackrf_buffer_header = await asyncio.to_thread(self.process.stdout.read, 4)
                if hackrf_buffer_header:
                    record_length, = struct.unpack('I', hackrf_buffer_header)
                    hackrf_buffer_data = await asyncio.to_thread(self.process.stdout.read, record_length)
                    await self.parse(hackrf_buffer_data)
                else:
                    break
        except Exception as e:
            print(f"Error during sweep loop: {e}")
        finally:
            await self.stop()
            self.sweep_complete = True

    async def parse(self, hackrf_data):
        try:
            step_low_freq, step_high_freq = struct.unpack('QQ', hackrf_data[:16])
            step_data = np.frombuffer(hackrf_data[16:], dtype='<f4')
            if step_data.size == 0:
                return

            async with self.lock:
                if step_low_freq / 1e6 <= self.start_freq:
                    self.sweep_data = {"x": [], "y": []}

                step_bandwidth = (step_high_freq - step_low_freq) / len(step_data)
                step_frequency_bins = np.arange(
                    step_low_freq + step_bandwidth / 2,
                    step_high_freq,
                    step_bandwidth
                )

                self.sweep_data["x"].extend(step_frequency_bins)
                self.sweep_data["y"].extend(step_data)

                if step_high_freq / 1e6 >= self.stop_freq:
                    sorted_indices = np.argsort(self.sweep_data["x"])
                    self.full_power_array = np.array(self.sweep_data["y"])[sorted_indices]

        except (struct.error, ValueError) as e:
            print(f"Data parsing error: {e}")

    async def stop(self):
        if self.process:
            try:
                print("Terminating subprocess...")
                self.process.terminate()
                await asyncio.to_thread(self.process.wait, timeout=5)
            except subprocess.TimeoutExpired:
                print("Process did not terminate in time. Killing...")
                self.process.kill()
            finally:
                self.process = None
        self.is_running = False

    async def get_data(self):
        async with self.lock:
            return np.array(self.full_power_array)

    async def get_number_of_points(self):
        async with self.lock:
            return len(self.full_power_array)

    def is_sweep_complete(self):
        return self.sweep_complete
