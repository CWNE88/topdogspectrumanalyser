import collections
import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QLinearGradient, QColor, QBrush
import pyqtgraph as pg
import logging
from typing import Optional

_TRACE_COLOURS = {
    "green":  (0, 200, 60),
    "yellow": (255, 210, 0),
    "cyan":   (0, 200, 200),
    "white":  (210, 210, 210),
    "blue":   (80, 120, 255),
}

logger = logging.getLogger(__name__)

class TwoD(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('k')  # Black background
        self.plot_widget.setLabel('left', 'Power', units='dBm')  # White label by default
        self.plot_widget.setLabel('bottom', 'Frequency', units='Hz')
        self.plot_widget.showGrid(x=True, y=True)  # Grid enabled

        # Fill curve — sits behind live trace; invisible by default
        self.fill_curve = pg.PlotCurveItem(pen=pg.mkPen(None))
        self.plot_widget.addItem(self.fill_curve)

        # Plot lines
        self.live_plot  = self.plot_widget.plot(pen=pg.mkPen('g', width=1), name='Live')
        self.max_plot   = self.plot_widget.plot(pen=pg.mkPen('y', width=2), name='Max Hold')
        self.min_plot   = self.plot_widget.plot(pen=pg.mkPen('b', width=2), name='Min Hold')
        # Right-channel stereo trace (red) — hidden by default
        self.right_plot = self.plot_widget.plot(pen=pg.mkPen('r', width=2), name='Right')

        for plot in (self.live_plot, self.max_plot, self.min_plot, self.right_plot):
            plot.setDownsampling(auto=True, method='peak')
            plot.setClipToView(True)
        # Use scatter plots for the peak markers
        self.peak_marker = self.plot_widget.plot(
            pen=None, symbol='t', symbolPen=None, symbolBrush='w', symbolSize=20
        )
        self.max_peak_marker = self.plot_widget.plot(
            pen=None, symbol='t', symbolPen=None, symbolBrush='w', symbolSize=20
        )

        # Text items for peak labels (always present but hidden when not used)
        self.peak_text = pg.TextItem("", anchor=(0.5, 0.5))
        self.plot_widget.addItem(self.peak_text)
        self.peak_text.hide()

        self.max_peak_text = pg.TextItem("", anchor=(0.5, 0.5))
        self.plot_widget.addItem(self.max_peak_text)
        self.max_peak_text.hide()

        # Peak list markers — 5 numbered triangles (cyan)
        self._peak_list_markers = []
        self._peak_list_texts   = []
        for i in range(5):
            m = self.plot_widget.plot(
                pen=None, symbol='t', symbolPen=None,
                symbolBrush=pg.mkColor(0, 220, 220), symbolSize=18
            )
            t = pg.TextItem(str(i + 1), anchor=(0.5, 1.6),
                            color=pg.mkColor(0, 220, 220))
            self.plot_widget.addItem(t)
            t.hide()
            self._peak_list_markers.append(m)
            self._peak_list_texts.append(t)

        # Use QVBoxLayout to avoid GraphicsLayoutWidget issues
        layout = QVBoxLayout()
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        self.frequency_bins: Optional[np.ndarray] = None
        self.live_power_levels: Optional[np.ndarray] = None
        self.max_power_levels: Optional[np.ndarray] = None
        self.peak_search_enabled: bool = False
        self.max_peak_search_enabled: bool = False
        self.min_hold_enabled: bool = False
        self.ref_level: float = 0.0
        self.range_db: float = 100.0
        self.log_scale: bool = True
        self.log_freq: bool = False
        self.plot_widget.setYRange(-100, 0)
        self.plot_widget.enableAutoRange(enable=False)

        # Marker lines: name → pg.InfiniteLine
        self._marker_lines: dict = {}

        # Display line (yellow dashed horizontal)
        self._display_line: Optional[pg.InfiniteLine] = None

        # Threshold line (red dashed horizontal)
        self._threshold_line: Optional[pg.InfiniteLine] = None

        # Trace A (cyan dashed) and Trace B (orange dashed) overlays
        self.trace_a_plot = self.plot_widget.plot(
            pen=pg.mkPen(color=(0, 200, 255, 180), width=1, style=Qt.PenStyle.DashLine),
            name='Trace A'
        )
        self.trace_b_plot = self.plot_widget.plot(
            pen=pg.mkPen(color=(255, 165, 0, 180), width=1, style=Qt.PenStyle.DashLine),
            name='Trace B'
        )
        # A-B difference trace (magenta)
        self.trace_ab_plot = self.plot_widget.plot(
            pen=pg.mkPen(color=(220, 80, 220, 200), width=1),
            name='A-B'
        )

        # Persistence ghost traces
        self._persist_plots: list = []
        self._persist_buffer: collections.deque = collections.deque()
        self._persist_depth: int = 0

        # Colour and fill state
        self._trace_colour_name: str = "green"
        self._trace_colour_rgb: tuple = _TRACE_COLOURS["green"]
        self._fill_type: str = "off"  # "off" | "gradient" | "solid" | "glow"

        logger.debug("TwoD: Widget initialised")

    def set_live_visible(self, visible: bool) -> None:
        """Show or hide the live trace."""
        if visible:
            self.live_plot.setVisible(True)
            self.fill_curve.setVisible(True)
            self.live_plot.setPen(pg.mkPen(color=self._trace_colour_rgb, width=1))
            self._apply_fill()
        else:
            self.live_plot.setVisible(False)
            self.fill_curve.setVisible(False)

    def _apply_fill(self) -> None:
        """Apply or clear the fill curve based on current fill type and colour."""
        if self._fill_type == "off":
            self.fill_curve.setFillLevel(None)
            self.fill_curve.setBrush(None)
            self.fill_curve.setPen(pg.mkPen(None))
            return

        r, g, b = self._trace_colour_rgb
        fill_bottom = self.ref_level - self.range_db - 20
        self.fill_curve.setFillLevel(fill_bottom)
        self.fill_curve.setPen(pg.mkPen(None))

        if self._fill_type == "gradient":
            grad = QLinearGradient(0, 0, 0, 1)
            grad.setCoordinateMode(QLinearGradient.CoordinateMode.ObjectBoundingMode)
            grad.setColorAt(0.0, QColor(r, g, b, 150))
            grad.setColorAt(0.6, QColor(r // 2, g // 2, b // 2, 60))
            grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            self.fill_curve.setBrush(QBrush(grad))

        elif self._fill_type == "solid":
            self.fill_curve.setBrush(QBrush(QColor(r, g, b, 70)))

        elif self._fill_type == "glow":
            # Intense near the trace, quickly fading — neon/plasma look
            grad = QLinearGradient(0, 0, 0, 1)
            grad.setCoordinateMode(QLinearGradient.CoordinateMode.ObjectBoundingMode)
            grad.setColorAt(0.00, QColor(r, g, b, 230))
            grad.setColorAt(0.10, QColor(r // 2, g // 2, b // 2, 110))
            grad.setColorAt(0.30, QColor(0, 0, 0, 35))
            grad.setColorAt(1.00, QColor(0, 0, 0, 0))
            self.fill_curve.setBrush(QBrush(grad))

    def set_fill_type(self, fill_type: str) -> None:
        """Set fill style: 'off', 'gradient', 'solid', or 'glow'."""
        self._fill_type = fill_type
        self._apply_fill()

    def set_trace_colour(self, name: str) -> None:
        """Change the live trace colour. Updates pen, fill, and persistence colours."""
        self._trace_colour_name = name
        self._trace_colour_rgb = _TRACE_COLOURS.get(name, (0, 200, 60))
        r, g, b = self._trace_colour_rgb
        self.live_plot.setPen(pg.mkPen(color=(r, g, b), width=1))
        self._apply_fill()

    def set_amplitude(self, ref_level: float, range_db: float) -> None:
        """Set the amplitude reference level and range."""
        self.ref_level = ref_level
        self.range_db = range_db
        if self.log_scale:
            self.plot_widget.setYRange(ref_level - range_db, ref_level)
        else:
            y_top = 10.0 ** (ref_level / 10.0)
            y_bot = 10.0 ** ((ref_level - range_db) / 10.0)
            self.plot_widget.setYRange(y_bot, y_top)
        self._apply_fill()

    def set_log_freq(self, enabled: bool) -> None:
        """Switch between linear and logarithmic frequency axis."""
        self.log_freq = enabled
        self.plot_widget.setLogMode(x=enabled, y=False)
        if self.frequency_bins is not None and len(self.frequency_bins) > 0:
            if enabled:
                self._set_xrange_log(self.frequency_bins)
            else:
                self.plot_widget.setXRange(self.frequency_bins[0], self.frequency_bins[-1], padding=0)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"TwoD: Log frequency axis {'enabled' if enabled else 'disabled'}")

    def set_log_scale(self, enabled: bool) -> None:
        """Switch between logarithmic dBm and linear mW amplitude display."""
        self.log_scale = enabled
        if enabled:
            self.plot_widget.setLabel('left', 'Power', units='dBm')
            self.plot_widget.setYRange(self.ref_level - self.range_db, self.ref_level)
        else:
            self.plot_widget.setLabel('left', 'Power', units='mW')
            y_top = 10.0 ** (self.ref_level / 10.0)
            y_bot = 10.0 ** ((self.ref_level - self.range_db) / 10.0)
            self.plot_widget.setYRange(y_bot, y_top)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"TwoD: Log scale {'enabled' if enabled else 'disabled'}")

    def _set_xrange_log(self, freq_bins: np.ndarray) -> None:
        """Set x range in log10 space using the first positive bin as the lower bound."""
        positive = freq_bins[freq_bins > 0]
        x_min = float(positive[0]) if len(positive) > 0 else 1.0
        x_max = float(freq_bins[-1])
        self.plot_widget.setXRange(np.log10(x_min), np.log10(x_max), padding=0)

    def update_frequency_bins(self, freq_bins: np.ndarray) -> None:
        """Update the frequency bins for the plot."""
        self.frequency_bins = freq_bins
        if self.log_freq:
            self._set_xrange_log(freq_bins)
        else:
            self.plot_widget.setXRange(freq_bins[0], freq_bins[-1], padding=0)

    def set_peak_search_enabled(self, enabled: bool) -> None:
        """Enable or disable peak search."""
        self.peak_search_enabled = enabled
        if not enabled:
            self.peak_marker.setData([], [])
            self.peak_text.hide()
            # Also hide max peak marker and text if peak search is disabled
            self.max_peak_text.hide()
            self.max_peak_marker.setData([], [])
        else:
            self.peak_text.show()
            if self.max_peak_search_enabled:
                self.max_peak_text.show()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"TwoD: Peak search {'enabled' if enabled else 'disabled'}")

    def set_peak_list(self, peaks: list) -> None:
        """Display up to 5 numbered peak markers. peaks = [(freq, power), ...]."""
        for i, (m, t) in enumerate(zip(self._peak_list_markers, self._peak_list_texts)):
            if i < len(peaks):
                freq, power = peaks[i]
                m.setData([freq], [power])
                t.setPos(freq, power)
                t.show()
            else:
                m.setData([], [])
                t.hide()

    def set_max_peak_search_enabled(self, enabled: bool) -> None:
        """Enable or disable max hold."""
        self.max_peak_search_enabled = enabled
        if not enabled:
            self.max_plot.setData([], [])
            self.max_peak_marker.setData([], [])
            self.max_peak_text.hide()
        else:
            if self.peak_search_enabled:
                self.max_peak_text.show()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"TwoD: Max hold {'enabled' if enabled else 'disabled'}")

    def set_min_hold_enabled(self, enabled: bool) -> None:
        """Enable or disable min hold (blue trace)."""
        self.min_hold_enabled = enabled
        if not enabled:
            self.min_plot.setData([], [])
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"TwoD: Min hold {'enabled' if enabled else 'disabled'}")

    def _format_frequency(self, freq_hz: float) -> str:
        """Format frequency with appropriate unit (Hz, kHz, MHz, GHz)."""
        if freq_hz >= 1e9:
            return f"{freq_hz / 1e9:.2f} GHz"
        elif freq_hz >= 1e6:
            return f"{freq_hz / 1e6:.2f} MHz"
        elif freq_hz >= 1e3:
            return f"{freq_hz / 1e3:.2f} kHz"
        else:
            return f"{freq_hz:.2f} Hz"

    def _format_amplitude(self, value: float) -> str:
        """Format an amplitude value with the correct unit for the current scale."""
        if self.log_scale:
            return f"{value:.2f} dBm"
        return f"{value:.4g} mW"

    def _text_x(self, freq_hz: float) -> float:
        """Return the scene x-coordinate for a frequency value.

        In log-freq mode pyqtgraph's ViewBox uses log10 units, so TextItem.setPos
        must receive log10(freq) — InfiniteLine handles this internally but TextItem
        does not have a setLogMode equivalent.
        """
        if self.log_freq:
            return np.log10(max(freq_hz, 1.0))
        return freq_hz

    def _add_peak_text(self, peak_frequency: float, peak_value: float) -> None:
        """Add or update the live peak text label."""
        freq_str = self._format_frequency(peak_frequency)
        amp_str = self._format_amplitude(peak_value)
        text = (
            f"<span style='color: green;background-color: black;'>Live peak</span> <br>"
            f"<span style='color: white;background-color: black;'>{freq_str}</span> <br>"
            f"<span style='color: white;background-color: black;'>{amp_str}</span>"
        )
        self.peak_text.setHtml(text)
        y_min, y_max = self.plot_widget.viewRange()[1]
        self.peak_text.setPos(self._text_x(peak_frequency), y_min + 0.8 * (y_max - y_min))

    def _add_max_peak_text(self, max_peak_frequency: float, max_peak_value: float) -> None:
        """Add or update the max peak text label."""
        freq_str = self._format_frequency(max_peak_frequency)
        amp_str = self._format_amplitude(max_peak_value)
        text = (
            f"<span style='color: yellow;background-color: black;'>Max peak</span> <br>"
            f"<span style='color: white;background-color: black;'>{freq_str}</span><br>"
            f"<span style='color: white;background-color: black;'>{amp_str}</span>"
        )
        self.max_peak_text.setHtml(text)
        y_min, y_max = self.plot_widget.viewRange()[1]
        self.max_peak_text.setPos(self._text_x(max_peak_frequency), y_min + 0.9 * (y_max - y_min))

    # ------------------------------------------------------------------
    # Display line
    # ------------------------------------------------------------------

    def set_display_line(self, enabled: bool, level: float) -> None:
        """Show or hide the display line at the given dBm level."""
        if enabled:
            if self._display_line is None:
                self._display_line = pg.InfiniteLine(
                    angle=0, movable=False,
                    pen=pg.mkPen(color=(255, 255, 0, 200), width=1, style=Qt.PenStyle.DashLine),
                    label="DL", labelOpts={'color': 'y', 'position': 0.02,
                                           'anchors': [(0, 0), (0, 0)]}
                )
                self.plot_widget.addItem(self._display_line)
            self._display_line.setValue(level)
        else:
            if self._display_line is not None:
                self.plot_widget.removeItem(self._display_line)
                self._display_line = None

    # ------------------------------------------------------------------
    # Threshold line
    # ------------------------------------------------------------------

    def set_threshold_line(self, enabled: bool, level: float) -> None:
        """Show or hide the peak-detection threshold line."""
        if enabled:
            if self._threshold_line is None:
                self._threshold_line = pg.InfiniteLine(
                    angle=0, movable=False,
                    pen=pg.mkPen(color=(255, 80, 80, 200), width=1, style=Qt.PenStyle.DashLine),
                    label="Threshold", labelOpts={'color': (255, 80, 80), 'position': 0.98,
                                                   'anchors': [(1, 0), (1, 0)]}
                )
                self.plot_widget.addItem(self._threshold_line)
            self._threshold_line.setValue(level)
        else:
            if self._threshold_line is not None:
                self.plot_widget.removeItem(self._threshold_line)
                self._threshold_line = None

    # ------------------------------------------------------------------
    # Trace A / B
    # ------------------------------------------------------------------

    def update_trace_a(self, freq_bins: Optional[np.ndarray], power_levels: Optional[np.ndarray]) -> None:
        if freq_bins is not None and power_levels is not None:
            data = power_levels if self.log_scale else 10.0 ** (power_levels / 10.0)
            self.trace_a_plot.setData(freq_bins, data)
        else:
            self.trace_a_plot.setData([], [])

    def update_trace_b(self, freq_bins: Optional[np.ndarray], power_levels: Optional[np.ndarray]) -> None:
        if freq_bins is not None and power_levels is not None:
            data = power_levels if self.log_scale else 10.0 ** (power_levels / 10.0)
            self.trace_b_plot.setData(freq_bins, data)
        else:
            self.trace_b_plot.setData([], [])

    def update_trace_ab_diff(self, freq_bins: Optional[np.ndarray], diff_levels: Optional[np.ndarray]) -> None:
        """Show A-B difference trace (always in dB regardless of scale mode)."""
        if freq_bins is not None and diff_levels is not None:
            self.trace_ab_plot.setData(freq_bins, diff_levels)
        else:
            self.trace_ab_plot.setData([], [])

    def clear_all_traces(self) -> None:
        self.trace_a_plot.setData([], [])
        self.trace_b_plot.setData([], [])
        self.trace_ab_plot.setData([], [])

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    _PERSIST_DEPTHS = {"off": 0, "short": 5, "medium": 15, "long": 30}

    def set_persistence(self, mode: str) -> None:
        """Set persistence ghost-trace mode."""
        new_depth = self._PERSIST_DEPTHS.get(mode, 0)
        for plot in self._persist_plots:
            self.plot_widget.removeItem(plot)
        self._persist_plots.clear()
        r, g, b = self._trace_colour_rgb
        for _ in range(new_depth):
            plot = self.plot_widget.plot(pen=pg.mkPen(color=(r // 2, g // 2, b // 2, 20), width=1))
            self._persist_plots.append(plot)
        self._persist_depth = new_depth
        prev = list(self._persist_buffer)[-new_depth:] if new_depth > 0 else []
        self._persist_buffer = collections.deque(prev, maxlen=max(new_depth, 1))
        logger.debug(f"TwoD: Persistence set to {mode} ({new_depth} frames)")

    def _update_persistence(self, freq_bins: np.ndarray, live_data: np.ndarray) -> None:
        """Render ghost traces from the history buffer, then push the current frame."""
        n_plots = len(self._persist_plots)
        if n_plots == 0:
            return

        buf_list = list(self._persist_buffer)
        for i, plot in enumerate(self._persist_plots):
            buf_idx = len(buf_list) - n_plots + i
            if 0 <= buf_idx < len(buf_list):
                fraction = i / max(n_plots - 1, 1) if n_plots > 1 else 1.0
                alpha = int(15 + fraction * 55)
                r, g, b = self._trace_colour_rgb
                plot.setPen(pg.mkPen(color=(r // 2, g // 2, b // 2, alpha), width=1))
                bfreq, bdata = buf_list[buf_idx]
                if len(bfreq) == len(freq_bins):
                    plot.setData(bfreq, bdata)
                else:
                    plot.setData([], [])
            else:
                plot.setData([], [])

        self._persist_buffer.append((freq_bins.copy(), live_data.copy()))

    # ------------------------------------------------------------------
    # Marker lines
    # ------------------------------------------------------------------

    # Pen specs per marker name: (colour, solid/dashed)
    _FREQ_COLOUR = '#ffd700'   # gold — frequency markers (matches sample rate display)
    _PWR_COLOUR  = '#00FFFF'   # cyan  — power markers
    _MARKER_PENS = {
        'F1': (_FREQ_COLOUR, False),
        'F2': (_FREQ_COLOUR, True),
        'P1': (_PWR_COLOUR,  False),
        'P2': (_PWR_COLOUR,  True),
    }
    _ACTIVE_WIDTH  = 2
    _INACTIVE_WIDTH = 1

    def set_marker(self, name: str, kind: str, position: float, active: bool = False) -> None:
        """Create or update a marker line."""
        colour, dashed = self._MARKER_PENS.get(name, ('w', False))
        width = self._ACTIVE_WIDTH if active else self._INACTIVE_WIDTH
        style = Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine
        pen = pg.mkPen(colour, width=width, style=style)
        angle = 90 if kind == 'freq' else 0
        label_colour = colour

        if name not in self._marker_lines:
            line = pg.InfiniteLine(
                angle=angle,
                movable=False,
                pen=pen,
                label=name,
                labelOpts={'color': label_colour, 'position': 0.95,
                           'anchors': [(0, 0), (0, 0)]}
            )
            self.plot_widget.addItem(line)
            self._marker_lines[name] = line
        else:
            line = self._marker_lines[name]
            line.setPen(pen)

        line.setValue(position)

    def clear_marker(self, name: str) -> None:
        """Remove a marker line from the plot."""
        if name in self._marker_lines:
            self.plot_widget.removeItem(self._marker_lines.pop(name))

    def update_widget_data(
        self,
        live_power_levels,
        max_power_levels: np.ndarray,
        frequency_bins: np.ndarray,
        min_power_levels: Optional[np.ndarray] = None,
    ) -> None:
        """Update the 2D plot with live, max hold, and optional min hold levels.

        live_power_levels may be a tuple (left_db, right_db) for stereo audio,
        or a plain ndarray for all other sources.
        """
        if live_power_levels is None or frequency_bins is None:
            return

        # Handle stereo tuple from audio source
        stereo = isinstance(live_power_levels, tuple)
        if stereo:
            left_db, right_db = live_power_levels
            live_power_levels = left_db  # use left as the "live" trace for hold/peak

        self.live_power_levels = live_power_levels
        self.max_power_levels = max_power_levels

        if (self.frequency_bins is None or
                len(self.frequency_bins) != len(frequency_bins) or
                self.frequency_bins[0] != frequency_bins[0] or
                self.frequency_bins[-1] != frequency_bins[-1]):
            self.update_frequency_bins(frequency_bins)

        freq_bins = frequency_bins

        live_data = live_power_levels if self.log_scale else 10.0 ** (live_power_levels / 10.0)

        # Persistence ghost traces (rendered before live so live draws on top)
        self._update_persistence(freq_bins, live_data)

        # Fill curve (same data as live; brush controls visibility)
        self.fill_curve.setData(freq_bins, live_data)

        # Live trace (left channel in stereo mode)
        self.live_plot.setData(freq_bins, live_data)

        # Right channel — red, only in stereo mode
        if stereo:
            right_data = right_db if self.log_scale else 10.0 ** (right_db / 10.0)
            self.right_plot.setData(freq_bins, right_data)
        else:
            self.right_plot.setData([], [])

        # Max hold plot (yellow) — hidden while buffer is None (e.g. after retune)
        if self.max_peak_search_enabled:
            if max_power_levels is not None:
                max_data = max_power_levels if self.log_scale else 10.0 ** (max_power_levels / 10.0)
                self.max_plot.setData(freq_bins, max_data)
                self.max_plot.setVisible(True)
            else:
                self.max_plot.setVisible(False)

        # Min hold plot (blue)
        if self.min_hold_enabled:
            if min_power_levels is not None:
                min_data = min_power_levels if self.log_scale else 10.0 ** (min_power_levels / 10.0)
                self.min_plot.setData(freq_bins, min_data)
                self.min_plot.setVisible(True)
            else:
                self.min_plot.setVisible(False)

        # Peak markers and text
        if self.peak_search_enabled:
            peak_idx = np.argmax(live_data)
            peak_freq = freq_bins[peak_idx]
            peak_value = live_data[peak_idx]
            self.peak_marker.setData([peak_freq], [peak_value])
            self._add_peak_text(peak_freq, peak_value)

        if self.peak_search_enabled and self.max_peak_search_enabled:
            max_peak_idx = np.argmax(max_data)
            max_peak_freq = freq_bins[max_peak_idx]
            max_peak_value = max_data[max_peak_idx]
            self.max_peak_marker.setData([max_peak_freq], [max_peak_value])
            self._add_max_peak_text(max_peak_freq, max_peak_value)

        #logger.debug("TwoD: Updated widget data")