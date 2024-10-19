import sys
import numpy as np
import sounddevice as sd
import scipy.fftpack
from PyQt6 import QtWidgets, QtCore
import pyqtgraph as pg


class SpectrumAnalyzer(QtWidgets.QWidget):
    def __init__(self, sampling_rate=44100):
        super().__init__()

        self.sampling_rate = sampling_rate
        self.sample_size = 1024
        self.setWindowTitle("Spectrum Analyser")
        self.setGeometry(100, 100, 800, 600)
        self.layout = QtWidgets.QVBoxLayout(self)
        self.plot_widget = pg.PlotWidget()
        self.layout.addWidget(self.plot_widget)
        self.plot_widget.setLogMode(x=True, y=False)
        self.plot_widget.setLabel("bottom", "Frequency (Hz)")
        self.plot_widget.setYRange(0, 0.1)
        self.plot_widget.showGrid(True, True)

        self.frequency_data = np.zeros(self.sampling_rate)
        self.plot_item = self.plot_widget.plot(self.frequency_data, pen="g")

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(20)

        self.stream = sd.InputStream(
            samplerate=self.sampling_rate,
            channels=1,
            blocksize=self.sample_size,
            callback=self.audio_callback,
        )
        self.stream.start()

        self.window = np.hanning(self.sample_size)

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.data = indata[:, 0]  # Use the first channel

    def update_plot(self):
        if hasattr(self, "data"):
            # Apply a window function
            # window = self.window(self.data)
            windowed_data = self.data * self.window

            # Perform FFT
            fft_data = np.abs(scipy.fftpack.fft(windowed_data, n=44100))[:22050]
            self.frequency_data = fft_data  # Use raw FFT data

            # Update the plot
            self.plot_item.setData(self.frequency_data)

            # Update x-axis ticks for logarithmic scale
            self.update_x_ticks()

    def update_x_ticks(self):
        # Specific ticks you want to display

        ticks = [
            (20, "20 Hz"),
            (200, "200 Hz"),
            (2000, "2 kHz"),
            (20000, "20 kHz"),
        ]

        # self.plot_widget.getAxis('bottom').setTicks([ticks])

    def closeEvent(self, event):
        self.stream.stop()
        self.stream.close()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = SpectrumAnalyzer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
