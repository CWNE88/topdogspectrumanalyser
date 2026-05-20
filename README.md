# Top Dog Spectrum Analyser
Python Spectrum Analyser using HackRF or RTL-SDR



![Screenshot1](https://github.com/CWNE88/topdogspectrumanalyser/blob/master/screenshot1.png)


![Screenshot2](https://github.com/CWNE88/topdogspectrumanalyser/blob/master/screenshot2.png)


![Screenshot2](https://github.com/CWNE88/topdogspectrumanalyser/blob/master/screenshot3.png)


![Screenshot2](https://github.com/CWNE88/topdogspectrumanalyser/blob/master/screenshot4.png)


![Screenshot2](https://github.com/CWNE88/topdogspectrumanalyser/blob/master/screenshot5.png)


** PROJECT IS STILL EXTREMELY EXPERIMENTAL **

Required installs
numpy pyqtgraph PyQt6 pyopengl pyrtlsdr 


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
