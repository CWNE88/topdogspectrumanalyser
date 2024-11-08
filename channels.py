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
        self.setGeometry(100, 500, 1500, 600)

        self.hackrf_sweep = HackRFSweep()
        self.start_freq = 2400
        self.stop_freq = 2500
        self.bin_size = 30000
        self.setup_sweep()

        self.number_of_points = self.hackrf_sweep.get_number_of_points()
        self.check_data_ready()  # Set up a timer to check data availability

        # Setup plot
        self.plot_widget = pg.PlotWidget()
        self.setCentralWidget(self.plot_widget)
        self.plot_widget.setTitle("Spectrum Analyser")
        self.plot_widget.setLabel('left', 'Amplitude (dBm)')
        self.plot_widget.setLabel('bottom', 'Frequency (MHz)')
        self.plot_widget.setYRange(-100, -65)

        self.initialise_plot()  # Initialise the plot
        self.draw_reference_line()  # Draw the reference line

        self.paused = False
        self.main_curve_visible = True  # Track visibility of the main curve
        self.max_hold_curve_visible = True  # Track visibility of the max hold curve
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(20)

    def setup_sweep(self):
        self.hackrf_sweep.setup(start_freq=self.start_freq, stop_freq=self.stop_freq, bin_size=self.bin_size)
        self.hackrf_sweep.run()

    def initialise_plot(self):
        self.number_of_points = self.hackrf_sweep.get_number_of_points()
        self.frequency_bins = np.linspace(self.start_freq, self.stop_freq, self.number_of_points)
        self.max_hold_levels = np.full(self.number_of_points, -150.0)

        # Clear previous plots
        self.plot_widget.clear()

        # Create new plot curves
        self.max_hold_curve = self.plot_widget.plot(pen='y', alpha=0.5)
        self.curve = self.plot_widget.plot(pen='g')

        # Buffer for last 56 power levels
        self.last_values = np.zeros((56, self.number_of_points))
        self.current_index = 0

        # Create average curve
        self.average_curve = self.plot_widget.plot(pen='w', name='Average')

    def draw_reference_line(self):
        """Draw a blue line at 90% height of the y scale between 2401 MHz and 2423 MHz."""
        y_range = self.plot_widget.viewRange()  # Get current view range
        y_min, y_max = y_range[1]  # y_min and y_max are in the second element of the tuple
        reference_y = y_min + 0.9 * (y_max - y_min)  # 90% height of the y range
        reference_y2 = y_min + 0.85 * (y_max - y_min)  # 90% height of the y range
        

        reference_line = pg.LineSegmentROI([[2401, reference_y], [2423, reference_y]], pen='b', 
                                            hoverPen='r', movable=False)
        self.plot_widget.addItem(reference_line)
        
        reference_line = pg.LineSegmentROI([[2473, reference_y], [2495, reference_y]], pen='b', 
                                            hoverPen='r', movable=False)
        self.plot_widget.addItem(reference_line)
        

        reference_line = pg.LineSegmentROI([[2426, reference_y], [2448, reference_y]], pen='b', 
                                            hoverPen='r', movable=False)
        self.plot_widget.addItem(reference_line)

        reference_line = pg.LineSegmentROI([[2451, reference_y], [2473, reference_y]], pen='b', 
                                            hoverPen='r', movable=False)
        self.plot_widget.addItem(reference_line)



    def check_data_ready(self):
        """Check if data is ready and update frequency bins."""
        self.number_of_points = self.hackrf_sweep.get_number_of_points()
        if self.number_of_points > 0:
            self.frequency_bins = np.linspace(self.start_freq, self.stop_freq, self.number_of_points)
            self.max_hold_levels = np.full(self.number_of_points, -150.0)
            self.last_values = np.zeros((56, self.number_of_points))  # Reset the buffer
            self.current_index = 0  # Reset the current index
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

        # Update the buffer with the new power levels
        self.last_values[self.current_index] = self.power_levels
        self.current_index = (self.current_index + 1) % 56  # Move to the next index (wrap around)

        # Compute the average of the last 56 values
        average_levels = np.mean(self.last_values, axis=0)

        # Only update if data has changed
        if self.main_curve_visible:
            self.curve.setData(self.frequency_bins, self.power_levels)
        else:
            self.curve.clear()  # Clear the main curve if not visible
        
        if self.max_hold_curve_visible:
            self.max_hold_curve.setData(self.frequency_bins, self.max_hold_levels)
        else:
            self.max_hold_curve.clear()  # Clear max hold curve if not visible

        # Update average curve
        self.average_curve.setData(self.frequency_bins, average_levels)
 
    def reset_sweep(self):
        self.hackrf_sweep.stop()  # Stop the current sweep
        self.setup_sweep()  # Reinitialise with new frequency settings

        # Allow some time for the sweep to restart before initialising the plot
        QTimer.singleShot(100, self.initialise_plot)

    def closeEvent(self, event):
        self.hackrf_sweep.stop()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SpectrumAnalyser()
    window.show()
    sys.exit(app.exec())

