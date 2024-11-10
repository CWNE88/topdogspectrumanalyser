#!/bin/python3
import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore
import pyqtgraph as pg

class TwoD(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        print("TwoD init")
        
        self.setGeometry(100, 500, 1500, 600)

        # Create the plot widget
        self.widget = pg.PlotWidget()
        self.power_levels = None
        self.frequency_bins = None
        self.max_hold_levels = None
        self.min_hold_levels = None

        self.peak_search_frequency = None
        self.peak_search_power = None

        self.max_hold_enabled = False
        self.min_hold_enabled = False
        self.peak_search_enabled = False
        self.peak_marker = None

        self.curve = self.widget.plot(pen='g', name='Current Power Levels')
        self.max_hold_curve = self.widget.plot(pen='y', alpha=0.5, name='Max Hold Levels')
        self.min_hold_curve = self.widget.plot(pen='b', alpha=0.5, name='Min Hold Levels') 


        
        self.widget.setLabel('left', 'Amplitude (dBm)')
        self.widget.setLabel('bottom', 'Frequency (MHz)')
        self.widget.setYRange(-100, -10)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.widget)

        self.paused = False
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_plot)

        self.peak_search_label = None   

    def update_widget_data(self, power_levels, max_hold_levels, min_hold_levels, frequency_bins, peak_search_enabled):
        if power_levels is not None and max_hold_levels is not None and frequency_bins is not None:
            self.power_levels = power_levels
            self.max_hold_levels = max_hold_levels
            self.min_hold_levels = min_hold_levels
            self.frequency_bins = frequency_bins
            self.peak_search_enabled = peak_search_enabled

    def set_max_hold_enabled(self, max_hold_enabled):
        self.max_hold_enabled = max_hold_enabled

    def set_min_hold_enabled(self, min_hold_enabled):
        self.min_hold_enabled = min_hold_enabled


    def set_peak_search_enabled(self, peak_search_enabled, peak_search_frequency, peak_search_power):
        self.peak_search_enabled = peak_search_enabled
        self.peak_search_frequency = peak_search_frequency
        self.peak_search_power = peak_search_power
        
        if self.peak_search_enabled:
            self.update_peak_marker()
        else:
            if self.peak_marker is not None:
                self.widget.removeItem(self.peak_marker)
                self.peak_marker = None

    def update_peak_marker(self):
        if self.peak_marker is None:
            self.peak_marker = pg.ScatterPlotItem(
                [self.peak_search_frequency / 1e6],  # x-coordinate in MHz
                [self.peak_search_power],            # y-coordinate in dB
                symbol='o',                          # Use circle symbol
                brush='w',                           
                size=10                              # Marker size
            )
            self.widget.addItem(self.peak_marker)
        else:
            
            self.peak_marker.setData(
                [self.peak_search_frequency / 1e6],  # x-coordinate in MHz
                [self.peak_search_power]             # y-coordinate in dB
            )

    def update_plot(self):
        if self.power_levels is not None and self.frequency_bins is not None:
            self.curve.setData(self.frequency_bins / 1e6, self.power_levels)  
            if self.max_hold_enabled:
                self.max_hold_curve.setData(self.frequency_bins / 1e6, self.max_hold_levels)
            else:
                self.max_hold_curve.clear()

            if self.max_hold_enabled and self.min_hold_enabled:  # Only plot min hold if max hold is enabled
                self.min_hold_curve.setData(self.frequency_bins / 1e6, self.min_hold_levels)
            else:
                self.min_hold_curve.clear()
            
            if self.peak_search_enabled:
                peak_search_text = (
                    f"<span style='color: green;background-color: black;'>Peak</span> <br>"
                    f"<span style='color: white;background-color: black;'>{self.peak_search_frequency/1e6:.2f} MHz</span><br>"
                    f"<span style='color: white; background-color: black;'>{self.peak_search_power:.2f} dB</span><br>"
                )

                if self.peak_search_label is None:
                    self.peak_search_label = pg.TextItem(peak_search_text)
                    self.peak_search_label.setHtml(peak_search_text)
                    self.widget.addItem(self.peak_search_label)

                self.peak_search_label.setHtml(peak_search_text)
                self.peak_search_label.setPos(self.peak_search_frequency / 1e6, self.widget.viewRange()[1][1])
            else:
                if self.peak_search_label is not None:
                    self.widget.removeItem(self.peak_search_label)
                    self.peak_search_label = None
