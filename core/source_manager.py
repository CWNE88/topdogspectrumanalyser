from datasources.base import SweepDataSource, SampleDataSource
from datasources.rtl_sweep import RtlSweepDataSource
from datasources.hackrf_sweep import HackRFSweepDataSource
from datasources.rtl_samples import RtlSamplesDataSource
from datasources.microphone_samples import MicrophoneSamplesDataSource
from datasources.hackrf_samples import HackrfSamplesDataSource
import logging

class SourceManager:
    def __init__(self, main_window):
        self.main_window = main_window

    def update_source_frequency(self):
        if self.main_window.current_source is None:
            logging.debug("No current source, skipping frequency update")
            return
        try:
            if isinstance(self.main_window.current_source, SampleDataSource):
                current_span = self.main_window.frequency.span
                span_changed = not hasattr(self.main_window, 'last_span') or abs(self.main_window.last_span - current_span) > 1e-6
                logging.debug(f"Checking span: last_span={getattr(self.main_window, 'last_span', None)}, current_span={current_span}, span_changed={span_changed}")
                
                if span_changed:
                    logging.debug("Span changed, performing full frequency update")
                    self.main_window.current_source.update_frequency(self.main_window.frequency.span, self.main_window.frequency.centre)
                    self.main_window.last_span = current_span
                else:
                    logging.debug("Centre frequency changed, updating without reinitialisation")
                    if hasattr(self.main_window.current_source, 'update_center_frequency'):
                        self.main_window.current_source.update_center_frequency(self.main_window.frequency.centre)
                        freq_bins = np.linspace(
                            self.main_window.frequency.centre - self.main_window.current_source.sample_rate / 2,
                            self.main_window.frequency.centre + self.main_window.current_source.sample_rate / 2,
                            1024
                        )
                        if self.main_window.current_stacked_index == 0:
                            self.main_window.two_d_widget.update_frequency_bins(freq_bins)
                        elif self.main_window.current_stacked_index == 1:
                            self.main_window.three_d_widget.update_frequency_bins(freq_bins)
                        elif self.main_window.current_stacked_index == 2:
                            self.main_window.waterfall_widget.update_frequency_bins(freq_bins)
                        elif self.main_window.current_stacked_index == 3:
                            self.main_window.surface_widget.update_frequency_bins(freq_bins)
                    else:
                        logging.warning("update_center_frequency not implemented, falling back to full update")
                        self.main_window.current_source.update_frequency(self.main_window.frequency.span, self.main_window.frequency.centre)
            else:
                logging.debug("Updating sweep source frequency")
                self.main_window.current_source.start(self.main_window.frequency)
            logging.debug("Source frequency updated successfully")
        except Exception as e:
            self.main_window.status_label.setText(f"Error updating source: {str(e)}")
            logging.error(f"Error updating source: {str(e)}")    

    def set_source(self, source: str):
        logging.debug(f"Attempting to set source: {source}")
        try:
            source_classes = {
                "rtl_sweep": RtlSweepDataSource,
                "hackrf_sweep": HackRFSweepDataSource,
                "rtl_samples": RtlSamplesDataSource,
                "microphone_samples": MicrophoneSamplesDataSource,
                "hackrf_samples": HackrfSamplesDataSource
            }
            source_class = source_classes.get(source)
            if source_class is None:
                self.main_window.status_label.setText(f"Invalid source: {source}")
                logging.error(f"Invalid source: {source}")
                return

            if self.main_window.current_source:
                try:
                    logging.debug(f"Stopping previous source: {self.main_window.current_source.__class__.__name__}")
                    self.main_window.current_source.stop()
                    if hasattr(self.main_window.current_source, 'is_running') and self.main_window.current_source.is_running:
                        logging.warning("Previous source did not stop properly")
                        self.main_window.current_source.stop()
                    if hasattr(self.main_window.current_source, 'thread') and self.main_window.current_source.thread is not None:
                        if self.main_window.current_source.thread.is_alive():
                            self.main_window.current_source.thread.join(timeout=5)
                            if self.main_window.current_source.thread.is_alive():
                                logging.warning("HackRF sweep thread did not terminate in time")
                        self.main_window.current_source.thread = None
                    logging.debug("Previous source stopped successfully")
                except Exception as e:
                    self.main_window.status_label.setText(f"Error stopping previous source: {str(e)}")
                    logging.error(f"Error stopping previous source: {str(e)}")
                finally:
                    self.main_window.current_source = None
                    self.main_window.live_power_levels = None
                    self.main_window.max_power_levels = None
                    self.main_window.frequency_bins = None

            if source == "rtl_sweep":
                self.main_window.frequency_manager.set_frequency_range(88e6, 108e6)
                self.main_window.current_source = source_class(self.main_window.frequency.start, self.main_window.frequency.stop, bin_size=100000)
                self.main_window.current_source.start(self.main_window.frequency)
            elif source == "hackrf_sweep":
                self.main_window.frequency_manager.set_frequency_range(2400e6, 2500e6)
                self.main_window.current_source = source_class(self.main_window.frequency.start, self.main_window.frequency.stop, bin_size=30000)
                self.main_window.current_source.start(self.main_window.frequency)
            elif source == "hackrf_samples":
                self.main_window.frequency_manager.set_frequency_range(2400e6, 2500e6)
                self.main_window.current_source = source_class(sample_rate=2e6, centre_freq=2450e6)
                self.main_window.current_source.start(self.main_window.frequency)
            elif source == "rtl_samples":
                self.main_window.frequency_manager.set_frequency_range(97e6, 99e6)
                logging.debug("Initialising RtlSamplesDataSource")
                self.main_window.current_source = source_class(sample_rate=2e6, centre_freq=98e6)
                try:
                    self.main_window.current_source.start(self.main_window.frequency)
                    logging.debug("RTL Samples started successfully")
                except Exception as e:
                    self.main_window.current_source = None
                    self.main_window.status_label.setText(f"RTL Samples start failed: {str(e)}")
                    logging.error(f"RTL Samples start failed: {str(e)}")
                    return
            else:  # microphone_samples
                self.main_window.frequency_manager.set_frequency_range(-22050, 22050)
                self.main_window.current_source = source_class(sample_rate=44100, centre_freq=0)
                try:
                    self.main_window.current_source.start(self.main_window.frequency)
                    logging.debug("Microphone Samples started successfully")
                except Exception as e:
                    self.main_window.current_source = None
                    self.main_window.status_label.setText(f"Microphone Samples start failed: {str(e)}")
                    logging.error(f"Microphone Samples start failed: {str(e)}")
                    return

            self.main_window.status_label.setText(f"Source set: {source}")
            self.main_window.button_peak_search.setEnabled(True)
            self.main_window.button_max_hold.setEnabled(True)
            self.main_window.button_hold.setEnabled(True)
            self.main_window.display_manager.set_display(0, "background-color: #666666; color: white; font-weight: bold;", self.main_window.button_2d)
            self.main_window.frequency_manager.update_frequency_values()
            logging.debug(f"Source set successfully: {source}")
        except Exception as e:
            self.main_window.status_label.setText(f"Error setting source: {str(e)}")
            self.main_window.current_source = None
            logging.error(f"Error setting source: {str(e)}")

    def start_fft(self, source_id: str):
        if not source_id:
            logging.error("start_fft called with None source_id")
            self.main_window.status_label.setText("Cannot start FFT: No source selected")
            return
        source_mapping = {
            "btnRtlSamples": "rtl_samples",
            "btnMicrophoneSamples": "microphone_samples",
            "btnHackrfSamples": "hackrf_samples"
        }
        source = source_mapping.get(source_id)
        if not source:
            self.main_window.status_label.setText(f"Invalid source for FFT: {source_id}")
            logging.error(f"Invalid source for FFT: {source_id}")
            return
        self.main_window.current_source_id = source_id
        logging.debug(f"Starting FFT for source_id={source_id}, mapped to {source}, updated current_source_id={self.main_window.current_source_id}")
        self.set_source(source)

    def set_fft_window(self, window_type: str):
        if not self.main_window.current_source or not isinstance(self.main_window.current_source, SampleDataSource):
            self.main_window.status_label.setText("No sample source running. Start FFT first.")
            logging.warning("No sample source running for FFT window")
            return
        try:
            self.main_window.current_source.set_window_type(window_type.lower())
            self.main_window.status_label.setText(f"{window_type} window selected")
            logging.debug(f"Set FFT window: {window_type}")
        except Exception as e:
            self.main_window.status_label.setText(f"Error setting FFT window: {str(e)}")
            logging.error(f"Error setting FFT window: {str(e)}")

    def set_fft_size(self, size: int):
        if not self.main_window.current_source or not isinstance(self.main_window.current_source, SampleDataSource):
            self.main_window.status_label.setText("No sample source running. Start FFT first.")
            logging.warning("No sample source running for FFT sample size")
            return
        try:
            self.main_window.current_source.set_fft_size(size)
            self.main_window.status_label.setText(f"FFT size set to {size}")
            logging.debug(f"Set FFT size: {size}")
        except Exception as e:
            self.main_window.status_label.setText(f"Error setting FFT size: {str(e)}")
            logging.error(f"Error setting FFT size: {str(e)}")

    def close(self):
        if self.main_window.current_source and hasattr(self.main_window.current_source, 'stop'):
            self.main_window.current_source.stop()
            if hasattr(self.main_window.current_source, 'thread') and self.main_window.current_source.thread is not None:
                if self.main_window.current_source.thread.is_alive():
                    self.main_window.current_source.thread.join(timeout=5)
                    if self.main_window.current_source.thread.is_alive():
                        logging.warning("HackRF sweep thread did not terminate in time")
                self.main_window.current_source.thread = None

