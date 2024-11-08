import sys
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer
from hackrf_sweep import HackRFSweep  

class SpectrumAnalyser(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Top Dog Spectrum Analyser")
        self.setGeometry(100, 100, 800, 600)

        
        self.hackrf_sweep = HackRFSweep()
        self.hackrf_sweep.setup(start_freq=2400, stop_freq=2500, bin_size=30000)
        self.hackrf_sweep.run()

        self.number_of_points = self.hackrf_sweep.get_number_of_points()
        self.check_data_ready()  # Set up a timer to check data availability

        # Setup plot
        self.plot_widget = pg.PlotWidget()
        self.setCentralWidget(self.plot_widget)
        self.plot_widget.setTitle("Spectrum Analyser")
        self.plot_widget.setLabel('left', 'Amplitude (dBm)')
        self.plot_widget.setLabel('bottom', 'Frequency (MHz)')
        self.plot_widget.setYRange(-100, -65)

        # Initialise frequency bins and max hold
        self.frequency_bins = np.linspace(self.hackrf_sweep.start_freq, self.hackrf_sweep.stop_freq, self.number_of_points)
        self.max_hold_curve = self.plot_widget.plot(pen='y', alpha=0.5)
        self.curve = self.plot_widget.plot(pen='g')
        
        self.max_hold_levels = np.full(self.number_of_points, -150.0)

        self.paused = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(20)

    def check_data_ready(self):
        """Check if data is ready and update frequency bins."""
        self.number_of_points = self.hackrf_sweep.get_number_of_points()
        if self.number_of_points > 0:
            self.frequency_bins = np.linspace(self.hackrf_sweep.start_freq, self.hackrf_sweep.stop_freq, self.number_of_points)
            self.max_hold_levels = np.full(self.number_of_points, -150.0)
        else:
            QTimer.singleShot(100, self.check_data_ready)  # Retry after a short delay

    def update(self):
        if self.paused:
            return

        self.power_levels = self.hackrf_sweep.get_data()
        if len(self.power_levels) != self.number_of_points:
            print(f"Warning: power_levels length {len(self.power_levels)} does not match frequency_bins length {self.number_of_points}. Trimming data.")
            self.power_levels = self.power_levels[:self.number_of_points]

        self.max_hold_levels = np.maximum(self.max_hold_levels, self.power_levels)

        # Only update if data has changed
        if not np.array_equal(self.curve.getData()[1], self.power_levels):
            self.curve.setData(self.frequency_bins, self.power_levels)
        if not np.array_equal(self.max_hold_curve.getData()[1], self.max_hold_levels):
            self.max_hold_curve.setData(self.frequency_bins, self.max_hold_levels)

    def keyPressEvent(self, event):
        if event.key() == 32:  # Space bar
            self.paused = not self.paused
            print("Paused" if self.paused else "Resumed")

    def closeEvent(self, event):
        self.hackrf_sweep.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SpectrumAnalyser()
    window.show()
    sys.exit(app.exec())
