#!/bin/python3
import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore
import pyqtgraph.opengl as gl
import pyqtgraph as pg
import matplotlib.pyplot as plt


class ThreeD(QtWidgets.QWidget):  # Inherit from QWidget to make it usable as a widget in your main application
    timer: QtCore.QTimer = None

    def __init__(self, number_of_points, number_of_lines):
        super().__init__()

        self.number_of_points = number_of_points
        self.number_of_lines = number_of_lines

        self.peak_power = None
        self.power_db = None
        self.peak_frequency = None
        self.centre_freq = None
        self.spans = None
        
        self.rbw = None
        self.averaging = None
        self.peak='off'                                             # peak marker sphere
        self.inputmode='default'                                    # input area
        self.linlog='lin'                                           # linear or logarithmic
        self.pause='disabled'                                       # pause display
        
        self.hold='enabled'
        self.grid=0
        self.peak='enabled'

        # Create the GLViewWidget
        self.widget = gl.GLViewWidget()
        

        self.widget.opts['distance'] = 40
        self.widget.setGeometry(0, 110, 1920, 1080)


        self.traces = {}
        for i in range(number_of_lines):
            self.x = np.linspace(-10, 10, self.number_of_points)
            self.y = np.full(self.number_of_points, 10)
            self.z = np.zeros([self.number_of_points])
            specanpts = np.vstack([self.x, self.y, self.z]).transpose()
            self.traces[i] = gl.GLLinePlotItem(pos=specanpts, color=np.zeros([self.number_of_points, 4]), antialias=False, mode='line_strip')
            self.widget.addItem(self.traces[i])

        def set_up_grids():


            # Create the background grids
            grid_x = gl.GLGridItem()
            grid_x.rotate(90, 0, 1, 0)
            grid_x.translate(-10, 0, 0)
            self.widget.addItem(grid_x)

            grid_y = gl.GLGridItem()
            grid_y.rotate(90, 1, 0, 0)
            grid_y.translate(0, 10, 0)
            self.widget.addItem(grid_y)

            grid_z = gl.GLGridItem()
            grid_z.translate(0, 0, -10)
            self.widget.addItem(grid_z)

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

        set_up_grids()


        ######### HISTORY LINES ###########
        
        self.lineyvalues = np.linspace(10, -10, self.number_of_lines)  
        self.traces = dict()                                         
        self.x = np.linspace (10, -10, self.number_of_points)              
        for i in range (self.number_of_lines):                         
            self.y = np.full ([self.number_of_points], self.lineyvalues[i]) 
            self.z = np.zeros ([self.number_of_points])                     
            specanpts = np.vstack ([self.x, self.y, self.z]).transpose() 
            self.traces[i] = gl.GLLinePlotItem (pos=specanpts, color=[0,1,0,1], antialias=False, mode='line_strip')     
            self.widget.addItem (self.traces[i])
              




        
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

        goodcolours = np.empty([self.number_of_points,4])
        goodcolours[:,3] = 1
        


        # Move previous lines along
        for i in range (self.number_of_lines-1):
            oldlinepoints=self.traces[i+1].pos      # get points of previous line
            oldlinecolours=self.traces[i+1].color   # get colours of previous line
            oldlinepoints[:,1]=self.lineyvalues[i]  # set y value of previous line to increment
            self.set_plotdata(name=i, points=oldlinepoints, color=oldlinecolours, width=1)  # plot previous line

        #cmap = plt.get_cmap('hot')
        cmap = plt.get_cmap('jet')
        #cmap = plt.get_cmap('gist_gray')
        

        # Current line  
        for i in range (self.number_of_points):
            
            normed_value = self.z[i] / 5
            goodcolours[i, :3] = cmap(normed_value)[:3] 
            goodcolours[i, 3] = 0.1
            #print (np.shape(self.z))

            
            #self.z=self.z * gain
 
        specanpts = np.vstack([self.x, self.y, self.z]).transpose()
        self.set_plotdata(name=self.number_of_lines-1, points=specanpts, color=goodcolours, width=1)

        self.widget.opts['azimuth'] = self.widget.opts['azimuth'] +0.1

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
