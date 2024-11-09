#!/bin/python3
import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore
import pyqtgraph as pg

class TwoD(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        print ("TwoD init")
        self.setWindowTitle("Top Dog Spectrum Analyser")
        self.setGeometry(100, 500, 1500, 600)

        # Create the plot widget
        self.widget = pg.PlotWidget()
        self.power_levels = None
        self.frequency_bins = None
        self.max_hold_levels = None

        self.curve = self.widget.plot(pen='g', name='Current Power Levels')
        self.max_hold_curve = self.widget.plot(pen='y', alpha=0.5, name='Max Hold Levels')

        self.widget.setTitle("Spectrum Analyser")
        self.widget.setLabel('left', 'Amplitude (dBm)')
        self.widget.setLabel('bottom', 'Frequency (MHz)')
        self.widget.setYRange(-100, -10)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.widget)

        self.paused = False
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        #self.timer.start(20)

    def update_widget_data(self, power_levels, max_hold_levels, frequency_bins):
        if power_levels is not None and max_hold_levels is not None and frequency_bins is not None:
            self.power_levels = power_levels
            self.max_hold_levels = max_hold_levels
            self.frequency_bins = frequency_bins
            
    def update_plot(self):
        if self.power_levels is not None and self.frequency_bins is not None:
            self.curve.setData(self.frequency_bins / 1e6, self.power_levels)  
            self.max_hold_curve.setData(self.frequency_bins / 1e6, self.max_hold_levels)
