import subprocess
import numpy as np
import threading

class RTLPowerSweep:
    def __init__(self):
        self.is_running = False
        self.sweep_complete = False
        self.process = None
        self.full_power_array = np.array([])
        self.databuffer = {
            "timestamp": "",
            "x": [],
            "y": []
        }
        self.lock = threading.Lock()
        self.thread = None
        self.params = {
            "start_freq": 88,   # Default values updated
            "stop_freq": 108,
            "bin_size": 1000,   # Default values updated
            "interval": 1,
            "gain": 20
        }
        self.last_timestamp = ""

    def setup(self, start_freq=88, stop_freq=108, bin_size=1000, interval=1, gain=20):
        """Set up the sweep parameters."""
        if start_freq >= stop_freq:
            raise ValueError("Start frequency must be less than stop frequency.")
        self.params = {
            "start_freq": start_freq,
            "stop_freq": stop_freq,
            "bin_size": bin_size,
            "interval": interval,
            "gain": gain
        }

    def run(self):
        """Start the rtl_power subprocess and process its output."""
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
                "output.csv"  # Example output file; adjust as needed
            ]
            print('Starting backend:')
            print(' '.join(cmdline))
            print()

            self.process = subprocess.Popen(
                cmdline,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.is_running = True
            self.sweep_complete = False
            self.thread = threading.Thread(target=self._sweep_loop)
            self.thread.start()
        else:
            print("Process is already running or parameters are not set.")

    def _sweep_loop(self):
        """Loop to read and process sweep data."""
        try:
            while self.is_running:
                line = self.process.stdout.readline().decode('utf-8')
                if not line:
                    break
                self.parse_output(line)
                print (self.parse_output(line))
        finally:
            print(f"Stopping sweep loop. Process: {self.process}")
            self.stop()
            self.sweep_complete = True

    def parse_output(self, line):
        """Parse one line of output from rtl_power."""
        try:
            # Split the line by commas and strip whitespace
            columns = [col.strip() for col in line.split(",")]

            # Extract and parse the relevant fields
            timestamp = " ".join(columns[:2])  # Combine date and time
            start_freq = int(columns[2])  # Starting frequency in Hz
            stop_freq = int(columns[3])  # Stopping frequency in Hz
            # step = float(columns[4])  # Frequency step size in Hz (if needed)

            # Generate frequency axis (x-axis) and power values (y-axis)
            y_axis = [float(y) for y in columns[6:]]
            x_axis = list(np.linspace(start_freq, stop_freq, len(y_axis)))

            # Update data buffer based on timestamp
            if timestamp != self.last_timestamp:
                # Print the data for debugging
                print("x data:", self.databuffer["x"])
                print("y data:", self.databuffer["y"])

                self.last_timestamp = timestamp
                self.databuffer = {
                    "timestamp": timestamp,
                    "x": x_axis,
                    "y": y_axis
                }
            else:
                self.databuffer["x"].extend(x_axis)
                self.databuffer["y"].extend(y_axis)

            # Update full_power_array if needed
            if start_freq <= self.params['start_freq'] and stop_freq >= self.params['stop_freq']:
                sorted_indices = np.argsort(self.databuffer["x"])
                self.full_power_array = np.array(self.databuffer["y"])[sorted_indices]
        except (ValueError, IndexError) as e:
            print(f"Data parsing error: {e}")

    def stop(self):
        """Stop the subprocess."""
        with self.lock:  # Ensure thread safety
            print(f"Stop called. Process: {self.process}, Is running: {self.is_running}")
            if self.process is not None:
                if self.is_running:
                    try:
                        print("Attempting to terminate subprocess...")
                        self.process.terminate()
                        self.process.wait(timeout=5)  # Wait for process to terminate
                        print("Subprocess terminated.")
                    except subprocess.TimeoutExpired:
                        print("Termination timeout expired. Killing process...")
                        self.process.kill()
                        self.process.wait(timeout=5)  # Wait for process to be killed
                        print("Subprocess killed.")
                    except Exception as e:
                        print(f"Error stopping process: {e}")
                    finally:
                        self.process = None
                        self.is_running = False
                else:
                    print("Process is not running or has already been stopped.")
            else:
                print("No subprocess to stop.")
        
        self.is_running = False

    def get_data(self):
        """Return the full sweep data."""
        with self.lock:
            return np.copy(self.full_power_array)
    
    def get_number_of_points(self):
        """Return the number of data points."""
        with self.lock:
            return len(self.full_power_array)

    def is_sweep_complete(self):
        """Check if the sweep has completed."""
        return self.sweep_complete
