import struct
import subprocess
import numpy as np

from . import SweepDataSource

from python_hackrf import pyhackrf  # type: ignore

SAMPLE_RATE = 20e6
TUNE_STEP = SAMPLE_RATE / 1e6
PY_FREQ_MIN_MHZ = 0  # 0 MHz
PY_FREQ_MAX_MHZ = 7_250  # 7250 MHz
PY_FREQ_MAX_HZ = PY_FREQ_MAX_MHZ * 1e6  # Hz
INTERLEAVED_OFFSET_RATIO = 0.375
PY_BLOCKS_PER_TRANSFER = 16

class HackRFSweepDataSourceOld(SweepDataSource):

    def __init__(self, start_freq: int, stop_freq: int):
        super().__init__(start_freq=start_freq, stop_freq=stop_freq)

        start_freq /= 1e6
        stop_freq /= 1e6
        bin_width = 100e3

        pyhackrf.pyhackrf_init()
        self.device = pyhackrf.pyhackrf_open()

        self.device.set_sweep_callback(self.on_sweep)
        self.device.pyhackrf_set_sample_rate_manual(SAMPLE_RATE, 1)

        frequencies = [start_freq, stop_freq]
        num_ranges = len(frequencies) // 2

        if pyhackrf.PY_MAX_SWEEP_RANGES < num_ranges:
            RuntimeError(f'specify a maximum of {pyhackrf.PY_MAX_SWEEP_RANGES} frequency ranges')

        for i in range(num_ranges):
            frequencies[i] = int(frequencies[i])

        for i in range(num_ranges):
            if frequencies[2 * i] >= frequencies[2 * i + 1]:
                raise RuntimeError('max frequency must be greater than min frequency.')

            step_count = 1 + (frequencies[2 * i + 1] - frequencies[2 * i] - 1) // TUNE_STEP
            frequencies[2 * i + 1] = int(frequencies[2 * i] + step_count * TUNE_STEP)

            if frequencies[2 * i] < PY_FREQ_MIN_MHZ:
                raise RuntimeError(f'min frequency must must be greater than {PY_FREQ_MIN_MHZ} MHz.')
            if frequencies[2 * i + 1] > PY_FREQ_MAX_MHZ:
                raise RuntimeError(f'max frequency may not be higher {PY_FREQ_MAX_MHZ} MHz.')

        start_frequency = int(frequencies[0] * 1e6)
        OFFSET = int(SAMPLE_RATE * INTERLEAVED_OFFSET_RATIO)

        fftSize = int(SAMPLE_RATE / bin_width)
        if fftSize < 4:
            raise RuntimeError(f'bin_width should be no more than {SAMPLE_RATE // 4} Hz')
        elif fftSize > 8180:
            raise RuntimeError(f'bin_width should be no less than {SAMPLE_RATE // 8180 + 1} Hz')


        if fftSize < 4:
                raise RuntimeError(f'bin_width should be no more than {SAMPLE_RATE // 4} Hz')
        elif fftSize > 8180:
            raise RuntimeError(f'bin_width should be no less than {SAMPLE_RATE // 8180 + 1} Hz')

        while ((fftSize + 4) % 8):
            fftSize += 1
        
        norm_factor = 1.0 / fftSize
        data_length = fftSize * 2
        window = np.hanning(fftSize)


        self.device.pyhackrf_init_sweep(frequencies, num_ranges, pyhackrf.PY_BYTES_PER_BLOCK, int(TUNE_STEP * 1e6), OFFSET, pyhackrf.py_sweep_style.INTERLEAVED)

        self.device.pyhackrf_start_rx_sweep()

        pass

    def on_sweep(self, device, data: np.ndarray[:], buffer_length: int, valid_length: int):
        global samples, last_idx
        frequency = 0
        index = 0

        for j in range(PY_BLOCKS_PER_TRANSFER):
            if data[index] == 127 and data[index + 1] == 127:
                # frequency = data[index + 2] + (data[index + 3] << 8) + (data[index + 4] << 16) + (data[index + 5] << 24)
                frequency = struct.unpack('I', data[index + 2:index + 6])[0]
            else:
                index += pyhackrf.PY_BYTES_PER_BLOCK
                continue
            
        return 1

    

class HackRFSweepDataSourceOldOld(SweepDataSource):
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



