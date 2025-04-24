# File: main.py
import sys
import numpy as np
from PyQt6.QtWidgets import QMainWindow, QApplication
from PyQt6.uic import loadUi
from core.ui_setup import UISetup
from core.frequency_manager import FrequencyManager
from core.source_manager import SourceManager
from core.display_manager import DisplayManager
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logging.critical("Loading main.py with FFT start fix - version 2025-04-21 FIXED HACKRF SWEEP BINARY OUTPUT AND ADDED SURFACE PLOT - OPTIMISED UPDATES FOR VISIBLE WIDGET ONLY - FIXED FREQUENCY NONE ISSUE IN FREQUENCYSELECTOR - DEBUGGING WATERFALL NONE ISSUE - TEMP SAFEGUARD - REVERTED TO PRE-SPECTRUMDATA - FIXED HACKRF SUBPROCESS TERMINATION - FIXED HACKRF THREAD CLEANUP - FIXED SHAPE MISMATCH ON SOURCE SWITCH")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("mainwindowhorizontal.ui", self)
        
        # Initialise state
        self.live_power_levels = None
        self.max_power_levels = None
        self.frequency_bins = None
        self.peak_search_enabled = False
        self.max_peak_search_enabled = False
        self.current_source = None
        self.current_source_id = None
        self.paused = False
        self.current_stacked_index = 4  # Start with logo view
        self.last_span = None
        
        # Initialise managers in correct order
        self.display_manager = DisplayManager(self)  # First for menu dependency
        self.frequency_manager = FrequencyManager(self)  # Second for keypad dependency
        self.ui_setup = UISetup(self)  # Third, after display and frequency managers
        self.source_manager = SourceManager(self)  # Last, no dependencies
        
        # Set initial UI state
        self.ui_setup.initialise_labels()
        logging.debug("MainWindow initialised")

    def closeEvent(self, event):
        """Handle application shutdown cleanly."""
        self.source_manager.close()
        event.accept()
        logging.debug("MainWindow: Application closed")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
