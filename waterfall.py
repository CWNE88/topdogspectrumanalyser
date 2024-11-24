import numpy as np
import pyqtgraph as pg
from PyQt6 import QtCore, QtWidgets

class Waterfall(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.widget = pg.GraphicsLayoutWidget(self)
        self.plot_item = self.widget.addPlot()


        self.image_item = pg.ImageItem()
        self.plot_item.addItem(self.image_item)
        self.plot_item.setLabel('left', 'History (Frames)')
        self.plot_item.setLabel('bottom', 'Frequency (MHz)')





        self.histogram_layout = pg.GraphicsLayoutWidget(self)
        self.histogram = pg.HistogramLUTItem()
        self.histogram_layout.addItem(self.histogram)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.widget)
        layout.addWidget(self.histogram_layout)

        layout.setStretch(0, 6)
        layout.setStretch(1, 1)
        

        self.live_power_levels = None
        self.frequency_bins = None
        self.waterfall_array = None
        self.initialised = False
        self.history_amount = 900
        self.min_level = -80
        self.max_level = -60

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_plot)

        self.colourmap = pg.colormap.get('magma')
        self.histogram.gradient.loadPreset("magma")

        # Set manual levels for the histogram (fixed range)
        self.histogram.setHistogramRange(self.min_level, self.max_level)
        self.histogram.setLevels(self.min_level, self.max_level)






    def update_frequency_bins(self, freq_bins):
        self.frequency_bins = freq_bins
        self.initialise_waterfall()

    def update_live_power_levels(self, pwr_lvls):
        self.live_power_levels = pwr_lvls

    def update_widget_data(self, power_levels, frequency_bins):
        if power_levels is not None and frequency_bins is not None:
            self.live_power_levels = power_levels
            self.frequency_bins = frequency_bins

            if not self.initialised:
                self.initialise_waterfall()
        else:
            print("Received 'None' data in one or more variables\n")

    def initialise_waterfall(self):
        if self.frequency_bins is None:
            print("frequency_bins is None!")
            return

        print("Initialising waterfall\n")
        self.waterfall_array = np.zeros((self.history_amount, len(self.frequency_bins)))
        self.initialised = True
        self.histogram.setImageItem(self.image_item)

    def update_plot(self):
        if self.live_power_levels is None or self.frequency_bins is None:
            print("Power levels or frequency bins are None\n")
            return

        if self.waterfall_array is None:
            print("Waterfall not initialised.\n")
            return

        self.waterfall_array = np.roll(self.waterfall_array, -1, axis=0)
        self.waterfall_array[-1] = self.live_power_levels

        lut = self.colourmap.getLookupTable(0.0, 1.0, 256)
        #self.image_item.setImage(self.waterfall_array.T, autoLevels=False, levels=(self.min_level, self.max_level), lut=lut)
        self.image_item.setImage(self.waterfall_array.T, autoLevels=False, lut=lut)


