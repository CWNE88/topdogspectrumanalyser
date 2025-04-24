#!/bin/python3
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph.opengl as gl
import pyqtgraph as pg
import numpy as np
from PyQt6 import QtWidgets
import logging
import time

# Configure logging to match other widgets
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class ThreeD(QtWidgets.QWidget):
    def __init__(self):
        """Initialise the 3D plot widget."""
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.widget)

        self.paused = False
        self.peak_search_enabled = False
        self.max_peak_search_enabled = False

        # Single grid at y = 10, matching Visualizer
        griditem = gl.GLGridItem()
        griditem.setSize(20, 20)
        griditem.setSpacing(2, 2)
        griditem.rotate(90, 1, 0, 0)
        griditem.translate(0, 10, 0)
        self.widget.addItem(griditem)

        # Centre frequency line and text
        centre_text = gl.GLTextItem()
        centre_text.setData(pos=(0.0, 10.0, 10.0), color=(255, 255, 255, 255), text="Centre frequency")
        self.widget.addItem(centre_text)

        line_points = [(0, 10, 10), (0, 10, 0)]
        line = gl.GLLinePlotItem(pos=line_points, color=(1, 1, 1, 1), width=2)
        self.widget.addItem(line)

        # Peak text (will display power level)
        self.peak_text = gl.GLTextItem()
        self.peak_text.setData(pos=(10.0, 10.0, 10.0), color=(255, 255, 255, 255), text="")
        self.widget.addItem(self.peak_text)

        self.number_of_lines = 25  # Reduced for performance, matching previous optimisation

        self.line_y_values = np.linspace(10, -10, self.number_of_lines)
        self.traces = dict()
        self.x = None
        self.y = None
        self.traces_initialised = False

        # Peak marker as a sphere, matching Visualizer
        peak_points = gl.MeshData.sphere(rows=10, cols=10)
        self.peak_sphere = gl.GLMeshItem(meshdata=peak_points, smooth=True, color=(1, 1, 1, 1), shader='balloon')
        self.peak_sphere.resetTransform()
        self.peak_sphere.scale(0.2, 0.2, 0.2)
        self.peak_sphere.translate(2, 0, 0)
        self.widget.addItem(self.peak_sphere)

        # Max hold trace
        self.max_hold_trace = None
        self.max_hold_z = None  # To store max hold z-values
        self.good_colours = None
        logging.debug("ThreeD: Widget initialised")

    def initialise_traces(self):
        """Initialise the 3D trace lines for spectrum display."""
        if self.frequency_bins is None or len(self.frequency_bins) == 0:
            logging.warning("ThreeD: frequency_bins is None or empty, cannot initialise traces")
            return
        
        # Map frequency bins to x-axis range (-10 to 10)
        freq_min = np.min(self.frequency_bins)
        freq_max = np.max(self.frequency_bins)
        if freq_max == freq_min:
            freq_max = freq_min + 1.0  # Avoid division by zero
        self.x = ((self.frequency_bins - freq_min) / (freq_max - freq_min)) * 20 - 10  # Scale to -10 to 10
        self.good_colours = np.empty((len(self.frequency_bins), 4))
        for i in range(self.number_of_lines):
            y_val = self.line_y_values[i]
            z_val = np.zeros_like(self.frequency_bins)
            specan_pts = np.vstack([self.x, np.full_like(self.frequency_bins, y_val), z_val]).T
            self.traces[i] = gl.GLLinePlotItem(
                pos=specan_pts,
                color=np.zeros([len(self.frequency_bins), 4]),
                antialias=True,
                mode="line_strip",
            )
            self.widget.addItem(self.traces[i])

        # Initialise max hold trace
        max_hold_pts = np.vstack([self.x, np.full_like(self.frequency_bins, self.line_y_values[0]), z_val]).T
        self.max_hold_trace = gl.GLLinePlotItem(
            pos=max_hold_pts,
            color=(0.0, 1.0, 0.0, 0.3),  # Green with alpha, matching Visualizer
            antialias=True,
            mode="line_strip",
            width=3  # Matching Visualizer
        )
        self.widget.addItem(self.max_hold_trace)
        self.max_hold_z = z_val.copy()  # Initialise max hold z-values

        self.traces_initialised = True
        logging.debug("ThreeD: Traces initialised")

    def set_plotdata(self, name, points, colour, width):
        """Set data for a specific trace."""
        if name == "max_hold":
            self.max_hold_trace.setData(pos=points, color=colour, width=width)
        else:
            self.traces[name].setData(pos=points, color=colour, width=width)

    def set_peak_search_enabled(self, is_enabled):
        """Enable or disable peak search marker."""
        self.peak_search_enabled = is_enabled
        if not is_enabled:
            self.peak_sphere.resetTransform()
            self.peak_sphere.translate(0, 0, -100)  # Move off-screen
            self.peak_text.setData(pos=(0, 0, -100), text="")
        logging.debug(f"ThreeD: Peak search {'enabled' if is_enabled else 'disabled'}")

    def set_max_peak_search_enabled(self, is_enabled):
        """Enable or disable max hold trace."""
        self.max_peak_search_enabled = is_enabled
        if not is_enabled:
            self.max_hold_trace.setData(pos=np.array([]), color=(0, 0, 0, 0))
            if self.max_hold_z is not None:
                # Reset max hold z-values when disabled
                self.max_hold_z = np.zeros_like(self.max_hold_z)
        elif self.max_hold_z is not None and self.live_power_levels is not None:
            # Reset max hold z-values when re-enabled, matching Visualizer
            self.max_hold_z = np.zeros_like(self.max_hold_z)
            self.update_max_hold(self.live_power_levels)
        logging.debug(f"ThreeD: Max hold {'enabled' if is_enabled else 'disabled'}")

    def update_frequency_bins(self, bins):
        """Update frequency bins."""
        if bins is not None and len(bins) > 0:
            if not np.all(np.isfinite(bins)):
                logging.error("ThreeD: frequency_bins contains non-finite values")
                return
            self.frequency_bins = bins
            self.traces_initialised = False  # Force reinitialization of traces
            if self.good_colours is None or len(self.good_colours) != len(bins):
                self.good_colours = np.empty((len(bins), 4))
            if self.max_hold_z is None or len(self.max_hold_z) != len(bins):
                self.max_hold_z = np.zeros(len(bins))
            self.initialise_traces()
            logging.debug(f"ThreeD: Updated frequency bins, {len(bins)} points")
        else:
            logging.warning("ThreeD: Frequency bins are None or empty")

    def update_max_hold(self, live_data):
        """Update max hold z-values with new live data."""
        for i in range(len(self.frequency_bins)):
            if self.max_hold_z[i] < live_data[i]:
                self.max_hold_z[i] = live_data[i]

    def update_widget_data(self, live_power_levels, max_power_levels, frequency_bins):
        """Update widget data and refresh the plot."""
        start_time = time.time()

        if live_power_levels is None or max_power_levels is None or frequency_bins is None:
            logging.warning("ThreeD: Received 'None' data in one or more variables")
            return

        if not np.all(np.isfinite(live_power_levels)) or not np.all(np.isfinite(max_power_levels)):
            logging.warning("ThreeD: Power levels contain non-finite values")
            return

        if not np.all(np.isfinite(frequency_bins)):
            logging.warning("ThreeD: frequency_bins contains non-finite values")
            return

        self.live_power_levels = live_power_levels
        self.max_hold_levels = max_power_levels

        if self.frequency_bins is None or len(self.frequency_bins) != len(frequency_bins):
            self.update_frequency_bins(frequency_bins)

        if not self.traces_initialised:
            self.initialise_traces()
            if not self.traces_initialised:
                return

        # Update traces
        for i in range(self.number_of_lines - 1):
            trace = self.traces[self.number_of_lines - i - 2]
            trace_pos = trace.pos
            trace_colour = trace.color
            trace_pos[:, 1] = self.line_y_values[self.number_of_lines - i - 1]
            self.set_plotdata(name=self.number_of_lines - i - 1, points=trace_pos, colour=trace_colour, width=1)

        # Process live data with logarithmic scaling, matching Visualizer
        self.y = np.full_like(self.frequency_bins, self.line_y_values[0])
        # Normalise power levels to fit z-axis range (0 to 8)
        min_power = np.min(live_power_levels)
        max_power = np.max(live_power_levels)
        if max_power == min_power:
            max_power = min_power + 1.0  # Avoid division by zero
        self.z = ((live_power_levels - min_power) / (max_power - min_power)) * 8  # Scale to 0-8

        # Colour mapping, matching Visualizer
        for i in range(len(self.frequency_bins)):
            self.good_colours[i] = pg.glColor((8 - self.z[i], 8 * 1.4))
            self.good_colours[i][3] = 1  # Ensure alpha is 1

        # Update main trace
        specan_pts = np.vstack((self.x, self.y, self.z)).T
        self.set_plotdata(name=0, points=specan_pts, colour=self.good_colours, width=5)  # Width 5, matching Visualizer

        # Update max hold trace
        if self.max_peak_search_enabled:
            max_z = ((max_power_levels - min_power) / (max_power - min_power)) * 8
            self.update_max_hold(max_z)
            max_hold_pts = np.vstack((self.x, np.full_like(self.frequency_bins, self.line_y_values[0]), self.max_hold_z)).T
            self.set_plotdata(name="max_hold", points=max_hold_pts, colour=(0.0, 1.0, 0.0, 0.3), width=3)
        else:
            self.max_hold_trace.setData(pos=np.array([]), color=(0, 0, 0, 0))

        # Update peak search marker
        if self.peak_search_enabled:
            data_to_search = self.max_hold_z if self.max_peak_search_enabled else self.z
            if data_to_search is not None:
                maxx_index = np.argmax(data_to_search)
                self.peak_sphere.resetTransform()
                self.peak_sphere.scale(0.2, 0.2, 0.2)
                z_val = np.max(data_to_search)
                self.peak_sphere.translate(self.x[maxx_index], 10, z_val)
                # Display peak power level, matching Visualizer
                self.peak_text.setData(
                    pos=(10.0, 10.0, 10.0),
                    color=(255, 255, 255, 255),
                    text=f"{self.live_power_levels[maxx_index]:.2f} dBm"
                )
            else:
                self.peak_sphere.resetTransform()
                self.peak_sphere.translate(0, 0, -100)
                self.peak_text.setData(pos=(0, 0, -100), text="")
        else:
            self.peak_sphere.resetTransform()
            self.peak_sphere.translate(0, 0, -100)
            self.peak_text.setData(pos=(0, 0, -100), text="")

        elapsed_time = time.time() - start_time
        logging.debug(f"ThreeD: Updated widget data in {elapsed_time*1000:.2f} ms")
