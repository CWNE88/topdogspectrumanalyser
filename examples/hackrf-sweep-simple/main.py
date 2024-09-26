import sys
import time
import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer
from hackrf_sweep import HackRFSweep  # Import your HackRFSweep class


class SpectrumAnalyser(QMainWindow):
    SAMPLE_SIZE = 1024  # Set this to match your bin size
    MAX_AMPLITUDE = 2.0
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Top Dog Spectrum Analyser")
        self.setGeometry(100, 100, 800, 600)

        # Initialize HackRFSweep
        self.hackrf_sweep = HackRFSweep()
        self.hackrf_sweep.setup(start_freq=80, stop_freq=210, bin_size=3000)
        self.hackrf_sweep.run()  # Start the sweep

        self.number_of_points = self.hackrf_sweep.get_number_of_points()
        while self.number_of_points == 0:
            time.sleep(0.1)
            self.number_of_points = self.hackrf_sweep.get_number_of_points()
            print("numberofpoints is ", str(self.number_of_points))

        # 2D plot for spectrum display
        self.plot_widget = pg.PlotWidget()
        self.setCentralWidget(self.plot_widget)
        self.plot_widget.setTitle("Spectrum Analyser")
        self.plot_widget.setLabel('left', 'Amplitude (dBm)')
        self.plot_widget.setLabel('bottom', 'Frequency (MHz)')
        self.plot_widget.setYRange(-100, -65)

        # Frequency bins for plotting
        self.frequency_bins = np.linspace(self.hackrf_sweep.start_freq, self.hackrf_sweep.stop_freq, self.number_of_points)
        self.curve = self.plot_widget.plot(pen='y')  # Current data plot
        self.max_hold_curve = self.plot_widget.plot(pen='r', alpha=0.5)  # Max hold plot

        # Initialize max hold array
        self.max_hold_levels = np.full(self.number_of_points, -150.0)  # Start with minimum values

        # Pause flag
        self.paused = False

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(20)  # More frequent updates

    def update(self):
        if self.paused:
            return  # Skip data acquisition if paused

        # Get power levels directly from HackRFSweep
        self.power_levels = self.hackrf_sweep.get_data()

        # Ensure power_levels matches the expected size
        if len(self.power_levels) != len(self.frequency_bins):
            print(f"Warning: power_levels length {len(self.power_levels)} does not match frequency_bins length {len(self.frequency_bins)}. Trimming data.")
            self.power_levels = self.power_levels[:len(self.frequency_bins)]

        # Update max hold values
        self.max_hold_levels = np.maximum(self.max_hold_levels, self.power_levels)

        # Update the plots
        self.curve.setData(self.frequency_bins, self.power_levels)
        self.max_hold_curve.setData(self.frequency_bins, self.max_hold_levels)

    def keyPressEvent(self, event):
        if event.key() == 32:  # Space bar key
            self.paused = not self.paused  # Toggle paused state
            print("Paused" if self.paused else "Resumed")

    def closeEvent(self, event):
            """Override the close event to clean up."""
            self.hackrf_sweep.stop()  # Stop the HackRFSweep instance
            event.accept()  # Accept the event to close the window

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SpectrumAnalyser()
    window.show()
    sys.exit(app.exec())


