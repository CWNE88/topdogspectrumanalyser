#!/bin/python3
from pyqtgraph.Qt import QtCore, QtGui
from scipy import signal
import pyqtgraph.opengl as gl
import pyqtgraph as pg
import numpy as np
import sys
from numpy.fft import fft, ifft
from rtlsdr import RtlSdr

import time
import matplotlib as mpl
from matplotlib.ticker import EngFormatter
#from libhackrf import *
from PyQt6 import QtWidgets
#from PyQt5.QtWidgets import *
#from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt6 import QtCore, QtGui, QtWidgets

import os
import matplotlib.pyplot as plt

class Visualizer():
    
    def get_samples(self, numberofsamples):
        samples=self.sdr.read_samples(numberofsamples)
        return samples
     
    def do_fft(self, samples):
        rawfft = np.fft.fft(samples*self.window)
        centred_fft = np.fft.fftshift(rawfft)     
        return centred_fft

    def __init__(self):
        
        ######################## VARIABLES #########################
        
        
        self.sdr = RtlSdr()                                         # device type RtlSdr() or HackRF()
        self.sdr.gain = 40                                          # gain value or 'auto'
        self.sdr.center_freq = 98e6                                 # tuned centre frequency
        self.sdr.sample_rate = 2e6                                  # bandwidth
        self.samplesize = 1024                                      # number of fft bins 
        self.window = signal.windows.flattop(self.samplesize)
        #self.window = np.kaiser (self.samplesize,14)                # create fft window
        self.rbw = self.sdr.sample_rate / self.samplesize           # resolution bandwidth
        self.bwperdiv = self.sdr.sample_rate / 10                   # bandwidth per division
        self.averaging = 20                                         # averaging amount (must be >= 1)
        self.engformat = mpl.ticker.EngFormatter(places=2)          # for displaying in engineering notation    
        self.peak='off'                                             # peak marker sphere
        self.inputmode='default'                                    # input area
        self.linlog='lin'                                           # linear or logarithmic
        self.pause='disabled'                                       # pause display
        self.numberoflines = 200                                    # number of lines on screen
        self.minimumspacebetweenpeaks = self.samplesize / 10        # makes a space one grid line before next peak
        self.hold='enabled'
        self.grid=0
        self.peak='enabled'
        
        self.delta1spot=0
        self.delta2spot=0
        
        
        ######################## GUI #########################
        
        self.app = QtWidgets.QApplication(sys.argv) # QtGui.QApplication(sys.argv)                                         # create a qt app 
        self.gldisplay = gl.GLViewWidget()                                              # create widget for 3d data 
        self.gldisplay.keyPressEvent = self.keyPressEvent        
        self.gldisplay.opts['distance'] = 28                                            
        self.gldisplay.opts['azimuth'] = 90
        self.gldisplay.opts['fov'] = 70
        self.gldisplay.opts['elevation'] = 28 #0
        self.gldisplay.opts['bgcolor'] = (0.0, 0.0, 0.0, 1.0)
        self.gldisplay.opts['devicePixelRatio'] = 1
        self.gldisplay.opts['center'] = QtGui.QVector3D(1.616751790046692, -0.9432722926139832, 0.0)
        #print (self.gldisplay.opts)
        self.gldisplay.show()               

        ########## GRAPHIC ELEMENTS ###############
        
        ######## COURSE GRID LINES #############
        
        
        self.hgridlines = dict()
        ypoints = np.linspace (0, 10, 11)
        for i in range (len(ypoints)):
            zlx = np.linspace(10, -10, self.samplesize)
            zly = np.full([self.samplesize], 10)
            zlz = np.full([self.samplesize], ypoints[i])
            thisline = np.vstack ([zlx, zly, zlz]).transpose()
            self.hgridlines[i] = gl.GLLinePlotItem (pos=thisline, antialias="False", mode='line_strip', width=2, color=[1, 1, 1, 1])
            #self.gldisplay.addItem(self.hgridlines[i])
        
        self.vgridlines = dict()
        xpoints = np.linspace (-10, 10, 11)
        for i in range (len(xpoints)):
            zlz = np.linspace(10, 0, self.samplesize)
            zly = np.full([self.samplesize], 10)
            zlx = np.full([self.samplesize], xpoints[i])
            zerolinepts = np.vstack ([zlx, zly, zlz]).transpose()
            self.vgridlines[i] = gl.GLLinePlotItem (pos=zerolinepts, antialias="False", mode='line_strip', width=2, color=[1, 1, 1, 1])
            #self.gldisplay.addItem(self.vgridlines[i])
            
            
        ######## FINE GRID LINES #############
        
        
        self.hfgridlines = dict()
        ypoints = np.linspace (0, 10, 101)
        for i in range (len(ypoints)):
            zlx = np.linspace(10, -10, self.samplesize)
            zly = np.full([self.samplesize], 10)
            zlz = np.full([self.samplesize], ypoints[i])
            thisline = np.vstack ([zlx, zly, zlz]).transpose()
            self.hfgridlines[i] = gl.GLLinePlotItem (pos=thisline, antialias="False", mode='line_strip', width=2, color=[0.5, 0.5, 0.5, 1])
            #self.gldisplay.addItem(self.hfgridlines[i])
        
        self.vfgridlines = dict()
        xpoints = np.linspace (-10, 10, 101)
        for i in range (len(xpoints)):
            zlz = np.linspace(10, 0, self.samplesize)
            zly = np.full([self.samplesize], 10)
            zlx = np.full([self.samplesize], xpoints[i])
            zerolinepts = np.vstack ([zlx, zly, zlz]).transpose()
            self.vfgridlines[i] = gl.GLLinePlotItem (pos=zerolinepts, antialias="False", mode='line_strip', width=2, color=[0.5, 0.5, 0.5, 1])
            #self.gldisplay.addItem(self.vfgridlines[i])
            
            
            

        ######### HISTORY LINES ###########
        
        self.lineyvalues = np.linspace(10, -10, self.numberoflines)  
        self.traces = dict()                                         
        self.x = np.linspace (10, -10, self.samplesize)              
        for i in range (self.numberoflines):                         
            self.y = np.full ([self.samplesize], self.lineyvalues[i]) 
            self.z = np.zeros ([self.samplesize])                     
            specanpts = np.vstack ([self.x, self.y, self.z]).transpose() 
            self.traces[i] = gl.GLLinePlotItem (pos=specanpts, color=np.zeros([self.samplesize,4]), antialias="True", mode='line_strip')     
            self.gldisplay.addItem (self.traces[i])                     
        
        ############# PEAK SPHERE ############
        
        peakpoints = gl.MeshData.sphere(rows=10, cols=10) 
        self.peaksphere = gl.GLMeshItem(meshdata=peakpoints, smooth=True, color=(1, 1, 1, 1), shader='balloon', glOptions='additive')
        self.peaksphere.resetTransform()
        self.peaksphere.scale(0.1, 0.1, 0.1)
        self.peaksphere.translate(2, 0, 0)
        self.gldisplay.addItem(self.peaksphere)
        
        ############ DELTA MARKERS ###########
        
        delta1points = gl.MeshData.sphere(rows=10, cols=10)
        self.delta1 = gl.GLMeshItem(meshdata=delta1points, smooth=True, color=(0.3, 0.3, 1, 1), shader='balloon', glOptions='additive')
        self.delta1.scale(0.1, 0.1, 0.1)
        self.delta1.translate(0, 10, 0)
        self.gldisplay.addItem(self.delta1)
        
        
        delta2points = gl.MeshData.sphere(rows=10, cols=10)
        self.delta2 = gl.GLMeshItem(meshdata=delta2points, smooth=True, color=(0.3, 1, 0.3, 1), shader='balloon', glOptions='additive')
        self.delta2.scale(0.1, 0.1, 0.1)
        self.delta2.translate(0, 10, 0)
        self.gldisplay.addItem(self.delta2)
        
        
        
                
        ############# MAX HOLD ############
        
        self.maxx=self.x                                                
        self.maxtrace = dict()
        self.peakx = np.linspace(10, -10, self.samplesize)
        self.peaky = np.full([self.samplesize], 10)
        self.peakz = self.z                  
        
        zerolinepts = np.vstack ([self.peakx, self.peaky, self.peakz]).transpose()
        self.maxtrace = gl.GLLinePlotItem (pos=zerolinepts, antialias="True", mode='line_strip', width=2, color=[1.0, 1.0, 0.0, 0.3])
        self.gldisplay.addItem(self.maxtrace)

        
    def start(self):
        if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
            QtGui.QGuiApplication.instance().exec()

    def set_plotdata(self, name, points, color, width):
        self.traces[name].setData(pos=points, color=color, width=width)
        
    def set_maxholddata(self, points, width):
        self.maxtrace.setData(pos=points, color=[0.0, 1.0, 0.0, 0.3], width=width)
        
        
        
        
        
    def update(self):
        if self.pause!=('enabled'):
            y = np.full([self.samplesize], self.lineyvalues[0])  
            for i in range (self.averaging):
                tempfft=self.do_fft(self.get_samples(self.samplesize))
                self.z = self.z + tempfft
            self.z = self.z / self.averaging
            
            for i in range (self.numberoflines-1):
                tempy=self.traces[self.numberoflines-i-2].pos               
                tempcolours=self.traces[self.numberoflines-i-2].color       
                tempy[:,1]=self.lineyvalues[self.numberoflines-i-1]         
                self.set_plotdata(name=self.numberoflines-i-1, points=tempy, color=tempcolours,  width=1)
            
            # This is the current line
            goodcolours = np.empty([self.samplesize,4])
            goodcolours[:,3] = 1
            
            self.z = abs(self.z)                    
            self.z = np.clip(self.z, 1e-12, None)   
            self.z = np.log10(self.z+1)             
            self.z = self.z*6                       


            ## Peak sphere
            maxvalue=np.max(self.z)
            maxxindex=np.where(self.z == np.amax(self.z))
            self.peaksphere.resetTransform()
            self.peaksphere.scale(0.2, 0.2, 0.2)
            self.peaksphere.translate(self.x[maxxindex], 10, np.max(self.z))
            
            ## delta 1
            
            
            
            
            #self.delta1.scale(0.1, 0.1, 0.1)
            #self.delta1.translate(0, 10, 0)
            #self.gldisplay.addItem(self.delta1)
        
        
        
            
                    
            for i in range (self.samplesize):
                goodcolours[i]=pg.glColor((8-self.z[i] ,  8*1.4))
            
            # plot live
            specanpts = np.vstack([self.x, y, self.z]).transpose()    
            self.set_plotdata(name=0, points=specanpts, color=goodcolours, width=5)
            
            
            
            ############# MAX HOLD ############
                  
            for i in range (self.samplesize):
                if self.peakz[i]<self.z[i]:
                    self.peakz[i]=self.z[i]
            
            maxholdpoints = np.vstack ([self.peakx, self.peaky, self.peakz]).transpose()
            self.set_maxholddata (points=maxholdpoints, width=3)            
            
         

            # display movement
            self.gldisplay.opts['azimuth'] = self.gldisplay.opts['azimuth'] +0.1
            #self.gldisplay.opts['fov'] = self.gldisplay.opts['fov']  +0.4
            #self.gldisplay.opts['elevation'] = self.gldisplay.opts['elevation'] +0.2
            
            
    
            

    def animation(self):
        timer = QtCore.QTimer()
        timer.timeout.connect(self.update)
        timer.start(10)
        self.start()
         
    
    
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Space:
            if self.pause=='enabled':
                self.pause='disabled'
                print ("Pause disabled")
            elif self.pause=='disabled':
                self.pause='enabled'
                print ("Pause enabled")
        
        if event.key() == QtCore.Qt.Key_1:
            self.sdr.center_freq = self.sdr.center_freq-100e6
            print ("Centre frequency: " + self.engformat(self.sdr.center_freq)+"Hz")
        
        if event.key() == QtCore.Qt.Key_2:
            self.sdr.center_freq = self.sdr.center_freq+100e6
            print ("Centre frequency: " + self.engformat(self.sdr.center_freq)+"Hz")
        
        if event.key() == QtCore.Qt.Key_3:
            self.sdr.center_freq = self.sdr.center_freq-10e6
            print ("Centre frequency: " + self.engformat(self.sdr.center_freq)+"Hz")
        
        if event.key() == QtCore.Qt.Key_4:
            self.sdr.center_freq = self.sdr.center_freq+10e6
            print ("Centre frequency: " + self.engformat(self.sdr.center_freq)+"Hz")
        
        if event.key() == QtCore.Qt.Key_5:
            self.sdr.center_freq = self.sdr.center_freq-1e6
            print ("Centre frequency: " + self.engformat(self.sdr.center_freq)+"Hz")
        
        if event.key() == QtCore.Qt.Key_6:
            self.sdr.center_freq = self.sdr.center_freq+1e6
            print ("Centre frequency: " + self.engformat(self.sdr.center_freq)+"Hz")
        
        if event.key() == QtCore.Qt.Key_7:
            self.sdr.center_freq = self.sdr.center_freq-100e3
            print ("Centre frequency: " + self.engformat(self.sdr.center_freq)+"Hz")
        
        if event.key() == QtCore.Qt.Key_8:
            self.sdr.center_freq = self.sdr.center_freq+100e3
            print ("Centre frequency: " + self.engformat(self.sdr.center_freq)+"Hz")


        if event.key() == QtCore.Qt.Key_Z:
            if self.delta1spot+0.2 < 10:
                self.delta1spot = self.delta1spot+0.2
            self.delta1.resetTransform()                             
            self.delta1.scale(0.1, 0.1, 0.1)
            self.delta1.translate(self.delta1spot, 10, 0)
            print ("Marker 1 Frequency: " + self.engformat(self.sdr.center_freq-self.delta1spot*50*self.rbw) + "Hz")
            print ("Delta marker frequencies: " + self.engformat((self.sdr.center_freq-self.delta2spot*50*self.rbw) - (self.sdr.center_freq-self.delta1spot*50*self.rbw)))
            
        if event.key() == QtCore.Qt.Key_X:
            if self.delta1spot-0.2 > -10:
                self.delta1spot = self.delta1spot-0.2
            self.delta1.resetTransform()                             
            self.delta1.scale(0.1, 0.1, 0.1)
            self.delta1.translate(self.delta1spot, 10, 0)
            print ("Marker 1 Frequency: " + self.engformat(self.sdr.center_freq-self.delta1spot*50*self.rbw) + "Hz")
            print ("Delta marker frequencies: " + self.engformat((self.sdr.center_freq-self.delta2spot*50*self.rbw) - (self.sdr.center_freq-self.delta1spot*50*self.rbw)))
            
        if event.key() == QtCore.Qt.Key_A:
            if self.delta2spot+0.2 < 10:
                self.delta2spot = self.delta2spot+0.2
            self.delta2.resetTransform()                             
            self.delta2.scale(0.1, 0.1, 0.1)
            self.delta2.translate(self.delta2spot, 10, 0)
            print ("Marker 2 Frequency: " + self.engformat(self.sdr.center_freq-self.delta2spot*50*self.rbw) + "Hz")
            print ("Delta marker frequencies: " + self.engformat((self.sdr.center_freq-self.delta2spot*50*self.rbw) - (self.sdr.center_freq-self.delta1spot*50*self.rbw)))
            
        if event.key() == QtCore.Qt.Key_S:
            if self.delta2spot-0.2 > -10:
                self.delta2spot = self.delta2spot-0.2
            self.delta2.resetTransform()                             
            self.delta2.scale(0.1, 0.1, 0.1)
            self.delta2.translate(self.delta2spot, 10, 0)
            print ("Marker 2 Frequency: " + self.engformat(self.sdr.center_freq-self.delta2spot*50*self.rbw) + "Hz")
            print ("Delta marker frequencies: " + self.engformat((self.sdr.center_freq-self.delta2spot*50*self.rbw) - (self.sdr.center_freq-self.delta1spot*50*self.rbw)))
            

        
        if event.key() == QtCore.Qt.Key_H:
            if self.hold=='enabled':
                self.hold='disabled'
                print ("Hold disabled")
                self.gldisplay.removeItem(self.maxtrace)
            elif self.hold=='disabled':
                self.hold='enabled'
                print ("Hold enabled")
                self.gldisplay.addItem(self.maxtrace)
                
                self.peakz = self.z
                maxholdpoints = np.vstack ([self.peakx, self.peaky, self.peakz]).transpose()
                self.set_maxholddata (points=maxholdpoints, width=3) 

        if event.key() == QtCore.Qt.Key_M:
            if self.peak=='enabled':
                self.peak='disabled'
                self.gldisplay.removeItem(self.peaksphere)
                print ("Marker disabled")
            elif self.peak=='disabled':
                self.peak='enabled'
                self.gldisplay.addItem(self.peaksphere)
                print ("Marker enabled")

        if event.key() == QtCore.Qt.Key_G:
            if self.grid==0:
                self.grid=1
                print ("Course grid enabled")
                for i in range (11):
                    self.gldisplay.addItem(self.hgridlines[i])
                    self.gldisplay.addItem(self.vgridlines[i])
                    
            elif self.grid==1:
                self.grid=2
                print ("Fine grid enabled")
                for i in range (11):
                    self.gldisplay.removeItem(self.hgridlines[i])
                    self.gldisplay.removeItem(self.vgridlines[i])
                for i in range (101):
                    self.gldisplay.addItem(self.hfgridlines[i])
                    self.gldisplay.addItem(self.vfgridlines[i])                    
                    
            elif self.grid==2:
                self.grid=3
                print ("Both grids enabled")
                for i in range (11):
                    self.gldisplay.addItem(self.hgridlines[i])
                    self.gldisplay.addItem(self.vgridlines[i])                   
                    
            elif self.grid==3:
                self.grid=0
                print ("Grid disabled")
                for i in range (11):
                    self.gldisplay.removeItem(self.hgridlines[i])
                    self.gldisplay.removeItem(self.vgridlines[i])
                for i in range (101):
                    self.gldisplay.removeItem(self.hfgridlines[i])
                    self.gldisplay.removeItem(self.vfgridlines[i])                    

        if event.key() == QtCore.Qt.Key_Left:
            self.gldisplay.opts['center'] =self.gldisplay.opts['center'] - QtGui.QVector3D(1,0,0)
        
        if event.key() == QtCore.Qt.Key_Right:
            self.gldisplay.opts['center'] =self.gldisplay.opts['center'] + QtGui.QVector3D(1,0,0)

# Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    v = Visualizer()
    v.animation()

