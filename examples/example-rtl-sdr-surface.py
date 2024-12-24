import sys
import numpy as np
import pyfftw
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from vispy import app, scene
from rtlsdr import RtlSdr
from vispy.color import Colormap

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

        # Create 3D surface plot
        self.surface = scene.visuals.SurfacePlot(
            shading='smooth',
            color=(0.5, 0.5, 1, 0.8),
            parent=self.view.scene
        )

        # Create annotation
        self.annotation = scene.Text("Frequency (MHz)", parent=self.view.scene, color='white')
        self.annotation.pos = (0.5, -0.1, 0.3)
        self.annotation.font_size = 16

        self.annotation2 = scene.Text("Radio", parent=self.view.scene, color='white')
        self.annotation2.pos = (0.7, -0.1, 0.3)
        self.annotation2.font_size = 16

        self.annotation3 = scene.Text("More\nbullshit\nover\nhere", parent=self.view.scene, color='white')
        self.annotation3.pos = (0.2, -0.1, 0.3)
        self.annotation3.font_size = 16

        

        # Timer for animation
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(20)

        # SDR configuration
        self.sdr = RtlSdr()
        self.sdr.gain = 40
        self.sdr.center_freq = 98e6  # Center frequency in Hz
        self.sdr.sample_rate = 2e6  # Bandwidth in Hz
        self.sample_size = 1024  # Number of FFT bins
        self.n_bins = self.sample_size #// 2 + 1
        self.history_depth = 30  # Number of rows for history
        self.window = np.hanning(self.sample_size)

        # Prepare FFTW input and output arrays
        self.fft_input = pyfftw.empty_aligned(self.sample_size, dtype='complex64')
        self.fft_output = pyfftw.empty_aligned(self.sample_size, dtype='complex64')

        # Create FFTW plan
        self.fft_object = pyfftw.FFTW(
            self.fft_input,
            self.fft_output,
            direction='FFTW_FORWARD'
        )

        # History buffer to store FFT data
        self.fft_history = [np.zeros(self.n_bins) for _ in range(self.history_depth)]

        self.dbm_history = np.zeros((10, self.n_bins))  # Averaging buffer
        self.dbm_index = 0  # Index for averaging buffer

        self.update_thread = UpdateThread()
        self.update_thread.update_signal.connect(self.update_surface)
        self.update_thread.finished_signal.connect(self.update_thread_finished)
        self.update_thread.start()

    def animate(self):
        # Get live FFT data from SDR
        fft_data = self.update_sdr()

        # Shift history back
        self.fft_history = [fft_data] + self.fft_history[:-1]

        # Update surface item in separate thread
        self.update_thread.update(self.fft_history)

    def update_surface(self, z_values):
        # Define thresholds for min and max
        z_min = -10  # Example minimum value
        z_max = 10   # Example maximum value

        # Create a colormap (e.g., blue to red) 
        cmap = Colormap(['blue', 'red'])

        # Clip values to min and max thresholds
        clipped_values = np.clip(z_values, z_min, z_max)

        # Scale clipped values to range [0, 1]
        data_min = np.min(clipped_values)
        data_max = np.max(clipped_values)
        scaled_values = (clipped_values - data_min) / (data_max - data_min)

        # Map scaled values to colormap
        colors = cmap.map(scaled_values)[:, :3]  # Map to RGB, ignore alpha

        # Update the surface plot data
        x, y = np.meshgrid(
            np.linspace(0, 1, z_values.shape[1]),
            np.linspace(0, 1, z_values.shape[0])
        )
        self.surface.set_data(x=x, y=y, z=z_values)
        #print (z_values)

        # Set vertex colors
        self.surface.mesh_data.set_vertex_colors(colors.reshape(-1, 3))


    def update_thread_finished(self):
        print("Update thread finished")

    def update_sdr(self):
        try:
            # Read samples from the SDR device
            samples = self.sdr.read_samples(self.sample_size)

            # Apply Hanning window and copy data into FFTW input
            np.copyto(self.fft_input, samples * self.window)

            # Execute FFT using FFTW
            self.fft_object()
            fft_data = np.abs(self.fft_output)
            dbm = 20 * np.log10(fft_data + 1e-12)

            # Apply averaging
            self.dbm_history[self.dbm_index] = dbm[:self.n_bins] / 100
            self.dbm_index = (self.dbm_index + 1) % len(self.dbm_history)
            averaged_dbm = np.mean(self.dbm_history, axis=0)

            return averaged_dbm
        except Exception as e:
            print(f"Error reading from SDR: {e}")
            return np.zeros(self.n_bins)

    def closeEvent(self, event):
        # Stop the update thread
        self.update_thread.stop()
        self.update_thread.wait()

        # Close the SDR device
        self.sdr.close()

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
