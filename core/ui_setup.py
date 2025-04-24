from PyQt6.QtWidgets import QStackedWidget, QPushButton
from PyQt6.QtCore import QTimer
from twodimension import TwoD
from threedimension import ThreeD
from waterfall import Waterfall
from surface import Surface
from logo import Logo
from menumanager import MenuManager
from keypad import Keypad
import logging

class UISetup:
    def __init__(self, main_window):
        self.main_window = main_window
        
        # Initialise widgets
        self.main_window.two_d_widget = TwoD()
        self.main_window.three_d_widget = ThreeD()
        self.main_window.waterfall_widget = Waterfall()
        self.main_window.surface_widget = Surface()
        self.main_window.logo_widget = Logo()

        self.main_window.stacked_widget = QStackedWidget()
        self.main_window.stacked_widget.addWidget(self.main_window.two_d_widget)      # Index 0
        self.main_window.stacked_widget.addWidget(self.main_window.three_d_widget)    # Index 1
        self.main_window.stacked_widget.addWidget(self.main_window.waterfall_widget)  # Index 2
        self.main_window.stacked_widget.addWidget(self.main_window.surface_widget)    # Index 3
        self.main_window.stacked_widget.addWidget(self.main_window.logo_widget)       # Index 4

        self.main_window.graphical_display.layout().addWidget(self.main_window.stacked_widget)
        self.main_window.stacked_widget.setCurrentIndex(self.main_window.current_stacked_index)

        # Initialise menu and keypad
        self.main_window.menu = MenuManager(self.main_window.display_manager.on_menu_selection, self.main_window)
        self.main_window.keypad = Keypad(self.main_window, self.main_window.frequency_manager.on_keypad_change, 
                                       self.main_window.frequency_manager.on_frequency_select)

        # Initialise timers
        self.main_window.logo_timer = QTimer(self.main_window)
        self.main_window.logo_timer.timeout.connect(self.main_window.logo_widget.update_rotation)
        self.main_window.logo_timer.start(20)  # Start logo animation

        self.main_window.timer = QTimer(self.main_window)
        self.main_window.timer.timeout.connect(self.main_window.display_manager.update_data)
        self.main_window.timer.start(20)

        # Connect buttons
        self.main_window.button_frequency.clicked.connect(lambda: self.main_window.menu.select_menu("Frequency"))
        self.main_window.button_input_1.clicked.connect(lambda: self.main_window.menu.select_menu("Input 1"))

        self.main_window.button_2d.clicked.connect(self.main_window.display_manager.menu_actions["btn2d"])
        self.main_window.button_3d.clicked.connect(self.main_window.display_manager.menu_actions["btn3d"])
        self.main_window.button_waterfall.clicked.connect(self.main_window.display_manager.menu_actions["btnWaterfall"])
        self.main_window.button_surface.clicked.connect(self.main_window.display_manager.menu_actions["btnSurface"])

        self.main_window.button_hold.clicked.connect(self.main_window.display_manager.toggle_hold)
        self.main_window.button_max_hold.clicked.connect(self.main_window.display_manager.toggle_max_peak_search)
        self.main_window.button_peak_search.clicked.connect(self.main_window.display_manager.toggle_peak_search)

        for i in range(1, 9):
            button = getattr(self.main_window, f"button_soft_{i}", None)
            if button:
                button.clicked.connect(lambda checked, idx=i-1: self.main_window.menu.handle_button_press(idx))

        # Disable buttons initially
        self.main_window.button_peak_search.setEnabled(False)
        self.main_window.button_max_hold.setEnabled(False)
        self.main_window.button_hold.setEnabled(False)

    def initialise_labels(self):
        self.main_window.output_centre_freq.setText("-")
        self.main_window.output_span.setText("-")
        self.main_window.output_start_freq.setText("-")
        self.main_window.output_stop_freq.setText("-")
        self.main_window.output_res_bw.setText("-")
        self.main_window.output_sample_rate.setText("-")
        self.main_window.output_gain.setText("-")
        self.main_window.status_label.setText("No source selected")
        self.main_window.input_value.setText("")
        logging.debug("Labels initialised")
