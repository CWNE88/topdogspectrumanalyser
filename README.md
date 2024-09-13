# spectrumanalyser
Python Spectrum Analyser using HackRF or RTL-SDR

** PROJECT IS STILL EXTREMELY EXPERIMENTAL **

The aim is to provide data for a spectrum analyser, using the HackRF or RTL-SDR, and possibly others.

For the purpose of high speed, the spectrum data is obtained using hackrf_sweep for the HackRF, and rtl_power for the RTL-SDR. These programs provide power level data over a wide bandwidth.

The other more common method to get frequency data is to get samples from the device and perform FFT calculations. This method is much slower and CPU intensive.

There are advantages and disadvantages to each method.

Sweep Method:

Advantages:
- Very fast
- Wide bandwidth
- Low CPU usage

Disadvantages:

- Parts of the sweep may not complete before signal is gone, leaving gaps in the output

Sample Method:

Advantages:
- Very precise
- Shows all frequencies at given sample time

Disadvantages:

- High CPU usage
- Slower
- Limited to device bandwidth (20MHz for HackRF, 2MHz for RTL-SDR)

The relevant backend can be chosen for the device required, and the method required.
The data is returned from the Sweep class to include the frequency range and power values.



