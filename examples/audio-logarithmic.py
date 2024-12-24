import sys
import numpy as np
import sounddevice as sd
import scipy.fftpack
from PyQt6 import QtWidgets, QtCore
import pyqtgraph as pg


class SpectrumAnalyser(QtWidgets.QWidget):
    def __init__(self, sample_rate=44100):
        super().__init__()

        self.sample_rate = sample_rate
        self.sample_size = 1024
        self.setWindowTitle("Spectrum Analyser")
        
        self.layout = QtWidgets.QVBoxLayout(self)
        self.plot_widget = pg.PlotWidget()
        self.layout.addWidget(self.plot_widget)
        self.plot_widget.setLogMode(x=False, y=False)
        self.plot_widget.setLabel("bottom", "Frequency (Hz)")
        self.plot_widget.setYRange(-240, 50)
        self.plot_widget.setXRange(0, self.sample_rate/2)
        self.plot_widget.showGrid(True, True)

        
        self.frequency_data = np.linspace (0, self.sample_rate//2, self.sample_size)
        self.plot_item = self.plot_widget.plot(self.frequency_data, pen="g")

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(20)

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
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
            windowed_data = self.data * self.window
            

            fft_data = np.abs(scipy.fftpack.rfft(windowed_data))
            dbm = 20 * np.log10(fft_data + 1e-12)
            
            self.plot_item.setData(self.frequency_data, dbm)




        


    def closeEvent(self, event):
        self.stream.stop()
        self.stream.close()
        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = SpectrumAnalyser()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
