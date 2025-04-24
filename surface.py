import numpy as np
from vispy import scene
from vispy.color import Colormap
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from vispy.scene import visuals
import logging

# Configure logging to match TwoD's usage
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class Surface(QWidget):
    def __init__(self):
        """Initialise the Surface plot widget."""
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)  # Match TwoD's layout setup

        # Create VisPy canvas
        self.canvas = scene.SceneCanvas(keys='interactive', show=True)
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = 'turntable'
        self.view.camera.distance = 2
        self.view.camera.fov = 60

        # Create 3D surface plot
        self.surface = visuals.SurfacePlot(
            shading='smooth',
            color=(0.5, 0.5, 1, 0.8),
            parent=self.view.scene
        )

        # Add the VisPy canvas to the layout
        self.layout.addWidget(self.canvas.native)

        # Initialise data attributes
        self.history_depth = 25
        self.fft_history = None
        self.number_of_points = 0
        self.frequency_bins = None
        self.peak_search_enabled = False
        self.max_peak_search_enabled = False
        logging.debug("Surface: Widget initialised")

    def update_frequency_bins(self, frequency_bins):
        """Update the frequency bins for the plot."""
        if frequency_bins is not None and len(frequency_bins) > 0:
            if not np.all(np.isfinite(frequency_bins)):
                logging.error("Surface: frequency_bins contains non-finite values")
                return
            self.frequency_bins = frequency_bins * 1e-6  # Convert Hz to MHz, matching TwoD
            self.number_of_points = len(frequency_bins)
            # Reinitialize the FFT history to match the new number of points
            self.fft_history = [np.zeros(self.number_of_points) for _ in range(self.history_depth)]
            logging.debug(f"Surface: Updated frequency bins, {self.number_of_points} points")
        else:
            logging.warning("Surface: Frequency bins are None or empty")

    def set_peak_search_enabled(self, enabled: bool):
        """Enable or disable peak search (not used for surface plot, but required by main.py)."""
        self.peak_search_enabled = enabled
        logging.debug(f"Surface: Peak search {'enabled' if enabled else 'disabled'} (no-op)")

    def set_max_peak_search_enabled(self, enabled: bool):
        """Enable or disable max hold (not used for surface plot, but required by main.py)."""
        self.max_peak_search_enabled = enabled
        logging.debug(f"Surface: Max hold {'enabled' if enabled else 'disabled'} (no-op)")

    def update_widget_data(self, live_data, max_data, frequency_bins):
        """Update the surface plot with new data."""
        if live_data is None or frequency_bins is None:
            logging.warning("Surface: Received 'None' data in one or more variables")
            return

        if not np.all(np.isfinite(live_data)):
            logging.warning("Surface: live_data contains non-finite values")
            return

        if self.frequency_bins is None or len(self.frequency_bins) != len(frequency_bins):
            self.update_frequency_bins(frequency_bins)

        # Shift history back and add new data
        self.fft_history = [live_data] + self.fft_history[:-1]
        fft_history_array = np.array(self.fft_history)

        # Update the surface plot
        self.update_surface(fft_history_array)
        logging.debug("Surface: Updated widget data")

    def update_surface(self, z_values):
        """Update the surface plot with the given z values."""
        if z_values.size == 0:
            logging.warning("Surface: z_values is empty, cannot update surface")
            return

        # Dynamic scaling based on z_values
        z_min = np.min(z_values)
        z_max = np.max(z_values)
        if z_max == z_min:
            z_max = z_min + 1.0  # Avoid division by zero
        cmap = Colormap(['blue', 'red'])

        # Flatten the scaled values for Colormap mapping
        scaled_values = (z_values - z_min) / (z_max - z_min)
        colours = cmap.map(scaled_values.flatten())  # Returns shape (history_depth * number_of_points, 4)

        # Take only RGB (drop alpha channel) and reshape to match z_values
        colours = colours[:, :3].reshape(z_values.shape[0], z_values.shape[1], 3)

        # Map frequency bins to x-axis (0 to 1)
        x = np.linspace(0, 1, z_values.shape[1])
        y = np.linspace(0, 1, z_values.shape[0])
        x, y = np.meshgrid(x, y)
        offset_z_values = (z_values - z_min) / (z_max - z_min)  # Normalise z-values to 0-1 for visualisation
        self.surface.set_data(x=x, y=y, z=offset_z_values)
        self.surface.mesh_data.set_vertex_colors(colours.reshape(-1, 3))
        logging.debug(f"Surface: Updated surface with z range {z_min:.2f}-{z_max:.2f}")
