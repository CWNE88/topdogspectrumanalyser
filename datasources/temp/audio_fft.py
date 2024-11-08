#!/bin/python3
from pyqtgraph.Qt import QtCore, QtGui
from scipy import signal
import pyqtgraph.opengl as gl
import numpy as np
import sys
import sounddevice as sd
from PyQt6 import QtWidgets  # Ensure this import is present
#from . import DataSource

class AudioDataSource():

#class AudioDataSource(DataSource):

    
    def __init__(self, sample_rate=44100, samplesize=16384):
        self.sample_rate = sample_rate
        self.samplesize = samplesize
        self.window = signal.windows.flattop(self.samplesize)  # Create FFT window
        self.samples = np.zeros(samplesize)  # Buffer for audio samples
        
        ######################## GUI #########################
        self.app = QtWidgets.QApplication(sys.argv)  # Create a Qt app 
        self.gldisplay = gl.GLViewWidget()               # Create widget for 3D data 
        self.gldisplay.opts['distance'] = 28                                            
        self.gldisplay.opts['azimuth'] = 0 
        self.gldisplay.opts['elevation'] = 0 
        self.gldisplay.opts['fov'] = 70
        self.gldisplay.opts['bgcolor'] = (0.0, 0.0, 0.0, 1.0)
        self.gldisplay.opts['devicePixelRatio'] = 1
        self.gldisplay.opts['center'] = QtGui.QVector3D(0.0, 0.0, 0.0)

        self.peak_text = gl.GLTextItem()
        self.peak_text.setData(pos=(0.0, 10.0, 10.0), color=(255, 255, 255, 255), text='Peak frequency')
        self.gldisplay.addItem(self.peak_text)


        self.gldisplay.show()               

        ########## GRAPHIC ELEMENTS ###############
        self.titletext = gl.GLTextItem()
        self.titletext.setData(pos=(0.0, -10.0, -8.0), color=(255, 255, 255, 255), text='Microphone Spectrum Analyser')
        self.gldisplay.addItem(self.titletext)

        # Create logarithmic x-axis values
        freq_bins = np.fft.rfftfreq(self.samplesize, 1/self.sample_rate)  # Get real FFT frequencies
        #self.x = np.zeros([len(freq_bins)]) 
        print (len(freq_bins))
        

        #freq_bins = np.linspace(0, 8193, num=8193)  # Example freq_bins

        # Normalise freq_bins to [0, 1]
        normalised_bins = freq_bins / 8193

        # Scale to desired range [-10, 10]
#        self.x = normalised_bins * 20 - 10  # Scale to [-10, 10]

        normalised_bins = freq_bins / 8193


        log_array = np.logspace(0, 1.301, 8193)  # 1.301 is log10(20)
        shifted_array = log_array - 10
        final_array = np.clip(shifted_array, -10, 10)

        self.x = final_array

        #self.x = np.log10(freq_bins + 1)  # Logarithmic scaling
        print (np.shape(self.x))
        print (self.x)
        self.y = np.zeros([len(self.x)])  # Ensure y matches x
        self.z = np.zeros([len(self.x)])  # Ensure z matches x
        
        specanpts = np.vstack([self.x, self.y, self.z]).transpose() 
        
        self.trace = gl.GLLinePlotItem(pos=specanpts, color=(0, 1, 0, 1), antialias=True, mode='line_strip')     
        self.gldisplay.addItem(self.trace)

        self.stream = sd.InputStream(samplerate=self.sample_rate, channels=1, callback=self.audio_callback)
        self.stream.start()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(20)

    def start(self):
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QGuiApplication.instance().exec()

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.samples = indata[:, 0]  # Store the audio samples
        

    def do_fft(self, samples):
        # Ensure samples match window size
        if len(samples) < self.samplesize:
            samples = np.pad(samples, (0, self.samplesize - len(samples)), 'constant')
        elif len(samples) > self.samplesize:
            samples = samples[:self.samplesize]
            
        rawfft = np.fft.fft(samples * self.window)
        centred_fft = np.fft.fftshift(rawfft)     
        return centred_fft

    def update(self):
        # Perform FFT
        tempfft = self.do_fft(self.samples)
        
        # Calculate magnitude and power
        power = np.abs(tempfft[:self.samplesize // 2 + 1])  # Take the positive frequencies including Nyquist
        power = np.clip(power, 1e-12, None)  # Avoid log(0)
        power = np.log10(power + 1) * 10  # Apply logarithm and scale by 10
        power = np.clip(power, 0, 20)
        
        # Prepare the plot data
        self.z = power*20  # Power on the z-axis
        specanpts = np.vstack([self.x, self.y, self.z]).transpose()
        
        self.trace.setData(pos=specanpts)

    def animation(self):
        self.start()

# Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    v = AudioDataSource()
    v.animation()
