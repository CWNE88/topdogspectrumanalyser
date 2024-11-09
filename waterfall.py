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

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.widget)

        self.power_levels = None
        self.max_hold_levels = None
        self.frequency_bins = None
        self.waterfall_array = None 
        self.initialised = False
        self.history_amount = 200
        self.min_level = -80
        self.max_level = -60

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_plot)
        #self.timer.start(20)
        self.colourmap = pg.colormap.get('magma')


    def update_widget_data(self, power_levels, max_hold_levels, frequency_bins):
        
        if power_levels is not None and max_hold_levels is not None and frequency_bins is not None:
            self.power_levels = power_levels
            self.max_hold_levels = max_hold_levels
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

    def update_plot(self):
        if self.power_levels is None or self.frequency_bins is None:
            print("Power levels or frequency bins are None\n")
            return

        if self.waterfall_array is None:
            print("Waterfall not initialised.\n")
            return

        self.waterfall_array[:-1] = self.waterfall_array[1:]    # Shift old data up
        self.waterfall_array[-1] = self.power_levels            # Insert new data at the bottom
        lut = self.colourmap.getLookupTable(0.0, 1.0, 256)
        self.image_item.setImage(self.waterfall_array.T, autoLevels=False, levels=(self.min_level, self.max_level), lut=lut)
        

        