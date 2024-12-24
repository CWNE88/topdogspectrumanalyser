import sys
import numpy as np
import pyfftw
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from vispy import app, scene
from rtlsdr import RtlSdr
from vispy.color import Colormap

from hackrf_sweep import HackRFSweep  

class UpdateThread(QThread):
    update_signal = pyqtSignal(np.ndarray)
    finished_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fft_history = None
        self.running = True
 
    def run(self):
        while self.running:
            if self.fft_history is not None:
                z_values = np.array(self.fft_history)
                self.update_signal.emit(z_values)
                self.fft_history = None
            else:
                self.msleep(20)  # Sleep for 20 ms
        self.finished_signal.emit()

    def update(self, fft_history):
        self.fft_history = fft_history

    def stop(self):
        self.running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Create VisPy canvas
        self.canvas = scene.SceneCanvas(keys='interactive', show=True)
        self.setCentralWidget(self.canvas.native)

        # Configure 3D view
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = 'turntable'
        self.view.camera.distance = 2
        self.view.camera.fov = 60
        #self.view.camera.center = (0.5, 0.5, 5)  
        self.history_depth = 25

        # Create 3D surface plot
        self.surface = scene.visuals.SurfacePlot(
            shading='smooth',
            color=(0.5, 0.5, 1, 0.8),
            parent=self.view.scene
        )

        self.hackrf_sweep = HackRFSweep()
        self.hackrf_sweep.setup(start_freq=2400, stop_freq=2500, bin_size=30000)
        self.hackrf_sweep.run()

        self.number_of_points = 0  
        self.frequency_bins = None
        self.fft_history = None
        self.timer = QTimer()

        # Start checking if data is ready
        self.check_data_ready()

    def check_data_ready(self):
        """Continuously check if HackRF sweep data is ready."""
        self.number_of_points = self.hackrf_sweep.get_number_of_points()
        print (self.number_of_points)

        if self.number_of_points > 0:
            # Data is ready, initialize buffers and start animation
            self.frequency_bins = np.linspace(self.hackrf_sweep.start_freq, self.hackrf_sweep.stop_freq, self.number_of_points)
            self.fft_history = [np.zeros(self.number_of_points) for _ in range(self.history_depth)]  # History depth of 30

            self.timer.timeout.connect(self.animate)
            self.timer.start(20)  # Start animation with 20 ms interval
        else:
            # Retry after a short delay
            QTimer.singleShot(100, self.check_data_ready)

    def animate(self):
        """Update the plot with new data."""
        fft_data = self.update_sdr()

        if fft_data is not None:
            # Shift history back and add new data
            self.fft_history = [fft_data] + self.fft_history[:-1]
            fft_history_array = np.array(self.fft_history)
            #print (fft_history_array)

            # Update the surface plot
            self.update_surface(fft_history_array)

    def update_surface(self, z_values):
        """Update the surface plot."""
        if z_values.size == 0:
            return

        z_min = -80
        z_max = -50
        cmap = Colormap(['blue', 'red'])

        clipped_values = np.clip(z_values, z_min, z_max)
        scaled_values = (clipped_values - clipped_values.min()) / (clipped_values.max() - clipped_values.min())
        colors = cmap.map(scaled_values)[:, :3]

        x, y = np.meshgrid(
            np.linspace(0, 1, z_values.shape[1]),
            np.linspace(0, 1, z_values.shape[0])
        )
        #print (z_values)
        offset_z_values = z_values /100 #+ 100  # Offset z-values up by 100
        self.surface.set_data(x=x, y=y, z=offset_z_values)
        self.surface.mesh_data.set_vertex_colors(colors.reshape(-1, 3))

    def update_sdr(self):
        """Fetch new data from HackRF."""
        power_levels = self.hackrf_sweep.get_data()
        if len(power_levels) != self.number_of_points:
            print(f"Warning: Data length mismatch. Expected {self.number_of_points}, got {len(power_levels)}. Trimming data.")
            power_levels = power_levels[:self.number_of_points]
        return power_levels

    def closeEvent(self, event):
        self.hackrf_sweep.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
