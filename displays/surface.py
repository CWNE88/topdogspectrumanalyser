import numpy as np
from vispy import scene
from vispy.color import Colormap
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from vispy.scene import visuals
import logging

class Surface(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Create VisPy canvas
        self.canvas = scene.SceneCanvas(keys='interactive', show=False)
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = 'turntable'
        self.view.camera.distance = 1.7
        self.view.camera.azimuth = 19.0
        self.view.camera.elevation = 41.0
        self.view.camera.center = (0.4438475157657086, 0.502243020296804, 0.4779799807118244)

        # Create 3D surface plot
        self.surface = visuals.SurfacePlot(
            shading='smooth',
            color=(0.5, 0.5, 1, 0.8),
            parent=self.view.scene
        )

        # Peak marker: green header line + white freq/power lines
        self.annotation_peak_label = scene.Text("", parent=self.view.scene, color='green')
        self.annotation_peak_label.pos = (0.5, -0.1, 0.38)
        self.annotation_peak_label.font_size = 14

        self.annotation_peak_info = scene.Text("", parent=self.view.scene, color='white')
        self.annotation_peak_info.pos = (0.5, -0.1, 0.32)
        self.annotation_peak_info.font_size = 14

        # White sphere to mark the peak on the surface
        self.peak_sphere = visuals.Sphere(
            radius=0.01,
            color='white',
            parent=self.view.scene
        )
        self.peak_sphere.visible = False

        # Add the VisPy canvas to the layout
        self.layout.addWidget(self.canvas.native)

        # Initialise data attributes
        self.history_depth = 100
        self.fft_history_array = None
        self.number_of_points = 0
        self.frequency_bins = None
        self.peak_search_enabled = False
        self.max_peak_search_enabled = False
        self.z_scale_min = -100.0
        self.z_scale_max = 0.0
        self._cmap = Colormap(['blue', 'red'])
        self.auto_rotate = False

    @staticmethod
    def _format_freq(freq_mhz: float) -> str:
        """Format a frequency in MHz to a readable string."""
        if abs(freq_mhz) >= 1.0:
            return f"{freq_mhz:.3f} MHz"
        if abs(freq_mhz) >= 0.001:
            return f"{freq_mhz * 1000:.3f} kHz"
        return f"{freq_mhz * 1e6:.1f} Hz"

    def update_frequency_bins(self, frequency_bins):
        """Update the frequency bins for the plot."""
        if frequency_bins is not None and len(frequency_bins) > 0:
            if not np.all(np.isfinite(frequency_bins)):
                logging.error("Surface: frequency_bins contains non-finite values")
                return
            self.frequency_bins = frequency_bins * 1e-6  # Convert Hz to MHz
            self.number_of_points = len(frequency_bins)
            self.fft_history_array = np.zeros((self.history_depth, self.number_of_points))
            x = np.linspace(0, 1, self.number_of_points)
            y = np.linspace(0, 1, self.history_depth)  # row 0 (newest) → y=0 (front)
            self._mesh_x, self._mesh_y = np.meshgrid(x, y)
            logging.debug(f"Surface: Updated frequency bins, {self.number_of_points} points")
        else:
            logging.warning("Surface: Frequency bins are None or empty")

    def set_peak_search_enabled(self, enabled: bool):
        """Enable or disable peak search and update the peak marker."""
        self.peak_search_enabled = enabled

        if not enabled:
            self.annotation_peak_label.text = ""
            self.annotation_peak_info.text = ""
            self.peak_sphere.visible = False
            return

        if self.fft_history_array is None or self.frequency_bins is None:
            self.annotation_peak_label.text = "Live peak"
            self.annotation_peak_info.text = "N/A"
            self.peak_sphere.visible = False
            return

        live_data = self.fft_history_array[0]
        if len(live_data) == 0 or len(self.frequency_bins) != len(live_data):
            self.annotation_peak_label.text = "Live peak"
            self.annotation_peak_info.text = "N/A"
            self.peak_sphere.visible = False
            return

        self._place_peak_marker(live_data)

    def set_max_peak_search_enabled(self, enabled: bool):
        """No-op — max hold is not applicable to the surface plot."""
        self.max_peak_search_enabled = enabled

    def set_amplitude(self, ref_level: float, range_db: float) -> None:
        """Set the amplitude reference level and range."""
        self.z_scale_max = ref_level
        self.z_scale_min = ref_level - range_db

    def _place_peak_marker(self, live_data):
        """Position the peak sphere and update annotation text."""
        peak_idx = np.argmax(live_data)
        peak_freq = self.frequency_bins[peak_idx]
        peak_value = live_data[peak_idx]

        freq_min = self.frequency_bins[0]
        freq_max = self.frequency_bins[-1]
        normalised_x = (peak_freq - freq_min) / (freq_max - freq_min) if freq_max != freq_min else 0.5
        normalised_y = 0.0  # row 0 (newest) is at y=0 (front)

        if self.z_scale_max == self.z_scale_min:
            normalised_z = 0.5
        else:
            normalised_z = float(np.clip(
                (peak_value - self.z_scale_min) / (self.z_scale_max - self.z_scale_min), 0.0, 1.0
            ))

        self.annotation_peak_label.text = "Live peak"
        self.annotation_peak_label.pos = (normalised_x, -0.1, 0.38)

        self.annotation_peak_info.text = f"{self._format_freq(peak_freq)}\n{peak_value:.1f} dBm"
        self.annotation_peak_info.pos = (normalised_x, -0.1, 0.32)

        self.peak_sphere.transform = scene.transforms.MatrixTransform()
        self.peak_sphere.transform.translate((normalised_x, normalised_y, normalised_z))
        self.peak_sphere.visible = True

    def _update_peak_marker(self, live_data):
        """Update peak marker each frame when peak search is active."""
        if self.fft_history_array is None or self.frequency_bins is None:
            self.annotation_peak_label.text = "Live peak"
            self.annotation_peak_info.text = "N/A"
            self.peak_sphere.visible = False
            return

        if len(live_data) == 0 or len(self.frequency_bins) != len(live_data):
            self.annotation_peak_label.text = "Live peak"
            self.annotation_peak_info.text = "N/A"
            self.peak_sphere.visible = False
            return

        self._place_peak_marker(live_data)

    def set_history_lines(self, n: int) -> None:
        self.history_depth = n
        if self.number_of_points > 0:
            self.fft_history_array = np.zeros((self.history_depth, self.number_of_points))
            x = np.linspace(0, 1, self.number_of_points)
            y = np.linspace(0, 1, self.history_depth)  # row 0 (newest) → y=0 (front)
            self._mesh_x, self._mesh_y = np.meshgrid(x, y)

    def toggle_auto_rotate(self) -> None:
        self.auto_rotate = not self.auto_rotate

    def update_widget_data(self, live_data, max_data, frequency_bins, min_power_levels=None):
        """Update the surface plot with new data."""
        if live_data is None or frequency_bins is None:
            return

        if (self.frequency_bins is None or
                len(self.frequency_bins) != len(frequency_bins) or
                self.frequency_bins[0] != frequency_bins[0] * 1e-6 or
                self.frequency_bins[-1] != frequency_bins[-1] * 1e-6):
            self.update_frequency_bins(frequency_bins)

        if self.fft_history_array is None:
            return

        # Shift history in-place; np.roll would allocate a full copy
        self.fft_history_array[1:] = self.fft_history_array[:-1]
        self.fft_history_array[0] = live_data

        if self.auto_rotate:
            self.view.camera.azimuth = (self.view.camera.azimuth + 0.1) % 360

        self.update_surface(self.fft_history_array)

        if self.peak_search_enabled:
            self._update_peak_marker(live_data)

    def update_surface(self, z_values):
        """Update the surface plot with the given z values using a fixed scale."""
        if z_values.size == 0:
            logging.warning("Surface: z_values is empty, cannot update surface")
            return

        if self.z_scale_max == self.z_scale_min:
            normalised_z_values = np.ones_like(z_values) * 0.5
        else:
            normalised_z_values = (z_values - self.z_scale_min) / (self.z_scale_max - self.z_scale_min)
            normalised_z_values = np.clip(normalised_z_values, 0.0, 1.0)

        colours = self._cmap.map(normalised_z_values.flatten())[:, :3]
        colours = colours.reshape(z_values.shape[0], z_values.shape[1], 3)

        self.surface.set_data(x=self._mesh_x, y=self._mesh_y, z=normalised_z_values)
        self.surface.mesh_data.set_vertex_colors(colours.reshape(-1, 3))
