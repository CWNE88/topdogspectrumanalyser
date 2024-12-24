# Top Dog Spectrum Analyser
Python Spectrum Analyser using HackRF, RTL-SDR and audio

** PROJECT IS STILL EXTREMELY EXPERIMENTAL **

- Install hackrf and rtl

sudo apt install hackrf rtl-sdr


- Set up python virtual environment

python3 -m venv tdnsa


- Activate the environment

source tdnsa/bin/activate


- Install python pre-requisites

pip install \
numpy \
pyqtgraph \
pyqt6 \
scipy \
pyopengl \
pyrtlsdr \
matplotlib \
numpy-stl \
pyhackrf \
sounddevice \
pyfftw \
vispy



Once the python environment is active, start the program with python3 main.py

Currently the only working input is hackrf_sweep, which is default at start.

 


The aim is to provide data for a spectrum analyser, using the HackRF or RTL-SDR, and possibly others.

For the purpose of high speed, the spectrum data is obtained using hackrf_sweep for the HackRF, and rtl_power for the RTL-SDR. These programs provide power level data over a wide bandwidth.


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








