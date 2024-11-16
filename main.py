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
from SignalProcessing import DSP as dsp
import matplotlib as mpl
from menu import MenuManager, MenuItem
import cProfile

class MainWindow(QtWidgets.QMainWindow):
    menu: MenuManager = None

    is_paused = False

    def __init__(self):
        super().__init__()

        uic.loadUi("mainwindowhorizontal.ui", self)
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.start_freq = 115e6
        self.stop_freq = 135e6
        self.bin_size = 10e3
        self.centre_freq = None
        
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
        self.get_current_widget_timer().start(20)
        self.stacked_widget.setCurrentIndex(self.current_stacked_index)
        
        self.hackrf_sweep = HackRFSweep()
        self.hackrf_sweep.setup(start_freq=self.start_freq, stop_freq=self.stop_freq, bin_size=self.bin_size)
        self.hackrf_sweep.run()

        self.frequency_bins = None
        self.frequency_bins_changed = False
        self.live_power_levels = None
        
        self.max_hold_enabled = False
        self.max_power_levels = None
        
        self.min_hold_enabled = False
        self.min_power_levels = None
        
        self.average_enabled = False
        self.average_power_levels = None

        self.peak_search_enabled = False        
        self.peak_search_frequency = None
        self.peak_search_power = None

        self.max_peak_search_enabled = False    # True if self.max_hold_enabled and self.peak_search_enabled are true
        self.max_peak_search_frequency = None
        self.max_peak_search_power = None

        self.peak_search_label = None
        self.max_peak_search_label = None
                
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_data)
        self.timer.start(40)
        self.set_button_focus_policy(self)  # Avoids buttons keeping focus after pressing, so space bar works
        self.connect_buttons()

        self.menu = MenuManager(self, self.on_menu_selection)

        # display stuff
        self.res_bw = None
        self.span = None
        self.engformat = mpl.ticker.EngFormatter(places=2) 
    
    def set_button_focus_policy(self, parent):
        for widget in parent.findChildren(QtWidgets.QPushButton):
            widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def on_menu_selection(self, item: MenuItem):
        #print (item.elementId)
        if item.elementId == "button_hold":
            self.toggle_hold()
        elif item.elementId == "button_2d":
            self.button_2d.setStyleSheet("background-color: #666666; color: white; font-weight: bold;")
            self.set_display(0)
        elif item.elementId == "button_3d":
            self.button_3d.setStyleSheet("background-color: #666666; color: white; font-weight: bold;")
            self.set_display(1)
        elif item.elementId == "button_waterfall":
            self.set_display(2)
        elif item.elementId == "button_boxes":
            self.set_display(3)
        elif item.elementId == "button_peak_search":
            self.toggle_peak_search()
        elif item.elementId == "button_max_hold":
            self.toggle_max_hold()

    #def keyPressEvent(self, event: QKeyEvent):
    #    self.menu.keyPressEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() == Qt.KeyboardModifier.AltModifier and event.key() == Qt.Key.Key_Return:
            # Create a new window for the graphical display
            self.graphical_display_window = QtWidgets.QWidget()
            self.graphical_display_window.setWindowTitle("Graphical Display")
            self.graphical_display_window.setLayout(QtWidgets.QVBoxLayout())
            
            # Remove the graphical display from the main window
            graphical_display_widget = self.findChild(QtWidgets.QWidget, "graphical_display")
            graphical_display_widget_parent = graphical_display_widget.parent()
            graphical_display_widget_parent.layout().removeWidget(graphical_display_widget)
            
            # Add the graphical display to the new window
            self.graphical_display_window.layout().addWidget(graphical_display_widget)
            
            # Show the new window
            self.graphical_display_window.show()
        
        self.menu.keyPressEvent(event)

    def toggle_peak_search(self):
        self.peak_search_enabled = not self.peak_search_enabled
        if self.peak_search_enabled:
            print ("Peak search enabled")
            self.status_label.setText("Peak search enabled")
            self.button_peak_search.setStyleSheet("background-color: #666666; color: white; font-weight: bold;")
        else:
            print ("Peak search disabled")
            self.status_label.setText("Peak search disabled")
            self.button_peak_search.setStyleSheet("background-color: #ffffff; color: black; font-weight: bold;")

    def toggle_max_hold(self):
        self.max_hold_enabled = not self.max_hold_enabled
        if self.max_hold_enabled:
            print ("Max hold enabled")
            self.status_label.setText("Max hold enabled")
            self.button_max_hold.setStyleSheet("background-color: #666666; color: white; font-weight: bold;")
            self.max_power_levels = self.live_power_levels
            self.two_d_widget.set_max_hold_enabled (True)
        else:
            print ("Max hold disabled")
            self.status_label.setText("Max hold disabled")
            self.button_max_hold.setStyleSheet("background-color: #ffffff; color: black; font-weight: bold;")
            self.max_power_levels = None
            
            

    def toggle_hold(self):
        self.is_paused = not self.is_paused

        if self.is_paused:
            print("Animation paused")
            self.status_label.setText("Animation pause")
            self.button_hold.setStyleSheet("background-color: #ff2222; color: white; font-weight: bold;")
            self.get_current_widget_timer().stop()
        else:
            print("Animation resumed")
            self.status_label.setText("Animation resumed")
            self.button_hold.setStyleSheet("background-color: #222222; color: white; font-weight: bold;")
            self.get_current_widget_timer().start(20)
            
    def connect_buttons(self):
        button_actions = {
            "button_mode": lambda: self.handle_menu_button("Mode"),
            "button_preset": lambda: self.preset(),
            "button_max_hold": lambda: self.toggle_max_hold(),
            "button_hold": lambda: self.toggle_hold(),
            "button_peak_search": lambda: self.toggle_peak_search(),
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
        self.status_label = self.findChild(QtWidgets.QLabel, "status_label")
        self.input_value = self.findChild(QtWidgets.QLabel, "input_value")
        self.label_sample_rage = self.findChild(QtWidgets.QLabel, "label_sample_rate")
        


    def set_display(self, index):        
        print ("in main set_display")
        self.get_current_widget_timer().stop()
        self.current_stacked_index = index
        self.stacked_widget.setCurrentIndex(index)
        if self.stacked_widget==2:
            self.three_d_widget.set_number_of_points(len(self.frequency_bins))
            print (len(self.frequency_bins))
            self.three_d_widget.initialise_traces()
            
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
        power_level_data = self.hackrf_sweep.get_data()

        if len(power_level_data) > 0:
            self.status_label.setText("bin length" +(str(len(power_level_data))))

            # Set up self.frequency_bins if different from previous
            if self.frequency_bins is None or self.start_freq != self.last_start_freq or self.stop_freq != self.last_stop_freq:
                
                # Create new frequency bins
                self.frequency_bins = np.linspace(self.start_freq, self.stop_freq, len(power_level_data))
                self.last_start_freq = self.start_freq
                self.last_stop_freq = self.stop_freq
                self.span = self.stop_freq - self.start_freq
                self.centre_freq = self.span/2 + self.start_freq
                self.res_bw = (self.span / len(self.frequency_bins))
                self.frequency_bins_changed = True

                # Update gui values
                self.output_start_freq.setText(self.engformat(self.start_freq) + "Hz")
                self.output_stop_freq.setText(self.engformat(self.stop_freq) + "Hz")
                self.output_span.setText(self.engformat(self.span) + "Hz")
                self.output_res_bw.setText(self.engformat(self.res_bw) + "Hz")
                self.output_centre_freq.setText(self.engformat(self.centre_freq) + "Hz")

                ## TESTING
                self.label_sample_rate.setText("Sweeps /s")
                

            
            # Update power array
            self.live_power_levels = power_level_data

            # Max hold
            if self.max_hold_enabled:
                if self.max_power_levels is None:
                    self.max_power_levels = np.array(self.live_power_levels)
                else:
                    self.max_power_levels = np.maximum(self.max_power_levels, self.live_power_levels)
            
            # Peak search
            if self.peak_search_enabled:
                peak_index = np.argmax(self.live_power_levels)
                self.peak_search_power = self.live_power_levels[peak_index]
                self.peak_search_frequency = self.frequency_bins[peak_index]
            
                # Max hold peak search
                if self.max_hold_enabled:
                    peak_index = np.argmax(self.max_power_levels)
                    self.max_peak_search_power = self.max_power_levels[peak_index]
                    self.max_peak_search_frequency = self.frequency_bins[peak_index]
                

            # Pass data to widgets
            if not self.is_paused:

                # If 2d widget
                if self.current_stacked_index == 0:
                    
                    # always update live power
                    self.two_d_widget.update_live_power_levels(self.live_power_levels)

                    # update max hold
                    if self.max_hold_enabled:
                        self.two_d_widget.set_max_hold_enabled(True)
                        self.two_d_widget.update_max_power_levels(self.max_power_levels)
                    else:
                        self.two_d_widget.set_max_hold_enabled(False)

                    # update peak search
                    if self.peak_search_enabled:
                        self.two_d_widget.set_peak_search_enabled(True)
                        self.two_d_widget.set_peak_search_frequency_and_power(self.peak_search_frequency, self.peak_search_power)
                    else:
                        self.two_d_widget.set_peak_search_enabled(False)
                    
                    # update max peak search
                    if self.max_peak_search_enabled:
                        self.two_d_widget.set_max_peak_search_enabled(True)
                        self.two_d_widget.set_max_peak_search_frequency_and_power(self.max_peak_search_frequency, self.max_peak_search_power)
                    else:
                        self.two_d_widget.set_max_peak_search_enabled(False)

                    #
                    if self.frequency_bins_changed:
                        self.two_d_widget.update_frequency_bins(self.frequency_bins)
                        self.frequency_bins_changed = False
                    
                # If 3d widget
                if self.current_stacked_index == 1:

                    # update peak search
                    if self.peak_search_enabled:
                        self.three_d_widget.set_peak_search_enabled(True)
                        self.three_d_widget.set_peak_search_frequency_and_power(self.peak_search_frequency, self.peak_search_power)
                    
                    # Only pass frequencies if traces haven't been initialised
                    if not self.three_d_widget.traces_initialised:
                        self.three_d_widget.update_frequency_bins(self.frequency_bins)
                    
                    # Pass power to widget
                    self.three_d_widget.update_live_power_levels(self.live_power_levels)
                    if not self.three_d_widget.traces_initialised:
                        self.three_d_widget.initialise_traces()
                    self.three_d_widget.traces_initialised = True
                    

                if self.current_stacked_index == 2:
                    #self.waterfall_widget.update_widget_data(self.live_power_levels, self.frequency_bins)
                    self.waterfall_widget.update_live_power_levels(self.live_power_levels)

                
                

 
    def closeEvent(self, event):
        self.hackrf_sweep.stop()
        event.accept()

    def check_data_ready(self):
        self.number_of_points = self.hackrf_sweep.get_number_of_points()
        if self.number_of_points > 0:
            self.frequency_bins = np.linspace(self.hackrf_sweep.start_freq, self.hackrf_sweep.stop_freq, self.number_of_points)
            self.max_power_levels = np.full(self.number_of_points, -150.0)
        else:
            QtCore.QTimer.singleShot(100, self.check_data_ready)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
    #cProfile.run('sys.exit(app.exec())')
