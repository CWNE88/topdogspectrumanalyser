import sys
import os
import signal
import logging
import numpy as np
from PyQt6.QtWidgets import QMainWindow, QApplication, QProxyStyle, QStyle
from PyQt6.uic import loadUi
from PyQt6.QtCore import Qt, QTimer
from core.ui_setup import UISetup
from core.frequency_manager import FrequencyManager
from core.source_manager import SourceManager
from core.display_manager import DisplayManager
from core.marker_manager import MarkerManager
from core.preset_manager import PresetManager
from core.popout_window import PopoutWindow
from datasources.base import SampleDataSource, SweepDataSource
from datasources.audio_samples import MicrophoneSamplesDataSource
from utils.constants import DisplayMode, UIConstants, FFTSize, AmplitudeConstants, EntryMode
from utils.validators import clamp_centre_span
from utils.frequency_helpers import calculate_frequency_bins_from_range, update_display_frequency_bins
from core.calibration_manager import CalibrationManager

# Configure logging with British English spelling
import os
_log_level = getattr(logging, os.environ.get("LOGLEVEL", "WARNING").upper(), logging.WARNING)
logging.basicConfig(level=_log_level,
                   format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._initialise_ui()
        self._initialise_state()
        self._initialise_managers()

        # Install event filter on application to catch Alt+Enter before ANY widget processing
        self.app.installEventFilter(self)

        logging.debug("MainWindow initialised successfully")

    def _initialise_ui(self) -> None:
        """Load and set up the UI file with error handling."""
        try:
            loadUi("main_window.ui", self)
        except Exception as e:
            logging.critical(f"Failed to load UI: {e}")
            sys.exit(1)
        # Buttons with their own stylesheet in the .ui file cause Qt to use that
        # stylesheet for QToolTip, inheriting the dark background. Fix by appending
        # an explicit QToolTip rule to every button that already has a stylesheet.
        _tt = " QToolTip { background-color: #f5f5dc; color: #000000; border: 1px solid #999999; padding: 3px; font-weight: normal; }"
        from PyQt6.QtWidgets import QPushButton
        for btn in self.findChildren(QPushButton):
            ss = btn.styleSheet()
            if ss:
                # Bare properties (no selector) must be wrapped before adding a rule block
                if '{' not in ss:
                    ss = f"QPushButton {{ {ss} }}"
                btn.setStyleSheet(ss + _tt)

    def _initialise_state(self) -> None:
        """Initialise all application state. Grouped by concern."""
        self._init_source_state()
        self._init_display_state()
        self._init_hold_tare_state()

    def _init_source_state(self) -> None:
        self.current_source       = None
        self.current_source_id    = None
        self.last_span            = None
        self.live_power_levels    = None
        self.max_power_levels     = None
        self.min_power_levels     = None
        self.frequency_bins       = None
        self.paused               = False
        self._keypad_actions      = None  # built lazily after UISetup
        self.hackrf_lna_gain      = 16    # shared across hackrf sweep/samples (valid LNA steps: 0,8,16,24,32,40)
        self.hackrf_vga_gain      = 20

    def _init_display_state(self) -> None:
        self.current_stacked_index   = DisplayMode.LOGO
        self.display_format          = DisplayMode.TWO_D
        self.analysis_mode           = "fft"       # "fft" | "psd" | "constellation"
        self.ref_level               = AmplitudeConstants.DEFAULT_REF_LEVEL
        self.range_db                = AmplitudeConstants.DEFAULT_RANGE_DB
        self.log_scale               = True         # True = dBm, False = linear mW
        self.log_freq                = False
        self.display_line_enabled    = False
        self.display_line_level      = -50.0
        self.peak_threshold          = -100.0
        self.peak_excursion          = 6.0
        self.threshold_enabled       = False
        self.popout_window           = None
        self.popout_clone_widget     = None
        self.is_popped_out           = False
        self.preset_name_slot        = 0
        self.preset_name_text        = ""

    def _init_hold_tare_state(self) -> None:
        self.tare_active          = False
        self.baseline_power_levels = None
        self.min_hold_enabled     = False

    # _init_trace_state and _init_constellation_state removed —
    # this state now lives in DisplayManager.__init__.

    # _init_zero_span_state removed — zero span state now lives in DisplayManager.__init__.

    # _init_calibration_state removed — pending cal state now lives in CalibrationManager.

    def _initialise_managers(self) -> None:
        """Initialise all manager classes with proper error handling."""
        try:
            # Initialise in dependency order
            self.display_manager = DisplayManager(self)
            self.frequency_manager = FrequencyManager(self)
            self.calibration_manager = CalibrationManager()
            self.ui_setup = UISetup(self)
            self.source_manager = SourceManager(self)
            self.marker_manager = MarkerManager(self)
            self.preset_manager = PresetManager(self)

            # Set initial UI state
            self.ui_setup.initialise_labels()
        except Exception as e:
            logging.critical(f"Failed to initialise managers: {e}")
            sys.exit(1)

    def _resolve_display_index(self) -> int:
        """Compute the stacked widget index from analysis_mode × display_format."""
        if self.analysis_mode == "constellation":
            if self.display_format == DisplayMode.THREE_D:
                return DisplayMode.CONSTELLATION_3D
            return DisplayMode.CONSTELLATION_2D
        return self.display_format

    def set_window_type(self, window_type: str):
        self.source_manager.set_fft_window(window_type)

    def set_fft_size(self, fft_size: int):
        if not FFTSize.is_valid(fft_size):
            min_size = FFTSize.get_min()
            max_size = FFTSize.get_max()
            raise ValueError(
                f"FFT size must be a power of 2 between {min_size} and {max_size}, got {fft_size}"
            )
        self.source_manager.set_fft_size(fft_size)

    def eventFilter(self, obj, event):
        """Intercept keyboard events application-wide when in preset_name entry mode."""
        from PyQt6.QtCore import QEvent
        if (event.type() == QEvent.Type.KeyPress
                and getattr(self, 'frequency_entry_mode', None) == EntryMode.PRESET_NAME
                and obj is not self):
            self.keyPressEvent(event)
            if event.isAccepted():
                return True
        return False

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts for navigation and controls."""
        key = event.key()
        modifiers = event.modifiers()

        # Preset name entry — intercept all printable input before other handlers
        if getattr(self, 'frequency_entry_mode', None) == EntryMode.PRESET_NAME:
            if key == Qt.Key.Key_Backspace:
                self.preset_name_text = self.preset_name_text[:-1]
                self.input_value.setText(self.preset_name_text)
                event.accept()
                return
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.preset_manager.confirm_name(self.preset_name_slot, self.preset_name_text)
                event.accept()
                return
            text = event.text()
            if text and text.isprintable() and len(self.preset_name_text) < 30:
                self.preset_name_text += text
                self.input_value.setText(self.preset_name_text)
                event.accept()
                return

        # Escape: return from popout if active, otherwise go back in soft-key menu
        if key == Qt.Key.Key_Escape:
            event.accept()
            if self.is_popped_out:
                self.return_widget_from_popout()
            else:
                self.menu.go_back()
            return

        # Alt+Enter: Pop out/in display widget (check before other Enter handling)
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and modifiers & Qt.KeyboardModifier.AltModifier:
            event.accept()  # Mark event as handled to prevent button activation
            if self.is_popped_out:
                self.return_widget_from_popout()
            else:
                self.popout_current_display()
            return

        # Up/Down arrow keys: Adjust centre frequency (prevent widget focus navigation)
        if key == Qt.Key.Key_Up:
            event.accept()  # Prevent default widget behavior
            self.handle_frequency_up()
            return
        elif key == Qt.Key.Key_Down:
            event.accept()  # Prevent default widget behavior
            self.handle_frequency_down()
            return

        # Space bar: Toggle hold
        if key == Qt.Key.Key_Space:
            event.accept()  # Prevent default widget behavior (e.g., button activation)
            self.display_manager.toggle_hold()
            return

        # Function keys (F1-F8)
        if Qt.Key.Key_F1 <= key <= Qt.Key.Key_F8:
            self._handle_function_key(key)
            event.accept()
            return

        # Menu navigation shortcuts
        menu_actions = {
            Qt.Key.Key_F: lambda: self.menu.select_menu("Frequency"),
            Qt.Key.Key_S: lambda: self.menu.select_menu("Span"),
            Qt.Key.Key_A: lambda: self.menu.select_menu("Amplitude"),
            Qt.Key.Key_I: lambda: self.menu.select_menu("Input"),
            Qt.Key.Key_N: lambda: self.menu.select_menu("Analysis"),
            Qt.Key.Key_M: lambda: self.menu.select_menu("Marker"),
            Qt.Key.Key_T: lambda: self.menu.select_menu("Trace"),
            Qt.Key.Key_W: lambda: self.menu.select_root_menu("BW"),
            Qt.Key.Key_K: lambda: self.menu.select_root_menu("Marker"),
            Qt.Key.Key_V: lambda: self.ui_setup.toggle_layout(),
            Qt.Key.Key_X: lambda: self.display_manager.toggle_max_peak_search(),
            Qt.Key.Key_P: lambda: self.display_manager.toggle_peak_search(),
            Qt.Key.Key_D: lambda: self.menu.select_menu("Display")
        }

        # Build keypad actions once; rebuild only if not yet initialised
        if self._keypad_actions is None:
            self._keypad_actions = self._build_keypad_actions()

        # When digits are being entered, keypad actions (G/M/K/H multipliers) take
        # priority over menu shortcuts so that e.g. 'M' means MHz not Marker.
        if self.keypad.data_input and key in self._keypad_actions:
            event.accept()
            self._keypad_actions[key]()
            return

        # Execute action if key matches
        if key in menu_actions:
            event.accept()
            menu_actions[key]()
            return
        elif key in self._keypad_actions:
            event.accept()
            self._keypad_actions[key]()
            return

        super().keyPressEvent(event)

    def handle_dial_change(self, value: int):
        """Handle QDial widget value changes for centre frequency adjustment.

        When Centre Frequency mode is active, dial movements adjust the centre frequency
        by 1/20th of the span per dial unit. Works for both sample and sweep sources,
        excluding microphone. The dial wraps around (0-99), with wrap detection for
        calculating relative movement.

        Args:
            value (int): New dial position value (0-99).
        """
        # Calculate the change in dial position (handle wrapping)
        if not hasattr(self, 'last_dial_value'):
            self.last_dial_value = value
            return

        # Get dial range (QDial default is 0-99)
        dial_range = self.dial.maximum() - self.dial.minimum() + 1

        # Calculate delta with wrap detection
        # Wrapping forward (99->0): delta large negative → +1; backward (0->99): large positive → -1
        delta = value - self.last_dial_value
        if delta > dial_range / 2:
            delta -= dial_range
        elif delta < -dial_range / 2:
            delta += dial_range

        self.last_dial_value = value

        if delta != 0:
            self._adjust_centre_frequency(delta)

    def handle_frequency_up(self):
        """Handle Up button press to increase centre frequency.

        Increases centre frequency by 1/20th of the span, same as one dial step up.
        Only works in centre frequency mode with sample sources (not microphone).
        """
        self._adjust_centre_frequency(delta=1)

    def handle_frequency_down(self):
        """Handle Down button press to decrease centre frequency.

        Decreases centre frequency by 1/20th of the span, same as one dial step down.
        Only works in centre frequency mode with sample sources (not microphone).
        """
        self._adjust_centre_frequency(delta=-1)

    def _adjust_ref_level(self, delta: int) -> None:
        """Adjust reference level by one dB/div per step.

        Args:
            delta (int): Number of steps (+1 up, -1 down).
        """
        step = self.range_db / AmplitudeConstants.DIVISIONS
        self.ref_level += delta * step
        self.display_manager.set_amplitude_on_all_displays(self.ref_level, self.range_db)
        logging.debug(f"Ref level adjusted to {self.ref_level:.1f} dBm")

    def _adjust_display_line(self, delta: int) -> None:
        """Adjust display line level by one dB/div per step."""
        step = self.range_db / AmplitudeConstants.DIVISIONS
        self.display_line_level += delta * step
        self.display_manager._update_display_line()
        self.status_label.setText(f"Display line: {self.display_line_level:.1f} dBm")
        logging.debug(f"Display line adjusted to {self.display_line_level:.1f} dBm")

    _ZS_TIME_STEPS = [
        0.0001, 0.0002, 0.0005,
        0.001,  0.002,  0.005,
        0.01,   0.02,   0.05,
        0.1,    0.2,    0.5,   1.0, 2.0,
    ]

    def _adjust_zero_span_trigger(self, delta: int) -> None:
        y_range = self.zero_span_widget.plot_widget.getViewBox().viewRange()[1]
        step = (y_range[1] - y_range[0]) / 100.0
        self.display_manager.zero_span_trigger_level += delta * step
        self.zero_span_widget.set_trigger_level(self.display_manager.zero_span_trigger_level)
        self.status_label.setText(f"Trigger level: {self.display_manager.zero_span_trigger_level:.4f}")

    def _adjust_zero_span_time(self, delta: int) -> None:
        steps = self._ZS_TIME_STEPS
        idx = min(range(len(steps)), key=lambda i: abs(steps[i] - self.display_manager.zero_span_time_window))
        idx = max(0, min(len(steps) - 1, idx + delta))
        self.display_manager.zero_span_time_window = steps[idx]
        t = self.display_manager.zero_span_time_window
        if t >= 1.0:
            label = f"{t:.0f} s"
        elif t >= 0.001:
            label = f"{t * 1000:.3g} ms"
        else:
            label = f"{t * 1e6:.3g} µs"
        self.status_label.setText(f"Time window: {label}")

    def _adjust_centre_frequency(self, delta: int):
        """Adjust centre frequency by a delta amount.

        Args:
            delta (int): Number of steps to adjust (+1 for up, -1 for down).
        """
        mode = getattr(self, 'frequency_entry_mode', EntryMode.CENTRE)

        if mode == EntryMode.MARKER:
            self.marker_manager.move_active(delta)
            return
        if mode == EntryMode.REF_LEVEL:
            self._adjust_ref_level(delta)
            return
        if mode == EntryMode.DISPLAY_LINE:
            self._adjust_display_line(delta)
            return
        if mode == EntryMode.ZERO_SPAN_TIME:
            self._adjust_zero_span_time(delta)
            return
        if mode == EntryMode.ZERO_SPAN_TRIGGER:
            self._adjust_zero_span_trigger(delta)
            return
        if mode == EntryMode.WF_FLOOR:
            self.waterfall_widget.adjust_wf_floor(float(delta))
            self.status_label.setText(f"WF floor: {self.waterfall_widget.wf_min_db:.1f} dBm")
            return
        if mode == EntryMode.WF_CEILING:
            self.waterfall_widget.adjust_wf_ceiling(float(delta))
            self.status_label.setText(f"WF ceiling: {self.waterfall_widget.wf_max_db:.1f} dBm")
            return
        if mode != EntryMode.CENTRE:
            return

        # Check if we have a running source
        if not self.current_source:
            return

        # Only handle RF sources; skip microphone and any unknown source types
        if isinstance(self.current_source, MicrophoneSamplesDataSource):
            return
        if not isinstance(self.current_source, (SampleDataSource, SweepDataSource)):
            return

        # Calculate frequency step: 1/20th of displayed span per step
        # self.frequency.span represents the displayed span for all source types
        freq_step_per_unit = self.frequency.span / 20.0
        freq_change = delta * freq_step_per_unit

        # Compute proposed new start/stop
        new_centre = self.frequency.centre + freq_change
        half_span  = self.frequency.span / 2
        new_start  = new_centre - half_span
        new_stop   = new_centre + half_span

        # Clamp to hardware limits using the single authoritative utility.
        # If no source type is known yet, leave new_start/new_stop unclamped —
        # tuning without an active source type should not be possible in practice.
        src_type = self.source_manager.last_source_type
        if src_type:
            new_centre, new_span = clamp_centre_span(
                new_centre, self.frequency.span, src_type,
                self.source_manager._SOURCE_LIMITS
            )
            new_start = new_centre - new_span / 2
            new_stop  = new_centre + new_span / 2

        # Nothing to do if the range is invalid (both walls hit simultaneously)
        if new_stop <= new_start:
            self.status_label.setText("At frequency limit")
            return
        # Already pinned at the wall — nothing to do
        if (abs(new_start - self.frequency.start) < 1.0 and
                abs(new_stop - self.frequency.stop) < 1.0):
            self.status_label.setText("At frequency limit")
            return

        try:
            old_start = self.frequency.start
            old_stop  = self.frequency.stop
            self.frequency.set_start_stop(new_start, new_stop)
            self.display_manager._clear_hold()
            self.frequency_manager.update_frequency_values()

            # Update the source based on type
            if isinstance(self.current_source, SampleDataSource):
                if hasattr(self.current_source, 'update_centre_frequency'):
                    self.current_source.update_centre_frequency(self.frequency.centre)
            elif isinstance(self.current_source, SweepDataSource):
                from utils.frequency_selector import FrequencyRange
                new_freq_range = FrequencyRange(self.frequency.start, self.frequency.stop)
                self.current_source.stop()
                self.current_source.start(new_freq_range)

            if self.frequency_bins is not None and len(self.frequency_bins) > 0:
                freq_bins = calculate_frequency_bins_from_range(
                    self.frequency.start,
                    self.frequency.stop,
                    len(self.frequency_bins)
                )
                update_display_frequency_bins(self, freq_bins)

            # Reposition any active markers proportionally to the new range
            mm = getattr(self, 'marker_manager', None)
            if mm is not None and old_start is not None and old_stop is not None:
                mm.reposition_on_frequency_change(
                    old_start, old_stop,
                    self.frequency.start, self.frequency.stop
                )

        except ValueError as e:
            logging.warning(f"Cannot set frequency range: {e}")

    def _build_keypad_actions(self) -> dict:
        """Build the keypad actions dict once, after UISetup is complete."""
        actions = {
            Qt.Key.Key_Period: lambda: self.keypad.handle_data_character(".")(),
            Qt.Key.Key_Minus: self._handle_minus_key,
            Qt.Key.Key_Backspace: self._handle_backspace,
            Qt.Key.Key_Delete: self._handle_backspace,
            Qt.Key.Key_G: lambda: self._finalise_input(1e9),
            Qt.Key.Key_M: lambda: self._finalise_input(1e6),
            Qt.Key.Key_K: lambda: self._finalise_input(1e3),
            Qt.Key.Key_Return: lambda: self._finalise_input(1),
            Qt.Key.Key_Enter: lambda: self._finalise_input(1),
        }
        for digit_key in range(Qt.Key.Key_0, Qt.Key.Key_9 + 1):
            actions[digit_key] = self._make_numeric_handler(digit_key - Qt.Key.Key_0)
        return actions

    def _make_numeric_handler(self, digit: int):
        """Create a numeric key handler with proper closure.

        Args:
            digit (int): The digit (0-9) to handle.

        Returns:
            Callable that handles the numeric key press.
        """
        return lambda: self._handle_numeric_key(digit)

    def _cycle_display(self) -> None:
        """Cycle through available display modes."""
        display_cycle = [DisplayMode.TWO_D, DisplayMode.THREE_D, DisplayMode.WATERFALL, DisplayMode.SURFACE]
        current_index = self.current_stacked_index

        # Get next index in cycle
        if current_index in display_cycle:
            next_index = display_cycle[(display_cycle.index(current_index) + 1) % len(display_cycle)]
        else:
            next_index = DisplayMode.TWO_D

        self.display_manager.set_display(next_index, UIConstants.BUTTON_ACTIVE_STYLE, None)

    def _handle_function_key(self, key: Qt.Key) -> None:
        """Handle F1-F8 function key presses."""
        index = key - Qt.Key.Key_F1
        self.menu.handle_button_press(index)

    def _handle_numeric_key(self, digit: int) -> None:
        """Handle numeric key presses (0-9)."""
        self.keypad.handle_data_character(digit)()

    def _handle_minus_key(self) -> None:
        """Handle minus/backspace key logic."""
        if not self.keypad.data_input or self.keypad.data_input == "-":
            self.keypad.handle_data_character("-")()
        else:
            self._handle_backspace()

    def _handle_backspace(self) -> None:
        """Handle backspace key press to remove the last character."""
        if self.keypad.data_input:
            self.keypad.data_input = self.keypad.data_input[:-1]
            self.keypad.on_change(self.keypad.data_input)

    def _finalise_input(self, multiplier: float) -> None:
        """Finalise keypad input with specified unit multiplier."""
        # In ref_level mode all unit keys mean dBm (multiplier = 1)
        if getattr(self, 'frequency_entry_mode', EntryMode.CENTRE) == EntryMode.REF_LEVEL:
            multiplier = 1
        self.keypad.on_frequency_select_inner(multiplier)()
        self.keypad.reset()

    def popout_current_display(self) -> None:
        """Pop out the current display widget into a separate window."""
        # Don't pop out the logo view
        if self.current_stacked_index == DisplayMode.LOGO:
            self.status_label.setText("Cannot pop out logo view")
            logging.debug("PopoutDisplay: Cannot pop out logo view")
            return

        # Don't pop out if already popped out
        if self.is_popped_out:
            self.status_label.setText("Display already popped out")
            logging.debug("PopoutDisplay: Display already popped out")
            return

        # Map of popout-capable displays → (widget_ref, title, needs_clone)
        from displays.three_dimension import ThreeD
        from displays.surface import Surface
        from displays.ribbon import RibbonWidget as _RibbonWidget
        _popout_map = {
            DisplayMode.TWO_D:     (self.two_d_widget,    "2D Spectrum Display",  False, None),
            DisplayMode.THREE_D:   (self.three_d_widget,  "3D Spectrum Display",  True,  ThreeD),
            DisplayMode.WATERFALL: (self.waterfall_widget,"Waterfall Display",    False, None),
            DisplayMode.SURFACE:   (self.surface_widget,  "Surface Display",      True,  Surface),
            DisplayMode.RIBBON:    (self.ribbon_widget,   "Ribbon Display",       True,  _RibbonWidget),
        }

        entry = _popout_map.get(self.current_stacked_index)
        if entry is None:
            logging.warning(f"PopoutDisplay: Invalid display index {self.current_stacked_index}")
            return

        widget, title, needs_clone, clone_class = entry
        self.popout_window = PopoutWindow(self, title, self.current_stacked_index)

        if needs_clone:
            # OpenGL widgets must be cloned — they cannot be reparented safely
            clone = self.popout_window.create_clone_widget(clone_class)
            self.popout_clone_widget = clone
            widget.hide()
        else:
            self.popout_window.set_widget(widget, self.stacked_widget)
            self.popout_clone_widget = None

        self.popout_window.show()
        self.popout_window.update_title()

        # Switch main window to logo while display is popped out (static, no animation).
        # Use setCurrentWidget instead of setCurrentIndex — reparenting a widget out of
        # the stacked widget shifts all subsequent physical indices, so a raw index lookup
        # would land on the wrong page.
        self.stacked_widget.setCurrentWidget(self.logo_widget)

        self.is_popped_out = True
        self.status_label.setText(f"{title} popped out — Alt+Enter or ESC to return")
        logging.debug(f"PopoutDisplay: {title} popped out (clone={needs_clone})")

    def return_widget_from_popout(self) -> None:
        """Return the popped-out widget back to the main window."""
        if not self.is_popped_out or not self.popout_window:
            return

        # Single map for all known display widgets
        _widget_by_mode = {
            DisplayMode.TWO_D:     self.two_d_widget,
            DisplayMode.THREE_D:   self.three_d_widget,
            DisplayMode.WATERFALL: self.waterfall_widget,
            DisplayMode.SURFACE:   self.surface_widget,
            DisplayMode.RIBBON:    self.ribbon_widget,
        }
        original_widget = _widget_by_mode.get(self.current_stacked_index)

        if self.popout_window.is_clone_widget:
            # Clone path: destroy clone, show the original that was hidden
            if self.popout_clone_widget:
                self.popout_clone_widget.deleteLater()
                self.popout_clone_widget = None
            if original_widget:
                original_widget.show()
        else:
            # Reparent path: re-insert widget into the stacked widget
            widget = self.popout_window.popped_widget
            if widget:
                self.stacked_widget.insertWidget(self.current_stacked_index, widget)
                widget.show()

        # Restore the stacked widget to the correct page
        if original_widget:
            self.stacked_widget.setCurrentWidget(original_widget)
        else:
            self.stacked_widget.setCurrentIndex(self.current_stacked_index)
        self.logo_timer.stop()

        # Close and clean up pop-out window
        if self.popout_window:
            self.popout_window.popped_widget = None  # Prevent recursive close
            self.popout_window.close()
            self.popout_window = None

        self.is_popped_out = False
        self.status_label.setText("Display returned to main window")
        logging.debug("PopoutDisplay: Widget returned to main window")

    def closeEvent(self, event) -> None:
        """Handle application shutdown cleanly."""
        try:
            # Stop timers first, then drain the Qt event queue so any timer
            # event already queued before stop() is processed harmlessly while
            # the source is still alive — not after it's been torn down.
            self.timer.stop()
            self.logo_timer.stop()
            QApplication.processEvents()

            # Return widget from popout if needed
            if self.is_popped_out:
                self.return_widget_from_popout()

            self.source_manager.close()
            logging.debug("Application closed successfully")
            event.accept()
        except Exception as e:
            logging.critical(f"Error during application close: {e}")
            event.ignore()
            return
        # Bypass Python/C++ finalizer ordering issues in pyqtgraph + PyQt6
        # that cause intermittent segfaults during garbage collection.
        os._exit(0)

class _TooltipStyle(QProxyStyle):
    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_ToolTip_WakeUpDelay:
            return 1000
        return super().styleHint(hint, option, widget, returnData)


if __name__ == "__main__":
    # Must be set before QApplication is created.
    # GLLinePlotItem caches a compiled shader program at the class level
    # (_shaderProgram).  Without context sharing, a shader compiled in the
    # main window's GL context cannot be reused in the popout window's
    # separate context, causing every GLLinePlotItem.paint() to fail with
    # "Error while drawing item" when a 3D/Surface/Ribbon display is
    # popped out.  AA_ShareOpenGLContexts puts all QOpenGLWidget contexts
    # into the same share group so the cached shader is valid everywhere.
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setStyle(_TooltipStyle())

    # Allow Ctrl+C to close the app cleanly via the existing closeEvent.
    # Qt's C++ event loop never returns to Python long enough to deliver SIGINT
    # on its own, so a timer forces a brief Python re-entry every 200 ms.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    sigint_timer = QTimer()
    sigint_timer.start(200)
    sigint_timer.timeout.connect(lambda: None)

    window = MainWindow(app)
    window.show()
    window.ui_setup.start_timers()
    sys.exit(app.exec())