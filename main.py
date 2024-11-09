#!/usr/bin/python3
import sys
import datetime
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets, uic, QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from input_hackrf_sweep import HackRFSweep
import twodimension
import threedimension
import waterfall
import boxes
from PyQt6.QtWidgets import QStackedWidget

from menu import MenuManager, MenuItem

class MainWindow(QtWidgets.QMainWindow):
    menu: MenuManager = None

    is_paused = False

    def __init__(self):
        super().__init__()

        uic.loadUi("mainwindowhorizontal.ui", self)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.start_freq = 2.4e9 
        self.stop_freq = 2.5e9
        self.bin_size = 50e3
        
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

        self.connect_buttons()

        self.menu = MenuManager(self, self.on_menu_selection)

    def on_menu_selection(self, item: MenuItem):
        if item.elementId == "button_hold":
            self.toggle_hold()
        elif item.elementId == "button_2d":
            self.set_display(0)
        elif item.elementId == "button_3d":
            self.set_display(1)
        elif item.elementId == "button_waterfall":
            self.set_display(2)
        elif item.elementId == "button_boxes":
            self.set_display(3)
        

    def keyPressEvent(self, event: QKeyEvent):
        self.menu.keyPressEvent(event)
    
    
    def toggle_hold(self):
        self.is_paused = not self.is_paused

        if self.is_paused:
            print("Animation paused")
            self.button_hold.setStyleSheet("background-color: #ff2222; color: white; font-weight: bold;")
        else:
            print("Animation resumed")
            self.button_hold.setStyleSheet("background-color: #222222; color: white; font-weight: bold;")


    def connect_buttons(self):
        button_actions = {
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
