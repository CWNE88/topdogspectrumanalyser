#!/bin/python3
import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore
import pyqtgraph.opengl as gl
import pyqtgraph as pg

class ThreeD(QtWidgets.QWidget):  # Inherit from QWidget to make it usable as a widget in your main application
    timer: QtCore.QTimer = None

    def __init__(self):
        super().__init__()


        ######################## VARIABLES #########################

        self.number_of_bins = None
        self.number_of_lines = 20
        self.peak_power = None
        self.power_db = None
        self.peak_frequency = None
        self.centre_freq = None
        self.spans = None
        self.samplesize = 1024                                      # number of fft bins
        self.rbw = None
        self.averaging = None
        self.peak='off'                                             # peak marker sphere
        self.inputmode='default'                                    # input area
        self.linlog='lin'                                           # linear or logarithmic
        self.pause='disabled'                                       # pause display
        self.numberoflines = 200                                    # number of lines on screen
        self.hold='enabled'
        self.grid=0
        self.peak='enabled'



        # Create the GLViewWidget
        self.widget = gl.GLViewWidget()
        self.widget.opts['distance'] = 40
        self.widget.setWindowTitle('This is a GLViewWidget object within the pyqtgraph (top-level library) opengl (submodule)')
        self.widget.setGeometry(0, 110, 1920, 1080)

        # Create the background grids
        gx = gl.GLGridItem()
        gx.rotate(90, 0, 1, 0)
        gx.translate(-10, 0, 0)
        self.widget.addItem(gx)

        gy = gl.GLGridItem()
        gy.rotate(90, 1, 0, 0)
        gy.translate(0, -10, 0)
        self.widget.addItem(gy)

        gz = gl.GLGridItem()
        gz.translate(0, 0, -10)
        self.widget.addItem(gz)

        self.titletext = gl.GLTextItem()
        self.titletext.setData(pos=(0.0, -10.0, -8.0), color=(255, 255, 255, 255), text='Top Dog Spectrum Analyser')
        self.widget.addItem(self.titletext)

        self.legend_x_low = gl.GLTextItem()
        self.legend_x_low.setData(pos=(-10.0, 0.0, 0.0), color=(255, 255, 255, 255), text='-10 X')
        self.widget.addItem(self.legend_x_low)
        self.legend_x_high = gl.GLTextItem()
        self.legend_x_high.setData(pos=(10.0, 0.0, 0.0), color=(255, 255, 255, 255), text='+10 X')
        self.widget.addItem(self.legend_x_high)
        self.legend_y_low = gl.GLTextItem()
        self.legend_y_low.setData(pos=(0.0, -10.0, 0.0), color=(255, 255, 255, 255), text='-10 Y')
        self.widget.addItem(self.legend_y_low)
        self.legend_y_high = gl.GLTextItem()
        self.legend_y_high.setData(pos=(0.0, 10.0, 0.0), color=(255, 255, 255, 255), text='+10 Y')
        self.widget.addItem(self.legend_y_high)
        self.legend_z_low = gl.GLTextItem()
        self.legend_z_low.setData(pos=(0.0, 0.0, -10.0), color=(255, 255, 255, 255), text='-10 Z')
        self.widget.addItem(self.legend_z_low)
        self.legend_z_high = gl.GLTextItem()
        self.legend_z_high.setData(pos=(0.0, 0.0, 10.0), color=(255, 255, 255, 255), text='+10 Z')
        self.widget.addItem(self.legend_z_high)


        self.traces = {}  
                
        self.x = np.linspace(-10, 10, self.samplesize)              
        self.y = np.zeros([self.samplesize]) 
        self.z = np.zeros([self.samplesize])         

        print (self.x)            
        print (self.y)
        print (self.z)
        specanpts = np.vstack([self.x, self.y, self.z]).transpose() 
        
        self.traces[0] = gl.GLLinePlotItem(pos=specanpts, color=np.zeros([self.samplesize, 4]), antialias=True, mode='line_strip')     
        self.widget.addItem(self.traces[0])

        
    def start_animation(self):
        print("in threedimension.ThreeD.start_animation")
        self.animation()

    def stop_animation(self):
        print("in threedimension.ThreeD.stop_animation")
        if self.timer is not None:
            self.timer.stop()

    def get_widget(self):
        return self.widget

    def set_plotdata(self, name, points, color, width):
        self.traces[name].setData(pos=points, color=color, width=width)

    def update(self):
        print ("in threedimension.ThreeD.update")

        # Simple line
        #self.x = np.linspace(-10, 10, self.samplesize)
        #self.y = np.zeros(self.samplesize) 
        #self.z = np.zeros(self.samplesize) 

       
        # Line with random
        self.x = np.linspace(-10, 10, self.samplesize)
        self.y = np.zeros(self.samplesize) 
        #self.z = np.random.rand(self.samplesize)*10
        

        
        # Prepare the plot data
        print (np.shape(self.x))
        print (np.shape(self.y))
        print (np.shape(self.z))

        print (self.x)            
        print (self.y)
        print (self.z)
        

        specanpts = np.vstack([self.y, self.x, self.z]).transpose()
       
        self.set_plotdata(name=0, points=specanpts, color=[0,1,0,1], width=1)
    
        





    ### THIS METHOD NEVER GETS CALLED
    def animation(self):
        print("in threedimension.ThreeD.animation")
        if self.timer is None:
            self.timer = QtCore.QTimer()
            self.timer.setInterval(20)
            self.timer.timeout.connect(self.update)

        self.timer.start()

# Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)  # Only create QApplication if this is being run standalone
    v = ThreeD()
    v.animation()
    sys.exit(app.exec())
