#!/bin/python3
import sys
import numpy as np
from PyQt6 import QtWidgets, QtCore
import pyqtgraph as pg

class TwoD(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        print("TwoD init")
        
        # Plot data
        self.frequency_bins = None
        self.live_power_levels = None
        
        self.max_hold_enabled = False
        self.max_power_levels = None
        
        self.min_hold_enabled = False
        self.min_power_levels = None
        
        self.average_enabled = False
        self.average_power_levels = None

        self.peak_search_enabled = False        
        self.peak_search_frequency = None
        self.peak_search_power = None
        self.peak_search_marker = None

        self.max_peak_search_enabled = False    # True if self.max_hold_enabled and self.peak_search_enabled are true
        self.max_peak_search_frequency = None
        self.max_peak_search_power = None
        self.max_peak_search_marker = None

        self.peak_search_label = None
        self.max_peak_search_label = None
                

        # Create the plot widget
        self.widget = pg.PlotWidget()
        self.widget.showGrid(x=True, y=True)
        self.widget.setLabel('left', 'Amplitude (dBm)')
        self.widget.setLabel('bottom', 'Frequency (MHz)')
        self.widget.setYRange(-100, -10)


        self.live_trace = self.widget.plot(pen='g', name='Current Power Levels')
        self.max_hold_trace = self.widget.plot(pen='y', name='Max Hold Levels')
        self.min_hold_trace = self.widget.plot(pen='b', name='Min Hold Levels')
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.widget)

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_plot)

    def update_frequency_bins(self, freq_bins):
        self.frequency_bins = freq_bins

    def update_live_power_levels(self, pwr_lvls):
        self.live_power_levels = pwr_lvls

    def set_max_hold_enabled(self, max_hold):
        self.max_hold_enabled = max_hold

    def update_max_power_levels(self, pwr_lvls):
        self.max_power_levels = pwr_lvls
    
    def set_min_hold_enabled(self, min_hold):
        self.min_hold_enabled = min_hold
    
    def update_min_hold_levels(self, pwr_lvls):
        self.min_hold_levels = pwr_lvls

    def set_average_enabled(self, av):
        self.average_enabled = av
    
    def update_average_power(self, pwr_lvls):
        self.average_power_levels = pwr_lvls

    def set_peak_search_enabled(self, pk_en):
        self.peak_search_enabled = pk_en

    def set_peak_search_frequency_and_power(self, pk, pwr):
        self.peak_search_frequency = pk
        self.peak_search_power = pwr

    def set_max_peak_search_enabled(self, max_pk_en):
        self.max_peak_search_enabled = max_pk_en

    def set_max_peak_search_frequency_and_power(self, pk, pwr):
        self.max_peak_search_frequency = pk
        self.max_peak_search_power = pwr

    def update_peak_search_marker(self):
        
        if self.peak_search_marker is None:
            self.peak_search_marker = pg.ScatterPlotItem(
                [self.peak_search_frequency / 1e6],  
                [self.peak_search_power],            
                symbol='t',
                brush='w',
                size=15
            )
            self.widget.addItem(self.peak_search_marker)
        else:
            self.peak_search_marker.setData(
                [self.peak_search_frequency / 1e6],  
                [self.peak_search_power]             
                )

    def update_max_peak_search_marker(self):
        if self.max_peak_search_marker is None:
            self.max_peak_search_marker = pg.ScatterPlotItem(
                [self.max_peak_search_frequency / 1e6],  
                [self.max_peak_search_power],            
                symbol='t',
                brush='w',
                size=15
            )
            self.widget.addItem(self.max_peak_search_marker)
        else:
            self.max_peak_search_marker.setData(
                [self.max_peak_search_frequency / 1e6],  
                [self.max_peak_search_power]             
                )

    def update_plot(self):
        if self.live_power_levels is not None and self.frequency_bins is not None:
            self.live_trace.setData(self.frequency_bins / 1e6, self.live_power_levels)
        else:
            self.live_trace.clear() 
            
        if self.max_hold_enabled and self.max_power_levels is not None:
            self.max_hold_trace.setData(self.frequency_bins / 1e6, self.max_power_levels)
        else:
            self.max_hold_trace.clear()
            if self.max_peak_search_label is not None:
                self.widget.removeItem(self.max_peak_search_label)
                self.max_peak_search_label = None

        if self.peak_search_enabled:

            peak_text = (
                f"<span style='color: green;background-color: black;'>Peak</span> <br>"
                f"<span style='color: white;background-color: black;'>{self.peak_search_frequency / 1e6:.2f} MHz</span><br>"
                f"<span style='color: white; background-color: black;'>{self.peak_search_power:.2f} dB</span><br>"
            )
            if self.peak_search_label is None:
                self.peak_search_label = pg.TextItem(peak_text)
                self.peak_search_label.setHtml(peak_text)
                self.widget.addItem(self.peak_search_label)
            else:
                self.peak_search_label.setHtml(peak_text)
            ymin, ymax = self.widget.viewRange()[1]  # Get the y-axis range
            y_90_percent = ymin + 0.9 * (ymax - ymin)
            self.peak_search_label.setPos(self.peak_search_frequency / 1e6, y_90_percent)
            
            self.update_peak_search_marker()

            if self.max_peak_search_enabled:
                
                max_peak_text = (
                    f"<span style='color: yellow;background-color: black;'>Max Peak</span> <br>"
                    f"<span style='color: white;background-color: black;'>{self.max_peak_search_frequency / 1e6:.2f} MHz</span><br>"
                    f"<span style='color: white; background-color: black;'>{self.max_peak_search_power:.2f} dB</span><br>"
                )
                if self.max_peak_search_label is None:
                    self.max_peak_search_label = pg.TextItem(max_peak_text)
                    self.max_peak_search_label.setHtml(max_peak_text)
                    self.widget.addItem(self.max_peak_search_label)
                else:
                    self.max_peak_search_label.setHtml(max_peak_text)
                ymin, ymax = self.widget.viewRange()[1]  # Get the y-axis range
                self.max_peak_search_label.setPos(self.max_peak_search_frequency / 1e6, ymin + (ymax - ymin))
                
                self.update_max_peak_search_marker()
            else:
                self.widget.removeItem(self.max_peak_search_label)
                self.max_peak_search_label = None
        
        
        else:
            if self.max_peak_search_label is not None:
                self.widget.removeItem(self.max_peak_search_label)
                self.max_peak_search_label = None
                self.widget.removeItem(self.max_peak_search_marker)
            

            else:
                if self.peak_search_label is not None:
                    self.widget.removeItem(self.peak_search_label)
                    self.peak_search_label = None
                    self.widget.removeItem(self.peak_search_marker)
                    self.peak_search_marker = None

