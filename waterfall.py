import numpy as np
import pyqtgraph as pg
from PyQt6 import QtCore, QtWidgets
import logging

# Configure logging to match other widgets
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class Waterfall(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        logging.debug("Waterfall: Initialising widget")

        self.widget = pg.GraphicsLayoutWidget(self, show=True)
        self.plot_item = self.widget.addPlot()

        self.image_item = pg.ImageItem()
        self.plot_item.addItem(self.image_item)
        logging.debug("Waterfall: ImageItem added to plot")
        self.plot_item.setLabel('left', 'History (Frames)')
        self.plot_item.setLabel('bottom', 'Frequency (MHz)')

        self.histogram_layout = pg.GraphicsLayoutWidget(self, show=True)
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
        self.history_amount = 1000
        self.min_level = -80  # Default, will be updated dynamically
        self.max_level = -40

        self.colourmap = pg.colormap.get('magma')
        self.histogram.gradient.loadPreset("magma")

        # Set initial histogram levels
        self.histogram.setHistogramRange(self.min_level, self.max_level)
        self.histogram.setLevels(self.min_level, self.max_level)

        # Set a dummy image to prevent NoneType errors in setRect
        dummy_image = np.zeros((self.history_amount, 1))  # Temporary 1-column image
        self.image_item.setImage(dummy_image, autoLevels=False, levels=(self.min_level, self.max_level))
        logging.debug("Waterfall: Set dummy image to prevent setRect errors")

        logging.debug("Waterfall: Widget initialised")

    def update_frequency_bins(self, freq_bins):
        """Update frequency bins and configure axis scaling."""
        logging.debug(f"Waterfall: Entering update_frequency_bins, freq_bins shape={freq_bins.shape if freq_bins is not None else None}")
        self.frequency_bins = freq_bins
        self.initialised = False  # Force reinitialization when frequency bins change
        if self.frequency_bins is not None and len(self.frequency_bins) > 0:
            try:
                # Convert Hz to MHz
                if not np.all(np.isfinite(self.frequency_bins)):
                    logging.error("Waterfall: frequency_bins contains non-finite values")
                    return
                min_freq = float(self.frequency_bins[0]) * 1e-6  # Convert Hz to MHz
                max_freq = float(self.frequency_bins[-1]) * 1e-6
                logging.debug(f"Waterfall: Calculated min_freq={min_freq}, max_freq={max_freq}")
                
                # Debug the parameters before calling setRect
                width = max_freq - min_freq
                height = self.history_amount
                logging.debug(f"Waterfall: Setting image rect with x={min_freq}, y=0, width={width}, height={height}")
                
                # Ensure all parameters are valid numbers
                if not all(isinstance(x, (int, float)) for x in [min_freq, width, height]):
                    logging.error(f"Waterfall: Invalid parameters for setRect: min_freq={min_freq}, width={width}, height={height}")
                    # Fallback to a default range
                    min_freq = 0.0
                    max_freq = 100.0
                    width = max_freq - min_freq
                    height = 1000
                    logging.debug(f"Waterfall: Fallback parameters: min_freq={min_freq}, max_freq={max_freq}, width={width}, height={height}")

                self.image_item.setRect(min_freq, 0, width, height)
                self.plot_item.setXRange(min_freq, max_freq)
                logging.debug(f"Waterfall: Updated frequency bins, range {min_freq:.2f}-{max_freq:.2f} MHz")
            except Exception as e:
                logging.error(f"Waterfall: Error in frequency bin calculation: {str(e)}")
                # Fallback to a default range
                min_freq = 0.0
                max_freq = 100.0
                width = max_freq - min_freq
                height = 1000
                self.image_item.setRect(min_freq, 0, width, height)
                self.plot_item.setXRange(min_freq, max_freq)
                logging.debug(f"Waterfall: Fallback frequency bins, range {min_freq:.2f}-{max_freq:.2f} MHz")
        else:
            logging.warning("Waterfall: Frequency bins are None or empty")
            # Fallback to a default range
            min_freq = 0.0
            max_freq = 100.0
            width = max_freq - min_freq
            height = 1000
            self.image_item.setRect(min_freq, 0, width, height)
            self.plot_item.setXRange(min_freq, max_freq)
            logging.debug(f"Waterfall: Fallback frequency bins, range {min_freq:.2f}-{max_freq:.2f} MHz")

    def update_widget_data(self, live_power_levels, max_power_levels, frequency_bins):
        """Update widget data and refresh the waterfall plot."""
        logging.debug(f"Waterfall: Entering update_widget_data, live_power_levels shape={live_power_levels.shape if live_power_levels is not None else None}, frequency_bins shape={frequency_bins.shape if frequency_bins is not None else None}")
        if live_power_levels is None or frequency_bins is None:
            logging.warning("Waterfall: Received 'None' data in one or more variables")
            return

        self.live_power_levels = live_power_levels
        if self.frequency_bins is None or len(self.frequency_bins) != len(frequency_bins):
            logging.debug("Waterfall: Frequency bins changed, updating")
            self.update_frequency_bins(frequency_bins)

        if not self.initialised:
            logging.debug("Waterfall: Not initialised, calling initialise_waterfall")
            self.initialise_waterfall()
            if not self.initialised:
                logging.warning("Waterfall: Initialisation failed")
                return

        # Calculate dynamic min and max levels based on data
        if np.all(np.isfinite(self.live_power_levels)):
            data_min = float(np.min(self.live_power_levels))
            data_max = float(np.max(self.live_power_levels))
            self.min_level = data_min
            self.max_level = data_max if data_max > data_min else data_min + 1.0  # Avoid zero range
            logging.debug(f"Waterfall: Updated level range, min={self.min_level}, max={self.max_level}")
        else:
            logging.warning("Waterfall: live_power_levels contains non-finite values, using default levels")
            self.min_level = -80
            self.max_level = -40

        # Update histogram levels
        self.histogram.setHistogramRange(self.min_level, self.max_level)
        self.histogram.setLevels(self.min_level, self.max_level)

        # Shift the waterfall array up and add new data
        self.waterfall_array[:-1] = self.waterfall_array[1:]
        self.waterfall_array[-1] = self.live_power_levels
        logging.debug(f"Waterfall: Updated waterfall_array, shape={self.waterfall_array.shape}")

        # Update the image with dynamic levels
        self.image_item.setImage(self.waterfall_array.T, autoLevels=False, levels=(self.min_level, self.max_level))
        logging.debug("Waterfall: Updated widget data")

    def initialise_waterfall(self):
        """Initialise the waterfall array."""
        logging.debug("Waterfall: Entering initialise_waterfall")
        if self.frequency_bins is None:
            logging.warning("Waterfall: frequency_bins is None, cannot initialise")
            return

        logging.info("Waterfall: Initialising waterfall")
        self.waterfall_array = np.zeros((self.history_amount, len(self.frequency_bins)))
        self.initialised = True
        self.histogram.setImageItem(self.image_item)

        # Set the initial image data
        self.image_item.setImage(self.waterfall_array.T, autoLevels=False, levels=(self.min_level, self.max_level))
        logging.debug("Waterfall: Set initial image data in initialise_waterfall")

        logging.debug("Waterfall: Waterfall initialised")
