#!/bin/python3
import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore
import pyqtgraph.opengl as gl
import pyqtgraph as pg
from PyQt6 import QtWidgets, uic, QtCore
from pyqtgraph.Qt import QtCore, QtGui
from PyQt6.QtCore import Qt
import pyqtgraph.opengl as gl
from numpy.fft import fft
from logo import points  
import matplotlib as mpl
from matplotlib.ticker import EngFormatter

class TwoD(QtWidgets.QWidget):  # Inherit from QWidget to make it usable as a widget in your main application
    timer: QtCore.QTimer = None

    def __init__(self):
        super().__init__()

        # Create and configure 2D PlotWidget
        self.two_d_widget = pg.PlotWidget()
        self.two_d_widget.showGrid(x=True, y=True)
        self.two_d_widget.setLabel('left', 'Power (dB)')
        self.two_d_widget.setLabel('bottom', 'Frequency asdfasdf(Mhz)')
        self.two_d_widget.setYRange(-30, 60)
        self.two_d_widget.text_item = pg.TextItem("two d nigga")
        self.two_d_widget.text_item.setAnchor((1, 1))
        
        print ("test")
 

    def start_animation(self):
        print("in start_animation")
        self.animation()

    def stop_animation(self):
        print("in stop_animation")
        if self.timer is not None:
            self.timer.stop()

    def get_widget(self):
        return self.two_d_widget  # Return the plot widget so it can be used in the main application

    def set_plotdata(self, name, points, color, width):
        pass
    

    def update(self):
        pass
    

    def animation(self):
        print ("in animation")
        if self.timer is None:
            self.timer = QtCore.QTimer()
            self.timer.setInterval(20)
            self.timer.timeout.connect(self.update)

        self.timer.start()

# Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)  # Only create QApplication if this is being run standalone
    object = TwoD()
    object.animation()
    sys.exit(app.exec())
