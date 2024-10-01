import sys
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets, uic, QtCore
from PyQt6.QtCore import Qt
from numpy.fft import fft
from logo import points  
import matplotlib as mpl
from matplotlib.ticker import EngFormatter
from menumanager import MenuManager
from datasources.rtlsdr_fft import RtlSdrDataSource
from datasources.hackrf_fft import HackRFDataSource
from datasources.hackrf_sweep import HackRFSweepDataSourceOld
from datasources.rtlsdr_sweep import RtlSweepDataSource
from datasources import DataSource, SweepDataSource

class MainWindow(QtWidgets.QMainWindow):
    CENTRE_FREQUENCY = 98e6
    INITIAL_SAMPLE_SIZE = 4096
    GAIN = 30
    AMPLIFIER = True
    LNA_GAIN = 10
    VGA_GAIN = 10

    sweep_data = None

    def __init__(self):
        super().__init__()

        # Load the UI file
        uic.loadUi('topdogspectrumanalysermainwindow.ui', self)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        # Create a PyQtGraph PlotWidget
        self.plot_widget = pg.PlotWidget()
        self.setup_layout()

        # Initialize MenuManager
        self.menu_manager = MenuManager()

        # Initialize data source
        self.data_source = None

        # Matplotlib formatter
        self.engformat = mpl.ticker.EngFormatter(places=3)

        # Start the timer for updating the plot
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)

        # Pause state
        self.is_paused = False

        # Connect the button to toggle hold
        self.buttonhold = self.findChild(QtWidgets.QPushButton, 'buttonhold')
        if self.buttonhold:
            self.buttonhold.pressed.connect(self.toggle_hold)

        # Initialize labels and buttons
        self.initialize_labels()
        self.initialize_buttons()

        # Set focus policy for all buttons
        self.setFocusPolicyForButtons(self)

        # Connect main buttons to their submenu functions
        self.connect_main_buttons()

        # Set initial button labels
        self.update_button_labels()

    def initialize_labels(self):
        """Initialize labels in the UI."""
        self.inputtext = self.findChild(QtWidgets.QLabel, 'inputtext')
        self.outputtext = self.findChild(QtWidgets.QLabel, 'outputtext')
        self.output_centre_freq = self.findChild(QtWidgets.QLabel, 'output_centre_freq')
        self.output_res_bw = self.findChild(QtWidgets.QLabel, 'output_res_bw')

    def initialize_buttons(self):
        """Initialize soft buttons."""
        self.buttonsoft1 = self.findChild(QtWidgets.QPushButton, 'buttonsoft1')
        self.buttonsoft2 = self.findChild(QtWidgets.QPushButton, 'buttonsoft2')
        self.buttonsoft3 = self.findChild(QtWidgets.QPushButton, 'buttonsoft3')
        self.buttonsoft4 = self.findChild(QtWidgets.QPushButton, 'buttonsoft4')
        self.buttonsoft5 = self.findChild(QtWidgets.QPushButton, 'buttonsoft5')
        self.buttonsoft6 = self.findChild(QtWidgets.QPushButton, 'buttonsoft6')
        self.buttonsoft7 = self.findChild(QtWidgets.QPushButton, 'buttonsoft7')
        self.buttonsoft8 = self.findChild(QtWidgets.QPushButton, 'buttonsoft8')

    def setFocusPolicyForButtons(self, parent):
        """Set focus policy for all QPushButton children."""
        for widget in parent.findChildren(QtWidgets.QPushButton):
            widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def connect_main_buttons(self):
        """Connect main buttons to their respective submenu functions."""
        self.buttonfrequency = self.findChild(QtWidgets.QPushButton, 'buttonfrequency')
        self.buttonfrequency.pressed.connect(lambda: self.show_submenu('frequency1'))

        self.buttonspan = self.findChild(QtWidgets.QPushButton, 'buttonspan')
        self.buttonspan.pressed.connect(lambda: self.show_submenu('span1'))

        self.buttonamplitude = self.findChild(QtWidgets.QPushButton, 'buttonamplitude')
        self.buttonamplitude.pressed.connect(lambda: self.show_submenu('amplitude1'))

        # Connect soft buttons
        self.buttonsoft1.pressed.connect(lambda: self.handle_soft_button(0))
        self.buttonsoft2.pressed.connect(lambda: self.handle_soft_button(1))
        self.buttonsoft3.pressed.connect(lambda: self.handle_soft_button(2))

        # Connect buttons to switch data source
        self.connect_data_source_buttons()

    def connect_data_source_buttons(self):
        """Connect buttons to switch data source."""
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

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F:
            print("Menu level: frequency1")
            self.show_submenu('frequency1')    
        elif event.key() == Qt.Key.Key_S:
            print("Menu level: span1")
            self.show_submenu('span1')
        elif event.key() == Qt.Key.Key_A:
            print("Menu level: amplitude1")
            self.show_submenu('amplitude1')     
        elif event.key() == Qt.Key.Key_Space:
            print("Toggle hold")
            self.toggle_hold()
        event.accept()

        # Display the logo as a static plot on startup
        self.display_logo()
        print("Waiting for user to select data source...")

    def setup_layout(self):
        layout = self.findChild(QtWidgets.QWidget, 'graphical_display').layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(self.findChild(QtWidgets.QWidget, 'graphical_display'))
        else:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        layout.addWidget(self.plot_widget)

    def display_logo(self):
        x_vals, y_vals = zip(*points)
        self.plot_widget.plot(x_vals, y_vals, pen=None, symbol='t', symbolBrush='b')

    def update_plot(self):
        if self.data_source and not self.is_paused:
            if isinstance(self.data_source, DataSource):
                try:
                    self.output_centre_freq.setText(self.engformat(self.data_source.sdr.center_freq) + " Hz")
                    self.output_res_bw.setText(self.engformat(self.data_source.sdr.sample_rate / self.INITIAL_SAMPLE_SIZE) + " Hz")

                    samples = self.data_source.read_samples(self.INITIAL_SAMPLE_SIZE)

                    if samples is not None and len(samples) > 0:
                        power_db = self.perform_fft(samples)
                        frequency_bins = np.linspace(0, self.data_source.sample_rate, len(power_db))
                        frequency_bins += (self.CENTRE_FREQUENCY - self.data_source.sample_rate / 2)

                        self.plot_widget.clear()
                        self.plot_widget.plot(frequency_bins / 1e6, power_db, pen='g')

                        self.plot_widget.setXRange(
                            self.CENTRE_FREQUENCY / 1e6 - (self.data_source.sample_rate / 2 / 1e6),
                            self.CENTRE_FREQUENCY / 1e6 + (self.data_source.sample_rate / 2 / 1e6)
                        )

                        index_of_peak = np.argmax(power_db)
                        peak_y_value = power_db[index_of_peak]
                        corresponding_x_value = frequency_bins[index_of_peak]
                        print("Peak value is " + str(peak_y_value))
                        print("At frequency  " + str(corresponding_x_value))

                except Exception as e:
                    print(f"Error reading samples: {e}")

            elif isinstance(self.data_source, SweepDataSource):
                if self.sweep_data is not None:
                    self.plot_widget.clear()
                    self.plot_widget.plot(self.sweep_data['x'], self.sweep_data['y'], pen='g')

                    index_of_peak = np.argmax(self.sweep_data['y'])
                    peak_y_value = self.sweep_data['y'][index_of_peak]
                    corresponding_x_value = self.sweep_data['x'][index_of_peak]
                    print("Peak value is " + str(peak_y_value))
                    print("At frequency  " + str(corresponding_x_value))

    def show_submenu(self, menu_name):
        self.menu_manager.show_submenu(menu_name)
        self.update_button_labels()

    def update_button_labels(self):
        labels = self.menu_manager.get_button_labels()
        buttons = [self.buttonsoft1, self.buttonsoft2, self.buttonsoft3, self.buttonsoft4,
                   self.buttonsoft5, self.buttonsoft6, self.buttonsoft7, self.buttonsoft8]
        
        for i, button in enumerate(buttons):
            if i < len(labels):
                button.setText(labels[i])
            else:
                button.setText('')

    def handle_soft_button(self, button_index):
        self.menu_manager.handle_button_press(button_index)
        self.update_button_labels()

    def perform_fft(self, samples):
        window = np.hamming(len(samples))
        windowed_samples = samples * window
        raw_fft = fft(windowed_samples)
        centred_fft = np.fft.fftshift(raw_fft)

        magnitude = np.abs(centred_fft)
        power_spectrum = magnitude ** 2
        log_magnitude = 10 * np.log10(power_spectrum + 1e-12)
        return log_magnitude

    def toggle_hold(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            print("Animation paused")
            self.buttonhold.setStyleSheet("background-color: #ff2222; color: white; font-weight: bold;")
        else:
            print("Animation resumed")
            self.buttonhold.setStyleSheet("background-color: #222222; color: white; font-weight: bold;")

    def use_rtl_source(self):
        print("Using RTL-SDR data source")
        self.data_source = RtlSdrDataSource(self.CENTRE_FREQUENCY)
        self.timer.start(20)

    def use_hackrf_source(self):
        print("Using HackRF data source")
        self.data_source = HackRFDataSource(self.CENTRE_FREQUENCY)
        self.timer.start(20)

    def use_rtl_sweep_source(self):
        print("Using RTL-SDR sweep data source")
        self.data_source = RtlSweepDataSource(self.CENTRE_FREQUENCY)
        self.timer.start(20)

    def use_hackrf_sweep_source(self):
        print("Using HackRF sweep data source")
        self.data_source = HackRFSweepDataSourceOld(start_freq=self.CENTRE_FREQUENCY - 1e6, 
                                                     stop_freq=self.CENTRE_FREQUENCY + 1e6)
        self.timer.start(20)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
