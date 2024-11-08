#!/usr/bin/python3
import sys
import datetime
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets, uic, QtCore
from PyQt6.QtCore import Qt
from input_hackrf_sweep import HackRFSweep
import twodimension
import threedimension
import waterfall
import boxes

from PyQt6.QtWidgets import QStackedWidget

class MainWindow(QtWidgets.QMainWindow):
   

    def __init__(self):
        super().__init__()

        uic.loadUi("mainwindowhorizontal.ui", self)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.start_freq = 2.4e9
        self.stop_freq = 2.5e9
        self.bin_size = 10e3
        
        self.two_d_widget = twodimension.TwoD()
        self.three_d_widget = threedimension.ThreeD()
        self.waterfall_widget = waterfall.Waterfall()
        self.boxes_widget = boxes.Boxes()


        self.stacked_widget = QStackedWidget(self)
        self.stacked_widget.addWidget(self.two_d_widget)
        self.stacked_widget.addWidget(self.three_d_widget)
        self.stacked_widget.addWidget(self.waterfall_widget)
        self.stacked_widget.addWidget(self.boxes_widget)

        graphical_display_widget = self.findChild(QtWidgets.QWidget, "graphical_display")
        graphical_display_widget.layout().addWidget(self.stacked_widget)

        self.current_stacked_index = 0
        self.stacked_widget.setCurrentIndex(self.current_stacked_index)


        self.hackrf_sweep = HackRFSweep()
        self.hackrf_sweep.setup(start_freq=self.start_freq, stop_freq=self.stop_freq, bin_size=self.bin_size)
        self.hackrf_sweep.run()

        self.power_levels = None
        self.max_hold_levels = None
        self.frequency_bins = None

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(20)

        self.initialise_buttons()
 
        self.connect_buttons()


    def initialise_buttons(self):
        button_names = [
            "button_soft_1", "button_soft_2", "button_soft_3", "button_soft_4", "button_soft_5", "button_soft_6",
            "button_soft_7", "button_soft_8", "button_hold", "button_2d", "button_3d", "button_waterfall", 
            "button_max_hold", "button_peak_search", "button_input_1", "button_input_2", "button_frequency", 
            "button_span", "button_amplitude", "button_preset", "button_mode", "button_export_image",
            "button_ghz", "button_mhz", "button_khz", "button_hz", "button_boxes"
        ]
        self.buttons = {name: self.findChild(QtWidgets.QPushButton, name) for name in button_names}



    def connect_buttons(self):
        button_actions = {
            "button_frequency": lambda: self.handle_menu_button("Frequency"),
            "button_span": lambda: self.handle_menu_button("Span"),
            "button_amplitude": lambda: self.handle_menu_button("Amplitude"),
            "button_soft_1": lambda: self.handle_soft_button(0),
            "button_soft_2": lambda: self.handle_soft_button(1),
            "button_soft_3": lambda: self.handle_soft_button(2),
            "button_soft_4": lambda: self.handle_soft_button(3),
            "button_soft_5": lambda: self.handle_soft_button(4),
            "button_soft_6": lambda: self.handle_soft_button(5),
            "button_soft_7": lambda: self.handle_soft_button(6),
            "button_soft_8": lambda: self.handle_soft_button(7),
            "button_mode": lambda: self.handle_menu_button("Mode"),
            "button_preset": lambda: self.preset(),
            "button_max_hold": lambda: self.toggle_max_hold(),
            "button_hold": lambda: self.toggle_hold(),
            "button_peak_search": lambda: self.toggle_peak(),
            "button_2d": lambda: self.set_display(0),
            "button_3d": lambda: self.set_display(1),
            "button_waterfall": lambda: self.set_display(2),
            "button_boxes": lambda: self.set_display(3),
            "button_vert_horiz": lambda: self.toggle_orientation(),
            "button_export_image": lambda: self.export_image()
        }

        for button_name, action in button_actions.items():
            button = self.buttons.get(button_name)
            if button:
                button.pressed.connect(action)

    
    def initialise_labels(self):
        self.output_centre_freq = self.findChild(QtWidgets.QLabel, "output_centre_freq")
        self.output_sample_rate = self.findChild(QtWidgets.QLabel, "output_sample_rate")
        self.output_span = self.findChild(QtWidgets.QLabel, "output_span")
        self.output_start_freq = self.findChild(QtWidgets.QLabel, "output_start_freq")
        self.output_stop_freq = self.findChild(QtWidgets.QLabel, "output_stop_freq")
        self.output_gain = self.findChild(QtWidgets.QLabel, "output_gain")
        self.output_res_bw = self.findChild(QtWidgets.QLabel, "output_res_bw")
        self.inputValue = self.findChild(QtWidgets.QLabel, "input_value")


    def set_display(self, index):
        self.get_current_widget_timer().stop()
        self.current_stacked_index = index
        self.stacked_widget.setCurrentIndex(index)
        self.get_current_widget_timer().start(20)

    def get_current_widget_timer(self):
        widget_timers = {
            0: self.two_d_widget.timer,
            1: self.three_d_widget.timer,
            2: self.waterfall_widget.timer,
            3: self.boxes_widget.timer
        }
        return widget_timers.get(self.current_stacked_index)

    def update_data(self):
        power_levels = self.hackrf_sweep.get_data()

        if len(power_levels) > 0:
            if self.frequency_bins is None or self.start_freq != self.last_start_freq or self.stop_freq != self.last_stop_freq:
                self.frequency_bins = np.linspace(self.start_freq, self.stop_freq, len(power_levels))
                self.last_start_freq = self.start_freq
                self.last_stop_freq = self.stop_freq

            if self.power_levels is None or len(self.power_levels) != len(power_levels):
                self.power_levels = np.copy(power_levels)
                

            if np.max(np.abs(self.power_levels - power_levels)) > 0.1:
                self.power_levels = power_levels

                if self.max_hold_levels is None:
                    self.max_hold_levels = np.array(self.power_levels)
                else:
                    self.max_hold_levels = np.maximum(self.max_hold_levels, self.power_levels)

            if self.current_stacked_index == 0:
                self.two_d_widget.update_widget_data(self.power_levels, self.max_hold_levels, self.frequency_bins)
            elif self.current_stacked_index == 1:
                self.three_d_widget.update_widget_data(self.power_levels, self.max_hold_levels, self.frequency_bins)
            elif self.current_stacked_index == 2:
                self.waterfall_widget.update_widget_data(self.power_levels, self.max_hold_levels, self.frequency_bins)
            elif self.current_stacked_index == 3:
                self.boxes_widget.update_widget_data(self.power_levels, self.max_hold_levels, self.frequency_bins)

                
            

 
    def closeEvent(self, event):
        self.hackrf_sweep.stop()
        event.accept()

    def check_data_ready(self):
        self.number_of_points = self.hackrf_sweep.get_number_of_points()
        if self.number_of_points > 0:
            self.frequency_bins = np.linspace(self.hackrf_sweep.start_freq, self.hackrf_sweep.stop_freq, self.number_of_points)
            self.max_hold_levels = np.full(self.number_of_points, -150.0)
        else:
            QtCore.QTimer.singleShot(100, self.check_data_ready)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
