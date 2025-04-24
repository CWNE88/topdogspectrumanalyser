import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg
import logging

# Configure logging to match main.py's usage
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class TwoD(QWidget):
    def __init__(self):
        super().__init__()
        self.plot_widget = pg.PlotWidget()
        # Set appearance to match original
        self.plot_widget.setBackground('k')  # Black background
        self.plot_widget.setLabel('left', 'Power', units='dBm')  # White label by default
        self.plot_widget.setLabel('bottom', 'Frequency', units='MHz')
        self.plot_widget.showGrid(x=True, y=True)  # Grid enabled

        # Plot lines with original colors
        self.live_plot = self.plot_widget.plot(pen=pg.mkPen('g', width=2), name='Live')  # Green for live data
        self.max_plot = self.plot_widget.plot(pen=pg.mkPen('y', width=2), name='Max Hold')  # Yellow for max hold
        # Use a scatter plot for the peak marker to show a white downward triangle
        self.peak_marker = self.plot_widget.plot(
            pen=None, symbol='t', symbolPen=None, symbolBrush='w', symbolSize=10
        )
        self.max_peak_marker = self.plot_widget.plot(
            pen=None, symbol='t', symbolPen=None, symbolBrush='w', symbolSize=10
        )

        # Use QVBoxLayout to avoid GraphicsLayoutWidget issues
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.plot_widget)
        self.setLayout(self.layout)

        self.frequency_bins = None
        self.peak_search_enabled = False
        self.max_peak_search_enabled = False
        logging.debug("TwoD: Widget initialised")

    def update_frequency_bins(self, freq_bins: np.ndarray):
        """Update the frequency bins for the plot."""
        self.frequency_bins = freq_bins
        min_freq = freq_bins[0] * 1e-6  # Convert Hz to MHz
        max_freq = freq_bins[-1] * 1e-6
        self.plot_widget.setXRange(min_freq, max_freq)
        logging.debug(f"TwoD: Updated x-range to {min_freq:.2f}-{max_freq:.2f} MHz")

    def set_peak_search_enabled(self, enabled: bool):
        """Enable or disable peak search."""
        self.peak_search_enabled = enabled
        if not enabled:
            self.peak_marker.setData([], [])
        logging.debug(f"TwoD: Peak search {'enabled' if enabled else 'disabled'}")

    def set_max_peak_search_enabled(self, enabled: bool):
        """Enable or disable max hold."""
        self.max_peak_search_enabled = enabled
        if not enabled:
            self.max_plot.setData([], [])  # Clear max hold plot when disabled
            self.max_peak_marker.setData([], [])  # Clear max peak marker as well
        logging.debug(f"TwoD: Max hold {'enabled' if enabled else 'disabled'}")

    def update_widget_data(self, live_power_levels: np.ndarray, max_power_levels: np.ndarray, frequency_bins: np.ndarray):
        """Update the 2D plot with live and max power levels."""
        if live_power_levels is None or max_power_levels is None or frequency_bins is None:
            logging.warning("TwoD: Received 'None' data")
            return

        if self.frequency_bins is None:
            self.update_frequency_bins(frequency_bins)

        freq_bins = frequency_bins * 1e-6  # Convert Hz to MHz
        live_data = live_power_levels
        max_data = max_power_levels

        if not np.all(np.isfinite(live_data)):
            logging.warning("TwoD: live_data contains non-finite values")
            return
        if not np.all(np.isfinite(max_data)):
            logging.warning("TwoD: max_data contains non-finite values")
            return
        if not np.all(np.isfinite(freq_bins)):
            logging.warning("TwoD: freq_bins contains non-finite values")
            return

        # Always update the live plot (green)
        self.live_plot.setData(freq_bins, live_data)

        # Update max hold plot (yellow) only if enabled
        if self.max_peak_search_enabled:
            self.max_plot.setData(freq_bins, max_data)
        else:
            self.max_plot.setData([], [])  # Clear max hold plot if disabled

        # Update peak markers
        if self.peak_search_enabled:
            peak_idx = np.argmax(live_data)
            peak_freq = freq_bins[peak_idx]
            self.peak_marker.setData([peak_freq], [live_data[peak_idx]])
        else:
            self.peak_marker.setData([], [])

        if self.max_peak_search_enabled:
            max_peak_idx = np.argmax(max_data)
            max_peak_freq = freq_bins[max_peak_idx]
            self.max_peak_marker.setData([max_peak_freq], [max_data[max_peak_idx]])
        else:
            self.max_peak_marker.setData([], [])

        #self.plot_widget.setYRange(-100, 0)  # Match original y-range
        logging.debug("TwoD: Updated widget data")
