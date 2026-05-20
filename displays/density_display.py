"""Density (persistence) spectrum display — 2D histogram coloured by dwell time."""

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtWidgets import QWidget, QVBoxLayout
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_AMP_BINS    = 512
_AMP_MIN     = -200.0   # fixed histogram range — independent of display settings
_AMP_RNG     = 300.0    # covers -200 to +100 dBm; viewport clips the rest
_DECAY_RATES = {"fast": 0.88, "medium": 0.96, "slow": 0.995, "off": 1.0}


class DensityDisplay(QWidget):
    """2D persistence histogram: frequency × amplitude, coloured by dwell density.

    Each update the current trace is accumulated into a histogram.  A
    configurable decay factor causes old history to fade.  The histogram is
    log-normalised and rendered as a coloured image behind the live trace.
    """

    def __init__(self) -> None:
        super().__init__()
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('k')
        self.plot_widget.setLabel('left', 'Power', units='dBm')
        self.plot_widget.setLabel('bottom', 'Frequency', units='Hz')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)

        # Density histogram image — drawn first so the trace sits on top
        self._img = pg.ImageItem()
        self._img.setColorMap(pg.colormap.get('magma'))
        self.plot_widget.addItem(self._img)

        # Live trace
        self.live_plot = pg.PlotCurveItem(antialias=True)
        self.plot_widget.addItem(self.live_plot)

        # Max / min hold lines
        self.max_plot = pg.PlotCurveItem(antialias=True)
        self.plot_widget.addItem(self.max_plot)
        self.min_plot = pg.PlotCurveItem(antialias=True)
        self.plot_widget.addItem(self.min_plot)

        # Peak markers
        self.peak_marker = self.plot_widget.plot(
            pen=None, symbol='t', symbolPen=None, symbolBrush='w', symbolSize=14)
        self.max_peak_marker = self.plot_widget.plot(
            pen=None, symbol='t', symbolPen=None, symbolBrush=(255, 220, 0), symbolSize=14)
        self.peak_text = pg.TextItem("", anchor=(0.5, 0.5))
        self.plot_widget.addItem(self.peak_text)
        self.peak_text.hide()
        self.max_peak_text = pg.TextItem("", anchor=(0.5, 0.5))
        self.plot_widget.addItem(self.max_peak_text)
        self.max_peak_text.hide()

        # Trace A / B / A-B
        self.trace_a_plot  = pg.PlotCurveItem(antialias=True)
        self.trace_b_plot  = pg.PlotCurveItem(antialias=True)
        self.trace_ab_plot = pg.PlotCurveItem(antialias=True)
        self.plot_widget.addItem(self.trace_a_plot)
        self.plot_widget.addItem(self.trace_b_plot)
        self.plot_widget.addItem(self.trace_ab_plot)

        # Display / threshold lines
        self._display_line:   Optional[pg.InfiniteLine] = None
        self._threshold_line: Optional[pg.InfiniteLine] = None
        self._marker_lines: dict = {}

        layout = QVBoxLayout()
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        # Amplitude / axis state
        self.ref_level = 0.0
        self.range_db  = 100.0
        self.log_scale = True
        self.log_freq  = False

        # Hold flags
        self.peak_search_enabled      = False
        self.max_peak_search_enabled  = False
        self.min_hold_enabled         = False

        # Histogram state
        self._hist: Optional[np.ndarray] = None  # (n_freq, AMP_BINS)
        self._hist_n_freq    = 0
        self._decay          = _DECAY_RATES["medium"]
        self._decay_name     = "medium"
        self._colourmap_name = "magma"
        self._last_freq_rect: Optional[tuple] = None  # (f_start, f_stop) — triggers rect refresh

        self.plot_widget.setYRange(-100, 0)
        self.plot_widget.enableAutoRange(enable=False)
        self._apply_styles()
        logger.debug("DensityDisplay: initialised")

    # ------------------------------------------------------------------
    # Styles
    # ------------------------------------------------------------------

    def _apply_styles(self) -> None:
        self.live_plot.setPen(pg.mkPen(color=(220, 220, 220), width=1))
        self.max_plot.setPen(pg.mkPen(color=(255, 220, 0), width=1, style=Qt.PenStyle.DashLine))
        self.min_plot.setPen(pg.mkPen(color=(80, 100, 255), width=1, style=Qt.PenStyle.DashLine))
        self.trace_a_plot.setPen(pg.mkPen(color=(0, 200, 255, 180), width=1, style=Qt.PenStyle.DashLine))
        self.trace_b_plot.setPen(pg.mkPen(color=(255, 165, 0, 180), width=1, style=Qt.PenStyle.DashLine))
        self.trace_ab_plot.setPen(pg.mkPen(color=(220, 80, 220, 200), width=1))

    # ------------------------------------------------------------------
    # Density-specific controls
    # ------------------------------------------------------------------

    def set_decay(self, mode: str) -> None:
        self._decay = _DECAY_RATES.get(mode, 0.96)
        self._decay_name = mode

    def set_colourmap(self, name: str) -> None:
        try:
            self._img.setColorMap(pg.colormap.get(name))
            self._colourmap_name = name
        except Exception as e:
            logger.warning(f"DensityDisplay: colourmap '{name}' unavailable: {e}")

    def clear_histogram(self) -> None:
        if self._hist is not None:
            self._hist[:] = 0.0

    # ------------------------------------------------------------------
    # Amplitude / axis
    # ------------------------------------------------------------------

    def set_amplitude(self, ref_level: float, range_db: float) -> None:
        self.ref_level = ref_level
        self.range_db  = range_db
        if self.log_scale:
            self.plot_widget.setYRange(ref_level - range_db, ref_level)
        else:
            y_top = 10.0 ** (ref_level / 10.0)
            y_bot = 10.0 ** ((ref_level - range_db) / 10.0)
            self.plot_widget.setYRange(y_bot, y_top)

    def set_log_scale(self, enabled: bool) -> None:
        self.log_scale = enabled
        self._img.setVisible(enabled)
        self._hist = None  # dB bins don't map to linear display — clear on switch
        if enabled:
            self.plot_widget.setLabel('left', 'Power', units='dBm')
            self.plot_widget.setYRange(self.ref_level - self.range_db, self.ref_level)
        else:
            self.plot_widget.setLabel('left', 'Power', units='mW')
            y_top = 10.0 ** (self.ref_level / 10.0)
            y_bot = 10.0 ** ((self.ref_level - self.range_db) / 10.0)
            self.plot_widget.setYRange(y_bot, y_top)

    def set_log_freq(self, enabled: bool) -> None:
        self.log_freq = enabled
        self.plot_widget.setLogMode(x=enabled, y=False)

    def set_persistence(self, mode: str) -> None:
        pass  # density IS persistence — no separate action

    # ------------------------------------------------------------------
    # Hold / peak / visibility
    # ------------------------------------------------------------------

    def set_live_visible(self, visible: bool) -> None:
        self.live_plot.setPen(
            pg.mkPen(color=(220, 220, 220), width=1) if visible else pg.mkPen(None))

    def set_peak_search_enabled(self, enabled: bool) -> None:
        self.peak_search_enabled = enabled
        if not enabled:
            self.peak_marker.setData([], [])
            self.peak_text.hide()
            self.max_peak_marker.setData([], [])
            self.max_peak_text.hide()
        else:
            self.peak_text.show()
            if self.max_peak_search_enabled:
                self.max_peak_text.show()

    def set_max_peak_search_enabled(self, enabled: bool) -> None:
        self.max_peak_search_enabled = enabled
        if not enabled:
            self.max_plot.setData([], [])
            self.max_peak_marker.setData([], [])
            self.max_peak_text.hide()
        else:
            if self.peak_search_enabled:
                self.max_peak_text.show()

    def set_min_hold_enabled(self, enabled: bool) -> None:
        self.min_hold_enabled = enabled
        if not enabled:
            self.min_plot.setData([], [])

    # ------------------------------------------------------------------
    # Display / threshold lines
    # ------------------------------------------------------------------

    def set_display_line(self, enabled: bool, level: float) -> None:
        if enabled:
            if self._display_line is None:
                self._display_line = pg.InfiniteLine(
                    angle=0, movable=False,
                    pen=pg.mkPen(color=(255, 255, 0, 200), width=1, style=Qt.PenStyle.DashLine),
                    label="DL", labelOpts={'color': 'y', 'position': 0.02,
                                           'anchors': [(0, 0), (0, 0)]})
                self.plot_widget.addItem(self._display_line)
            self._display_line.setValue(level)
        else:
            if self._display_line is not None:
                self.plot_widget.removeItem(self._display_line)
                self._display_line = None

    def set_threshold_line(self, enabled: bool, level: float) -> None:
        if enabled:
            if self._threshold_line is None:
                self._threshold_line = pg.InfiniteLine(
                    angle=0, movable=False,
                    pen=pg.mkPen(color=(255, 80, 80, 200), width=1, style=Qt.PenStyle.DashLine),
                    label="Threshold", labelOpts={'color': (255, 80, 80), 'position': 0.98,
                                                   'anchors': [(1, 0), (1, 0)]})
                self.plot_widget.addItem(self._threshold_line)
            self._threshold_line.setValue(level)
        else:
            if self._threshold_line is not None:
                self.plot_widget.removeItem(self._threshold_line)
                self._threshold_line = None

    # ------------------------------------------------------------------
    # Marker lines
    # ------------------------------------------------------------------

    _FREQ_COLOUR = '#ffd700'
    _PWR_COLOUR  = '#00FFFF'
    _MARKER_PENS = {
        'F1': (_FREQ_COLOUR, False), 'F2': (_FREQ_COLOUR, True),
        'P1': (_PWR_COLOUR,  False), 'P2': (_PWR_COLOUR,  True),
    }

    def set_marker(self, name: str, kind: str, position: float, active: bool = False) -> None:
        colour, dashed = self._MARKER_PENS.get(name, ('w', False))
        pen = pg.mkPen(colour, width=2 if active else 1,
                       style=Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine)
        angle = 90 if kind == 'freq' else 0
        if name not in self._marker_lines:
            line = pg.InfiniteLine(
                angle=angle, movable=False, pen=pen,
                label=name, labelOpts={'color': colour, 'position': 0.95,
                                       'anchors': [(0, 0), (0, 0)]})
            self.plot_widget.addItem(line)
            self._marker_lines[name] = line
        else:
            self._marker_lines[name].setPen(pen)
        self._marker_lines[name].setValue(position)

    def clear_marker(self, name: str) -> None:
        if name in self._marker_lines:
            self.plot_widget.removeItem(self._marker_lines.pop(name))

    # ------------------------------------------------------------------
    # Trace A / B
    # ------------------------------------------------------------------

    def update_trace_a(self, freq_bins, power_levels) -> None:
        if freq_bins is not None and power_levels is not None:
            self.trace_a_plot.setData(
                freq_bins, power_levels if self.log_scale else 10.0 ** (power_levels / 10.0))
        else:
            self.trace_a_plot.setData([], [])

    def update_trace_b(self, freq_bins, power_levels) -> None:
        if freq_bins is not None and power_levels is not None:
            self.trace_b_plot.setData(
                freq_bins, power_levels if self.log_scale else 10.0 ** (power_levels / 10.0))
        else:
            self.trace_b_plot.setData([], [])

    def update_trace_ab_diff(self, freq_bins, diff_levels) -> None:
        if freq_bins is not None and diff_levels is not None:
            self.trace_ab_plot.setData(freq_bins, diff_levels)
        else:
            self.trace_ab_plot.setData([], [])

    def clear_all_traces(self) -> None:
        self.trace_a_plot.setData([], [])
        self.trace_b_plot.setData([], [])
        self.trace_ab_plot.setData([], [])

    # ------------------------------------------------------------------
    # Histogram core
    # ------------------------------------------------------------------

    def _ensure_hist(self, n_freq: int) -> None:
        if self._hist is None or self._hist_n_freq != n_freq:
            self._hist = np.zeros((n_freq, _AMP_BINS), dtype=np.float32)
            self._hist_n_freq  = n_freq
            self._last_freq_rect = None

    def _update_hist(self, live_db: np.ndarray, freq_bins: np.ndarray) -> None:
        n = len(live_db)
        self._ensure_hist(n)

        if self._decay < 1.0:
            self._hist *= self._decay

        valid = ~np.isnan(live_db)
        raw_idx = np.full(n, -1, dtype=np.int32)
        raw_idx[valid] = ((live_db[valid] - _AMP_MIN) / _AMP_RNG * _AMP_BINS).astype(np.int32)
        in_range = (raw_idx >= 0) & (raw_idx < _AMP_BINS)
        fi = np.where(in_range)[0]
        if len(fi):
            self._hist[fi, raw_idx[fi]] += 1.0

        self._img.setImage(np.log1p(self._hist), autoLevels=True)

        f_start = float(freq_bins[0])
        f_stop  = float(freq_bins[-1])
        freq_key = (f_start, f_stop)
        if freq_key != self._last_freq_rect:
            self._img.setRect(QRectF(f_start, _AMP_MIN, f_stop - f_start, _AMP_RNG))
            self.plot_widget.setXRange(f_start, f_stop, padding=0)
            self._last_freq_rect = freq_key

    # ------------------------------------------------------------------
    # Main data update
    # ------------------------------------------------------------------

    def update_widget_data(
        self,
        live_power_levels,
        max_power_levels,
        frequency_bins: np.ndarray,
        min_power_levels=None,
    ) -> None:
        if live_power_levels is None or frequency_bins is None:
            return

        stereo = isinstance(live_power_levels, tuple)
        if stereo:
            live_power_levels, _ = live_power_levels

        if self.log_scale:
            live_data = live_power_levels
            max_data  = max_power_levels if max_power_levels is not None else live_power_levels
        else:
            live_data = 10.0 ** (live_power_levels / 10.0)
            max_data  = (10.0 ** (max_power_levels / 10.0)
                         if max_power_levels is not None else live_data)

        # Histogram always binned in dB space; hidden when log_scale=False
        if self.log_scale:
            self._update_hist(live_power_levels, frequency_bins)

        self.live_plot.setData(frequency_bins, live_data)

        if self.max_peak_search_enabled and max_power_levels is not None:
            self.max_plot.setData(frequency_bins, max_data)

        if self.min_hold_enabled and min_power_levels is not None:
            min_data = min_power_levels if self.log_scale else 10.0 ** (min_power_levels / 10.0)
            self.min_plot.setData(frequency_bins, min_data)

        if self.peak_search_enabled:
            peak_idx   = int(np.argmax(live_data))
            peak_freq  = frequency_bins[peak_idx]
            peak_value = live_data[peak_idx]
            self.peak_marker.setData([peak_freq], [peak_value])
            amp_str = f"{peak_value:.1f} dBm" if self.log_scale else f"{peak_value:.4g} mW"
            self.peak_text.setHtml(
                f"<span style='color:white;background-color:black;'>Peak<br>"
                f"{self._fmt_freq(peak_freq)}<br>{amp_str}</span>")
            y_min, y_max = self.plot_widget.viewRange()[1]
            x = np.log10(max(peak_freq, 1.0)) if self.log_freq else float(peak_freq)
            self.peak_text.setPos(x, y_min + 0.8 * (y_max - y_min))
            self.peak_text.show()

        if self.peak_search_enabled and self.max_peak_search_enabled and max_power_levels is not None:
            mp_idx   = int(np.argmax(max_data))
            mp_freq  = frequency_bins[mp_idx]
            mp_value = max_data[mp_idx]
            self.max_peak_marker.setData([mp_freq], [mp_value])
            y_min, y_max = self.plot_widget.viewRange()[1]
            x = np.log10(max(mp_freq, 1.0)) if self.log_freq else float(mp_freq)
            self.max_peak_text.setPos(x, y_min + 0.9 * (y_max - y_min))
            self.max_peak_text.show()

    @staticmethod
    def _fmt_freq(hz: float) -> str:
        if hz >= 1e9:
            return f"{hz / 1e9:.2f} GHz"
        if hz >= 1e6:
            return f"{hz / 1e6:.2f} MHz"
        if hz >= 1e3:
            return f"{hz / 1e3:.2f} kHz"
        return f"{hz:.2f} Hz"
