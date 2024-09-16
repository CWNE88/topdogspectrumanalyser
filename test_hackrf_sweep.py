# main.py

from backends.hackrf_sweep import HackRFSweep
import time

# Create an instance of HackRFSweep
sweep = HackRFSweep()

# Set up the sweep parameters
sweep.setup(start_freq=2400, stop_freq=2500, bin_size=5000)

# Start the sweep in a non-blocking way
sweep.run()

# Main loop to periodically check the status
while not sweep.is_sweep_complete():
    print("Sweep is running...")
    print(sweep.get_data())
    time.sleep(1)  # Adjust the sleep duration as needed

print("Sweep complete. Retrieving data...")
data = sweep.get_data()
print(f"Number of data points: {sweep.get_number_of_points()}")
print(f"Data: {data}")
