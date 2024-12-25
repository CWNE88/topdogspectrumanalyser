import sys
import numpy as np
import sounddevice as sd
import pyfftw  # Import pyFFTW
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from vispy import app, scene


class UpdateThread(QThread):
    update_signal = pyqtSignal(np.ndarray, np.ndarray)
    finished_signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fft_history_left = None
        self.fft_history_right = None
        self.running = True

    def run(self):
        while self.running:
            if self.fft_history_left is not None and self.fft_history_right is not None:
                z_values_left = np.array(self.fft_history_left)
                z_values_right = np.array(self.fft_history_right)
                self.update_signal.emit(z_values_left, z_values_right)
                self.fft_history_left = None
                self.fft_history_right = None
            else:
                self.msleep(20)  # Sleep for 10 ms
        self.finished_signal.emit()

    def update(self, fft_history_left, fft_history_right):
        self.fft_history_left = fft_history_left
        self.fft_history_right = fft_history_right

    def stop(self):
        self.running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Create VisPy canvas
        self.canvas = scene.SceneCanvas(keys='interactive')
        self.setCentralWidget(self.canvas.native)

        # Configure 3D view
        self.view = self.canvas.central_widget.add_view()
        self.view.camera = 'turntable'
        self.view.camera.distance = 5

        # Create 3D surface plots
        self.surface_left = scene.visuals.SurfacePlot(
            shading='smooth',
            color=(0, 1, 0, 1),
            parent=self.view.scene
        )
        self.surface_right = scene.visuals.SurfacePlot(
            shading='smooth',
            color=(1, 0, 0, 1),
            parent=self.view.scene
        )

        # Timer for animation
        self.timer = QTimer()
        self.timer.timeout.connect(self.animate)
        self.timer.start(20)

        # Audio configuration
        self.sample_rate = 44.1e3
        self.sample_size = 512
        self.n_bins = int(self.sample_size / 2 + 1)
        self.history_depth = 100 
        self.window = np.hanning(self.sample_size)
        self.averaging_amount = 1

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=2,
            blocksize=self.sample_size,
            callback=self.audio_callback,
        )
        self.stream.start()

        # Prepare FFTW input and output arrays
        self.fft_input = pyfftw.empty_aligned(self.sample_size, dtype='float32')
        self.fft_output = pyfftw.empty_aligned(self.n_bins, dtype='complex64')

        # Create FFTW plan
        self.fft_object = pyfftw.FFTW(
            self.fft_input,
            self.fft_output
        )

        # History buffer to store FFT data
        self.fft_history_left = [np.zeros(self.n_bins) for _ in range(self.history_depth)]
        self.fft_history_right = [np.zeros(self.n_bins) for _ in range(self.history_depth)]

        self.dbm_history_left = np.zeros((self.averaging_amount, self.n_bins))  # Averaging buffer
        self.dbm_history_right = np.zeros((self.averaging_amount, self.n_bins))  # Averaging buffer
        self.dbm_index = 0  # Index for averaging buffer

        self.update_thread = UpdateThread()
        self.update_thread.update_signal.connect(self.update_surface)
        self.update_thread.finished_signal.connect(self.update_thread_finished)
        self.update_thread.start()

    def animate(self):
        if hasattr(self, "data"):
            # Get live FFT data
            fft_data_left, fft_data_right = self.update_sound()

            # Shift history back
            self.fft_history_left = [fft_data_left] + self.fft_history_left[:-1]
            self.fft_history_right = [fft_data_right] + self.fft_history_right[:-1]

            # Update surface item in separate thread
            self.update_thread.update(self.fft_history_left, self.fft_history_right)

    def update_surface(self, z_values_left, z_values_right):
        z_array_left = np.array(z_values_left)
        z_array_right = np.array(z_values_right)
        x, y = np.meshgrid(
            np.linspace(0, 1, z_array_left.shape[1]),
            np.linspace(0, 1, z_array_left.shape[0])
        )
        self.surface_left.set_data(x=x, y=y, z=z_array_left)
        self.surface_right.set_data(x=x, y=y, z=z_array_right)

    def update_thread_finished(self):
        print("Update thread finished")

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.data = indata  # Use both channels


    def update_sound(self):
        if not hasattr(self, "data"):
            return np.zeros(self.n_bins), np.zeros(self.n_bins)

        # Apply Hanning window and copy data into FFTW input
        np.copyto(self.fft_input, self.data[:, 0] * self.window)  # Left channel
        self.fft_object()
        fft_data_left = np.abs(self.fft_output)
        dbm_left = 20 * np.log10(fft_data_left + 1e-12)

        np.copyto(self.fft_input, self.data[:, 1] * self.window)  # Right channel
        self.fft_object()
        fft_data_right = np.abs(self.fft_output)
        dbm_right = 20 * np.log10(fft_data_right + 1e-12)

        # Apply averaging
        self.dbm_history_left[self.dbm_index] = dbm_left[:self.n_bins] / 200
        self.dbm_history_right[self.dbm_index] = dbm_right[:self.n_bins] / 200
        self.dbm_index = (self.dbm_index + 1) % len(self.dbm_history_left)
        averaged_dbm_left = np.mean(self.dbm_history_left, axis=0)
        averaged_dbm_right = np.mean(self.dbm_history_right, axis=0)

        return averaged_dbm_left, averaged_dbm_right

    def closeEvent(self, event):
        # Stop the audio stream on close
        self.stream.stop()
        self.stream.close()

        # Stop the update thread
        self.update_thread.stop()
        self.update_thread.wait()

        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

