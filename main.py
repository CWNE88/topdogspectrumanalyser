import sys
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets, uic, QtCore
import signal
 
from numpy.fft import fft
from logo import points  

from datasources.rtlsdr_fft import RtlSdrDataSource
from datasources.hackrf_fft import HackRFDataSource
from datasources.hackrf_sweep import HackRFSweepDataSourceOld
from datasources.rtlsdr_sweep import RtlSweepDataSource
from datasources import DataSource, SweepDataSource

datasources = [
    RtlSdrDataSource,
    HackRFDataSource,
]

class MainWindow(QtWidgets.QMainWindow):
    CENTRE_FREQUENCY = 98e6
    INITIAL_SAMPLE_SIZE = 2048
    GAIN = 30
    AMPLIFIER = True
    LNA_GAIN = 10
    VGA_GAIN = 10

    sweep_data = None

    def __init__(self):
        super().__init__()

        # Load the UI file
        uic.loadUi('topdogspectrumanalysermainwindow.ui', self)

        # Create a PyQtGraph PlotWidget
        self.plot_widget = pg.PlotWidget()
        # self.curve = self.plot_widget.plot(pen='y')
        self.setup_layout()

        # Initially, no data source
        self.data_source = None
     
        # Menu level
        self.menu_level = None
     
        # Start the timer for updating the plot, but don't start yet
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)

        # Initialise pause state
        self.is_paused = False

        # Connect the button to toggle pause/resume
        self.buttonhold = self.findChild(QtWidgets.QPushButton, 'buttonhold')
        if self.buttonhold:
            self.buttonhold.pressed.connect(self.toggle_pause)
         
        self.buttonfrequency = self.findChild(QtWidgets.QPushButton, 'buttonfrequency')
        self.buttonfrequency.pressed.connect(self.menu_frequency1)

        self.buttonspan = self.findChild(QtWidgets.QPushButton, 'buttonspan')
        self.buttonspan.pressed.connect(self.menu_span1)
        
        self.buttonamplitude = self.findChild(QtWidgets.QPushButton, 'buttonamplitude')
        self.buttonamplitude.pressed.connect(self.menu_amplitude1)
        
        self.buttonsoft1 = self.findChild(QtWidgets.QPushButton, 'buttonsoft1')
        self.buttonsoft1.pressed.connect(self.softbutton1)

        self.inputtext = self.findChild(QtWidgets.QLabel, 'inputtext')
        self.outputtext = self.findChild(QtWidgets.QLabel, 'outputtext')

        # Connect buttons to switch data source
        
        self.button_instrument4 = self.findChild(QtWidgets.QPushButton, 'buttoninstrument4')
        self.button_instrument9 = self.findChild(QtWidgets.QPushButton, 'buttoninstrument9')
        self.button_instrument5 = self.findChild(QtWidgets.QPushButton, 'buttoninstrument5')
        self.button_instrument10 = self.findChild(QtWidgets.QPushButton, 'buttoninstrument10')

        if self.button_instrument4:
            self.button_instrument4.pressed.connect(self.use_rtl_source)
        if self.button_instrument9:
            self.button_instrument9.pressed.connect(self.use_hackrf_source)
        if self.button_instrument5:
            self.button_instrument5.pressed.connect(self.use_rtl_sweep_source)
        if self.button_instrument10:
            self.button_instrument10.pressed.connect(self.use_hackrf_sweep_source)            

        # Display the logo as a static plot on startup
        self.display_logo()

        print("Waiting for user to select data source...")

    def setup_layout(self):
        # Clear existing layout items
        layout = self.findChild(QtWidgets.QWidget, 'graphical_display').layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(self.findChild(QtWidgets.QWidget, 'graphical_display'))
        else:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        # Add the PlotWidget to the layout
        layout.addWidget(self.plot_widget)

    def display_logo(self):
        x_vals, y_vals = zip(*points)  # Unpack the points into x and y values
        self.plot_widget.plot(x_vals, y_vals, pen=None, symbol='o', symbolBrush='b')  # Plot points in red

    def update_plot(self):
        if self.data_source and not self.is_paused:
            if isinstance(self.data_source, DataSource):  # Only update if data source is selected and not paused
                try:

                    samples = self.data_source.read_samples(self.INITIAL_SAMPLE_SIZE)
                    if samples is not None and len(samples) > 0:
                        power_level = self.perform_fft(samples)

                        # Update frequency bins based on the current sample rate
                        frequency_bins = np.linspace(0, self.data_source.sample_rate, len(power_level))
                        frequency_bins += (self.CENTRE_FREQUENCY - self.data_source.sample_rate / 2)  # Center the frequency

                        # Update the plot
                        self.plot_widget.clear()
                        self.plot_widget.plot(frequency_bins / 1e6, power_level, pen='g')  # Frequency in MHz

                        # Adjust the X axis range to centre around the centre frequency
                        self.plot_widget.setXRange(self.CENTRE_FREQUENCY / 1e6 - (self.data_source.sample_rate / 2 / 1e6),
                                                    self.CENTRE_FREQUENCY / 1e6 + (self.data_source.sample_rate / 2 / 1e6))
                except Exception as e:
                    print(f"Error reading samples: {e}")
            elif isinstance(self.data_source, SweepDataSource):
                if self.sweep_data is not None:
                    self.plot_widget.clear()
                    self.plot_widget.plot(self.sweep_data['x'], self.sweep_data['y'], pen='g')

    def perform_fft(self, samples):
        window = np.hamming(len(samples))
        windowed_samples = samples * window
        raw_fft = fft(windowed_samples)
        centred_fft = np.fft.fftshift(raw_fft)
        magnitude = np.abs(centred_fft)
        log_magnitude = np.log10(magnitude + 1e-12)
        return log_magnitude

    def menu_frequency1(self):
        self.buttonsoft1.setText("Centre\nFrequency")
        self.buttonsoft2.setText("Start\nFrequency")
        self.buttonsoft3.setText("Stop\nFrequency")
        self.buttonsoft4.setText("CF Step\nAuto/Man")
        self.buttonsoft5.setText("Frequency\nOffset")
        self.buttonsoft6.setText("Centre Freq /2\n to Centre Freq")
        self.buttonsoft7.setText("Centre Freq x2\n to Centre Freq")
        self.buttonsoft8.setText("")
        self.menu_level="frequency1"

    def menu_span1(self):
        self.buttonsoft1.setText("Span")
        self.buttonsoft2.setText("Span Zoom")        
        self.buttonsoft3.setText("Full Span")
        self.buttonsoft4.setText("Zero Span")
        self.buttonsoft5.setText("Last Span")
        self.buttonsoft6.setText("")
        self.buttonsoft7.setText("")
        self.buttonsoft8.setText("")
        
    def menu_amplitude1(self):
        self.buttonsoft1.setText("Reference\nLevel")
        self.buttonsoft2.setText("Attenuation\nAuto/Man")        
        self.buttonsoft3.setText("Log\ndB/Division")
        self.buttonsoft4.setText("Zero Span")
        self.buttonsoft5.setText("Linear")
        self.buttonsoft6.setText("Range\nLevel")
        self.buttonsoft7.setText("Ref Level\nOffset")
        self.buttonsoft8.setText("More\n1 of 2")
    
    def menu_amplitude2(self):
        self.buttonsoft1.setText("Max MXR\nLevel")
        self.buttonsoft2.setText("Amplitude\nUnits")
        self.buttonsoft3.setText("Coupling\nAC/DC")
        self.buttonsoft4.setText("Norm Ref\nPosition")
        self.buttonsoft5.setText("Preselect\nAuto Peak")
        self.buttonsoft6.setText("Preselect\nManual Adj")
        self.buttonsoft7.setText("")
        self.buttonsoft8.setText("More\n2 of 2")
    
    def softbutton1(self):
        print("Soft button 1 pressed")
        if self.menu_level=="frequency1":
            print("Centre Frequency")
            self.inputtext.setText('Centre Frequency:')
 

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            print("Animation paused")
            self.buttonhold.setStyleSheet("background-color: #ff2222; color: white; font-weight: bold;")
        else:
            print("Animation resumed")
            self.buttonhold.setStyleSheet("background-color: #222222; color: white; font-weight: bold;")

    def use_rtl_source(self):
        """Switch to RTL-SDR data source."""
        print("Switching to RTL-SDR data source")
        self.switch_data_source(RtlSdrDataSource)

    def use_hackrf_source(self):
        """Switch to HackRF data source."""
        print("Switching to HackRF data source")
        self.switch_data_source(HackRFDataSource)

    def use_rtl_sweep_source(self):
        """Switch to RTL Sweep data source."""
        print("Switching to RTL Sweep data source")
        self.switch_data_source(RtlSweepDataSource)

    def use_hackrf_sweep_source(self):
        """Switch to HackRF Sweep data source."""
        print("Switching to HackRF Sweep data source")
        self.switch_data_source(HackRFSweepDataSourceOld)



    def switch_data_source(self, source_class):
        """General method to switch any data source and resume animation if it was paused."""
    
        # Check if the current data source is already of the requested type
        if self.data_source and isinstance(self.data_source, source_class):
            print(f"{source_class.__name__} is already active, no need to switch.")
            return  # Do nothing if the data source is already active

        # Clean up the current data source
        if self.data_source:
            self.data_source.cleanup()
            QtCore.QThread.sleep(1)  # Brief pause to ensure cleanup

        # Initialize the new data source with appropriate parameters
        if issubclass(source_class, HackRFDataSource):
            self.data_source = source_class(
                self.CENTRE_FREQUENCY, 
                sample_rate=20e6, 
                amplifier=self.AMPLIFIER, 
                lna_gain=self.LNA_GAIN, 
                vga_gain=self.VGA_GAIN
            )
        elif issubclass(source_class, RtlSdrDataSource) or issubclass(source_class, RtlSweepDataSource):
            self.data_source = source_class(
                self.CENTRE_FREQUENCY, 
                sample_rate=2e6, 
                gain=self.GAIN
            )
        elif issubclass(source_class, HackRFSweepDataSourceOld):
            self.data_source = source_class(
                on_sweep_callback=self.on_sweep,
                start_freq=2.4e9,
                stop_freq=2.5e9,
                bin_size=10e3
            )
        else:
            print(f"Unsupported data source: {source_class.__name__}")
            return

        # Resume the animation if it was paused
        if self.is_paused:
            self.toggle_pause()  # Unpause if paused

        # Reset the plot to use the new data source
        self.reset_plot()

    def on_sweep(self, data):
        self.sweep_data = data

    def reset_plot(self):
        """Reset the plot and start updating with the new data source."""
        self.plot_widget.clear()  # Clear the current plot
        self.timer.start(20)  # Restart the timer (if it was stopped)


if __name__ == '__main__':

    def signal_handler(sig, frame):
        app.quit()

    app = QtWidgets.QApplication(sys.argv)
    signal.signal(signal.SIGINT, signal_handler)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

