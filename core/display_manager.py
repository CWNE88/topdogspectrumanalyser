import numpy as np
from PyQt6.QtWidgets import QPushButton
from datasources.base import SweepDataSource, SampleDataSource
from menumanager import MenuItem
import logging

class DisplayManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def toggle_peak_search(self):
        self.main_window.peak_search_enabled = not self.main_window.peak_search_enabled
        self.main_window.button_peak_search.setStyleSheet(
            "background-color: #ff2222; color: white; font-weight: bold;" if self.main_window.peak_search_enabled
            else "background-color: #222222; color: white; font-weight: bold;"
        )
        self.main_window.two_d_widget.set_peak_search_enabled(self.main_window.peak_search_enabled)
        self.main_window.three_d_widget.set_peak_search_enabled(self.main_window.peak_search_enabled)
        self.main_window.status_label.setText("Peak Search " + ("enabled" if self.main_window.peak_search_enabled else "disabled"))
        logging.debug(f"Peak search: {'enabled' if self.main_window.peak_search_enabled else 'disabled'}")

    def toggle_max_peak_search(self):
        self.main_window.max_peak_search_enabled = not self.main_window.max_peak_search_enabled
        self.main_window.button_max_hold.setStyleSheet(
            "background-color: #ff2222; color: white; font-weight: bold;" if self.main_window.max_peak_search_enabled
            else "background-color: #222222; color: white; font-weight: bold;"
        )
        self.main_window.two_d_widget.set_max_peak_search_enabled(self.main_window.max_peak_search_enabled)
        self.main_window.three_d_widget.set_max_peak_search_enabled(self.main_window.max_peak_search_enabled)
        self.main_window.status_label.setText("Max Hold " + ("enabled" if self.main_window.max_peak_search_enabled else "disabled"))
        logging.debug(f"Max hold: {'enabled' if self.main_window.max_peak_search_enabled else 'disabled'}")

    def toggle_hold(self):
        self.main_window.paused = not self.main_window.paused
        self.main_window.button_hold.setStyleSheet(
            "background-color: #ff2222; color: white; font-weight: bold;" if self.main_window.paused
            else "background-color: #222222; color: white; font-weight: bold;"
        )
        self.main_window.status_label.setText("Updates " + ("paused" if self.main_window.paused else "resumed"))
        logging.debug(f"Updates: {'paused' if self.main_window.paused else 'resumed'}")

    def set_display(self, index: int, style: str, button: QPushButton):
        if self.main_window.current_stacked_index == 4 and index != 4:
            self.main_window.logo_timer.stop()
        elif index == 4:
            self.main_window.logo_timer.start(20)

        self.main_window.stacked_widget.setCurrentIndex(index)
        if index < 4:
            self.main_window.button_2d.setStyleSheet("background-color: #222222; color: white; font-weight: bold;")
            self.main_window.button_3d.setStyleSheet("background-color: #222222; color: white; font-weight: bold;")
            self.main_window.button_waterfall.setStyleSheet("background-color: #222222; color: white; font-weight: bold;")
            self.main_window.button_surface.setStyleSheet("background-color: #222222; color: white; font-weight: bold;")
            button.setStyleSheet(style)
        self.main_window.current_stacked_index = index
        logging.debug(f"Set display index: {index}")

    @property
    def menu_actions(self):
        return {
            "btnHold": self.toggle_hold,
            "btn2d": lambda: self.set_display(0, "background-color: #666666; color: white; font-weight: bold;", self.main_window.button_2d),
            "btn3d": lambda: self.set_display(1, "background-color: #666666; color: white; font-weight: bold;", self.main_window.button_3d),
            "btnWaterfall": lambda: self.set_display(2, "background-color: #666666; color: white; font-weight: bold;", self.main_window.button_waterfall),
            "btnSurface": lambda: self.set_display(3, "background-color: #666666; color: white; font-weight: bold;", self.main_window.button_surface),
            "btnCentreFrequency": lambda: self.main_window.frequency_manager.change_entry_mode('centre'),
            "btnStartFrequency": lambda: self.main_window.frequency_manager.change_entry_mode('start'),
            "btnStopFrequency": lambda: self.main_window.frequency_manager.change_entry_mode('stop'),
            "btnSpan": lambda: self.main_window.frequency_manager.change_entry_mode('span'),
            "btnISM24": lambda: self.main_window.frequency_manager.set_frequency_range(2.4e9, 2.5e9),
            "btnISM58": lambda: self.main_window.frequency_manager.set_frequency_range(5.7e9, 5.9e9),
            "btnRtlSweep": lambda: self.main_window.source_manager.set_source("rtl_sweep"),
            "btnHackRFSweep": lambda: self.main_window.source_manager.set_source("hackrf_sweep"),
            "btnFFT": lambda: self.main_window.source_manager.start_fft(self.main_window.current_source_id),
            "btnHamming": lambda: self.main_window.source_manager.set_fft_window("Hamming"),
            "btnHanning": lambda: self.main_window.source_manager.set_fft_window("Hanning"),
            "btnRectangle": lambda: self.main_window.source_manager.set_fft_window("Rectangle"),
            "btnFFT512": lambda: self.main_window.source_manager.set_fft_size(512),
            "btnFFT1024": lambda: self.main_window.source_manager.set_fft_size(1024),
            "btnFFT2048": lambda: self.main_window.source_manager.set_fft_size(2048),
            "btnFFT4096": lambda: self.main_window.source_manager.set_fft_size(4096),
        }

    def on_menu_selection(self, item: MenuItem):
        logging.debug(f"Entering on_menu_selection with item.id={item.id}, current_source_id={self.main_window.current_source_id}")
        
        if item.id in ["btnRtlSamples", "btnMicrophoneSamples", "btnHackrfSamples"]:
            self.main_window.current_source_id = item.id
            logging.debug(f"Updated current_source_id={self.main_window.current_source_id} from sample source selection")
        
        if item.id == "btnFFT":
            if not self.main_window.current_source_id:
                logging.warning(f"No current_source_id set for FFT")
                self.main_window.status_label.setText("No source selected for FFT")
                return
            if self.main_window.current_source_id in ["btnRtlSamples", "btnMicrophoneSamples", "btnHackrfSamples"]:
                logging.debug(f"Starting FFT with current_source_id={self.main_window.current_source_id}")
                self.menu_actions["btnFFT"]()
                if item.sub_menu:
                    self.main_window.menu.select_menu(item.label)
            else:
                self.main_window.status_label.setText(f"Invalid FFT source: {self.main_window.current_source_id}")
                logging.error(f"Invalid FFT source: {self.main_window.current_source_id}")
                self.main_window.current_source_id = None
        
        elif item.sub_menu:
            logging.debug(f"Navigating to submenu for item.id={item.id}")
            self.main_window.menu.select_menu(item.label)
        
        else:
            logging.debug(f"Executing action for item.id={item.id}")
            action = self.menu_actions.get(item.id, lambda: self.main_window.status_label.setText(f"Action {item.id} not implemented"))
            action()
        
        logging.debug(f"Exiting on_menu_selection with item.id={item.id}, current_source_id={self.main_window.current_source_id}")

    def update_data(self):
        if self.main_window.current_source is None or self.main_window.paused:
            logging.debug("No source or paused, skipping update")
            return

        try:
            if self.main_window.current_stacked_index > 3:
                logging.debug("Logo widget visible, skipping data update")
                return

            if isinstance(self.main_window.current_source, SampleDataSource):
                power_levels, freq_bins = self.main_window.current_source.get_power_levels()
                if power_levels is None or freq_bins is None:
                    self.main_window.status_label.setText("No data from source")
                    logging.warning("No data from source")
                    return
                self.main_window.frequency_bins = freq_bins
            elif isinstance(self.main_window.current_source, SweepDataSource):
                power_levels = self.main_window.current_source.get_data()
                if power_levels is None or len(power_levels) == 0:
                    self.main_window.status_label.setText("No data from source")
                    logging.warning("No data from source")
                    return
                num_bins = len(power_levels)
                if self.main_window.frequency.start is None or self.main_window.frequency.stop is None:
                    logging.warning(f"Frequency start/stop is None: start={self.main_window.frequency.start}, stop={self.main_window.frequency.stop}")
                    self.main_window.frequency.set_start_stop(2400e6, 2500e6)
                    logging.debug(f"Reset frequency: start={self.main_window.frequency.start}, stop={self.main_window.frequency.stop}")
                logging.debug(f"Before creating freq_bins: start={self.main_window.frequency.start}, stop={self.main_window.frequency.stop}, num_bins={num_bins}")
                self.main_window.frequency_bins = np.linspace(self.main_window.frequency.start, self.main_window.frequency.stop, num_bins)
            else:
                self.main_window.status_label.setText(f"Invalid source type: {type(self.main_window.current_source)}")
                logging.error(f"Invalid source type: {type(self.main_window.current_source)}")
                return

            if self.main_window.live_power_levels is None:
                self.main_window.live_power_levels = power_levels
                self.main_window.max_power_levels = power_levels.copy()
            else:
                self.main_window.live_power_levels = power_levels
                if self.main_window.max_power_levels.shape != power_levels.shape:
                    logging.debug(f"Shape mismatch detected: max_power_levels {self.main_window.max_power_levels.shape}, power_levels {power_levels.shape}. Resetting max_power_levels.")
                    self.main_window.max_power_levels = power_levels.copy()
                elif self.main_window.max_peak_search_enabled:
                    self.main_window.max_power_levels = np.maximum(self.main_window.max_power_levels, power_levels)
                else:
                    self.main_window.max_power_levels = power_levels.copy()

            if self.main_window.current_stacked_index == 0:
                self.main_window.two_d_widget.update_widget_data(self.main_window.live_power_levels, self.main_window.max_power_levels, self.main_window.frequency_bins)
            elif self.main_window.current_stacked_index == 1:
                self.main_window.three_d_widget.update_widget_data(self.main_window.live_power_levels, self.main_window.max_power_levels, self.main_window.frequency_bins)
            elif self.main_window.current_stacked_index == 2:
                self.main_window.waterfall_widget.update_widget_data(self.main_window.live_power_levels, self.main_window.max_power_levels, self.main_window.frequency_bins)
            elif self.main_window.current_stacked_index == 3:
                self.main_window.surface_widget.update_widget_data(self.main_window.live_power_levels, self.main_window.max_power_levels, self.main_window.frequency_bins)

            logging.debug(f"Data updated successfully for widget index {self.main_window.current_stacked_index}")
        except Exception as e:
            self.main_window.status_label.setText(f"Error updating data: {str(e)}")
            logging.error(f"Error updating data: {str(e)}")
