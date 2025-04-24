# Top Dog Spectrum Analyser
Python Spectrum Analyser using HackRF or RTL-SDR

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

The relevant backend can be chosen for the device required, and the method required.
The data is returned from the Sweep class to include the frequency range and power values.

Shortcut keys


A,Amplitude
D,Delta Markers
Down,Down
F,Frequency
F1,Soft Key 1
F2,Soft Key 2
F3,Soft Key 3
F4,Soft Key 4
F5,Soft Key 5
F6,Soft Key 6
F7,Soft Key 7
F8,Soft Key 8
G,GHz
H,Hz
K,kHz
M,MHz
N,Next Peak
O,Orientation
P,Peak Search
R,pReset
S,Span
Space,Hold
Up,Up
X,Max hold
Z,Zero span


Issues

Source selection

When frequency changes, the plots fail.
Possible solution is a flag to say frequency has changed, and to reset frequency bins at that time

Surface plot not yet integrated.

GUI buttons shading not right when selecting display.

Max hold in 2d plot has remnant of previous max hold when activated again.

Peak search for max hold not working.

Colour map option in waterfall not working.








