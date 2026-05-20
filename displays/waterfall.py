import collections
import time
import numpy as np
import pyqtgraph as pg
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)

_MAX_HISTORY = 2000
_DEFAULT_SPR = 0.1    # seconds-per-row until empirical rate arrives
_DEFAULT_SPAN = 60.0


# ── Custom axis formatters ──────────────────────────────────────────────────

class _FreqAxis(pg.AxisItem):
    """X axis: formats Hz values as Hz / kHz / MHz / GHz."""
    def tickStrings(self, values, scale, spacing):
        out = []
        for v in values:
            hz = abs(v)
            if hz >= 1e9:
                out.append(f"{v/1e9:.4g}G")
            elif hz >= 1e6:
                out.append(f"{v/1e6:.4g}M")
            elif hz >= 1e3:
                out.append(f"{v/1e3:.4g}k")
            else:
                out.append(f"{v:.4g}")
        return out


class _TimeAxis(pg.AxisItem):
    """Left axis: maps row index → time label.

    Uses history_lines and wf_time_span so labels always read 0 → selected
    span, independent of the fluctuating seconds_per_row estimate.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history_lines: int   = 600
        self.wf_time_span:  float = _DEFAULT_SPAN

    def tickStrings(self, values, scale, spacing):
        H    = max(self.history_lines, 1)
        span = self.wf_time_span
        out  = []
        for v in values:
            s = float(v) / H * span
            if s == 0.0:
                out.append("0")
            elif s < 60:
                out.append(f"{s:.0f}s")
            else:
                m = s / 60.0
                out.append(f"{m:.0f}m" if m == int(m) else f"{m:.1f}m")
        return out


# ── gqrx-style colourmap ───────────────────────────────────────────────────

def _build_gqrx_cmap() -> pg.ColorMap:
    pos = np.array([0.0, 0.20, 0.40, 0.60, 0.80, 1.0])
    col = np.array([
        [  0,   0,   0, 255],
        [  0,   0, 200, 255],
        [  0, 200, 200, 255],
        [200, 200,   0, 255],
        [200,   0,   0, 255],
        [255, 255, 255, 255],
    ], dtype=np.uint8)
    return pg.ColorMap(pos, col)


_GQRX_CMAP = _build_gqrx_cmap()


# ── Main widget ────────────────────────────────────────────────────────────

class Waterfall(QtWidgets.QWidget):
    """
    Waterfall display with:
    - Double-buffer circular scroll (zero-copy per frame)
    - Row deduplication: only adds a new row when data changes, so that
      the buffer depth correctly represents real time even when the display
      timer fires faster than the source's sweep rate.
    - Time axis always labelled 0 → wf_time_span, independent of rate noise.
    - Independent amplitude range (wf_min_db / wf_max_db).
    """

    def __init__(self):
        super().__init__()

        self._time_axis = _TimeAxis(orientation='left')

        self._gfx = pg.GraphicsLayoutWidget()
        self.plot_item = self._gfx.addPlot(
            axisItems={
                'bottom': _FreqAxis(orientation='bottom'),
                'left':   self._time_axis,
            }
        )
        self.plot_item.invertY(True)
        self.plot_item.setLabel('left',   'Time')
        self.plot_item.setLabel('bottom', 'Frequency')
        self.plot_item.showGrid(x=False, y=True, alpha=0.2)
        self.plot_item.setMenuEnabled(False)
        self.plot_item.enableAutoRange(enable=False)

        self.image_item = pg.ImageItem()
        self.image_item.setAutoDownsample(False)
        self.plot_item.addItem(self.image_item)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._gfx)

        self._marker_lines: dict = {}

        # Amplitude (independent of spectrum)
        self.wf_min_db: float = -100.0
        self.wf_max_db: float =  -20.0

        # Time / history
        self.wf_time_span:    float = _DEFAULT_SPAN
        self.seconds_per_row: float = _DEFAULT_SPR
        self.history_lines:   int   = self._calc_lines()

        # Circular double-buffer
        self._buf:    np.ndarray | None = None
        self._ptr:    int  = 0
        self._n_bins: int  = 0

        # Deduplication: skip _add_row when the frame is identical to last
        self._last_row: np.ndarray | None = None

        # Empirical rate measurement (rolling window of unique-row timestamps)
        self._row_times: collections.deque = collections.deque(maxlen=10)

        self.frequency_bins    = None
        self.live_power_levels = None
        self.initialised: bool = False
        self.frozen:      bool = False

        # Colourmap
        self._colourmap_name: str   = 'magma'
        self.colourmap: pg.ColorMap = pg.colormap.get('magma')
        self._lut:      np.ndarray  = self.colourmap.getLookupTable(nPts=256, mode='byte')
        self._lut_rgba: np.ndarray  = self.colourmap.getLookupTable(nPts=256, alpha=True)
        self.image_item.setLookupTable(self._lut)
        self.image_item.setLevels((self.wf_min_db, self.wf_max_db))

        logger.debug("Waterfall: initialised")

    # ── Internal helpers ───────────────────────────────────────────────────

    def _calc_lines(self) -> int:
        spr = max(self.seconds_per_row, 1e-4)
        return min(_MAX_HISTORY, max(10, int(self.wf_time_span / spr)))

    def _init_buffer(self) -> None:
        H = self._calc_lines()
        W = len(self.frequency_bins)
        self.history_lines = H
        self._n_bins = W
        self._buf = np.full((2 * H, W), self.wf_min_db, dtype=np.float32)
        self._ptr = 0
        logger.debug(f"Waterfall: {H}×{W} rows, span={self.wf_time_span}s, "
                     f"spr={self.seconds_per_row:.3f}s")

    def _add_row(self, row: np.ndarray) -> None:
        H = self.history_lines
        self._ptr = (self._ptr - 1) % H
        self._buf[self._ptr]     = row
        self._buf[self._ptr + H] = row

    def _display_view(self) -> np.ndarray:
        return self._buf[self._ptr : self._ptr + self.history_lines]

    def _update_time_axis(self) -> None:
        """Sync time axis with current history_lines and wf_time_span."""
        self._time_axis.history_lines = self.history_lines
        self._time_axis.wf_time_span  = self.wf_time_span
        self._time_axis.picture = None   # invalidate tick cache
        self._time_axis.update()

    def _set_axes_once(self) -> None:
        """Set image rect and view ranges once per init / span change.

        Y axis is in row units (0 at top = newest). Labels are driven by
        _TimeAxis which always displays 0 → wf_time_span regardless of the
        fluctuating seconds_per_row.
        """
        H  = self.history_lines
        f0 = float(self.frequency_bins[0])
        f1 = float(self.frequency_bins[-1])
        self.plot_item.enableAutoRange(enable=False)
        self.image_item.setRect(f0, 0, f1 - f0, H)
        self.plot_item.setXRange(f0, f1, padding=0)
        self.plot_item.setYRange(0, H, padding=0)
        self._update_time_axis()

    def _initialise(self) -> bool:
        if self.frequency_bins is None:
            return False
        self._init_buffer()
        self._last_row  = None
        self._row_times.clear()
        view = self._display_view()
        img  = np.ascontiguousarray(view.T, dtype=np.float32)
        self.image_item.setImage(img, autoLevels=False,
                                 levels=(self.wf_min_db, self.wf_max_db))
        self._set_axes_once()
        self.initialised = True
        return True

    # ── Public API ─────────────────────────────────────────────────────────

    def set_time_per_row(self, seconds: float) -> None:
        """Hint from display_manager about the source rate.

        Updates seconds_per_row which feeds _calc_lines on the next reinit.
        Does NOT update axis labels (those are fixed to wf_time_span) and
        does NOT trigger reinit (only span changes do that).
        """
        if seconds <= 0:
            return
        change = abs(seconds - self.seconds_per_row) / max(self.seconds_per_row, 1e-6)
        if change > 0.05:
            self.seconds_per_row = seconds

    def set_wf_time_span(self, seconds: float) -> None:
        """Change history duration; forces reinit on next data frame."""
        self.wf_time_span = seconds
        self.initialised  = False
        logger.debug(f"Waterfall: time span → {seconds}s")

    def set_wf_range(self, min_db: float, max_db: float) -> None:
        self.wf_min_db = min_db
        self.wf_max_db = max_db
        self.image_item.setLevels((min_db, max_db))

    def adjust_wf_floor(self, delta_db: float) -> None:
        new_floor = min(self.wf_min_db + delta_db, self.wf_max_db - 1)
        self.set_wf_range(new_floor, self.wf_max_db)

    def adjust_wf_ceiling(self, delta_db: float) -> None:
        new_ceil = max(self.wf_max_db + delta_db, self.wf_min_db + 1)
        self.set_wf_range(self.wf_min_db, new_ceil)

    def toggle_freeze(self) -> None:
        self.frozen = not self.frozen

    def set_colourmap(self, name: str) -> None:
        try:
            cmap = _GQRX_CMAP if name == 'gqrx' else pg.colormap.get(name)
            self._colourmap_name = name
            self.colourmap  = cmap
            self._lut       = cmap.getLookupTable(nPts=256, mode='byte')
            self._lut_rgba  = cmap.getLookupTable(nPts=256, alpha=True)
            self.image_item.setLookupTable(self._lut)
        except Exception as e:
            logger.warning(f"Waterfall: colourmap '{name}' failed: {e}")

    def update_frequency_bins(self, freq_bins) -> None:
        self.frequency_bins = freq_bins
        self.initialised    = False

    def set_amplitude(self, ref_level: float, range_db: float) -> None:
        pass   # waterfall has its own independent range

    # ── Markers ────────────────────────────────────────────────────────────

    _MARKER_PENS = {
        'F1': ('#ffd700', False),
        'F2': ('#ffd700', True),
    }

    def set_marker(self, name: str, kind: str, position: float,
                   active: bool = False) -> None:
        colour, dashed = self._MARKER_PENS.get(name, ('w', False))
        style = Qt.PenStyle.DashLine if dashed else Qt.PenStyle.SolidLine
        pen = pg.mkPen(colour, width=2 if active else 1, style=style)
        if name not in self._marker_lines:
            line = pg.InfiniteLine(
                angle=90, movable=False, pen=pen,
                label=name,
                labelOpts={'color': colour, 'position': 0.95,
                           'anchors': [(0, 0), (0, 0)]}
            )
            self.plot_item.addItem(line)
            self._marker_lines[name] = line
        else:
            self._marker_lines[name].setPen(pen)
        self._marker_lines[name].setValue(position)

    def clear_marker(self, name: str) -> None:
        if name in self._marker_lines:
            self.plot_item.removeItem(self._marker_lines.pop(name))

    # ── Main data update ───────────────────────────────────────────────────

    def update_widget_data(self, live_power_levels, max_power_levels,
                           frequency_bins, min_power_levels=None) -> None:
        if live_power_levels is None or frequency_bins is None:
            return
        if self.frozen:
            return

        if isinstance(live_power_levels, tuple):
            live_power_levels = live_power_levels[0]

        self.live_power_levels = live_power_levels

        bins_changed = (
            self.frequency_bins is None
            or len(self.frequency_bins) != len(frequency_bins)
            or self.frequency_bins[0]  != frequency_bins[0]
            or self.frequency_bins[-1] != frequency_bins[-1]
        )
        if bins_changed:
            self.update_frequency_bins(frequency_bins)

        if not self.initialised:
            if not self._initialise():
                return

        # Deduplication: the 20ms display timer fires faster than most sweep
        # sources deliver new data. Only write a row when the data changed.
        data = np.asarray(live_power_levels, dtype=np.float32)
        is_new = self._last_row is None or not np.array_equal(data, self._last_row)

        if is_new:
            self._last_row = data.copy()
            self._add_row(data)

            # Empirical rate: measure interval between genuinely new rows.
            # This naturally reflects the actual source sweep/FFT rate.
            now = time.monotonic()
            self._row_times.append(now)
            if len(self._row_times) >= 4:
                elapsed = self._row_times[-1] - self._row_times[0]
                n = len(self._row_times) - 1
                if elapsed > 0:
                    emp_spr = elapsed / n
                    change = abs(emp_spr - self.seconds_per_row) / max(self.seconds_per_row, 1e-6)
                    if change > 0.05:
                        self.seconds_per_row = emp_spr
                        # No reinit — axis labels are span-fixed, not rate-dependent

        view = self._display_view()
        img  = np.ascontiguousarray(view.T, dtype=np.float32)
        self.image_item.setImage(img, autoLevels=False,
                                 levels=(self.wf_min_db, self.wf_max_db))

    # ── Export compat ──────────────────────────────────────────────────────

    @property
    def waterfall_array(self):
        if self._buf is None or not self.initialised:
            return None
        return self._display_view()
