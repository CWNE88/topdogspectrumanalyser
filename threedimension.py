#!/bin/python3
from pyqtgraph.Qt import QtCore, QtGui
from scipy import signal
import pyqtgraph.opengl as gl
import pyqtgraph as pg
import numpy as np
import sys
from numpy.fft import fft, ifft
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
        self.live_power_levels = None
        self.frequency_bins = None
        self.max_hold_levels = None

        self.widget.keyPressEvent = self.keyPressEvent
        self.widget.opts["distance"] = 28
        self.widget.opts["azimuth"] = 90
        self.widget.opts["fov"] = 70
        self.widget.opts["elevation"] = 28
        self.widget.opts["bgcolor"] = (0.0, 0.0, 0.0, 1.0)
        self.widget.opts["devicePixelRatio"] = 1
        self.widget.opts["center"] = QtGui.QVector3D(1.616751790046692, -0.9432722926139832, 0.0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.widget)

        self.paused = False
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update)

        self.peak_search_enabled = False
        self.peak_marker = None

        self.side_grid = gl.GLGridItem()
        self.side_grid.rotate(90, 0, 1, 0)
        self.side_grid.translate(-10, 0, 0)
        self.widget.addItem(self.side_grid)
        self.side_grid_translated = False



        self.back_grid = gl.GLGridItem()
        self.back_grid.rotate(90, 1, 0, 0)
        self.back_grid.translate(0, -10, 0)
        self.widget.addItem(self.back_grid)
        

        self.colourmap = pg.colormap.get('magma')

        self.bottom_grid = gl.GLGridItem()
        self.bottom_grid.translate(0, 0, -10)
        self.widget.addItem(self.bottom_grid)

        self.numberoflines = 100

        self.peak_text = gl.GLTextItem()
        self.peak_text.setData(pos=(5.0, 10.0, 10.0), color=(255, 255, 255, 255), text="Peak frequency")
        self.widget.addItem(self.peak_text)

        self.lineyvalues = np.linspace(10, -10, self.numberoflines)

        self.traces = dict()
        
        self.x = None
        self.y = None
        self.traces_initialised = False
        self.last_live_power_levels = None
        print ("3d init")

        #peakpoints = gl.MeshData.sphere(rows=10, cols=10)
        peakpoints = gl.MeshData.cylinder(rows=10, cols=20, radius = [0,1]) 
        #self.peak_search_marker = gl.GLMeshItem(meshdata=peakpoints, smooth=True, color=(1, 1, 1, 1), shader='balloon')
        self.peak_search_marker = gl.GLMeshItem(meshdata=peakpoints, smooth=True, color=(1, 1, 1, 1), shader='balloon')
        self.peak_search_marker.resetTransform()
        self.peak_search_marker.scale(0.1, 0.1, 0.1)
        self.peak_search_marker.translate(2, 0, 0)
        self.widget.addItem(self.peak_search_marker)

        self.engformat = mpl.ticker.EngFormatter(places=2) 

    def initialise_traces(self):
        
    
        print ("in initialise_traces")
        
        
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
        self.good_colours = np.empty((len(self.frequency_bins), 4))
        print ("self.traces_initialised = True")

    def start(self):
        if (sys.flags.interactive != 1) or not hasattr(QtCore, "PYQT_VERSION"):
            QtGui.QGuiApplication.instance().exec()

    def set_plotdata(self, name, points, color, width):
        self.traces[name].setData(pos=points, color=color, width=width)

    def set_number_of_points(self, number):
        self.number_of_points = number

    def set_maxholddata(self, points, width):
        self.maxtrace.setData(pos=points, color=[0.0, 1.0, 0.0, 0.3], width=width)

    def set_peak_search_enabled(self, pk_en):
        self.peak_search_enabled = pk_en

    def set_peak_search_frequency_and_power(self, pk, pwr):
        self.peak_search_frequency = pk
        self.peak_search_power = pwr


    def map_z_to_colour(self, z):
        z_min, z_max = np.min(self.z), np.max(self.z)
        normalised_z = (z - z_min) / (z_max - z_min)
        lut = self.colourmap.getLookupTable(0.0, 1.0, 4)
        idx = int(normalised_z * (len(lut) - 1))
        rgb_colour = lut[idx][:3]  # Retrieve RGB values
        rgba_colour = np.append(rgb_colour, 255)  # Add alpha channel (fully opaque)
        return rgba_colour

    def update(self) -> None:
        
        if self.frequency_bins is None or self.live_power_levels is None:
            return
        
        if np.array_equal(self.live_power_levels, self.last_live_power_levels):
            return
        
        self.last_live_power_levels = self.live_power_levels.copy()
        
        # Update traces
        for i in range(self.numberoflines - 1):
            trace = self.traces[self.numberoflines - i - 2]
            trace_pos = trace.pos
            trace_color = trace.color
            trace_pos[:, 1] = self.lineyvalues[self.numberoflines - i - 1]
            self.set_plotdata(name=self.numberoflines - i - 1, points=trace_pos, color=trace_color, width=1)
        
        # Update main trace
        self.y = np.full_like(self.frequency_bins, self.lineyvalues[0])
        #self.z = self.live_power_levels / 10
        clipped = np.clip(self.live_power_levels, -70, None)

        self.z = (clipped - (-100)) / 50 * 20 - 20

    
        
        for i in range(len(self.frequency_bins)):
            z = self.z[i]
            colour = self.map_z_to_colour(z)

            self.good_colours[i] = colour
        
        # Update main trace data
        specan_pts = np.vstack((self.x, self.y, self.z)).T
        #self.set_plotdata(name=0, points=specan_pts, color=np.pad(self.good_colours, ((0,0),(0,1)), mode='constant', constant_values=255), width=1)
        self.set_plotdata(name=0, points=specan_pts, color=self.good_colours, width=1)


        # Update peak search marker
        if self.peak_search_enabled:
            maxx_index = np.argmax(self.live_power_levels)
            self.peak_search_marker.resetTransform()
            self.peak_search_marker.scale(0.2, 0.2, 0.2)
            self.peak_search_marker.translate(self.x[maxx_index], 10, np.max(self.z))
            self.peak_text.setData(
                pos=(self.x[maxx_index], 10.0, 0.0),
                color=(255, 255, 255, 255),
                text=f"{self.engformat(self.peak_search_frequency)}Hz",
            )


    def set_peak_search_enabled(self, is_enabled):
        self.peak_search_enabled = is_enabled
        
    
    def set_peak_search_value(self, power, frequency):
        self.peak_search_power = power
        self.peak_search_frequency = frequency
    
    def update_live_power_levels(self, power_levels):
        self.live_power_levels = power_levels

    def update_frequency_bins(self, bins):
        self.frequency_bins = bins
        
    def update_widget_data(self, live_power_levels, max_hold_levels, frequency_bins, peak_search_enabled):
        if (
            live_power_levels is not None
            and max_hold_levels is not None
            and frequency_bins is not None
        ):
            self.live_power_levels = live_power_levels
            self.max_hold_levels = max_hold_levels
            self.frequency_bins = frequency_bins
            self.peak_search_enabled = peak_search_enabled
