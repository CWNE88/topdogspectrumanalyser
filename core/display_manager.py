import numpy as np
from PyQt6.QtWidgets import QPushButton
from datasources.base import SweepDataSource, SampleDataSource
from datasources.rtl_sweep import RtlSweepDataSource
from datasources.hackrf_sweep import HackRFSweepDataSource
from datasources.hackrf_samples import HackrfSamplesDataSource
from datasources.rtl_samples import RtlSamplesDataSource
from menu.menu_manager import MenuItem
from utils.constants import DisplayMode, UIConstants, FrequencyPresets, MenuButtonId, FFTSize, AmplitudeConstants, SourceType, SourceLimits
from utils.frequency_helpers import format_hz
from utils.validators import clamp_centre_span
from core.export_manager import ExportManager
from core.display_data_processor import DataProcessor
from core.tare_state import TareState
from core.duty_cycle import DutyCycleAnalyser
from typing import Optional, Dict, Callable
import logging

logger = logging.getLogger(__name__)


class DisplayManager:
    """Manages display widgets, UI controls, and menu routing.

    Data acquisition and processing is delegated to DataProcessor.
    Image export is delegated to ExportManager.
    """

    DISPLAY_WIDGETS_MAP = {
        DisplayMode.TWO_D:             lambda mw: mw.two_d_widget,
        DisplayMode.THREE_D:           lambda mw: mw.three_d_widget,
        DisplayMode.WATERFALL:         lambda mw: mw.waterfall_widget,
        DisplayMode.SURFACE:           lambda mw: mw.surface_widget,
        DisplayMode.CONSTELLATION_2D:  lambda mw: mw.constellation_2d_widget,
        DisplayMode.CONSTELLATION_3D:  lambda mw: mw.constellation_3d_widget,
        DisplayMode.ZERO_SPAN:         lambda mw: mw.zero_span_widget,
        DisplayMode.RIBBON:            lambda mw: mw.ribbon_widget,
        DisplayMode.DENSITY:           lambda mw: mw.density_widget,
    }

    def __init__(self, main_window):
        self.main_window = main_window
        self.tare_state  = TareState()

        # Trace A/B memory — owned here, not on MainWindow
        self.trace_a:         Optional[np.ndarray] = None
        self.trace_a_freq:    Optional[np.ndarray] = None
        self.trace_a_visible: bool                 = False
        self.trace_b:         Optional[np.ndarray] = None
        self.trace_b_freq:    Optional[np.ndarray] = None
        self.trace_b_visible: bool                 = False
        self.trace_ab_enabled: bool                = False

        # Constellation display settings
        self.constellation_modulation: str   = "qpsk"
        self.constellation_range:      float = 1.5
        self.constellation_points:     int   = 2000

        # Trace display settings
        self.persistence_mode:   str  = "off"
        self.live_trace_visible: bool = True

        # Averaging state
        self.avg_mode: str = "off"
        self.avg_n:    int = 1

        # Duty cycle
        self.duty_cycle_enabled:  bool = False
        self.duty_cycle_analyser = DutyCycleAnalyser()

        # Peak / hold UI state
        self.peak_search_enabled:     bool = False
        self.max_peak_search_enabled: bool = False
        self.peak_list_enabled:       bool = False

        # Zero span
        self.zero_span_active:        bool  = False
        self.zero_span_trigger_mode:  str   = "free_run"
        self.zero_span_trigger_level: float = 0.0
        self.zero_span_time_window:   float = 0.01
        self.zero_span_buffer               = None

        self._data_proc  = DataProcessor(main_window, self)
        self._exporter   = ExportManager(main_window)
        self.menu_actions: Dict[str, Callable] = self._build_menu_actions()
        logger.debug("DisplayManager initialised")

    # ------------------------------------------------------------------
    # Public timer entry point (delegated to DataProcessor)
    # ------------------------------------------------------------------

    def update_data(self) -> None:
        """Periodic timer callback — delegates to DataProcessor."""
        self._data_proc.update_data()


    def set_peak_search(self, enabled: bool) -> None:
        """Set peak search to a specific state (used by preset restore)."""
        if self.peak_search_enabled != enabled:
            self.toggle_peak_search()

    def set_max_peak_search(self, enabled: bool) -> None:
        """Set max hold to a specific state (used by preset restore)."""
        if self.max_peak_search_enabled != enabled:
            self.toggle_max_peak_search()

    def toggle_peak_search(self):
        """Toggle peak search functionality."""
        mw = self.main_window
        self.peak_search_enabled = not self.peak_search_enabled
        style = UIConstants.BUTTON_ENABLED_STYLE if self.peak_search_enabled else UIConstants.BUTTON_INACTIVE_STYLE
        mw.button_peak_search.setStyleSheet(style)
        for widget_getter in self.DISPLAY_WIDGETS_MAP.values():
            widget = widget_getter(mw)
            if hasattr(widget, 'set_peak_search_enabled'):
                widget.set_peak_search_enabled(self.peak_search_enabled)
        if mw.is_popped_out and mw.popout_window:
            popped = mw.popout_window.popped_widget
            if popped and hasattr(popped, 'set_peak_search_enabled'):
                popped.set_peak_search_enabled(self.peak_search_enabled)
        status = "enabled" if self.peak_search_enabled else "disabled"
        mw.status_label.setText(f"Peak Search {status}")
        logger.debug(f"Peak search: {status}")

    def toggle_peak_list(self):
        """Toggle top-5 peak list."""
        mw = self.main_window
        self.peak_list_enabled = not self.peak_list_enabled
        if not self.peak_list_enabled:
            widget = mw.two_d_widget
            if hasattr(widget, 'set_peak_list'):
                widget.set_peak_list([])
            readout = getattr(mw, 'marker_readout_label', None)
            if readout is not None:
                readout.setText("")
        status = "on" if self.peak_list_enabled else "off"
        mw.status_label.setText(f"Peak List {status}")

    def toggle_max_peak_search(self):
        """Toggle max hold functionality."""
        mw = self.main_window
        self.max_peak_search_enabled = not self.max_peak_search_enabled
        style = UIConstants.BUTTON_ENABLED_STYLE if self.max_peak_search_enabled else UIConstants.BUTTON_INACTIVE_STYLE
        mw.button_max_hold.setStyleSheet(style)
        if self.max_peak_search_enabled:
            mw.max_power_levels = None  # start fresh on each enable
        for mode in [DisplayMode.TWO_D, DisplayMode.THREE_D]:
            widget = self.DISPLAY_WIDGETS_MAP[mode](mw)
            if hasattr(widget, 'set_max_peak_search_enabled'):
                widget.set_max_peak_search_enabled(self.max_peak_search_enabled)
        if mw.is_popped_out and mw.popout_window:
            popped = mw.popout_window.popped_widget
            if popped and hasattr(popped, 'set_max_peak_search_enabled'):
                popped.set_max_peak_search_enabled(self.max_peak_search_enabled)
        status = "enabled" if self.max_peak_search_enabled else "disabled"
        mw.status_label.setText(f"Max Hold {status}")
        logger.debug(f"Max hold: {status}")

    def toggle_hold(self):
        """Toggle pausing of display updates."""
        mw = self.main_window
        mw.paused = not mw.paused
        style = UIConstants.BUTTON_ENABLED_STYLE if mw.paused else UIConstants.BUTTON_INACTIVE_STYLE
        mw.button_hold.setStyleSheet(style)
        status = "paused" if mw.paused else "resumed"
        mw.status_label.setText(f"Updates {status}")
        logger.debug(f"Updates: {status}")

    def toggle_min_hold(self) -> None:
        """Toggle min hold accumulation."""
        mw = self.main_window
        mw.min_hold_enabled = not mw.min_hold_enabled
        mw.min_power_levels = None  # reset buffer on toggle
        style = UIConstants.BUTTON_ENABLED_STYLE if mw.min_hold_enabled else UIConstants.BUTTON_INACTIVE_STYLE
        for widget_getter in self.DISPLAY_WIDGETS_MAP.values():
            widget = widget_getter(mw)
            if hasattr(widget, 'set_min_hold_enabled'):
                widget.set_min_hold_enabled(mw.min_hold_enabled)
        if mw.is_popped_out and mw.popout_window:
            w = mw.popout_window.popped_widget
            if w and hasattr(w, 'set_min_hold_enabled'):
                w.set_min_hold_enabled(mw.min_hold_enabled)
        status = "enabled" if mw.min_hold_enabled else "disabled"
        mw.status_label.setText(f"Min Hold {status}")
        logger.debug(f"Min hold: {status}")

    def _clear_hold(self, notify: bool = False) -> None:
        """Clear both max and min hold buffers.

        Args:
            notify: When True, update the status label (use for user-triggered clears).
        """
        mw = self.main_window
        mw.max_power_levels = None
        mw.min_power_levels = None
        if notify:
            mw.status_label.setText("Hold buffers cleared")
        logger.debug("Hold buffers cleared")

    def set_analysis_mode(self, mode: str) -> None:
        """Switch analysis mode: 'fft' | 'psd' | 'constellation'."""
        mw = self.main_window
        if not isinstance(mw.current_source, SampleDataSource):
            mw.status_label.setText(f"{mode.upper()} mode only available for sample sources")
            return

        mw.analysis_mode = mode

        psd_on = (mode == "psd")
        if hasattr(mw.current_source, 'set_psd_mode'):
            mw.current_source.set_psd_mode(psd_on)

        idx = mw._resolve_display_index()
        if idx != mw.current_stacked_index:
            self.set_display(idx, UIConstants.BUTTON_ACTIVE_STYLE, None)

        if mode == "constellation":
            mw.constellation_2d_widget.set_modulation(self.constellation_modulation)
            mw.constellation_2d_widget.set_range(self.constellation_range)
            mw.constellation_2d_widget.set_max_points(self.constellation_points)
            mw.constellation_3d_widget.set_range(self.constellation_range)
            mw.constellation_3d_widget.set_max_points(self.constellation_points)

        if mode != "constellation":
            readout = getattr(mw, 'marker_readout_label', None)
            if readout is not None:
                readout.setText("")

        labels = {"fft": "FFT mode", "psd": "PSD mode (dB/Hz)", "constellation": "Constellation mode"}
        mw.status_label.setText(labels.get(mode, mode))
        logger.debug(f"Analysis mode → {mode}")

    def _reset_dsp_state(self) -> None:
        """Clear all hold/tare/averaging state — call before starting a new source."""
        mw = self.main_window
        mw.live_power_levels = None
        self._clear_hold()
        mw.frequency_bins = None
        mw.tare_active = False
        mw.baseline_power_levels = None
        self.tare_state = TareState()
        if mw.current_source and hasattr(mw.current_source, 'reset_averaging'):
            mw.current_source.reset_averaging()
        self._data_proc.reset_sweep_averager()
        logger.debug("DSP state reset")

    def _switch_display_format(self, fmt: int) -> None:
        """Switch display format, handling constellation-vs-spectrum routing."""
        mw = self.main_window
        # Exit zero span when switching to a spectrum display
        self._exit_zero_span()
        # Waterfall/Surface requested while in constellation → exit constellation
        if mw.analysis_mode == "constellation" and fmt in (DisplayMode.WATERFALL, DisplayMode.SURFACE):
            mw.analysis_mode = "fft"
            if hasattr(mw.current_source, 'set_psd_mode'):
                mw.current_source.set_psd_mode(False)

        mw.display_format = fmt
        idx = mw._resolve_display_index()
        self.set_display(idx, UIConstants.BUTTON_ACTIVE_STYLE, None)

        # Open the display-specific soft-button menu
        _display_menu = {
            DisplayMode.TWO_D:     "2D\nDisplay",
            DisplayMode.THREE_D:   "3D\nDisplay",
            DisplayMode.WATERFALL: "Waterfall\nDisplay",
            DisplayMode.SURFACE:   "Surface\nDisplay",
            DisplayMode.RIBBON:    "Ribbon\nDisplay",
            DisplayMode.DENSITY:   "Density\nDisplay",
        }
        mw.menu.select_menu(_display_menu.get(fmt, "Display"))

    def toggle_duty_cycle(self) -> None:
        """Toggle duty cycle display overlay."""
        mw = self.main_window
        if not isinstance(mw.current_source, SampleDataSource):
            mw.status_label.setText("Duty cycle only available for sample sources")
            return
        self.duty_cycle_enabled = not self.duty_cycle_enabled
        if not self.duty_cycle_enabled:
            self.duty_cycle_analyser.reset()
            readout = getattr(mw, 'marker_readout_label', None)
            if readout is not None:
                readout.setText("")
        status = "on" if self.duty_cycle_enabled else "off"
        mw.status_label.setText(f"Duty cycle {status}")
        logger.debug(f"Duty cycle {status}")

    def _set_constellation_modulation(self, mod: str) -> None:
        mw = self.main_window
        self.constellation_modulation = mod
        mw.constellation_2d_widget.set_modulation(mod)
        mw.constellation_3d_widget.set_modulation(mod)
        mw.status_label.setText(f"Constellation: {mod.upper()}")

    def _set_constellation_range(self, r: float) -> None:
        mw = self.main_window
        self.constellation_range = r
        mw.constellation_2d_widget.set_range(r)
        mw.constellation_3d_widget.set_range(r)
        mw.status_label.setText(f"Constellation range: ±{r}")

    def _set_constellation_points(self, n: int) -> None:
        mw = self.main_window
        self.constellation_points = n
        mw.constellation_2d_widget.set_max_points(n)
        mw.constellation_3d_widget.set_max_points(n)
        label = f"{n//1000}k" if n >= 1000 else str(n)
        mw.status_label.setText(f"Constellation points: {label}")

    def _set_constellation_mode(self, mode: str) -> None:
        """Set density/scatter mode on the 2D constellation widget."""
        mw = self.main_window
        if hasattr(mw, 'constellation_2d_widget'):
            mw.constellation_2d_widget.set_mode(mode)
        mw.status_label.setText(f"Constellation: {mode}")

    def _set_3d_history_lines(self, n: int) -> None:
        mw = self.main_window
        if hasattr(mw, 'three_d_widget'):
            mw.three_d_widget.set_history_lines(n)
        mw.status_label.setText(f"3D history: {n} lines")

    def _toggle_3d_grid(self) -> None:
        mw = self.main_window
        w = getattr(mw, 'three_d_widget', None)
        if w is None:
            return
        w.set_grid_visible(not w._grid_visible)
        state = "on" if w._grid_visible else "off"
        mw.status_label.setText(f"3D grid {state}")

    def _toggle_3d_auto_rotate(self) -> None:
        mw = self.main_window
        w = getattr(mw, 'three_d_widget', None)
        if w is None:
            return
        w.toggle_auto_rotate()
        state = "on" if w.auto_rotate else "off"
        mw.status_label.setText(f"3D auto-rotate {state}")

    def _set_surface_history_lines(self, n: int) -> None:
        mw = self.main_window
        if hasattr(mw, 'surface_widget'):
            mw.surface_widget.set_history_lines(n)
        mw.status_label.setText(f"Surface history: {n} lines")

    def _toggle_surface_auto_rotate(self) -> None:
        mw = self.main_window
        w = getattr(mw, 'surface_widget', None)
        if w is None:
            return
        w.toggle_auto_rotate()
        state = "on" if w.auto_rotate else "off"
        mw.status_label.setText(f"Surface auto-rotate {state}")

    # ------------------------------------------------------------------
    # Display line
    # ------------------------------------------------------------------

    def _toggle_display_line(self) -> None:
        mw = self.main_window
        mw.display_line_enabled = not mw.display_line_enabled
        self._update_display_line()
        status = "on" if mw.display_line_enabled else "off"
        mw.status_label.setText(f"Display line {status}: {mw.display_line_level:.1f} dBm")

    def _update_display_line(self) -> None:
        mw = self.main_window
        mw.two_d_widget.set_display_line(mw.display_line_enabled, mw.display_line_level)
        if hasattr(mw.three_d_widget, 'set_display_line'):
            mw.three_d_widget.set_display_line(mw.display_line_enabled, mw.display_line_level)
        mw.density_widget.set_display_line(mw.display_line_enabled, mw.display_line_level)

    def _enter_display_line_level(self) -> None:
        self.main_window.frequency_manager.change_entry_mode('display_line')

    # ------------------------------------------------------------------
    # Peak threshold & excursion
    # ------------------------------------------------------------------

    def _enter_threshold(self) -> None:
        mw = self.main_window
        if mw.threshold_enabled:
            mw.threshold_enabled = False
            self._update_threshold_line()
            mw.status_label.setText("Peak threshold off")
        else:
            mw.threshold_enabled = True
            self._update_threshold_line()
            mw.frequency_manager.change_entry_mode('threshold')

    def _update_threshold_line(self) -> None:
        mw = self.main_window
        mw.two_d_widget.set_threshold_line(mw.threshold_enabled, mw.peak_threshold)
        mw.density_widget.set_threshold_line(mw.threshold_enabled, mw.peak_threshold)

    def _enter_excursion(self) -> None:
        self.main_window.frequency_manager.change_entry_mode('excursion')

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _set_persistence(self, mode: str) -> None:
        mw = self.main_window
        self.persistence_mode = mode
        mw.two_d_widget.set_persistence(mode)
        mw.density_widget.set_persistence(mode)
        mw.status_label.setText(f"Persistence: {mode}")
        logger.debug(f"Persistence set to {mode}")

    # ------------------------------------------------------------------
    # Trace A/B
    # ------------------------------------------------------------------

    def _store_trace_a(self) -> None:
        mw = self.main_window
        if mw.live_power_levels is None:
            mw.status_label.setText("No data to store")
            return
        self.trace_a = mw.live_power_levels.copy()
        self.trace_a_freq = mw.frequency_bins.copy() if mw.frequency_bins is not None else None
        self.trace_a_visible = True
        mw.two_d_widget.update_trace_a(self.trace_a_freq, self.trace_a)
        if self.trace_ab_enabled and self.trace_b is not None:
            self._compute_trace_ab()
        mw.status_label.setText("Trace A stored")

    def _toggle_trace_a(self) -> None:
        mw = self.main_window
        if self.trace_a is None:
            mw.status_label.setText("No Trace A stored")
            return
        self.trace_a_visible = not self.trace_a_visible
        mw.two_d_widget.update_trace_a(
            self.trace_a_freq if self.trace_a_visible else None,
            self.trace_a if self.trace_a_visible else None
        )
        mw.status_label.setText(f"Trace A {'shown' if self.trace_a_visible else 'hidden'}")

    def _store_trace_b(self) -> None:
        mw = self.main_window
        if mw.live_power_levels is None:
            mw.status_label.setText("No data to store")
            return
        self.trace_b = mw.live_power_levels.copy()
        self.trace_b_freq = mw.frequency_bins.copy() if mw.frequency_bins is not None else None
        self.trace_b_visible = True
        mw.two_d_widget.update_trace_b(self.trace_b_freq, self.trace_b)
        if self.trace_ab_enabled and self.trace_a is not None:
            self._compute_trace_ab()
        mw.status_label.setText("Trace B stored")

    def _toggle_trace_b(self) -> None:
        mw = self.main_window
        if self.trace_b is None:
            mw.status_label.setText("No Trace B stored")
            return
        self.trace_b_visible = not self.trace_b_visible
        mw.two_d_widget.update_trace_b(
            self.trace_b_freq if self.trace_b_visible else None,
            self.trace_b if self.trace_b_visible else None
        )
        mw.status_label.setText(f"Trace B {'shown' if self.trace_b_visible else 'hidden'}")

    def _toggle_trace_ab(self) -> None:
        mw = self.main_window
        if self.trace_a is None or self.trace_b is None:
            mw.status_label.setText("Store both Trace A and Trace B first")
            return
        self.trace_ab_enabled = not self.trace_ab_enabled
        if self.trace_ab_enabled:
            self._compute_trace_ab()
        else:
            mw.two_d_widget.update_trace_ab_diff(None, None)
        mw.status_label.setText(f"A-B {'enabled' if self.trace_ab_enabled else 'disabled'}")

    def _clear_traces(self) -> None:
        mw = self.main_window
        self.trace_a = self.trace_a_freq = None
        self.trace_b = self.trace_b_freq = None
        self.trace_a_visible = self.trace_b_visible = self.trace_ab_enabled = False
        mw.two_d_widget.clear_all_traces()
        mw.status_label.setText("Traces cleared")

    def _compute_trace_ab(self) -> None:
        """Compute static Trace A − Trace B and push to the display once."""
        mw = self.main_window
        if self.trace_a is None or self.trace_b is None:
            return
        if len(self.trace_a) != len(self.trace_b):
            mw.status_label.setText("A-B: traces have different lengths")
            return
        freq = self.trace_a_freq if self.trace_a_freq is not None else mw.frequency_bins
        diff = self.trace_a - self.trace_b
        mw.two_d_widget.update_trace_ab_diff(freq, diff)

    def _toggle_live_trace(self) -> None:
        mw = self.main_window
        self.live_trace_visible = not self.live_trace_visible
        mw.two_d_widget.set_live_visible(self.live_trace_visible)
        mw.status_label.setText(f"Live trace {'on' if self.live_trace_visible else 'off'}")

    def _activate_sample_source(self, source_id: str) -> None:
        """Start a sample source and preserve the current analysis mode."""
        mw = self.main_window
        mw.source_manager.set_source(source_id)
        self.set_analysis_mode(mw.analysis_mode)
        if source_id == SourceType.HACKRF_SAMPLES.value:
            mw.menu.select_menu("HackRF\nSamples")

    _FULL_SPAN = {
        SourceType.HACKRF_SWEEP.value: (
            FrequencyPresets.HACKRF_SWEEP_FULL_START,
            FrequencyPresets.HACKRF_SWEEP_FULL_STOP,
            "Full span: 0 – 7 GHz",
        ),
        SourceType.RTL_SWEEP.value: (
            FrequencyPresets.RTL_SWEEP_FULL_START,
            FrequencyPresets.RTL_SWEEP_FULL_STOP,
            "Full span: 24 MHz – 1.766 GHz",
        ),
    }

    def _set_full_span(self) -> None:
        mw = self.main_window
        entry = self._FULL_SPAN.get(mw.source_manager.last_source_type)
        if entry:
            start, stop, label = entry
            mw.frequency_manager.set_frequency_range(start, stop)
            mw.status_label.setText(label)
        else:
            mw.status_label.setText("Full span only available for sweep sources")

    def _exit_zero_span(self) -> None:
        mw = self.main_window
        if not self.zero_span_active:
            return
        self.zero_span_active = False
        self.zero_span_buffer = None
        idx = mw._resolve_display_index()
        self.set_display(idx, UIConstants.BUTTON_ACTIVE_STYLE, None)
        logger.debug("Zero span exited")

    def _set_zero_span(self) -> None:
        mw = self.main_window
        if not isinstance(mw.current_source, SampleDataSource):
            mw.status_label.setText("Zero Span only available for sample sources")
            mw.menu.go_back()
            return
        self.zero_span_active = True
        self.zero_span_buffer = None
        mw.zero_span_widget._first_data = True
        mw.zero_span_widget.set_trigger_mode(self.zero_span_trigger_mode)
        mw.zero_span_widget.set_trigger_level(self.zero_span_trigger_level)
        mw.zero_span_widget.set_drag_callback(lambda v: setattr(self, 'zero_span_trigger_level', v))
        self.set_display(DisplayMode.ZERO_SPAN, "", None)
        mw.status_label.setText("Zero Span — dial Time button to adjust window")
        logger.debug("Zero span activated")

    def _set_zero_span_trigger_mode(self, mode: str) -> None:
        mw = self.main_window
        self.zero_span_trigger_mode = mode
        mw.zero_span_widget.set_trigger_mode(mode)
        if mode in ("rise", "fall"):
            mw.frequency_manager.change_entry_mode('zero_span_trigger')
        else:
            mw.frequency_manager.change_entry_mode('zero_span_time')

    def _enter_zero_span_time(self) -> None:
        self.main_window.frequency_manager.change_entry_mode('zero_span_time')

    def _set_audio_channel(self, mode: str) -> None:
        mw = self.main_window
        src = mw.current_source
        if hasattr(src, 'set_channel_mode'):
            src.set_channel_mode(mode)
            mw.status_label.setText(f"Audio channel: {mode}")
        else:
            mw.status_label.setText("Not an audio source")

    def _set_averaging(self, mode: str, n: int) -> None:
        """Apply trace averaging to the active source and update state/display."""
        mw = self.main_window
        src = mw.current_source
        if hasattr(src, 'set_averaging'):
            src.set_averaging(mode, n)
        self._data_proc._sweep_averager.set_mode(mode, n)
        self.avg_mode = mode
        self.avg_n = n
        mw.frequency_manager.update_frequency_values()

        if mode == "off":
            label = "Averaging off"
        else:
            kind = "Exp" if mode == "exp" else "Lin"
            label = f"Averaging {kind} ×{n}"
        mw.status_label.setText(label)
        logger.debug(f"Averaging set: mode={mode}, n={n}")

    def _spectrum_display_buttons(self) -> list:
        """Physical display-mode buttons to reset when switching display.
        Empty — display mode buttons have been repurposed; mode is selected via soft menu."""
        return []

    def set_display(self, index: int, style: str, button: QPushButton):
        """Set the active display widget."""
        mw = self.main_window
        if mw.is_popped_out:
            mw.return_widget_from_popout()
            mw.current_stacked_index = index
            if index < DisplayMode.LOGO:
                for btn in self._spectrum_display_buttons():
                    btn.setStyleSheet(UIConstants.BUTTON_INACTIVE_STYLE)
                if button is not None:
                    button.setStyleSheet(style)
            mw.popout_current_display()
            logger.debug(f"Switched popout display to index: {index}")
            return

        if mw.current_stacked_index == DisplayMode.LOGO and index != DisplayMode.LOGO:
            mw.logo_timer.stop()
        elif index == DisplayMode.LOGO:
            mw.logo_timer.start(UIConstants.LOGO_TIMER_INTERVAL)

        mw.stacked_widget.setCurrentIndex(index)
        if index < DisplayMode.LOGO:
            for btn in self._spectrum_display_buttons():
                btn.setStyleSheet(UIConstants.BUTTON_INACTIVE_STYLE)
            if button is not None:
                button.setStyleSheet(style)
        mw.current_stacked_index = index
        logger.debug(f"Set display index: {index}")

    def _scale_centre_frequency(self, factor: float) -> None:
        """Scale the centre frequency by a given factor, preserving span.

        Args:
            factor: Multiplication factor (e.g. 0.5 to halve, 2 to double).
        """
        try:
            mw = self.main_window
            if mw.frequency.centre is None:
                mw.status_label.setText("Centre frequency not set")
                return
            current_span = mw.frequency.span or 0
            new_centre_scaled = mw.frequency.centre * factor
            src_type = mw.source_manager.last_source_type
            new_centre, span = clamp_centre_span(
                new_centre_scaled, current_span, src_type,
                mw.source_manager._SOURCE_LIMITS
            )
            new_start = new_centre - span / 2
            new_stop  = new_centre + span / 2

            mw.frequency_manager.set_frequency_range(new_start, new_stop)
            label = "halved" if factor < 1 else "doubled"
            mw.status_label.setText(f"Centre frequency {label}")
            logger.debug(f"Centre frequency scaled by {factor}: {new_centre} Hz")
        except Exception as e:
            self.main_window.status_label.setText("Error adjusting frequency")
            logger.error(f"Error scaling centre frequency: {e}")

    def divide_centre_frequency_by_two(self):
        """Halve the centre frequency, preserving span."""
        self._scale_centre_frequency(0.5)

    def multiply_centre_frequency_by_two(self):
        """Double the centre frequency, preserving span."""
        self._scale_centre_frequency(2.0)

    # ------------------------------------------------------------------
    # Amplitude
    # ------------------------------------------------------------------

    def set_amplitude_on_all_displays(self, ref_level: float, range_db: float) -> None:
        """Push new amplitude settings to every display widget (and any active popout).

        Args:
            ref_level: Reference level in dBm (top of screen).
            range_db: Total dB range shown (bottom = ref_level − range_db).
        """
        mw = self.main_window
        for widget_getter in self.DISPLAY_WIDGETS_MAP.values():
            widget = widget_getter(mw)
            if hasattr(widget, 'set_amplitude'):
                widget.set_amplitude(ref_level, range_db)
        if mw.is_popped_out and mw.popout_clone_widget:
            if hasattr(mw.popout_clone_widget, 'set_amplitude'):
                mw.popout_clone_widget.set_amplitude(ref_level, range_db)
        db_per_div = range_db / AmplitudeConstants.DIVISIONS
        mw.status_label.setText(
            f"Ref level: {ref_level:+.0f} dBm  |  {db_per_div:.4g} dB/div"
        )
        logger.debug(f"Amplitude set: ref_level={ref_level} dBm, range_db={range_db} dB")

    def _set_db_per_div(self, db_per_div: int) -> None:
        mw = self.main_window
        mw.range_db = db_per_div * AmplitudeConstants.DIVISIONS
        self.set_amplitude_on_all_displays(mw.ref_level, mw.range_db)

    def _update_tare_button_label(self, label: str) -> None:
        self.main_window.menu.update_item_label("Amplitude", MenuButtonId.TARE.value, label)

    def _clear_tare(self) -> None:
        mw = self.main_window
        mw.tare_active = False
        mw.baseline_power_levels = None
        mw.max_power_levels = None  # Max hold is now stale
        self.tare_state = TareState()
        self._update_tare_button_label("Trace\nNormalisation")

    def _tare_action(self) -> None:
        """Start collecting a tare baseline, or clear an existing one."""
        mw = self.main_window
        if mw.tare_active or self.tare_state.collecting:
            self._clear_tare()
            mw.status_label.setText("Tare cleared")
            logger.debug("Tare cleared by user")
        else:
            self.tare_state = TareState(collecting=True)
            self._update_tare_button_label("Clear\nNormalisation")
            mw.status_label.setText(
                f"Collecting normalisation baseline... {UIConstants.TARE_NUM_SAMPLES} frames remaining"
            )
            logger.debug("Tare collection started")

    def _toggle_log_freq(self) -> None:
        """Toggle the frequency axis between linear and logarithmic."""
        mw = self.main_window
        mw.log_freq = not mw.log_freq
        enabled = mw.log_freq
        for widget_getter in self.DISPLAY_WIDGETS_MAP.values():
            widget = widget_getter(mw)
            if hasattr(widget, 'set_log_freq'):
                widget.set_log_freq(enabled)
        if mw.is_popped_out and mw.popout_clone_widget:
            if hasattr(mw.popout_clone_widget, 'set_log_freq'):
                mw.popout_clone_widget.set_log_freq(enabled)
        mw.menu.update_item_label("Display", MenuButtonId.LOG_FREQ.value,
                                   "Lin\nFreq" if enabled else "Log\nFreq")
        mw.status_label.setText(f"Frequency axis: {'Log' if enabled else 'Linear'}")
        logger.debug(f"Frequency axis set to {'log' if enabled else 'linear'}")

    def _set_log_scale(self, enabled: bool) -> None:
        """Switch all display widgets between logarithmic (dBm) and linear (mW) amplitude."""
        mw = self.main_window
        mw.log_scale = enabled
        for widget_getter in self.DISPLAY_WIDGETS_MAP.values():
            widget = widget_getter(mw)
            if hasattr(widget, 'set_log_scale'):
                widget.set_log_scale(enabled)
        if mw.is_popped_out and mw.popout_clone_widget:
            if hasattr(mw.popout_clone_widget, 'set_log_scale'):
                mw.popout_clone_widget.set_log_scale(enabled)
        mw.status_label.setText(f"Amplitude scale: {'Log (dBm)' if enabled else 'Linear (mW)'}")
        logger.debug(f"Amplitude scale set to {'log' if enabled else 'linear'}")

    # ------------------------------------------------------------------
    # RF Gain
    # ------------------------------------------------------------------

    def _set_rtl_gain(self, gain) -> None:
        mw = self.main_window
        src = mw.current_source
        if hasattr(src, 'set_gain'):
            src.set_gain(gain)
            label = "Auto" if gain == 'auto' else f"{gain} dB"
            mw.status_label.setText(f"RTL gain: {label}")
            mw.frequency_manager.update_gain_display()
        else:
            mw.status_label.setText("RF gain: no RTL source active")

    def _set_hackrf_lna(self, db: int) -> None:
        mw = self.main_window
        src = mw.current_source
        if hasattr(src, 'set_gains'):
            src.set_gains(lna_gain=db)
            mw.hackrf_lna_gain = db
            mw.source_manager._write_last_state()
            mw.status_label.setText(f"HackRF LNA: {db} dB")
            mw.frequency_manager.update_gain_display()
        else:
            mw.status_label.setText("RF gain: no HackRF source active")

    def _set_hackrf_vga(self, db: int) -> None:
        mw = self.main_window
        src = mw.current_source
        if hasattr(src, 'set_gains'):
            src.set_gains(vga_gain=db)
            mw.hackrf_vga_gain = db
            mw.source_manager._write_last_state()
            mw.status_label.setText(f"HackRF VGA: {db} dB")
            mw.frequency_manager.update_gain_display()
        else:
            mw.status_label.setText("RF gain: no HackRF source active")

    def _set_hackrf_amp(self, enabled: bool) -> None:
        mw = self.main_window
        src = mw.current_source
        if hasattr(src, 'set_amplifier'):
            src.set_amplifier(enabled)
            mw.status_label.setText(f"HackRF amp {'on' if enabled else 'off'}")
            mw.frequency_manager.update_gain_display()
        else:
            mw.status_label.setText("RF gain: no HackRF source active")

    def _set_hackrf_dc_alpha(self, alpha: float) -> None:
        mw = self.main_window
        src = mw.current_source
        if hasattr(src, 'set_dc_alpha'):
            src.set_dc_alpha(alpha)
            mw.status_label.setText(f"DC alpha: {alpha}")
        else:
            mw.status_label.setText("DC alpha: no HackRF samples source active")

    def _calc_time_per_row(self) -> float:
        """Return seconds-per-waterfall-row for the active source."""
        src = self.main_window.current_source
        if isinstance(src, SweepDataSource):
            rate = getattr(src, 'sweep_rate', 0)
            return 1.0 / rate if rate > 0 else 0.0
        if isinstance(src, SampleDataSource):
            sr  = getattr(src, 'sample_rate', 0)
            fft = getattr(src, 'sample_count', 1024)
            return fft / sr if sr > 0 else 0.0
        return 0.0

    def _set_waterfall_colourmap(self, name: str, label: str) -> None:
        mw = self.main_window
        mw.waterfall_widget.set_colourmap(name)
        mw.status_label.setText(f"Waterfall colour: {label}")

    def _wf_set_span(self, seconds: float) -> None:
        mw = self.main_window
        mw.waterfall_widget.set_wf_time_span(seconds)
        label = f"{int(seconds)}s" if seconds < 60 else f"{int(seconds//60)}min"
        mw.status_label.setText(f"Waterfall span: {label}")

    def _wf_enter_floor(self) -> None:
        self.main_window.frequency_manager.change_entry_mode('wf_floor')

    def _wf_enter_ceiling(self) -> None:
        self.main_window.frequency_manager.change_entry_mode('wf_ceiling')

    def _wf_toggle_freeze(self) -> None:
        mw = self.main_window
        mw.waterfall_widget.toggle_freeze()
        state = "frozen" if mw.waterfall_widget.frozen else "live"
        mw.status_label.setText(f"Waterfall {state}")

    # ------------------------------------------------------------------
    # 2D display controls
    # ------------------------------------------------------------------

    def _2d_set_fill_type(self, fill_type: str) -> None:
        mw = self.main_window
        mw.two_d_widget.set_fill_type(fill_type)
        label = {"gradient": "Gradient", "solid": "Solid", "glow": "Glow", "off": "Off"}.get(fill_type, fill_type)
        mw.status_label.setText(f"2D fill: {label}")

    def _2d_set_colour(self, name: str) -> None:
        mw = self.main_window
        mw.two_d_widget.set_trace_colour(name)
        mw.status_label.setText(f"2D colour: {name}")

    # ------------------------------------------------------------------
    # Density display controls
    # ------------------------------------------------------------------

    def _density_set_colourmap(self, name: str) -> None:
        mw = self.main_window
        mw.density_widget.set_colourmap(name)
        mw.status_label.setText(f"Density colourmap: {name}")

    def _density_set_decay(self, mode: str) -> None:
        mw = self.main_window
        mw.density_widget.set_decay(mode)
        mw.status_label.setText(f"Density decay: {mode}")

    def _density_clear(self) -> None:
        mw = self.main_window
        mw.density_widget.clear_histogram()
        mw.status_label.setText("Density: cleared")

    # ------------------------------------------------------------------
    # Calibration controls
    # ------------------------------------------------------------------

    def _cal_reference_power(self) -> float | None:
        """Return the power level to use as the measured reference for calibration.

        Checks the active marker first (freq marker → interpolate from live data;
        power marker → use its value directly).  Falls back to the current peak.
        """
        mw = self.main_window
        levels = mw.live_power_levels
        bins   = mw.frequency_bins
        if levels is None or bins is None:
            return None
        lvl = levels[0] if isinstance(levels, tuple) else levels

        mm = getattr(mw, 'marker_manager', None)
        if mm and mm.active_marker:
            marker = mm.markers.get(mm.active_marker)
            if marker and marker.enabled and marker.position is not None:
                if marker.kind == 'freq':
                    idx = int(np.argmin(np.abs(bins - marker.position)))
                    return float(lvl[idx])
                if marker.kind == 'power':
                    return float(marker.position)
        return float(np.max(lvl))

    def _refresh_source_label(self) -> None:
        """Redraw the source label, appending (cal) when an offset is active."""
        mw = self.main_window
        source_type = mw.source_manager.last_source_type
        if source_type is None:
            return
        name  = mw.source_manager.SOURCE_DISPLAY_NAMES.get(source_type, source_type)
        if mw.calibration_manager.is_calibrated(source_type):
            info     = mw.calibration_manager.get_info(source_type)
            cal_freq = info.get('cal_freq_hz')
            ref_db   = info.get('reference_db')
            offset   = info.get('offset_db', 0.0)
            if cal_freq is not None:
                freq_str = f" @ {format_hz(cal_freq)}"
                pwr_str  = f" / {ref_db:.1f} dBm" if ref_db is not None else ""
                badge = f" (Calibrated{freq_str}{pwr_str})"
            else:
                badge = f" (Calibrated with {offset:+.1f} dB offset)"
        else:
            badge = ""
        mw.output_source.setText(f"Input: {name}{badge}")

    def cal_show_status(self) -> None:
        """Display current calibration status in the status label (called on Cal button press)."""
        mw = self.main_window
        source_type = mw.source_manager.last_source_type
        if not source_type:
            mw.status_label.setText("No active source")
            return
        name = mw.source_manager.SOURCE_DISPLAY_NAMES.get(source_type, source_type)
        cal  = mw.calibration_manager
        if cal.is_calibrated(source_type):
            info     = cal.get_info(source_type)
            offset   = info.get('offset_db', 0.0)
            freq_hz  = info.get('cal_freq_hz')
            freq_str = f" at {freq_hz / 1e6:.3f} MHz" if freq_hz else ""
            mw.status_label.setText(f"{name}: offset {offset:+.1f} dB{freq_str}")
        else:
            mw.status_label.setText(f"{name}: no calibration set")

    def _cal_set_from_marker(self) -> None:
        """Read current marker/peak power, then prompt user to enter actual power."""
        mw = self.main_window
        if mw.source_manager.last_source_type is None:
            mw.status_label.setText("No active source — start a source first")
            return
        measured = self._cal_reference_power()
        if measured is None:
            mw.status_label.setText("No signal data — wait for source to produce data")
            return

        # Record where the calibration is being done (for display purposes only)
        mm = getattr(mw, 'marker_manager', None)
        cal_freq = None
        if mm and mm.active_marker:
            marker = mm.markers.get(mm.active_marker)
            if marker and marker.enabled and marker.kind == 'freq' and marker.position is not None:
                cal_freq = marker.position
        if cal_freq is None:
            cal_freq = getattr(mw.frequency, 'centre', None)

        mw.calibration_manager.pending_measured_db = measured
        mw.calibration_manager.pending_freq_hz     = cal_freq

        name = mw.source_manager.SOURCE_DISPLAY_NAMES.get(
            mw.source_manager.last_source_type, mw.source_manager.last_source_type)
        mw.frequency_manager.change_entry_mode('cal_offset')
        mw.status_label.setText(
            f"{name} reads {measured:+.1f} dBm — enter actual power, press dBm")

    def _cal_enter_offset(self) -> None:
        """Prompt the user to type a calibration offset directly."""
        mw = self.main_window
        source_type = mw.source_manager.last_source_type
        if source_type is None:
            mw.status_label.setText("No active source")
            return
        mw.calibration_manager.pending_measured_db = None  # flags direct-offset mode
        name    = mw.source_manager.SOURCE_DISPLAY_NAMES.get(source_type, source_type)
        current = mw.calibration_manager.get_offset(source_type)
        mw.frequency_manager.change_entry_mode('cal_offset_direct')
        mw.status_label.setText(
            f"{name} current offset: {current:+.1f} dB — enter new offset, press dB")

    def _cal_clear(self) -> None:
        """Remove calibration for the current source."""
        mw = self.main_window
        source_type = mw.source_manager.last_source_type
        if source_type is None:
            mw.status_label.setText("No active source")
            return
        mw.calibration_manager.clear(source_type)
        self._refresh_source_label()
        name = mw.source_manager.SOURCE_DISPLAY_NAMES.get(source_type, source_type)
        mw.status_label.setText(f"Calibration cleared for {name}")

    # ------------------------------------------------------------------
    # Preset contribution
    # ------------------------------------------------------------------

    def capture_preset(self) -> dict:
        mw = self.main_window
        return {
            # Amplitude
            'ref_level':           mw.ref_level,
            'range_db':            mw.range_db,
            'log_scale':           mw.log_scale,
            'log_freq':            mw.log_freq,
            # Averaging / trace
            'avg_mode':            self.avg_mode,
            'avg_n':               self.avg_n,
            'persistence_mode':    self.persistence_mode,
            # Peak detection
            'threshold_enabled':   mw.threshold_enabled,
            'peak_threshold':      mw.peak_threshold,
            'peak_excursion':      mw.peak_excursion,
            # Display line
            'display_line_enabled': mw.display_line_enabled,
            'display_line_level':   mw.display_line_level,
            # Display format / analysis
            'display_mode':        int(mw.current_stacked_index),
            'analysis_mode':       mw.analysis_mode,
            'display_format':      int(mw.display_format),
            'duty_cycle_enabled':  self.duty_cycle_enabled,
            # Hold state
            'peak_search_enabled': self.peak_search_enabled,
            'max_hold_enabled':    self.max_peak_search_enabled,
            # Waterfall
            'wf_floor':     getattr(getattr(mw, 'waterfall_widget', None), 'wf_min_db',       -100.0),
            'wf_ceiling':   getattr(getattr(mw, 'waterfall_widget', None), 'wf_max_db',        -20.0),
            'wf_time_span': getattr(getattr(mw, 'waterfall_widget', None), 'wf_time_span',      60.0),
            'wf_colourmap': getattr(getattr(mw, 'waterfall_widget', None), '_colourmap_name', 'magma'),
            # 2D
            'two_d_fill_type': getattr(getattr(mw, 'two_d_widget', None), '_fill_type',         'off'),
            'two_d_colour':    getattr(getattr(mw, 'two_d_widget', None), '_trace_colour_name', 'green'),
            # Density
            'density_colourmap': getattr(getattr(mw, 'density_widget', None), '_colourmap_name', 'magma'),
            'density_decay':     getattr(getattr(mw, 'density_widget', None), '_decay_name',     'medium'),
            # 3D
            'three_d_history_lines': getattr(getattr(mw, 'three_d_widget', None), 'num_history_lines', 300),
            'three_d_grid_visible':  getattr(getattr(mw, 'three_d_widget', None), '_grid_visible', True),
            'three_d_auto_rotate':   getattr(getattr(mw, 'three_d_widget', None), 'auto_rotate', False),
        }

    def apply_preset(self, s: dict) -> None:
        mw = self.main_window

        # Amplitude
        mw.ref_level = s.get('ref_level', mw.ref_level)
        mw.range_db  = s.get('range_db',  mw.range_db)
        self.set_amplitude_on_all_displays(mw.ref_level, mw.range_db)
        self._set_log_scale(s.get('log_scale', True))

        # Frequency axis log/lin
        log_freq = s.get('log_freq', False)
        if mw.log_freq != log_freq:
            mw.log_freq = log_freq
            for getter in self.DISPLAY_WIDGETS_MAP.values():
                w = getter(mw)
                if hasattr(w, 'set_log_freq'):
                    w.set_log_freq(log_freq)
            mw.menu.update_item_label("Display", MenuButtonId.LOG_FREQ.value,
                                       "Lin\nFreq" if log_freq else "Log\nFreq")

        # Averaging / trace / persistence
        self._set_averaging(s.get('avg_mode', 'off'), s.get('avg_n', 1))
        self._set_persistence(s.get('persistence_mode', 'off'))

        # Peak detection
        mw.threshold_enabled = s.get('threshold_enabled', False)
        mw.peak_threshold    = s.get('peak_threshold', -100.0)
        mw.peak_excursion    = s.get('peak_excursion',   6.0)
        self._update_threshold_line()

        # Display line
        mw.display_line_enabled = s.get('display_line_enabled', False)
        mw.display_line_level   = s.get('display_line_level',   -50.0)
        self._update_display_line()

        self.set_peak_search(s.get('peak_search_enabled', False))
        self.set_max_peak_search(s.get('max_hold_enabled', False))

        # Analysis mode and display format
        analysis_mode  = s.get('analysis_mode', 'fft')
        display_format = s.get('display_format', DisplayMode.TWO_D)
        display_mode   = s.get('display_mode', DisplayMode.TWO_D)
        mw.analysis_mode  = analysis_mode
        mw.display_format = display_format if display_format is not None else display_mode
        if hasattr(mw.current_source, 'set_psd_mode'):
            mw.current_source.set_psd_mode(analysis_mode == 'psd')

        # Duty cycle
        duty_cycle = s.get('duty_cycle_enabled', False)
        self.duty_cycle_enabled = duty_cycle
        if not duty_cycle:
            self.duty_cycle_analyser.reset()
            readout = getattr(mw, 'marker_readout_label', None)
            if readout:
                readout.setText("")

        # Resolve and set display index
        self.set_display(mw._resolve_display_index(), UIConstants.BUTTON_ACTIVE_STYLE, None)

        # Waterfall
        wf = getattr(mw, 'waterfall_widget', None)
        if wf is not None:
            wf.set_wf_range(s.get('wf_floor', -100.0), s.get('wf_ceiling', -20.0))
            wf.set_wf_time_span(s.get('wf_time_span', 60.0))
            wf.set_colourmap(s.get('wf_colourmap', 'magma'))

        # 2D
        w2d = getattr(mw, 'two_d_widget', None)
        if w2d is not None:
            w2d.set_fill_type(s.get('two_d_fill_type', 'off'))
            w2d.set_trace_colour(s.get('two_d_colour', 'green'))

        # Density
        wd = getattr(mw, 'density_widget', None)
        if wd is not None:
            wd.set_colourmap(s.get('density_colourmap', 'magma'))
            wd.set_decay(s.get('density_decay', 'medium'))

        # 3D
        w3d = getattr(mw, 'three_d_widget', None)
        if w3d is not None:
            w3d.set_history_lines(s.get('three_d_history_lines', 300))
            w3d.set_grid_visible(s.get('three_d_grid_visible', True))
            if s.get('three_d_auto_rotate', False) != w3d.auto_rotate:
                w3d.toggle_auto_rotate()

    def _build_menu_actions(self) -> Dict[str, Callable]:
        """Assemble the full dispatch table from logical sub-groups."""
        return {
            **self._frequency_actions(),
            **self._source_actions(),
            **self._amplitude_actions(),
            **self._trace_actions(),
            **self._display_actions(),
            **self._gain_actions(),
            **self._waterfall_actions(),
            **self._marker_actions(),
            **self._analysis_actions(),
            **self._calibration_actions(),
            **self._preset_actions(),
            **self._export_actions(),
        }

    def _frequency_actions(self) -> dict:
        mw = self.main_window
        return {
            MenuButtonId.CENTRE_FREQUENCY.value: lambda: mw.frequency_manager.change_entry_mode('centre'),
            MenuButtonId.START_FREQUENCY.value:  lambda: mw.frequency_manager.change_entry_mode('start'),
            MenuButtonId.STOP_FREQUENCY.value:   lambda: mw.frequency_manager.change_entry_mode('stop'),
            MenuButtonId.SPAN.value:             lambda: mw.frequency_manager.change_entry_mode('span'),
            MenuButtonId.FULL_SPAN.value:        self._set_full_span,
            MenuButtonId.ZERO_SPAN.value:        self._set_zero_span,
            MenuButtonId.ISM_24.value: lambda: mw.frequency_manager.set_frequency_range(
                FrequencyPresets.ISM_2_4_GHZ_START, FrequencyPresets.ISM_2_4_GHZ_STOP),
            MenuButtonId.ISM_58.value: lambda: mw.frequency_manager.set_frequency_range(
                FrequencyPresets.ISM_5_8_GHZ_START, FrequencyPresets.ISM_5_8_GHZ_STOP),
            MenuButtonId.CF_DIVIDED_BY_TWO.value: self.divide_centre_frequency_by_two,
            MenuButtonId.CF_TIMES_TWO.value:      self.multiply_centre_frequency_by_two,
            # RTL sample rates (zero span exit handled inside set_rtl_sample_rate)
            MenuButtonId.SAMPLE_RATE_250K.value:  lambda: mw.source_manager.set_rtl_sample_rate(250_000),
            MenuButtonId.SAMPLE_RATE_1024K.value: lambda: mw.source_manager.set_rtl_sample_rate(1_024_000),
            MenuButtonId.SAMPLE_RATE_1440K.value: lambda: mw.source_manager.set_rtl_sample_rate(1_440_000),
            MenuButtonId.SAMPLE_RATE_1800K.value: lambda: mw.source_manager.set_rtl_sample_rate(1_800_000),
            MenuButtonId.SAMPLE_RATE_2000K.value: lambda: mw.source_manager.set_rtl_sample_rate(2_000_000),
            MenuButtonId.SAMPLE_RATE_2048K.value: lambda: mw.source_manager.set_rtl_sample_rate(2_048_000),
            MenuButtonId.SAMPLE_RATE_2400K.value: lambda: mw.source_manager.set_rtl_sample_rate(2_400_000),
            # HackRF sample rates
            MenuButtonId.HACKRF_SAMPLE_RATE_2M.value:  lambda: mw.source_manager.set_hackrf_sample_rate(2e6),
            MenuButtonId.HACKRF_SAMPLE_RATE_4M.value:  lambda: mw.source_manager.set_hackrf_sample_rate(4e6),
            MenuButtonId.HACKRF_SAMPLE_RATE_8M.value:  lambda: mw.source_manager.set_hackrf_sample_rate(8e6),
            MenuButtonId.HACKRF_SAMPLE_RATE_10M.value: lambda: mw.source_manager.set_hackrf_sample_rate(10e6),
            MenuButtonId.HACKRF_SAMPLE_RATE_16M.value: lambda: mw.source_manager.set_hackrf_sample_rate(16e6),
            MenuButtonId.HACKRF_SAMPLE_RATE_20M.value: lambda: mw.source_manager.set_hackrf_sample_rate(20e6),
            # Audio sample rates
            MenuButtonId.AUDIO_SAMPLE_RATE_8K.value:  lambda: mw.source_manager.set_audio_sample_rate(8_000),
            MenuButtonId.AUDIO_SAMPLE_RATE_11K.value: lambda: mw.source_manager.set_audio_sample_rate(11_025),
            MenuButtonId.AUDIO_SAMPLE_RATE_16K.value: lambda: mw.source_manager.set_audio_sample_rate(16_000),
            MenuButtonId.AUDIO_SAMPLE_RATE_22K.value: lambda: mw.source_manager.set_audio_sample_rate(22_050),
            MenuButtonId.AUDIO_SAMPLE_RATE_44K.value: lambda: mw.source_manager.set_audio_sample_rate(44_100),
            MenuButtonId.AUDIO_SAMPLE_RATE_48K.value: lambda: mw.source_manager.set_audio_sample_rate(48_000),
            MenuButtonId.AUDIO_SAMPLE_RATE_96K.value: lambda: mw.source_manager.set_audio_sample_rate(96_000),
            MenuButtonId.AUDIO_MONO.value:   lambda: self._set_audio_channel('mono'),
            MenuButtonId.AUDIO_LEFT.value:   lambda: self._set_audio_channel('left'),
            MenuButtonId.AUDIO_RIGHT.value:  lambda: self._set_audio_channel('right'),
            MenuButtonId.AUDIO_STEREO.value: lambda: self._set_audio_channel('stereo'),
            # HackRF Sweep RBW
            MenuButtonId.HACKRF_SWEEP_RBW_5K.value:   lambda: mw.source_manager.set_sweep_bin_size(5_000),
            MenuButtonId.HACKRF_SWEEP_RBW_10K.value:  lambda: mw.source_manager.set_sweep_bin_size(10_000),
            MenuButtonId.HACKRF_SWEEP_RBW_20K.value:  lambda: mw.source_manager.set_sweep_bin_size(20_000),
            MenuButtonId.HACKRF_SWEEP_RBW_30K.value:  lambda: mw.source_manager.set_sweep_bin_size(30_000),
            MenuButtonId.HACKRF_SWEEP_RBW_50K.value:  lambda: mw.source_manager.set_sweep_bin_size(50_000),
            MenuButtonId.HACKRF_SWEEP_RBW_100K.value: lambda: mw.source_manager.set_sweep_bin_size(100_000),
            MenuButtonId.HACKRF_SWEEP_RBW_200K.value: lambda: mw.source_manager.set_sweep_bin_size(200_000),
            MenuButtonId.HACKRF_SWEEP_RBW_500K.value: lambda: mw.source_manager.set_sweep_bin_size(500_000),
            MenuButtonId.BW_NOT_AVAILABLE.value: lambda: mw.status_label.setText(
                "BW: no compatible source active"),
            # Zero span trigger
            MenuButtonId.ZERO_SPAN_FREE_RUN.value: lambda: self._set_zero_span_trigger_mode("free_run"),
            MenuButtonId.ZERO_SPAN_RISE.value:     lambda: self._set_zero_span_trigger_mode("rise"),
            MenuButtonId.ZERO_SPAN_FALL.value:     lambda: self._set_zero_span_trigger_mode("fall"),
            MenuButtonId.ZERO_SPAN_TIME.value:     self._enter_zero_span_time,
            # FFT / window
            MenuButtonId.HAMMING.value:   lambda: mw.set_window_type("hamming"),
            MenuButtonId.HANNING.value:   lambda: mw.set_window_type("hanning"),
            MenuButtonId.RECTANGLE.value: lambda: mw.set_window_type("rectangle"),
            MenuButtonId.FFT_512.value:   lambda: mw.set_fft_size(FFTSize.SIZE_512.value),
            MenuButtonId.FFT_1024.value:  lambda: mw.set_fft_size(FFTSize.SIZE_1024.value),
            MenuButtonId.FFT_2048.value:  lambda: mw.set_fft_size(FFTSize.SIZE_2048.value),
            MenuButtonId.FFT_4096.value:  lambda: mw.set_fft_size(FFTSize.SIZE_4096.value),
        }

    def _source_actions(self) -> dict:
        mw = self.main_window
        return {
            MenuButtonId.RTL_SAMPLES.value:        lambda: self._activate_sample_source(SourceType.RTL_SAMPLES.value),
            MenuButtonId.HACKRF_SAMPLES.value:     lambda: self._activate_sample_source(SourceType.HACKRF_SAMPLES.value),
            MenuButtonId.MICROPHONE_SAMPLES.value: lambda: self._activate_sample_source(SourceType.MICROPHONE_SAMPLES.value),
            MenuButtonId.RTL_SWEEP.value:          lambda: mw.source_manager.set_source(SourceType.RTL_SWEEP.value),
            MenuButtonId.HACKRF_SWEEP.value:       lambda: mw.source_manager.set_source(SourceType.HACKRF_SWEEP.value),
        }

    def _amplitude_actions(self) -> dict:
        mw = self.main_window
        return {
            MenuButtonId.HOLD.value:           self.toggle_hold,
            MenuButtonId.TARE.value:           self._tare_action,
            MenuButtonId.REF_LEVEL.value:      lambda: mw.frequency_manager.change_entry_mode('ref_level'),
            MenuButtonId.LOG.value:            lambda: self._set_log_scale(True),
            MenuButtonId.LINEAR.value:         lambda: self._set_log_scale(False),
            MenuButtonId.DB_PER_DIV_1.value:   lambda: self._set_db_per_div(1),
            MenuButtonId.DB_PER_DIV_2.value:   lambda: self._set_db_per_div(2),
            MenuButtonId.DB_PER_DIV_5.value:   lambda: self._set_db_per_div(5),
            MenuButtonId.DB_PER_DIV_10.value:  lambda: self._set_db_per_div(10),
            MenuButtonId.DB_PER_DIV_20.value:  lambda: self._set_db_per_div(20),
            MenuButtonId.MAX_HOLD.value:       self.toggle_max_peak_search,
            MenuButtonId.MIN_HOLD.value:       self.toggle_min_hold,
            MenuButtonId.CLEAR_HOLD.value:     lambda: self._clear_hold(notify=True),
            MenuButtonId.DISP_LINE_ONOFF.value: self._toggle_display_line,
            MenuButtonId.DISP_LINE_LEVEL.value: self._enter_display_line_level,
            MenuButtonId.PK_THRESHOLD.value:   self._enter_threshold,
            MenuButtonId.PK_EXCURSION.value:   self._enter_excursion,
        }

    def _trace_actions(self) -> dict:
        return {
            MenuButtonId.TRACE_STORE_A.value:   self._store_trace_a,
            MenuButtonId.TRACE_SHOW_A.value:    self._toggle_trace_a,
            MenuButtonId.TRACE_STORE_B.value:   self._store_trace_b,
            MenuButtonId.TRACE_SHOW_B.value:    self._toggle_trace_b,
            MenuButtonId.TRACE_A_MINUS_B.value: self._toggle_trace_ab,
            MenuButtonId.TRACE_LIVE.value:      self._toggle_live_trace,
            MenuButtonId.TRACE_CLEAR.value:     self._clear_traces,
            MenuButtonId.AVG_OFF.value:         lambda: self._set_averaging("off",  1),
            MenuButtonId.AVG_EXP_2.value:       lambda: self._set_averaging("exp",  2),
            MenuButtonId.AVG_EXP_4.value:       lambda: self._set_averaging("exp",  4),
            MenuButtonId.AVG_EXP_8.value:       lambda: self._set_averaging("exp",  8),
            MenuButtonId.AVG_EXP_16.value:      lambda: self._set_averaging("exp", 16),
            MenuButtonId.AVG_LIN_4.value:       lambda: self._set_averaging("lin",  4),
            MenuButtonId.AVG_LIN_16.value:      lambda: self._set_averaging("lin", 16),
            MenuButtonId.AVG_LIN_64.value:      lambda: self._set_averaging("lin", 64),
            MenuButtonId.PERSIST_OFF.value:     lambda: self._set_persistence("off"),
            MenuButtonId.PERSIST_SHORT.value:   lambda: self._set_persistence("short"),
            MenuButtonId.PERSIST_MEDIUM.value:  lambda: self._set_persistence("medium"),
            MenuButtonId.PERSIST_LONG.value:    lambda: self._set_persistence("long"),
        }

    def _display_actions(self) -> dict:
        return {
            MenuButtonId.TWO_D.value:     lambda: self._switch_display_format(DisplayMode.TWO_D),
            MenuButtonId.THREE_D.value:   lambda: self._switch_display_format(DisplayMode.THREE_D),
            MenuButtonId.WATERFALL.value: lambda: self._switch_display_format(DisplayMode.WATERFALL),
            MenuButtonId.SURFACE.value:   lambda: self._switch_display_format(DisplayMode.SURFACE),
            MenuButtonId.RIBBON.value:    lambda: self._switch_display_format(DisplayMode.RIBBON),
            MenuButtonId.DENSITY.value:   lambda: self._switch_display_format(DisplayMode.DENSITY),
            MenuButtonId.LOG_FREQ.value:  self._toggle_log_freq,
            MenuButtonId.TWO_D_FILL_GRADIENT.value: lambda: self._2d_set_fill_type("gradient"),
            MenuButtonId.TWO_D_FILL_SOLID.value:    lambda: self._2d_set_fill_type("solid"),
            MenuButtonId.TWO_D_FILL_GLOW.value:     lambda: self._2d_set_fill_type("glow"),
            MenuButtonId.TWO_D_FILL_OFF.value:      lambda: self._2d_set_fill_type("off"),
            MenuButtonId.TWO_D_COLOUR_GREEN.value:  lambda: self._2d_set_colour("green"),
            MenuButtonId.TWO_D_COLOUR_YELLOW.value: lambda: self._2d_set_colour("yellow"),
            MenuButtonId.TWO_D_COLOUR_CYAN.value:   lambda: self._2d_set_colour("cyan"),
            MenuButtonId.TWO_D_COLOUR_WHITE.value:  lambda: self._2d_set_colour("white"),
            MenuButtonId.TWO_D_COLOUR_BLUE.value:   lambda: self._2d_set_colour("blue"),
            MenuButtonId.THREE_D_GRID.value:        self._toggle_3d_grid,
            MenuButtonId.THREE_D_AUTO_ROTATE.value: self._toggle_3d_auto_rotate,
            MenuButtonId.THREE_D_HIST_50.value:     lambda: self._set_3d_history_lines(50),
            MenuButtonId.THREE_D_HIST_100.value:    lambda: self._set_3d_history_lines(100),
            MenuButtonId.THREE_D_HIST_200.value:    lambda: self._set_3d_history_lines(200),
            MenuButtonId.THREE_D_HIST_300.value:    lambda: self._set_3d_history_lines(300),
            MenuButtonId.THREE_D_HIST_500.value:    lambda: self._set_3d_history_lines(500),
            MenuButtonId.SURFACE_AUTO_ROTATE.value: self._toggle_surface_auto_rotate,
            MenuButtonId.SURFACE_HIST_10.value:     lambda: self._set_surface_history_lines(10),
            MenuButtonId.SURFACE_HIST_25.value:     lambda: self._set_surface_history_lines(25),
            MenuButtonId.SURFACE_HIST_50.value:     lambda: self._set_surface_history_lines(50),
            MenuButtonId.SURFACE_HIST_100.value:    lambda: self._set_surface_history_lines(100),
            MenuButtonId.SURFACE_HIST_200.value:    lambda: self._set_surface_history_lines(200),
            MenuButtonId.DENSITY_COLOURMAP_MAGMA.value:   lambda: self._density_set_colourmap("magma"),
            MenuButtonId.DENSITY_COLOURMAP_VIRIDIS.value: lambda: self._density_set_colourmap("viridis"),
            MenuButtonId.DENSITY_COLOURMAP_PLASMA.value:  lambda: self._density_set_colourmap("plasma"),
            MenuButtonId.DENSITY_COLOURMAP_INFERNO.value: lambda: self._density_set_colourmap("inferno"),
            MenuButtonId.DENSITY_DECAY_FAST.value:        lambda: self._density_set_decay("fast"),
            MenuButtonId.DENSITY_DECAY_MEDIUM.value:      lambda: self._density_set_decay("medium"),
            MenuButtonId.DENSITY_DECAY_SLOW.value:        lambda: self._density_set_decay("slow"),
            MenuButtonId.DENSITY_DECAY_OFF.value:         lambda: self._density_set_decay("off"),
            MenuButtonId.DENSITY_CLEAR.value:             self._density_clear,
        }

    def _gain_actions(self) -> dict:
        return {
            MenuButtonId.GAIN_NOT_AVAILABLE.value: lambda: self.main_window.status_label.setText(
                "RF gain: no compatible source active"),
            MenuButtonId.RTL_GAIN_AUTO.value: lambda: self._set_rtl_gain('auto'),
            MenuButtonId.RTL_GAIN_0.value:    lambda: self._set_rtl_gain(0),
            MenuButtonId.RTL_GAIN_10.value:   lambda: self._set_rtl_gain(10),
            MenuButtonId.RTL_GAIN_20.value:   lambda: self._set_rtl_gain(20),
            MenuButtonId.RTL_GAIN_30.value:   lambda: self._set_rtl_gain(30),
            MenuButtonId.RTL_GAIN_40.value:   lambda: self._set_rtl_gain(40),
            MenuButtonId.RTL_GAIN_50.value:   lambda: self._set_rtl_gain(50),
            MenuButtonId.HACKRF_LNA_0.value:  lambda: self._set_hackrf_lna(0),
            MenuButtonId.HACKRF_LNA_8.value:  lambda: self._set_hackrf_lna(8),
            MenuButtonId.HACKRF_LNA_16.value: lambda: self._set_hackrf_lna(16),
            MenuButtonId.HACKRF_LNA_24.value: lambda: self._set_hackrf_lna(24),
            MenuButtonId.HACKRF_LNA_32.value: lambda: self._set_hackrf_lna(32),
            MenuButtonId.HACKRF_LNA_40.value: lambda: self._set_hackrf_lna(40),
            MenuButtonId.HACKRF_VGA_0.value:  lambda: self._set_hackrf_vga(0),
            MenuButtonId.HACKRF_VGA_10.value: lambda: self._set_hackrf_vga(10),
            MenuButtonId.HACKRF_VGA_20.value: lambda: self._set_hackrf_vga(20),
            MenuButtonId.HACKRF_VGA_30.value: lambda: self._set_hackrf_vga(30),
            MenuButtonId.HACKRF_VGA_40.value: lambda: self._set_hackrf_vga(40),
            MenuButtonId.HACKRF_VGA_50.value: lambda: self._set_hackrf_vga(50),
            MenuButtonId.HACKRF_VGA_60.value: lambda: self._set_hackrf_vga(60),
            MenuButtonId.HACKRF_VGA_62.value: lambda: self._set_hackrf_vga(62),
            MenuButtonId.HACKRF_AMP_ON.value:        lambda: self._set_hackrf_amp(True),
            MenuButtonId.HACKRF_AMP_OFF.value:       lambda: self._set_hackrf_amp(False),
            MenuButtonId.HACKRF_DC_ALPHA_OFF.value:  lambda: self._set_hackrf_dc_alpha(0.0),
            MenuButtonId.HACKRF_DC_ALPHA_1_0.value:  lambda: self._set_hackrf_dc_alpha(1.0),
            MenuButtonId.HACKRF_DC_ALPHA_0_5.value:  lambda: self._set_hackrf_dc_alpha(0.5),
            MenuButtonId.HACKRF_DC_ALPHA_0_1.value:  lambda: self._set_hackrf_dc_alpha(0.1),
            MenuButtonId.HACKRF_DC_ALPHA_0_01.value: lambda: self._set_hackrf_dc_alpha(0.01),
        }

    def _waterfall_actions(self) -> dict:
        return {
            MenuButtonId.WFALL_COLOUR_GQRX.value:    lambda: self._set_waterfall_colourmap('gqrx',    "GQRX"),
            MenuButtonId.WFALL_COLOUR_MAGMA.value:   lambda: self._set_waterfall_colourmap('magma',   "Magma"),
            MenuButtonId.WFALL_COLOUR_VIRIDIS.value: lambda: self._set_waterfall_colourmap('viridis', "Viridis"),
            MenuButtonId.WFALL_COLOUR_INFERNO.value: lambda: self._set_waterfall_colourmap('inferno', "Inferno"),
            MenuButtonId.WFALL_COLOUR_PLASMA.value:  lambda: self._set_waterfall_colourmap('plasma',  "Plasma"),
            MenuButtonId.WFALL_COLOUR_GREY.value:    lambda: self._set_waterfall_colourmap('CET-L1',  "Grey"),
            MenuButtonId.WFALL_COLOUR_RAINBOW.value: lambda: self._set_waterfall_colourmap('CET-R4',  "Rainbow"),
            MenuButtonId.WFALL_SPAN_30.value:        lambda: self._wf_set_span(30),
            MenuButtonId.WFALL_SPAN_60.value:        lambda: self._wf_set_span(60),
            MenuButtonId.WFALL_SPAN_300.value:       lambda: self._wf_set_span(300),
            MenuButtonId.WFALL_SPAN_600.value:       lambda: self._wf_set_span(600),
            MenuButtonId.WFALL_FLOOR.value:          self._wf_enter_floor,
            MenuButtonId.WFALL_CEILING.value:        self._wf_enter_ceiling,
            MenuButtonId.WFALL_FREEZE.value:         self._wf_toggle_freeze,
        }

    def _marker_actions(self) -> dict:
        mw = self.main_window
        return {
            MenuButtonId.MARKER_F1.value:        lambda: mw.marker_manager.toggle_marker('F1'),
            MenuButtonId.MARKER_F2.value:        lambda: mw.marker_manager.toggle_marker('F2'),
            MenuButtonId.MARKER_P1.value:        lambda: mw.marker_manager.toggle_marker('P1'),
            MenuButtonId.MARKER_P2.value:        lambda: mw.marker_manager.toggle_marker('P2'),
            MenuButtonId.MARKER_TO_PEAK.value:   lambda: mw.marker_manager.snap_to_peak(),
            MenuButtonId.MARKER_NEXT_PEAK.value: lambda: mw.marker_manager.snap_to_next_peak(),
            MenuButtonId.MARKER_TO_CENTRE.value: lambda: mw.marker_manager.marker_to_centre(),
            MenuButtonId.MARKER_CLEAR_ALL.value: lambda: mw.marker_manager.clear_all(),
            MenuButtonId.PEAK_LIST.value:        self.toggle_peak_list,
        }

    def _analysis_actions(self) -> dict:
        return {
            MenuButtonId.DUTY_CYCLE.value:             self.toggle_duty_cycle,
            MenuButtonId.CONSTELLATION_SCATTER.value:  lambda: self._set_constellation_mode("scatter"),
            MenuButtonId.CONSTELLATION_DENSITY.value:  lambda: self._set_constellation_mode("density"),
            MenuButtonId.CONST_BPSK.value:   lambda: self._set_constellation_modulation("bpsk"),
            MenuButtonId.CONST_QPSK.value:   lambda: self._set_constellation_modulation("qpsk"),
            MenuButtonId.CONST_8PSK.value:   lambda: self._set_constellation_modulation("8psk"),
            MenuButtonId.CONST_16QAM.value:  lambda: self._set_constellation_modulation("16qam"),
            MenuButtonId.CONST_64QAM.value:  lambda: self._set_constellation_modulation("64qam"),
            MenuButtonId.CONST_RANGE_15.value: lambda: self._set_constellation_range(1.5),
            MenuButtonId.CONST_RANGE_20.value: lambda: self._set_constellation_range(2.0),
            MenuButtonId.CONST_RANGE_30.value: lambda: self._set_constellation_range(3.0),
            MenuButtonId.CONST_POINTS_500.value:  lambda: self._set_constellation_points(500),
            MenuButtonId.CONST_POINTS_2K.value:   lambda: self._set_constellation_points(2000),
            MenuButtonId.CONST_POINTS_5K.value:   lambda: self._set_constellation_points(5000),
            MenuButtonId.CONST_POINTS_10K.value:  lambda: self._set_constellation_points(10000),
        }

    def _calibration_actions(self) -> dict:
        return {
            MenuButtonId.CAL_SET.value:    self._cal_set_from_marker,
            MenuButtonId.CAL_OFFSET.value: self._cal_enter_offset,
            MenuButtonId.CAL_CLEAR.value:  self._cal_clear,
        }

    def _preset_actions(self) -> dict:
        mw = self.main_window
        return {
            MenuButtonId.PRESET_SLOT_1.value: lambda: mw.preset_manager.execute_slot(1),
            MenuButtonId.PRESET_SLOT_2.value: lambda: mw.preset_manager.execute_slot(2),
            MenuButtonId.PRESET_SLOT_3.value: lambda: mw.preset_manager.execute_slot(3),
            MenuButtonId.PRESET_SLOT_4.value: lambda: mw.preset_manager.execute_slot(4),
            MenuButtonId.PRESET_SLOT_5.value: lambda: mw.preset_manager.execute_slot(5),
            MenuButtonId.PRESET_SLOT_6.value: lambda: mw.preset_manager.execute_slot(6),
            MenuButtonId.PRESET_SLOT_7.value: lambda: mw.preset_manager.execute_slot(7),
            MenuButtonId.PRESET_SLOT_8.value: lambda: mw.preset_manager.execute_slot(8),
        }

    def _export_actions(self) -> dict:
        return {
            MenuButtonId.EXPORT_DISPLAY_PNG.value:  lambda: self._exporter.export_display('png'),
            MenuButtonId.EXPORT_DISPLAY_JPEG.value: lambda: self._exporter.export_display('jpeg'),
            MenuButtonId.EXPORT_DISPLAY_SVG.value:  lambda: self._exporter.export_display('svg'),
            MenuButtonId.EXPORT_WINDOW_PNG.value:   lambda: self._exporter.export_window('png'),
            MenuButtonId.EXPORT_WINDOW_JPEG.value:  lambda: self._exporter.export_window('jpeg'),
        }

    # Buttons that start a sample source then set analysis mode
    _ANALYSIS_MODE_BUTTONS = {
        MenuButtonId.FFT.value:           "fft",
        MenuButtonId.PSD.value:           "psd",
        MenuButtonId.CONSTELLATION.value: "constellation",
    }

    _SAMPLE_BUTTON_IDS = frozenset({
        MenuButtonId.RTL_SAMPLES.value,
        MenuButtonId.MICROPHONE_SAMPLES.value,
        MenuButtonId.HACKRF_SAMPLES.value,
    })

    def on_menu_selection(self, item: MenuItem):
        """Route a soft-key press to the appropriate action.

        Special handling only for cases that require source validation before
        dispatch (analysis mode buttons). Everything else goes through the
        menu_actions dispatch table or submenu navigation.
        """
        mw = self.main_window
        logger.debug(f"on_menu_selection: {item.id}")

        # Track which sample source was most recently selected
        if item.id in self._SAMPLE_BUTTON_IDS:
            mw.current_source_id = item.id

        # Analysis mode (FFT/PSD/Constellation): validate source before starting
        if item.id in self._ANALYSIS_MODE_BUTTONS:
            self._handle_analysis_mode_button(item)
            return

        # Submenu navigation — fire any registered action first, then navigate in
        if item.sub_menu:
            action = self.menu_actions.get(item.id)
            if action:
                action()
            mw.menu.select_menu(item.label)
            return

        # General dispatch — zero span, duty cycle, gain, export, etc. all live here
        action = self.menu_actions.get(
            item.id,
            lambda: mw.status_label.setText(f"Action {item.id} not implemented")
        )
        action()

    def _handle_analysis_mode_button(self, item: MenuItem) -> None:
        """Validate and start analysis mode (FFT / PSD / Constellation)."""
        mw = self.main_window
        mode = self._ANALYSIS_MODE_BUTTONS[item.id]
        source_id = mw.current_source_id
        if not source_id:
            mw.status_label.setText("No source selected")
            logger.warning(f"No current_source_id for {item.id}")
            return
        if source_id not in self._SAMPLE_BUTTON_IDS:
            mw.status_label.setText(f"Invalid source for {mode}: {source_id}")
            logger.error(f"Invalid source for {mode}: {source_id}")
            mw.current_source_id = None
            return
        mw.source_manager.set_source(source_id)
        self.set_analysis_mode(mode)
        if item.sub_menu:
            mw.menu.select_menu(item.label)

