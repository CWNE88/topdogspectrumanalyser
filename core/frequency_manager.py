import numpy as np
from frequencyselector import FrequencyRange
from datasources.base import SampleDataSource
import logging

class FrequencyManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.main_window.frequency = FrequencyRange(98e6, 100e6)
        logging.debug(f"Initialised frequency: start={self.main_window.frequency.start}, stop={self.main_window.frequency.stop}")

    def update_frequency_values(self):
        try:
            is_microphone = self.main_window.current_source and self.main_window.current_source.__class__.__name__ == "MicrophoneSamplesDataSource"
            unit = "kHz" if is_microphone else "MHz"
            divisor = 1e3 if is_microphone else 1e6
            
            centre = self.main_window.frequency.centre if self.main_window.frequency.centre is not None else 0
            span = self.main_window.frequency.span if self.main_window.frequency.span is not None else 0
            start = self.main_window.frequency.start if self.main_window.frequency.start is not None else 0
            stop = self.main_window.frequency.stop if self.main_window.frequency.stop is not None else 0
            res_bw = self.main_window.frequency.res_bw if self.main_window.frequency.res_bw is not None else 0

            self.main_window.output_centre_freq.setText(f"{centre / divisor:.2f} {unit}")
            self.main_window.output_span.setText(f"{span / divisor:.2f} {unit}")
            self.main_window.output_start_freq.setText(f"{start / divisor:.2f} {unit}")
            self.main_window.output_stop_freq.setText(f"{stop / divisor:.2f} {unit}")
            self.main_window.output_res_bw.setText(f"{res_bw / 1e3:.2f} kHz")
            if self.main_window.current_source and isinstance(self.main_window.current_source, SampleDataSource):
                self.main_window.output_sample_rate.setText(f"{self.main_window.current_source.sample_rate / 1e3:.2f} kHz")
            else:
                self.main_window.output_sample_rate.setText("-")
            logging.debug("Frequency values updated")
        except Exception as e:
            self.main_window.status_label.setText(f"Error updating labels: {str(e)}")
            logging.error(f"Error updating labels: {str(e)}")

    def set_frequency_range(self, start: float, stop: float):
        try:
            old_span = self.main_window.frequency.span if hasattr(self.main_window, 'frequency') else None
            
            self.main_window.frequency.set_start_stop(start, stop)
            logging.debug(f"After set_frequency_range: start={self.main_window.frequency.start}, stop={self.main_window.frequency.stop}")
            self.update_frequency_values()
            
            freq_bins = np.linspace(self.main_window.frequency.start, self.main_window.frequency.stop, 1024)
            if self.main_window.current_stacked_index == 0:
                self.main_window.two_d_widget.update_frequency_bins(freq_bins)
            elif self.main_window.current_stacked_index == 1:
                self.main_window.three_d_widget.update_frequency_bins(freq_bins)
            elif self.main_window.current_stacked_index == 2:
                self.main_window.waterfall_widget.update_frequency_bins(freq_bins)
            elif self.main_window.current_stacked_index == 3:
                self.main_window.surface_widget.update_frequency_bins(freq_bins)
            
            self.main_window.source_manager.update_source_frequency()
            logging.debug(f"Set frequency range: start={start}, stop={stop}")
        except Exception as e:
            self.main_window.status_label.setText(f"Error setting frequency: {str(e)}")
            logging.error(f"Error setting frequency: {str(e)}")

    def change_entry_mode(self, mode: str):
        self.main_window.frequency_entry_mode = mode
        self.main_window.keypad.reset()
        self.main_window.status_label.setText(f"Set {mode} frequency")
        logging.debug(f"Changed entry mode to {mode}")

    def on_keypad_change(self, value: str | None):
        self.main_window.input_value.setText(value if value else "")
        logging.debug(f"Keypad input changed: {value}")

    def on_frequency_select(self, freq: int):
        try:
            is_microphone = self.main_window.current_source and self.main_window.current_source.__class__.__name__ == "MicrophoneSamplesDataSource"
            max_span = 44100 if is_microphone else 2e6
            match self.main_window.frequency_entry_mode:
                case 'centre':
                    self.main_window.frequency.set_centre(freq)
                case 'start':
                    self.main_window.frequency.set_start(freq)
                case 'stop':
                    self.main_window.frequency.set_stop(freq)
                case 'span':
                    if freq > max_span:
                        self.main_window.status_label.setText(f"Span limited to {max_span/1e3:.2f} kHz for {'Microphone' if is_microphone else 'RTL'} Samples")
                        logging.warning(f"Span limited to {max_span/1e3} kHz")
                        return
                    self.main_window.frequency.set_span(freq)
            
            logging.debug(f"After on_frequency_select: start={self.main_window.frequency.start}, stop={self.main_window.frequency.stop}")
            self.update_frequency_values()
            
            freq_bins = np.linspace(self.main_window.frequency.start, self.main_window.frequency.stop, 1024)
            if self.main_window.current_stacked_index == 0:
                self.main_window.two_d_widget.update_frequency_bins(freq_bins)
            elif self.main_window.current_stacked_index == 1:
                self.main_window.three_d_widget.update_frequency_bins(freq_bins)
            elif self.current_stacked_index == 2:
                self.main_window.waterfall_widget.update_frequency_bins(freq_bins)
            elif self.current_stacked_index == 3:
                self.main_window.surface_widget.update_frequency_bins(freq_bins)
            
            self.main_window.source_manager.update_source_frequency()
            self.main_window.status_label.setText(f"{self.main_window.frequency_entry_mode.capitalize()} frequency set")
            self.main_window.keypad.reset()
            logging.debug(f"Frequency selected: {freq} for {self.main_window.frequency_entry_mode}")
        except Exception as e:
            self.main_window.status_label.setText(f"Error setting frequency: {str(e)}")
            logging.error(f"Error setting frequency: {str(e)}")

