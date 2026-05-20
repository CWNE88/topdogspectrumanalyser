import numpy as np
from utils.frequency_selector import FrequencyRange
from datasources.base import SampleDataSource, SweepDataSource
from datasources.audio_samples import MicrophoneSamplesDataSource
from utils.frequency_helpers import update_display_frequency_bins, format_frequency, format_hz
from utils.constants import EntryMode, SourceLimits
import logging

logger = logging.getLogger(__name__)

class FrequencyManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self._in_frequency_update = False
        from utils.constants import FrequencyPresets
        main_window.frequency = FrequencyRange(
            FrequencyPresets.FM_RADIO_START,
            FrequencyPresets.FM_RADIO_STOP
        )
        logger.debug("Initialised FrequencyManager")

    def update_frequency_values(self):
        try:
            is_microphone = isinstance(self.main_window.current_source, MicrophoneSamplesDataSource)

            centre = self.main_window.frequency.centre if self.main_window.frequency.centre is not None else 0
            span = self.main_window.frequency.span if self.main_window.frequency.span is not None else 0
            start = self.main_window.frequency.start if self.main_window.frequency.start is not None else 0
            stop = self.main_window.frequency.stop if self.main_window.frequency.stop is not None else 0

            # Calculate Resolution Bandwidth based on source type
            res_bw = 0
            if self.main_window.current_source:
                if isinstance(self.main_window.current_source, SweepDataSource):
                    # For sweep sources: RBW = bin_size
                    if hasattr(self.main_window.current_source, 'bin_size'):
                        res_bw = self.main_window.current_source.bin_size
                elif isinstance(self.main_window.current_source, SampleDataSource):
                    # For sample sources: RBW = sample_rate / fft_size (or num_samples)
                    sample_rate = getattr(self.main_window.current_source, 'sample_rate', 0)
                    fft_size = getattr(self.main_window.current_source, 'sample_count', 1024)
                    if sample_rate > 0 and fft_size > 0:
                        res_bw = sample_rate / fft_size

            centre_str, unit = format_frequency(centre, is_microphone)
            span_str, _ = format_frequency(span, is_microphone)
            start_str, _ = format_frequency(start, is_microphone)
            stop_str, _ = format_frequency(stop, is_microphone)

            self.main_window.output_centre_freq.setText(f"{centre_str} {unit}")
            self.main_window.output_span.setText(f"{span_str} {unit}")
            self.main_window.output_start_freq.setText(f"{start_str} {unit}")
            self.main_window.output_stop_freq.setText(f"{stop_str} {unit}")

            # Format RBW appropriately based on magnitude
            if res_bw >= 1e6:
                self.main_window.output_res_bw.setText(f"{res_bw / 1e6:.2f} MHz")
            elif res_bw >= 1e3:
                self.main_window.output_res_bw.setText(f"{res_bw / 1e3:.2f} kHz")
            elif res_bw > 0:
                self.main_window.output_res_bw.setText(f"{res_bw:.2f} Hz")
            else:
                self.main_window.output_res_bw.setText("-")

            # VBW = RBW / avg_n  (approaches RBW when averaging is off)
            avg_n = getattr(self.main_window.display_manager, 'avg_n', 1)
            vbw = res_bw / max(avg_n, 1)
            if vbw >= 1e6:
                self.main_window.output_video_bw.setText(f"{vbw / 1e6:.2f} MHz")
            elif vbw >= 1e3:
                self.main_window.output_video_bw.setText(f"{vbw / 1e3:.2f} kHz")
            elif vbw > 0:
                self.main_window.output_video_bw.setText(f"{vbw:.2f} Hz")
            else:
                self.main_window.output_video_bw.setText("-")

            # FFT size (sample sources only)
            if self.main_window.current_source and isinstance(self.main_window.current_source, SampleDataSource):
                fft_sz = getattr(self.main_window.current_source, 'sample_count', None)
                self.main_window.output_sample_size.setText(str(fft_sz) if fft_sz else "-")
            else:
                self.main_window.output_sample_size.setText("-")

            # Update sample rate or sweep rate display
            if self.main_window.current_source:
                if isinstance(self.main_window.current_source, SampleDataSource):
                    # For sample sources: display sample rate in S/s or MS/s
                    sample_rate = self.main_window.current_source.sample_rate
                    self.main_window.label_sample_rate.setText("Sample Rate:")
                    if sample_rate >= 1e6:
                        self.main_window.output_sample_rate.setText(f"{sample_rate / 1e6:.2f} MS/s")
                    else:
                        self.main_window.output_sample_rate.setText(f"{sample_rate / 1e3:.2f} kS/s")
                elif isinstance(self.main_window.current_source, SweepDataSource):
                    self.main_window.label_sample_rate.setText("Sweep Time:")
                    sweep_rate = getattr(self.main_window.current_source, 'sweep_rate', None)
                    if sweep_rate:
                        ms = 1000.0 / sweep_rate
                        if ms >= 1000:
                            self.main_window.output_sample_rate.setText(f"{ms / 1000:.2f} s")
                        else:
                            self.main_window.output_sample_rate.setText(f"{ms:.1f} ms")
                    else:
                        self.main_window.output_sample_rate.setText("-")
                else:
                    self.main_window.label_sample_rate.setText("Sample Rate:")
                    self.main_window.output_sample_rate.setText("-")
            else:
                self.main_window.label_sample_rate.setText("Sample Rate:")
                self.main_window.output_sample_rate.setText("-")

            # Keep popout window title in sync with current frequency/source
            if self.main_window.is_popped_out and self.main_window.popout_window:
                self.main_window.popout_window.update_title()

            self.update_gain_display()
            logger.debug(f"Frequency values updated: RBW={res_bw:.2f} Hz")
        except Exception as e:
            self.main_window.status_label.setText(f"Error updating labels: {str(e)}")
            logger.error(f"Error updating labels: {str(e)}")

    def update_gain_display(self) -> None:
        """Update the Gain readout to reflect the current source's gain settings."""
        src = self.main_window.current_source
        # Use duck typing — avoids coupling to concrete datasource classes.
        if hasattr(src, 'lna_gain') and hasattr(src, 'vga_gain') and hasattr(src, 'amp_enabled'):
            amp = "A+" if src.amp_enabled else "A-"
            self.main_window.output_gain.setText(
                f"L:{src.lna_gain} V:{src.vga_gain} {amp}"
            )
        elif hasattr(src, '_gain'):
            gain = src._gain
            self.main_window.output_gain.setText(
                "Auto" if gain == 'auto' else f"{gain} dB"
            )
        else:
            self.main_window.output_gain.setText("-")

    def _update_display_bins(self) -> None:
        """Update display frequency bins for the active widget using current frequency range."""
        # Hold buffers and averaging buffers are now at the wrong frequencies
        self.main_window.display_manager._clear_hold()
        self.main_window.display_manager._data_proc.reset_sweep_averager()
        src = self.main_window.current_source
        if src is not None and hasattr(src, 'reset_averaging'):
            src.reset_averaging()
        num_bins = getattr(
            getattr(self.main_window, 'current_source', None), 'sample_count', 1024
        ) or 1024
        freq_bins = np.linspace(
            self.main_window.frequency.start,
            self.main_window.frequency.stop,
            num_bins
        )
        update_display_frequency_bins(self.main_window, freq_bins)

    def set_frequency_range(self, start: float, stop: float):
        if self._in_frequency_update:
            logger.debug("set_frequency_range re-entry suppressed")
            return
        self._in_frequency_update = True
        try:
            old_start = self.main_window.frequency.start
            old_stop = self.main_window.frequency.stop
            self.main_window.frequency.set_start_stop(start, stop)
            logger.debug(f"After set_frequency_range: start={self.main_window.frequency.start}, stop={self.main_window.frequency.stop}")
            self.update_frequency_values()
            self._update_display_bins()
            self.main_window.source_manager.update_source_frequency()
            self.main_window.source_manager.update_source_memory()
            if old_start != start or old_stop != stop:
                self.main_window.max_power_levels = None
                self.main_window.min_power_levels = None
            mm = getattr(self.main_window, 'marker_manager', None)
            if mm is not None and old_start is not None and old_stop is not None:
                mm.reposition_on_frequency_change(old_start, old_stop, start, stop)
            logger.debug(f"Set frequency range: start={start}, stop={stop}")
        except Exception as e:
            self.main_window.status_label.setText(f"Error setting frequency: {str(e)}")
            logger.error(f"Error setting frequency: {str(e)}")
        finally:
            self._in_frequency_update = False

    def change_entry_mode(self, mode: str):
        self.main_window.frequency_entry_mode = mode
        self.main_window.keypad.reset()
        _mode_labels = {
            EntryMode.CENTRE:            "Set centre frequency",
            EntryMode.START:             "Set start frequency",
            EntryMode.STOP:              "Set stop frequency",
            EntryMode.SPAN:              "Set span",
            EntryMode.REF_LEVEL:         "Set ref level (dBm)",
            EntryMode.DISPLAY_LINE:      "Set display line level (dBm)",
            EntryMode.THRESHOLD:         "Set peak threshold (dBm)",
            EntryMode.EXCURSION:         "Set excursion (dB)",
            EntryMode.PRESET_NAME:       "Type name — press Enter or Hz to confirm",
            EntryMode.CAL_OFFSET:        "Enter actual power (dBm), press dBm",
            EntryMode.CAL_OFFSET_DIRECT: "Enter cal offset (dB), press dB",
            EntryMode.MARKER:            "Marker active — dial to move",
            EntryMode.ZERO_SPAN_TIME:    "Zero Span — dial to adjust time window",
            EntryMode.ZERO_SPAN_TRIGGER: "Zero Span — dial to adjust trigger level",
            EntryMode.WF_FLOOR:          "Set waterfall floor (dBm)",
            EntryMode.WF_CEILING:        "Set waterfall ceiling (dBm)",
        }
        self.main_window.status_label.setText(_mode_labels.get(mode, f"Set {mode}"))
        self._update_unit_buttons(mode)
        logger.debug(f"Changed entry mode to {mode}")

    _DBM_MODES = frozenset({
        EntryMode.REF_LEVEL, EntryMode.DISPLAY_LINE, EntryMode.THRESHOLD,
        EntryMode.WF_FLOOR, EntryMode.WF_CEILING, EntryMode.CAL_OFFSET,
    })
    _DB_MODES  = frozenset({EntryMode.CAL_OFFSET_DIRECT, EntryMode.EXCURSION})
    _NONE_MODES = frozenset({EntryMode.MARKER, EntryMode.ZERO_SPAN_TIME, EntryMode.ZERO_SPAN_TRIGGER})

    def _update_unit_buttons(self, mode: str) -> None:
        """Update keypad unit button labels to match the current entry mode."""
        keypad = self.main_window.keypad
        if mode in self._DBM_MODES:
            keypad.button_ghz.setText("")
            keypad.button_mhz.setText("")
            keypad.button_khz.setText("")
            keypad.button_hz.setText("dBm")
        elif mode in self._DB_MODES:
            keypad.button_ghz.setText("")
            keypad.button_mhz.setText("")
            keypad.button_khz.setText("")
            keypad.button_hz.setText("dB")
        elif mode in self._NONE_MODES:
            keypad.button_ghz.setText("")
            keypad.button_mhz.setText("")
            keypad.button_khz.setText("")
            keypad.button_hz.setText("")
        elif mode == EntryMode.PRESET_NAME:
            keypad.button_ghz.setText("")
            keypad.button_mhz.setText("")
            keypad.button_khz.setText("")
            keypad.button_hz.setText("OK")
            self.main_window.setFocus()
        else:
            keypad.button_ghz.setText("GHz")
            keypad.button_mhz.setText("MHz")
            keypad.button_khz.setText("kHz")
            keypad.button_hz.setText("Hz")

    def on_keypad_change(self, value: str | None):
        self.main_window.input_value.setText(value if value else "")
        logger.debug(f"Keypad input changed: {value}")

    def _handle_value_entry(self, mode: str, value: float) -> bool:
        """Handle non-frequency entry modes. Returns True if handled."""
        mw = self.main_window
        if mode == 'ref_level':
            mw.ref_level = value
            mw.display_manager.set_amplitude_on_all_displays(mw.ref_level, mw.range_db)
            mw.keypad.reset()
            return True
        if mode == 'display_line':
            mw.display_line_level = value
            mw.display_manager._update_display_line()
            mw.status_label.setText(f"Display line: {value:.1f} dBm")
            mw.keypad.reset()
            return True
        if mode == 'threshold':
            mw.peak_threshold = value
            mw.threshold_enabled = True
            mw.display_manager._update_threshold_line()
            mw.status_label.setText(f"Peak threshold: {value:.1f} dBm")
            mw.keypad.reset()
            return True
        if mode == 'excursion':
            mw.peak_excursion = abs(value)
            mw.status_label.setText(f"Excursion: {mw.peak_excursion:.1f} dB")
            mw.keypad.reset()
            return True
        if mode == 'wf_floor':
            wf = mw.waterfall_widget
            wf.set_wf_range(value, max(value + 1, wf.wf_max_db))
            mw.status_label.setText(f"WF floor: {value:.1f} dBm")
            mw.keypad.reset()
            return True
        if mode == 'wf_ceiling':
            wf = mw.waterfall_widget
            wf.set_wf_range(min(value - 1, wf.wf_min_db), value)
            mw.status_label.setText(f"WF ceiling: {value:.1f} dBm")
            mw.keypad.reset()
            return True
        if mode == 'cal_offset':
            # User entered the actual (known) power; compute offset = actual − measured
            measured    = mw.calibration_manager.pending_measured_db
            cal_freq    = mw.calibration_manager.pending_freq_hz
            source_type = mw.source_manager.last_source_type
            if measured is not None and source_type is not None:
                offset = mw.calibration_manager.set_from_marker(
                    source_type, measured, value, cal_freq_hz=cal_freq)
                mw.display_manager._refresh_source_label()
                name = mw.source_manager.SOURCE_DISPLAY_NAMES.get(source_type, source_type)
                mw.status_label.setText(f"{name}: cal offset {offset:+.1f} dB applied")
            mw.calibration_manager.pending_measured_db = None
            mw.calibration_manager.pending_freq_hz     = None
            mw.keypad.reset()
            return True
        if mode == 'cal_offset_direct':
            # User entered the dB offset directly
            source_type = mw.source_manager.last_source_type
            if source_type is not None:
                mw.calibration_manager.set_offset(source_type, value)
                mw.display_manager._refresh_source_label()
                name = mw.source_manager.SOURCE_DISPLAY_NAMES.get(source_type, source_type)
                mw.status_label.setText(f"{name}: cal offset {value:+.1f} dB set")
            mw.keypad.reset()
            return True
        return False

    def on_frequency_select(self, freq: int):
        try:
            mode = self.main_window.frequency_entry_mode

            if self._handle_value_entry(mode, float(freq)):
                return

            if mode == 'marker':
                mm = getattr(self.main_window, 'marker_manager', None)
                if mm and mm.active_marker:
                    marker = mm.markers[mm.active_marker]
                    if marker.kind == 'freq':
                        f = self.main_window.frequency
                        marker.position = max(f.start, min(f.stop, float(freq)))
                        mm._sync_display(mm.active_marker)
                        mm._refresh_status()
                self.main_window.keypad.reset()
                return

            # Determine max span from the source limits table (single source of truth)
            src_type   = self.main_window.source_manager.last_source_type
            src_limits = self.main_window.source_manager._SOURCE_LIMITS
            lim        = src_limits.get(src_type) if src_type else None
            if lim:
                max_span    = lim['max_span']
                source_name = self.main_window.source_manager.SOURCE_DISPLAY_NAMES.get(
                    src_type, src_type
                )
            else:
                max_span    = float('inf')
                source_name = "No source"

            f = self.main_window.frequency
            old_stop  = f.stop
            old_start = f.start

            match mode:
                case 'centre':
                    f.set_centre(freq)
                case 'start':
                    f.set_start(freq)
                case 'stop':
                    f.set_stop(freq)
                case 'span':
                    if freq > max_span:
                        self.main_window.status_label.setText(
                            f"Span limited to {format_hz(max_span)} for {source_name}"
                        )
                        logger.warning(f"Span limited to {max_span} Hz for {source_name}")
                        return
                    f.set_span(freq)
                case _:
                    logger.warning(f"on_frequency_select: unhandled mode '{mode}'")
                    return

            self.update_frequency_values()
            self._update_display_bins()
            self.main_window.source_manager.update_source_frequency()
            self.main_window.source_manager.update_source_memory()

            # Inform the user when the window was slid rather than anchored
            if mode == 'start' and f.stop != old_stop:
                self.main_window.status_label.setText("Start set — stop shifted to maintain span")
            elif mode == 'stop' and f.start != old_start:
                self.main_window.status_label.setText("Stop set — start shifted to maintain span")
            else:
                self.main_window.status_label.setText(f"{mode.capitalize()} frequency set")

            self.main_window.keypad.reset()
            logger.debug(f"Frequency selected: {freq} for {mode}")
        except Exception as e:
            self.main_window.status_label.setText(f"Error setting frequency: {str(e)}")
            logger.error(f"Error setting frequency: {str(e)}")

    # ------------------------------------------------------------------
    # Preset contribution
    # ------------------------------------------------------------------

    def capture_preset(self) -> dict:
        freq = self.main_window.frequency
        return {
            'freq_start': float(freq.start) if freq.start is not None else None,
            'freq_stop':  float(freq.stop)  if freq.stop  is not None else None,
        }

    def apply_preset(self, s: dict) -> None:
        start = s.get('freq_start')
        stop  = s.get('freq_stop')
        if start is not None and stop is not None:
            self.set_frequency_range(start, stop)
