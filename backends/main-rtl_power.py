import rtl_power
import time

def main():
    # Prompt user for input
    start_freq = float(input("Enter the start frequency (MHz): "))
    stop_freq = float(input("Enter the stop frequency (MHz): "))
    bin_size = int(input("Enter the bin size (Hz): "))

    # Create a Sweep instance
    sweeper = rtl_power.Sweep()

    # Set up the sweeper with user-provided parameters
    sweeper.setup(start_freq=start_freq, stop_freq=stop_freq, bin_size=bin_size)

    # Start the sweeper
    sweeper.start()
    
    # Allow the sweeper to run for a short duration (e.g., 3 seconds)
    time.sleep(10)
    
    # Stop the sweeper
    sweeper.stop()

    # Optionally, print or process the data
#    data = sweeper.get_data()
#    print("Sweep data:", data)

if __name__ == "__main__":
    main()
