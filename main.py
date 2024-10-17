#!/usr/bin/python3
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
from datasources import SampleDataSource, SweepDataSource
import SignalProcessing
from PyQt6.QtWidgets import QStackedWidget
import threedimension
import twodimension
from typing import Union

class MainWindow(QtWidgets.QMainWindow):
    CENTRE_FREQUENCY = 98e6 #2412e6

    GAIN = 36.4  # where is this value used?
    AMPLIFIER = True
    LNA_GAIN = 10
    VGA_GAIN = 10
    sweep_data = None
    INITIAL_SAMPLE_SIZE = 1024
    INITIAL_NUMBER_OF_LINES = 20
    dsp = SignalProcessing.process()
    #data_source: DataSourceDataSource | SweepDataSource = None    # Only newer python
    data_source: Union[SampleDataSource, SweepDataSource] = None

    def __init__(self):
        super().__init__()
        
        self.peak_frequency1 = "Peak On"
        self.peak_power = None
        self.is_peak_on = False
        self.is_vertical = False
        
        # Load the UI file
        uic.loadUi('mainwindowhorizontal.ui', self)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        # Create stacked widget
        self.stacked_widget = QStackedWidget(self)

        # Create and configure 2D PlotWidget
        self.two_d_widget = twodimension.TwoD()
        
        # Create and configure 3D GLViewWidget
        self.three_d_widget = threedimension.ThreeD(self.INITIAL_SAMPLE_SIZE, self.INITIAL_NUMBER_OF_LINES)

        # Add both widgets to the stacked widget
        self.stacked_widget.addWidget(self.two_d_widget.widget)
        self.stacked_widget.addWidget(self.three_d_widget.widget)

        # Set the stacked widget as the main display layout
        layout = self.findChild(QtWidgets.QWidget, 'graphical_display')
        layout.layout().addWidget(self.stacked_widget)
        self.current_display = 'plot'
        self.stacked_widget.setCurrentIndex(0)  # Show 2D plot initially
        self.display_logo()

        self.power_db = None
        self.data_source = None
        self.engformat = mpl.ticker.EngFormatter(places=3)
        self.timer = QtCore.QTimer()    # timer for updating plot
        self.timer.timeout.connect(self.update_plot)
        self.is_paused = False
        self.menu_manager = MenuManager()
        

        if self.buttonhold:
            self.buttonhold.pressed.connect(self.toggle_hold)
        if self.buttonpeak:
            self.buttonpeak.pressed.connect(self.toggle_peak)
        if self.button2d3d:
            self.button2d3d.pressed.connect(self.toggle_display)
        if self.buttonverthoriz:
            self.buttonverthoriz.pressed.connect(self.toggle_orientation)

        self.initialise_labels()
        self.initialise_buttons()
        self.input_label.setText('Select data source')
        self.connect_data_source_buttons()
        self.set_button_focus_policy(self) # Avoids buttons being active after pressing
        self.connect_main_buttons()
        self.update_button_labels()

    def load_new_ui(self, ui_file):
        # Clear the existing layout
        layout = self.findChild(QtWidgets.QWidget, 'graphical_display').layout()
        if layout:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        # Load the new UI
        uic.loadUi(ui_file, self)

        # Initialize stacked widget and child widgets
        self.stacked_widget = QStackedWidget(self)

        # Create and configure 2D PlotWidget
        self.two_d_widget = twodimension.TwoD()

        # Create and configure 3D GLViewWidget
        self.three_d_widget = threedimension.ThreeD(self.INITIAL_SAMPLE_SIZE, self.INITIAL_NUMBER_OF_LINES)

        # Add both widgets to the stacked widget
        self.stacked_widget.addWidget(self.two_d_widget.widget)
        self.stacked_widget.addWidget(self.three_d_widget.widget)

        # Set the stacked widget as the main display layout
        new_layout = self.findChild(QtWidgets.QWidget, 'graphical_display')
        new_layout.layout().addWidget(self.stacked_widget)
        
        self.current_display = 'plot'
        self.stacked_widget.setCurrentIndex(0)  # Show 2D plot initially
        self.display_logo()

        # Reinitialize components
        self.initialise_labels()  # Reinitialize labels if they exist in the new UI
        self.initialise_buttons()  # Reinitialize buttons if they exist in the new UI
        self.connect_data_source_buttons()  # Reconnect data source buttons if necessary
        self.update_button_labels()  # Update button labels based on the new UI



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
        self.output_centre_freq = self.findChild(QtWidgets.QLabel, 'output_centre_freq')
        self.output_sample_rate = self.findChild(QtWidgets.QLabel, 'output_sample_rate')

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
        self.buttonpeak = self.findChild(QtWidgets.QPushButton, 'buttonpeak')
        self.button2d3d = self.findChild(QtWidgets.QPushButton, 'button2d3d')
        self.buttonfrequency = self.findChild(QtWidgets.QPushButton, 'buttonfrequency')
        self.buttonspan = self.findChild(QtWidgets.QPushButton, 'buttonspan')
        self.buttonamplitude = self.findChild(QtWidgets.QPushButton, 'buttonamplitude')
        self.buttonpreset = self.findChild(QtWidgets.QPushButton, 'buttonpreset')
        self.buttonverthoriz = self.findChild(QtWidgets.QPushButton, 'buttonverthoriz')
        self.buttonhold = self.findChild(QtWidgets.QPushButton, 'buttonhold')
        self.buttonpeak = self.findChild(QtWidgets.QPushButton, 'buttonpeak')

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
        if self.button_preset:
            self.button_preset.pressed.connect(self.preset)

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
        elif event.key() == Qt.Key.Key_P:
            print("Toggle peak")
            self.toggle_peak()
        elif event.key() == Qt.Key.Key_O:
            print("Toggle orientation")
            self.toggle_orientation()
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

    def toggle_display(self):
        if self.current_display == 'plot':
            self.stacked_widget.setCurrentIndex(1)  # Show 3D display
            self.current_display = 'gldisplay'
            self.three_d_widget.start_animation()
            
        else:
            self.stacked_widget.setCurrentIndex(0)  # Show 2D plot
            self.three_d_widget.stop_animation()
            self.current_display = 'plot'
            self.timer.timeout.connect(self.update_plot)

    def display_logo(self):
        x_vals, y_vals = zip(*points)
        self.two_d_widget.widget.plot(x_vals, y_vals, pen=None, symbol='t', symbolBrush='b')
        print ("display logo")

    def update_plot(self):
        if self.data_source and not self.is_paused:
            #print (self.data_source.centre_freq)

            if isinstance(self.data_source, SampleDataSource):
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
                        

                        
                        if isinstance(self.data_source, AudioDataSource):
                            centrefft = fft[:int(self.INITIAL_SAMPLE_SIZE//2)]
                            magnitude = self.dsp.get_magnitude(centrefft)
                            self.power_db  = self.dsp.get_log_magnitude(magnitude)
                            frequency_bins = np.linspace(0, self.data_source.sample_rate, len(self.power_db))
                            half_length = len(frequency_bins) // 2  # Calculate half length
                            frequency_bins = frequency_bins[:half_length]
                            self.power_db = self.power_db[:half_length]
 

                        else:
                            centrefft = self.dsp.do_centre_fft(fft)                   
                            magnitude = self.dsp.get_magnitude(centrefft)
                            self.power_db  = self.dsp.get_log_magnitude(magnitude)
                            frequency_bins = np.linspace(0, self.data_source.sample_rate, len(self.power_db))
                            frequency_bins += (self.CENTRE_FREQUENCY - self.data_source.sample_rate / 2)

                        if self.current_display == 'plot':
                            self.two_d_widget.widget.clear()
                            self.two_d_widget.widget.plot(frequency_bins / 1e6, self.power_db, pen='g')
                        
                        # Set values in 3d widget
                        self.three_d_widget.z=self.power_db/10
 
                except Exception as e:
                    print(f"Error reading samples: {e}")

            elif isinstance(self.data_source, SweepDataSource):
                if self.sweep_data is not None:
                    self.two_d_widget.plot(self.sweep_data['x'], self.sweep_data['y'], pen='g')
                    index_of_peak = np.argmax(self.sweep_data['y'])
                    peak_y_value = self.sweep_data['y'][index_of_peak]
                    corresponding_x_value = self.sweep_data['x'][index_of_peak]
                    print("Peak value is " + str(peak_y_value))
                    print("At frequency  " + str(corresponding_x_value))
                    text_item = pg.TextItem(str(self.engformat(corresponding_x_value)) + "Hz\n" + str(self.engformat(peak_y_value) + " dB"  ))
                    text_item.setPos(corresponding_x_value / 1e6, peak_y_value)  

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


    def toggle_peak(self):
        self.is_peak_on = not self.is_peak_on
        if self.is_peak_on:
            print("Peak on")
            self.peak_frequency1 = pg.TextItem("Peak on")
            self.two_d_widget.widget.addItem(self.peak_frequency1)
        else:
            print("Peak off")
            self.two_d_widget.widget.removeItem(self.peak_frequency1)

    def toggle_hold(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            print("Animation paused")
            self.buttonhold.setStyleSheet("background-color: #ff2222; color: white; font-weight: bold;")
        else:
            print("Animation resumed")
            self.buttonhold.setStyleSheet("background-color: #222222; color: white; font-weight: bold;")

    def toggle_orientation(self):
        print ("toggle orientation")
        self.is_vertical = not self.is_vertical
        if self.is_vertical:
            print("Changing orientation to vertical")
            self.load_new_ui('mainwindowvertical.ui')
            
        else:
            print("Changing orientation to horizontal")
            self.load_new_ui('mainwindowhorizontal.ui')  

    def load_new_ui(self, ui_file):
        # Clear the existing layout
        layout = self.findChild(QtWidgets.QWidget, 'graphical_display').layout()
        if layout:
            while layout.count():
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

        uic.loadUi(ui_file, self)

        
        self.initialise_labels()  
        self.initialise_buttons() 
        self.setup_layout()  
        self.connect_data_source_buttons()  
        self.update_button_labels()  

    def use_rtl_source(self):     
        print("Using RTL-SDR data source")
        self.input_label.setText('Starting RTL device')
        self.button_instrument4.setStyleSheet("background-color: #a0a0a0; color: black; font-weight: normal;")
        self.button_instrument8.setStyleSheet("background-color: #ffffff; color: black; font-weight: normal;")
        self.button_instrument9.setStyleSheet("background-color: #ffffff; color: black; font-weight: normal;")
        app.processEvents()
        self.data_source = RtlSdrDataSource(self.CENTRE_FREQUENCY)
        self.window = self.dsp.create_window(self.data_source.sample_rate, 'hamming')
        self.input_label.setText('RTL device running')
        self.timer.start(20)

    def use_audio_source(self):
        print("Using audio data source")
        self.button_instrument4.setStyleSheet("background-color: #ffffff; color: black; font-weight: normal;")
        self.button_instrument8.setStyleSheet("background-color: #a0a0a0; color: black; font-weight: normal;")
        self.button_instrument9.setStyleSheet("background-color: #ffffff; color: black; font-weight: normal;")
        self.sample_rate=44100
        self.data_source = AudioDataSource()
        self.window = self.dsp.create_window(self.data_source.sample_rate, 'hamming')

        self.timer.start(20)

    def use_hackrf_source(self):
        print("Using HackRF data source")
        self.button_instrument8.setStyleSheet("background-color: #ffffff; color: black; font-weight: normal;")
        self.button_instrument9.setStyleSheet("background-color: #a0a0a0; color: black; font-weight: normal;")
        self.button_instrument4.setStyleSheet("background-color: #ffffff; color: black; font-weight: normal;")
        self.data_source = HackRFDataSource(self.CENTRE_FREQUENCY)
        self.input_label.setText('HackRF FFT device running')
        self.timer.start(20)

    def use_rtl_sweep_source(self):
        print("Using RTL-SDR sweep data source")
        self.data_source = RtlSweepDataSource(self.CENTRE_FREQUENCY)
        self.timer.start(20)

    def preset(self):
        self.two_d_widget.widget.getPlotItem().autoRange()
        

    def use_hackrf_sweep_source(self):
        print("Using HackRF sweep data source")
        
        def my_sweep_callback(data):
        # Process the sweep data here
            print("Sweep data received:", data)
        
        self.data_source = HackRFSweepDataSourceOld(start_freq=self.CENTRE_FREQUENCY - 1e6, 
                                                     stop_freq=self.CENTRE_FREQUENCY + 1e6)
        self.timer.start(20)

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    #window.showMaximized()
    window.show()
    sys.exit(app.exec())
