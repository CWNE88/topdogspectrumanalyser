#!/bin/python3
from pyqtgraph.Qt import QtCore, QtGui
from scipy import signal
import pyqtgraph.opengl as gl
import pyqtgraph as pg
import numpy as np
import sys
from numpy.fft import fft, ifft
from rtlsdr import RtlSdr
from pyqtgraph.Qt import mkQApp
import time
import matplotlib as mpl
from matplotlib.ticker import EngFormatter
from PyQt6 import QtWidgets
import os
import matplotlib.pyplot as plt

class ThreeD(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.widget = gl.GLViewWidget()
        self.power_levels = None
        self.frequency_bins = None
        self.max_hold_levels = None

        self.widget.keyPressEvent = self.keyPressEvent
        self.widget.opts["distance"] = 28
        self.widget.opts["azimuth"] = 90
        self.widget.opts["fov"] = 70
        self.widget.opts["elevation"] = 28
        self.widget.opts["bgcolor"] = (0.0, 0.0, 0.0, 1.0)
        self.widget.opts["devicePixelRatio"] = 1
        self.widget.opts["center"] = QtGui.QVector3D(
            1.616751790046692, -0.9432722926139832, 0.0
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.widget)

        self.paused = False
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)
        #self.timer.start(20)

        self.peak_search_enabled = False
        self.peak_marker = None

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

        self.numberoflines = 40

        centre_text = gl.GLTextItem()
        centre_text.setData(
            pos=(0.0, 10.0, 10.0), color=(255, 255, 255, 255), text="Centre frequency"
        )
        self.widget.addItem(centre_text)

        self.peak_text = gl.GLTextItem()
        self.peak_text.setData(
            pos=(5.0, 10.0, 10.0), color=(255, 255, 255, 255), text="Peak frequency"
        )
        self.widget.addItem(self.peak_text)

        self.lineyvalues = np.linspace(10, -10, self.numberoflines)

        self.traces = dict()
        self.x = None
        self.traces_initialised = False
        self.last_power_levels = None
        print ("3d init")


        peakpoints = gl.MeshData.sphere(rows=10, cols=10) 
        self.peaksphere = gl.GLMeshItem(meshdata=peakpoints, smooth=True, color=(1, 1, 1, 1), shader='balloon')
        self.peaksphere.resetTransform()
        self.peaksphere.scale(0.1, 0.1, 0.1)
        self.peaksphere.translate(2, 0, 0)
        self.widget.addItem(self.peaksphere)

    def initialise_traces(self):
        if self.traces_initialised or self.frequency_bins is None:
            return

        self.x = np.linspace(10, -10, len(self.frequency_bins))
        for i in range(self.numberoflines):
            y_val = self.lineyvalues[i]
            z_val = np.zeros_like(self.frequency_bins)
            specanpts = np.vstack([self.x, np.full_like(self.frequency_bins, y_val), z_val]).T
            self.traces[i] = gl.GLLinePlotItem(
                pos=specanpts,
                color=np.zeros([len(self.frequency_bins), 4]),
                antialias=True,
                mode="line_strip",
            )
            self.widget.addItem(self.traces[i])

        self.traces_initialised = True

    def start(self):
        if (sys.flags.interactive != 1) or not hasattr(QtCore, "PYQT_VERSION"):
            QtGui.QGuiApplication.instance().exec()

    def set_plotdata(self, name, points, color, width):
        self.traces[name].setData(pos=points, color=color, width=width)

    def set_maxholddata(self, points, width):
        self.maxtrace.setData(pos=points, color=[0.0, 1.0, 0.0, 0.3], width=width)

    def update(self):
        if self.frequency_bins is None or self.power_levels is None:
            return

        if np.array_equal(self.power_levels, self.last_power_levels):
            return

        self.last_power_levels = self.power_levels.copy()

        for i in range(self.numberoflines-1):
            trace = self.traces[self.numberoflines - i - 2]
            trace_pos = trace.pos
            trace_color = trace.color
            trace_pos[:, 1] = self.lineyvalues[self.numberoflines - i - 1]
            self.set_plotdata(name=self.numberoflines - i - 1, points=trace_pos, color=trace_color, width=1)

        y = np.full([len(self.frequency_bins)], self.lineyvalues[0])
        self.z = self.power_levels / 10

        goodcolours = np.empty([len(self.frequency_bins), 4])
        goodcolours[:, 3] = 1
        
        for i in range(len(self.frequency_bins)):
            goodcolours[i] = pg.glColor((8 - self.z[i], 8 * 1.4))

        specanpts = np.vstack([self.x, y, self.z]).T
        self.set_plotdata(name=0, points=specanpts, color=goodcolours, width=1)

        ###

        if self.peak_search_enabled:
            maxxindex=np.where(self.power_levels == np.amax(self.power_levels))
            self.peaksphere.resetTransform()
            self.peaksphere.scale(0.2, 0.2, 0.2)
            self.peaksphere.translate(self.x[maxxindex], 10, np.max(self.z))
            
            
            self.peak_text.setData(
            pos=(5.0, 10.0, 10.0), color=(255, 255, 255, 255), text="Peak frequency"
                 )


    



    def set_peak_search_enabled(self, is_enabled):
        self.peak_search_enabled = is_enabled
        print ("Peak search enabled is " + str(is_enabled))
    
    def set_peak_search_value(self, power, frequency):
        self.peak_search_power = power
        self.peak_search_frequency = frequency


    def update_widget_data(self, power_levels, max_hold_levels, frequency_bins, peak_search_enabled):
        if (
            power_levels is not None
            and max_hold_levels is not None
            and frequency_bins is not None
        ):
            self.power_levels = power_levels
            self.max_hold_levels = max_hold_levels
            self.frequency_bins = frequency_bins
            self.peak_search_enabled = peak_search_enabled

            self.y = np.zeros(len(self.frequency_bins))
            self.z = np.zeros(len(self.frequency_bins))
            self.initialise_traces()
 