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
        self.hackrf_sweep.setup(start_freq=5000, stop_freq=6000, bin_size=3000)
        self.hackrf_sweep.run()  # Start the sweep

        self.number_of_points = self.hackrf_sweep.get_number_of_points()
        while self.number_of_points == 0:
            time.sleep(0.1)
            
            self.number_of_points = self.hackrf_sweep.get_number_of_points()
            print    ("numberofpoints is ", str(self.number_of_points))
            

        


        # 2D plot for spectrum display
        self.plot_widget = pg.PlotWidget()
        self.setCentralWidget(self.plot_widget)
        self.plot_widget.setTitle("Spectrum Analyzer")
        self.plot_widget.setLabel('left', 'Amplitude')
        self.plot_widget.setLabel('bottom', 'Frequency (MHz)')

        # Set fixed Y-axis range
        self.plot_widget.setYRange(0, self.MAX_AMPLITUDE)

        # Frequency bins for plotting
        self.frequency_bins = np.linspace(self.hackrf_sweep.start_freq, self.hackrf_sweep.stop_freq, self.number_of_points) 
        self.curve = self.plot_widget.plot(pen='y')

        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        print ("something")
        self.timer.start(20)  # More frequent updates

    def update(self):
        # Get power levels directly from HackRFSweep
        self.power_levels = self.hackrf_sweep.get_data()
        #print (str(self.power_levels))
        
        # Ensure power_levels matches the expected size
        if len(self.power_levels) != len(self.frequency_bins):
            print(f"Warning: power_levels length {len(self.power_levels)} does not match frequency_bins length {len(self.frequency_bins)}. Trimming data.")
            self.power_levels = self.power_levels[:len(self.frequency_bins)]  # Trim to match frequency_bins size
        
        # Limit the amplitude to MAX_AMPLITUDE
        #self.power_levels = np.clip(self.power_levels, 0, self.MAX_AMPLITUDE)

        # Update the plot
        #print (str(self.frequency_bins))
        #print (str(self.power_levels))
        self.curve.setData(self.frequency_bins, self.power_levels)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SpectrumAnalyser()
    window.show()
    sys.exit(app.exec())
