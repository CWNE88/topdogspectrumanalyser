import sys
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets, uic, QtCore
from pyqtgraph.Qt import QtCore, QtGui
from PyQt6.QtCore import Qt
import pyqtgraph.opengl as gl
from numpy.fft import fft
from logo import points  
import matplotlib as mpl
from matplotlib.ticker import EngFormatter
from menumanager import MenuManager
from datasources.rtlsdr_fft import RtlSdrDataSource
from datasources.hackrf_fft import HackRFDataSource
from datasources.hackrf_sweep import HackRFSweepDataSourceOld
from datasources.rtlsdr_sweep import RtlSweepDataSource
from datasources.audio_fft import AudioDataSource
from datasources import DataSource, SweepDataSource
import SignalProcessing
from PyQt6.QtWidgets import QStackedWidget
import threedimension

class MainWindow(QtWidgets.QMainWindow):
    CENTRE_FREQUENCY = 98e6
    INITIAL_SAMPLE_SIZE = 4096*2
    GAIN = 36.4  # where is this value used?
    AMPLIFIER = True
    LNA_GAIN = 10
    VGA_GAIN = 10
    sweep_data = None
    dsp = SignalProcessing.process()
    data_source: DataSource | SweepDataSource = None

    def __init__(self):
        super().__init__()

        # Load the UI file
        uic.loadUi('topdogspectrumanalysermainwindow.ui', self)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.stacked_widget = QStackedWidget(self)  # sounds like a widget with big tits
        
        # Create and configure 2D PlotWidget
        self.two_d_widget = pg.PlotWidget()
        self.two_d_widget.showGrid(x=True, y=True)
        self.two_d_widget.setLabel('left', 'Power (dB)')
        self.two_d_widget.setLabel('bottom', 'Frequency (Mhz)')
        self.two_d_widget.setYRange(-30, 60)
 
        # Create and configure 3D GLViewWidget
        self.fancywidget = threedimension.ThreeD()
        self.three_d_widget = self.fancywidget.get_widget()

        # Add both widgets to the stacked widget
        self.stacked_widget.addWidget(self.two_d_widget)
        self.stacked_widget.addWidget(self.three_d_widget)

        # Set the stacked widget as the main display layout
        layout = self.findChild(QtWidgets.QWidget, 'graphical_display')
        layout.layout().addWidget(self.stacked_widget)

        # Set the initial display
        self.current_display = 'plot'
        self.stacked_widget.setCurrentIndex(0)  # Show 2D plot initially
        self.display_logo()

        self.menu_manager = MenuManager()
        self.data_source = None
        self.engformat = mpl.ticker.EngFormatter(places=3)
        self.timer = QtCore.QTimer()    # timer for updating plot
        self.timer.timeout.connect(self.update_plot)
        self.is_paused = False

        if self.buttonhold:
            self.buttonhold.pressed.connect(self.toggle_hold)

        if self.button2d3d:
            self.button2d3d.pressed.connect(self.toggle_display)

        self.initialise_labels()
        self.initialise_buttons()
        self.input_label.setText('Select data source')
        self.connect_data_source_buttons()
        self.set_button_focus_policy(self) # Avoids buttons being active after pressing
        self.connect_main_buttons()
        self.update_button_labels()

    def initialise_labels(self):
        self.output_centre_freq = self.findChild(QtWidgets.QLabel, 'output_centre_freq')
        self.output_sample_rate = self.findChild(QtWidgets.QLabel, 'output_sample_rate')
        self.output_span = self.findChild(QtWidgets.QLabel, 'output_span')
        self.output_start_freq = self.findChild(QtWidgets.QLabel, 'output_start_freq')
        self.output_stop_freq = self.findChild(QtWidgets.QLabel, 'output_stop_freq')
        self.output_gain = self.findChild(QtWidgets.QLabel, 'output_gain')
        self.output_gain = self.findChild(QtWidgets.QLabel, 'output_gain')
        self.output_res_bw = self.findChild(QtWidgets.QLabel, 'output_res_bw')
        self.input_value = self.findChild(QtWidgets.QLabel, 'input_value')

    def initialise_buttons(self):
        self.buttonsoft1 = self.findChild(QtWidgets.QPushButton, 'buttonsoft1')
        self.buttonsoft2 = self.findChild(QtWidgets.QPushButton, 'buttonsoft2')
        self.buttonsoft3 = self.findChild(QtWidgets.QPushButton, 'buttonsoft3')
        self.buttonsoft4 = self.findChild(QtWidgets.QPushButton, 'buttonsoft4')
        self.buttonsoft5 = self.findChild(QtWidgets.QPushButton, 'buttonsoft5')
        self.buttonsoft6 = self.findChild(QtWidgets.QPushButton, 'buttonsoft6')
        self.buttonsoft7 = self.findChild(QtWidgets.QPushButton, 'buttonsoft7')
        self.buttonsoft8 = self.findChild(QtWidgets.QPushButton, 'buttonsoft8')
        self.buttonhold = self.findChild(QtWidgets.QPushButton, 'buttonhold')
        self.button2d3d = self.findChild(QtWidgets.QPushButton, 'button2d3d')
        self.buttonfrequency = self.findChild(QtWidgets.QPushButton, 'buttonfrequency')
        self.buttonspan = self.findChild(QtWidgets.QPushButton, 'buttonspan')
        self.buttonamplitude = self.findChild(QtWidgets.QPushButton, 'buttonamplitude')

    def set_button_focus_policy(self, parent):
        for widget in parent.findChildren(QtWidgets.QPushButton):
            widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def connect_main_buttons(self):
        self.buttonfrequency.pressed.connect(lambda: self.handle_menu_button('frequency1'))
        self.buttonspan.pressed.connect(lambda: self.handle_menu_button('span1'))
        self.buttonamplitude.pressed.connect(lambda: self.handle_menu_button('amplitude1'))
        self.buttonsoft1.pressed.connect(lambda: self.handle_soft_button(0))
        self.buttonsoft2.pressed.connect(lambda: self.handle_soft_button(1))
        self.buttonsoft3.pressed.connect(lambda: self.handle_soft_button(2))
        self.buttonmode.pressed.connect(lambda: self.handle_menu_button('mode1'))
        
    def connect_data_source_buttons(self):
        self.button_preset = self.findChild(QtWidgets.QPushButton, 'buttonpreset')
        self.button_mode = self.findChild(QtWidgets.QPushButton, 'buttonmode')
        self.button_instrument4 = self.findChild(QtWidgets.QPushButton, 'buttoninstrument4')
        self.button_instrument8 = self.findChild(QtWidgets.QPushButton, 'buttoninstrument8')
        self.button_instrument9 = self.findChild(QtWidgets.QPushButton, 'buttoninstrument9')
        self.button_instrument5 = self.findChild(QtWidgets.QPushButton, 'buttoninstrument5')
        self.button_instrument10 = self.findChild(QtWidgets.QPushButton, 'buttoninstrument10')
        
        if self.button_instrument4:
            self.button_instrument4.pressed.connect(self.use_rtl_source)
        if self.button_instrument8:
            self.button_instrument8.pressed.connect(self.use_audio_source)
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

    def setup_layout(self):
        layout = self.findChild(QtWidgets.QWidget, 'graphical_display').layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(self.findChild(QtWidgets.QWidget, 'graphical_display'))
        else:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        layout.addWidget(self.two_d_widget)  # Default to the 2D plot

    def toggle_display(self):
        if self.current_display == 'plot':
            self.stacked_widget.setCurrentIndex(1)  # Show 3D display
            self.current_display = 'gldisplay'
            self.fancywidget.start_animation()
        else:
            self.stacked_widget.setCurrentIndex(0)  # Show 2D plot
            self.fancywidget.stop_animation()
            self.current_display = 'plot'

    def display_logo(self):
        x_vals, y_vals = zip(*points)
        self.two_d_widget.plot(x_vals, y_vals, pen=None, symbol='t', symbolBrush='b')
        print ("display logo")

        text_item = pg.TextItem("in the logo method")
        text_item.setAnchor((0, 0))
        self.two_d_widget.addItem(text_item)

    def update_plot(self):
        if self.data_source and not self.is_paused:
            if isinstance(self.data_source, DataSource):
                try:
                    self.output_centre_freq.setText(self.engformat(self.data_source.centre_freq) + "Hz")
                    self.output_sample_rate.setText(f"{int(self.data_source.sample_rate):,} SPS")
                    self.output_start_freq.setText(self.engformat(self.data_source.centre_freq - self.data_source.sample_rate / 2) + "Hz")
                    self.output_stop_freq.setText(self.engformat(self.data_source.centre_freq + self.data_source.sample_rate / 2) + "Hz")
                    self.output_span.setText(self.engformat(self.data_source.sample_rate) + "Hz")
                    self.output_gain.setText(str(self.data_source.gain) + " dB")
                    self.output_res_bw.setText(self.engformat(self.data_source.sample_rate / self.INITIAL_SAMPLE_SIZE) + " Hz")
                    self.output_sample_size.setText(str(self.INITIAL_SAMPLE_SIZE))

                    samples = self.data_source.read_samples(self.INITIAL_SAMPLE_SIZE)

                    if samples is not None and len(samples) > 0:
                        fft = self.dsp.do_fft(samples)
                        centrefft = self.dsp.do_centre_fft(fft)
                        magnitude = self.dsp.get_magnitude(centrefft)
                        power_db  = self.dsp.get_log_magnitude(magnitude)

                        frequency_bins = np.linspace(0, self.data_source.sample_rate, len(power_db))
                        frequency_bins += (self.CENTRE_FREQUENCY - self.data_source.sample_rate / 2)


                        index_of_peak = np.argmax(power_db)
                        peak_y_value = power_db[index_of_peak]
                        corresponding_x_value = frequency_bins[index_of_peak]

                        text_item = pg.TextItem(self.engformat(peak_y_value) + " dB")
                        text_item.setPos(corresponding_x_value / 1e6, peak_y_value)  

                        if self.current_display == 'plot':
                            self.two_d_widget.clear()
                            self.two_d_widget.plot(frequency_bins / 1e6, power_db, pen='g')
                            self.two_d_widget.addItem(text_item)
                            
                            #Automatic x range, disabled for now
                            #self.two_d_widget.setXRange(
                            #    self.CENTRE_FREQUENCY / 1e6 - (self.data_source.sample_rate / 2 / 1e6),
                            #    self.CENTRE_FREQUENCY / 1e6 + (self.data_source.sample_rate / 2 / 1e6)
                            #)

                except Exception as e:
                    print(f"Error reading samples: {e}")

            elif isinstance(self.data_source, SweepDataSource):
                if self.sweep_data is not None:
                    #self.two_d_widget.clear()
                    self.two_d_widget.plot(self.sweep_data['x'], self.sweep_data['y'], pen='g')

                    index_of_peak = np.argmax(self.sweep_data['y'])
                    peak_y_value = self.sweep_data['y'][index_of_peak]
                    corresponding_x_value = self.sweep_data['x'][index_of_peak]
                    print("Peak value is " + str(peak_y_value))
                    print("At frequency  " + str(corresponding_x_value))

    def show_submenu(self, menu_name):
        self.menu_manager.show_submenu(menu_name)
        self.update_button_labels()

    def print_current_menu(self, menu_name):
        print(f"Current menu level: {menu_name}")

    def handle_menu_button(self, menu_name):
        self.show_submenu(menu_name)
        self.print_current_menu(menu_name)
        if menu_name == 'frequency1':
            self.input_label.setText('Centre Frequency:')
        if menu_name == 'span1':
            self.input_label.setText('Span:')
        if menu_name == 'amplitude1':
            self.input_label.setText('Amplitude:')

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
        self.input_label.setText('Starting RTL device')
        self.button_instrument4.setStyleSheet("background-color: #a0a0a0; color: black; font-weight: normal;")
        self.button_instrument9.setStyleSheet("background-color: #ffffff; color: black; font-weight: normal;")
        app.processEvents()
        self.data_source = RtlSdrDataSource(self.CENTRE_FREQUENCY)
        self.window = self.dsp.create_window(self.data_source.sample_rate, 'hamming')
        self.input_label.setText('RTL device running')
        self.timer.start(20)

    def use_audio_source(self):
        print("Using audio data source")
        self.data_source = AudioDataSource(self.CENTRE_FREQUENCY)
        self.window = self.dsp.create_window(self.data_source.sample_rate, 'hamming')
        self.timer.start(20)

    def use_hackrf_source(self):
        print("Using HackRF data source")
        self.button_instrument9.setStyleSheet("background-color: #a0a0a0; color: black; font-weight: normal;")
        self.button_instrument4.setStyleSheet("background-color: #ffffff; color: black; font-weight: normal;")
        self.data_source = HackRFDataSource(self.CENTRE_FREQUENCY)
        self.input_label.setText('HackRF FFT device running')
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
    #window.showMaximized()
    window.show()
    sys.exit(app.exec())
