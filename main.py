# main.py

from backends.hackrf_sweep import HackRFSweep
from backends.rtl_power import RTLPowerSweep
from rtlsdr import RtlSdr
from libhackrf import *

import numpy as np
from numpy.fft import fft, ifft
import time


def get_samples(numberofsamples):
    samples=sdr.read_samples(numberofsamples)
    return samples

def do_fft(samples):
    X = fft(samples)
    X=(np.fft.fftshift(X))
    d=np.abs(X)/30
    return d


# Create an instance of HackRFSweep
hackrfsweep = HackRFSweep()
hackrfsweep.setup(start_freq=2400, stop_freq=2500, bin_size=5000)


print ()
print ("#####################")
print ("STARTING HACKRF SWEEP")
print ("#####################")
print ()

# Start the sweep in a non-blocking way
hackrfsweep.run()


for _ in range(5):
    print("Number of data points is ", str(hackrfsweep.get_number_of_points()))
    print(hackrfsweep.get_data())
    print()
    time.sleep(1)  # Adjust the sleep duration as needed

hackrfsweep.stop()

print ()
print ("##################")
print ("STARTING RTL SWEEP")
print ("##################")
print ()

# Starting RTL power sweep

rtl_power = RTLPowerSweep()
rtl_power.start_freq=88
rtl_power.stop_freq=108
rtl_power.run()

for _ in range(5):
    print("Number of data points is ", str(rtl_power.get_number_of_points()))
    print(rtl_power.get_data())
    print()
    time.sleep(1)  
rtl_power.stop()



# Starting HackRF sampling/fft

sdr = HackRF()
sdr.sample_rate = 2e6   #2097152                   
sdr.center_freq = 98e6
sdr.lna_gain=10
sdr.vga_gain=10
samplesize = 2048

print ()
print ("#############################")
print ("STARTING HACKRF sampling/FFT")
print ("#############################")
print ()

for _ in range(5):
    samples=get_samples(samplesize)
    fftvalues=do_fft(samples)
    print ("FFT values are", str(fftvalues))
    time.sleep(1)  


# Starting RTL sampling/fft

sdr = RtlSdr()
sdr.sample_rate = 2097152                   # sample rate
sdr.center_freq = 96e6     
sdr.gain='auto'  
samplesize = 2048

print ()
print ("#############################")
print ("STARTING RTL-SDR sampling/FFT")
print ("#############################")
print ()

for _ in range(5):
    samples=get_samples(samplesize)
    fftvalues=do_fft(samples)
    print ("FFT values are", str(fftvalues))
    time.sleep(1)  
