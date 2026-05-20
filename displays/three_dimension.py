from PyQt6 import QtGui, QtWidgets
import pyqtgraph.opengl as gl
import numpy as np
import logging
from matplotlib.colors import hsv_to_rgb

logger = logging.getLogger(__name__)


class ThreeD(QtWidgets.QWidget):

    X_RANGE        = (-10, 10)
    Y_RANGE        = (-10, 10)
    Z_SCALE        = 8
    DEFAULT_GRID_Y = 10    # front face — where the newest trace lives
    NUMBER_OF_LINES = 300
    TRACE_WIDTH    = 5
    MAX_HOLD_WIDTH = 3

    MAX_HOLD_COLOUR  = (1.0, 1.0, 0.0, 0.5)
    MIN_HOLD_COLOUR  = (0.2, 0.5, 1.0, 0.5)
    DISP_LINE_COLOUR = (1.0, 1.0, 0.0, 0.5)

    _MARKER_COLOURS = {
        'F1': (1.0, 0.84, 0.0, 0.55),
        'F2': (1.0, 0.84, 0.0, 0.30),
        'P1': (0.0, 1.0,  1.0, 0.55),
        'P2': (0.0, 1.0,  1.0, 0.30),
    }

    def __init__(self):
        super().__init__()

        self.ref_level: float = 0.0
        self.range_db:  float = 100.0
        self.log_freq:  bool  = False

        self.widget = gl.GLViewWidget()
        self.widget.opts["distance"]         = 28
        self.widget.opts["azimuth"]          = 90
        self.widget.opts["fov"]              = 70
        self.widget.opts["elevation"]        = 28
        self.widget.opts["bgcolor"]          = (0.0, 0.0, 0.0, 1.0)
        self.widget.opts["devicePixelRatio"] = 1
        self.widget.opts["center"] = QtGui.QVector3D(
            1.616751790046692, -0.9432722926139832, 0.0
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.widget)

        self.live_power_levels = None
        self.frequency_bins    = None
        self.max_hold_levels   = None
        self.peak_search_enabled     = False
        self.max_peak_search_enabled = False
        self.min_hold_enabled        = False
        self.traces_initialised      = False

        self.num_history_lines: int  = self.NUMBER_OF_LINES
        self.auto_rotate:       bool = False
        self._grid_visible:     bool = True

        self.x = None
        self.y = None
        self.z = None
        self.line_y_values = np.linspace(
            self.Y_RANGE[1], self.Y_RANGE[0], self.num_history_lines
        )
        self.traces         = {}
        self.max_hold_trace = None
        self.max_hold_z     = None
        self.min_hold_trace = None

        # grid — stored so it can be shown/hidden
        self._grid = gl.GLGridItem()
        self._grid.setSize(20, 20)
        self._grid.setSpacing(2, 2)
        self._grid.rotate(90, 1, 0, 0)
        self._grid.translate(0, self.DEFAULT_GRID_Y, 0)
        self.widget.addItem(self._grid)

        # live peak sphere (green) + label
        peak_pts = gl.MeshData.sphere(rows=10, cols=10)
        self.peak_sphere = gl.GLMeshItem(meshdata=peak_pts, smooth=True,
                                          color=(1, 1, 1, 1), shader='balloon')
        self.peak_sphere.scale(0.2, 0.2, 0.2)
        self.peak_sphere.translate(0, 0, -100)
        self.widget.addItem(self.peak_sphere)

        # max hold peak sphere
        self.max_peak_sphere = gl.GLMeshItem(meshdata=peak_pts, smooth=True,
                                              color=(1, 1, 1, 1), shader='balloon')
        self.max_peak_sphere.scale(0.2, 0.2, 0.2)
        self.max_peak_sphere.translate(0, 0, -100)
        self.widget.addItem(self.max_peak_sphere)

        # live peak label — 3 separate items so each line can have its own colour
        self._live_label = gl.GLTextItem()
        self._live_label.setData(pos=(0.0, 0.0, -100.0), color=(0, 255, 0, 255), text="")
        self.widget.addItem(self._live_label)
        self._live_freq = gl.GLTextItem()
        self._live_freq.setData(pos=(0.0, 0.0, -100.0), color=(255, 255, 255, 255), text="")
        self.widget.addItem(self._live_freq)
        self._live_power = gl.GLTextItem()
        self._live_power.setData(pos=(0.0, 0.0, -100.0), color=(255, 255, 255, 255), text="")
        self.widget.addItem(self._live_power)

        # max hold peak label
        self._max_label = gl.GLTextItem()
        self._max_label.setData(pos=(0.0, 0.0, -100.0), color=(255, 255, 0, 255), text="")
        self.widget.addItem(self._max_label)
        self._max_freq = gl.GLTextItem()
        self._max_freq.setData(pos=(0.0, 0.0, -100.0), color=(255, 255, 255, 255), text="")
        self.widget.addItem(self._max_freq)
        self._max_power = gl.GLTextItem()
        self._max_power.setData(pos=(0.0, 0.0, -100.0), color=(255, 255, 255, 255), text="")
        self.widget.addItem(self._max_power)

        # display line (lazy)
        self._display_line_item = None
        self._display_line_text = None
        self._display_line_enabled = False
        self._display_line_level   = -50.0

        # markers: name → {line, text, kind, position}
        self._marker_items: dict = {}

        logger.debug("ThreeD: initialised")

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    def _hz_to_x(self, hz: float) -> float:
        if self.frequency_bins is None or len(self.frequency_bins) < 2:
            return 0.0
        f0 = float(self.frequency_bins[0])
        f1 = float(self.frequency_bins[-1])
        if f1 == f0:
            return 0.0
        if self.log_freq:
            lhz = np.log10(max(hz, 1.0))
            lf0 = np.log10(max(f0, 1.0))
            lf1 = np.log10(max(f1, 1.0))
            span = lf1 - lf0
            if span == 0.0:
                return 0.0
            return -10.0 + ((lhz - lf0) / span) * 20.0
        return -10.0 + ((hz - f0) / (f1 - f0)) * 20.0

    def _dbm_to_z(self, dbm: float) -> float:
        ref_bottom = self.ref_level - self.range_db
        return float(np.clip(
            (dbm - ref_bottom) / self.range_db * self.Z_SCALE,
            0.0, self.Z_SCALE
        ))

    @staticmethod
    def _format_freq(hz: float) -> str:
        hz = abs(hz)
        if hz >= 1e9: return f"{hz/1e9:.3f} GHz"
        if hz >= 1e6: return f"{hz/1e6:.3f} MHz"
        if hz >= 1e3: return f"{hz/1e3:.3f} kHz"
        return f"{hz:.1f} Hz"

    @staticmethod
    def _vert_rect(x: float, y0: float, y1: float,
                   z0: float, z1: float) -> np.ndarray:
        return np.array([[x, y0, z0], [x, y1, z0], [x, y1, z1],
                         [x, y0, z1], [x, y0, z0]], dtype=float)

    @staticmethod
    def _horiz_rect(x0: float, x1: float, y0: float, y1: float,
                    z: float) -> np.ndarray:
        return np.array([[x0, y0, z], [x1, y0, z], [x1, y1, z],
                         [x0, y1, z], [x0, y0, z]], dtype=float)

    # ------------------------------------------------------------------
    # Trace initialisation
    # ------------------------------------------------------------------

    def update_frequency_bins(self, bins: np.ndarray) -> None:
        if bins is None or len(bins) == 0:
            return
        if (self.frequency_bins is not None
                and len(self.frequency_bins) == len(bins)
                and self.frequency_bins[0] == bins[0]
                and self.frequency_bins[-1] == bins[-1]):
            return
        self.frequency_bins = bins
        self.traces_initialised = False
        self.max_hold_z = np.zeros(len(bins))
        self.initialise_traces()

    def initialise_traces(self) -> None:
        if self.frequency_bins is None or len(self.frequency_bins) == 0:
            return

        for trace in self.traces.values():
            self.widget.removeItem(trace)
        self.traces.clear()

        saved_markers = {
            name: (items['kind'], items['position'])
            for name, items in self._marker_items.items()
        }
        for name in list(self._marker_items):
            self.widget.removeItem(self._marker_items[name]['line'])
            self.widget.removeItem(self._marker_items[name]['text'])
        self._marker_items.clear()

        if self.max_hold_trace is not None:
            self.widget.removeItem(self.max_hold_trace)
            self.max_hold_trace = None
        if self.min_hold_trace is not None:
            self.widget.removeItem(self.min_hold_trace)
            self.min_hold_trace = None
        if self._display_line_item is not None:
            self.widget.removeItem(self._display_line_item)
            self._display_line_item = None
        if self._display_line_text is not None:
            self.widget.removeItem(self._display_line_text)
            self._display_line_text = None

        f0 = float(np.min(self.frequency_bins))
        f1 = float(np.max(self.frequency_bins))
        if f1 == f0:
            f1 = f0 + 1.0
        if self.log_freq:
            log_bins = np.log10(np.maximum(self.frequency_bins, 1.0))
            lf0 = np.log10(max(f0, 1.0))
            lf1 = np.log10(max(f1, 1.0))
            span = lf1 - lf0 if lf1 != lf0 else 1.0
            self.x = -10 + ((log_bins - lf0) / span) * 20
        else:
            self.x = -10 + ((self.frequency_bins - f0) / (f1 - f0)) * 20

        z_zero = np.zeros_like(self.frequency_bins)

        for i in range(self.num_history_lines):
            pts = np.vstack([self.x,
                             np.full_like(self.x, self.line_y_values[i]),
                             z_zero]).T
            self.traces[i] = gl.GLLinePlotItem(
                pos=pts,
                color=np.zeros((len(self.x), 4), dtype=float),
                antialias=True, mode="line_strip"
            )

        # Add oldest traces first so newest (index 0) is drawn last and appears on top
        for i in range(self.num_history_lines - 1, -1, -1):
            self.widget.addItem(self.traces[i])

        front_y = np.full_like(self.x, self.line_y_values[0])
        pts_front = np.vstack([self.x, front_y, z_zero]).T

        self.max_hold_trace = gl.GLLinePlotItem(
            pos=pts_front.copy(), color=(0, 0, 0, 0),
            antialias=True, mode="line_strip", width=self.MAX_HOLD_WIDTH
        )
        self.widget.addItem(self.max_hold_trace)
        self.max_hold_z = z_zero.copy()

        self.min_hold_trace = gl.GLLinePlotItem(
            pos=pts_front.copy(), color=(0, 0, 0, 0),
            antialias=True, mode="line_strip", width=self.MAX_HOLD_WIDTH
        )
        self.widget.addItem(self.min_hold_trace)

        if self._display_line_enabled:
            self.set_display_line(True, self._display_line_level)

        for name, (kind, position) in saved_markers.items():
            self.set_marker(name, kind, position)

        self.traces_initialised = True
        logger.debug(f"ThreeD: traces initialised, {len(self.frequency_bins)} bins")

    # ------------------------------------------------------------------
    # Display line
    # ------------------------------------------------------------------

    def set_display_line(self, enabled: bool, level_dbm: float) -> None:
        self._display_line_enabled = enabled
        self._display_line_level   = level_dbm

        if not enabled:
            if self._display_line_item is not None:
                self.widget.removeItem(self._display_line_item)
                self._display_line_item = None
            if self._display_line_text is not None:
                self.widget.removeItem(self._display_line_text)
                self._display_line_text = None
            return

        z  = self._dbm_to_z(level_dbm)
        x0, x1 = float(self.X_RANGE[0]), float(self.X_RANGE[1])
        y0, y1 = float(self.Y_RANGE[0]), float(self.Y_RANGE[1])
        pts = self._horiz_rect(x0, x1, y0, y1, z)

        if self._display_line_item is None:
            self._display_line_item = gl.GLLinePlotItem(
                pos=pts, color=self.DISP_LINE_COLOUR, width=2
            )
            self.widget.addItem(self._display_line_item)
        else:
            self._display_line_item.setData(pos=pts, color=self.DISP_LINE_COLOUR)

        if self._display_line_text is None:
            self._display_line_text = gl.GLTextItem()
            self.widget.addItem(self._display_line_text)
        self._display_line_text.setData(
            pos=(x1 + 0.5, y0, z),
            color=(255, 255, 0, 220),
            text=f"DL: {level_dbm:.1f} dBm"
        )

    # ------------------------------------------------------------------
    # Markers
    # ------------------------------------------------------------------

    def set_marker(self, name: str, kind: str, position: float) -> None:
        colour = self._MARKER_COLOURS.get(name, (1.0, 1.0, 1.0, 0.4))
        y0, y1 = float(self.Y_RANGE[0]), float(self.Y_RANGE[1])

        if kind == 'freq':
            x = self._hz_to_x(position)
            pts = self._vert_rect(x, y0, y1, 0.0, float(self.Z_SCALE))
            label = f"{name}: {self._format_freq(position)}"
            text_pos = (x, float(self.DEFAULT_GRID_Y) + 0.5, float(self.Z_SCALE) + 0.5)
        else:
            z = self._dbm_to_z(position)
            pts = self._horiz_rect(
                float(self.X_RANGE[0]), float(self.X_RANGE[1]), y0, y1, z
            )
            label = f"{name}: {position:.1f} dBm"
            text_pos = (float(self.X_RANGE[1]) + 0.5, y0, z)

        tc = tuple(int(c * 255) for c in colour[:3]) + (220,)

        if name not in self._marker_items:
            line = gl.GLLinePlotItem(pos=pts, color=colour, width=2)
            text = gl.GLTextItem()
            self.widget.addItem(line)
            self.widget.addItem(text)
            self._marker_items[name] = {
                'line': line, 'text': text, 'kind': kind, 'position': position
            }
        else:
            self._marker_items[name]['line'].setData(pos=pts, color=colour)
            self._marker_items[name]['kind']     = kind
            self._marker_items[name]['position'] = position

        self._marker_items[name]['text'].setData(
            pos=text_pos, color=tc, text=label
        )

    def clear_marker(self, name: str) -> None:
        if name in self._marker_items:
            items = self._marker_items.pop(name)
            self.widget.removeItem(items['line'])
            self.widget.removeItem(items['text'])

    # ------------------------------------------------------------------
    # State toggles
    # ------------------------------------------------------------------

    def _place_sphere(self, sphere, x: float, y: float, z: float) -> None:
        sphere.resetTransform()
        sphere.scale(0.2, 0.2, 0.2)
        sphere.translate(x, y, z)

    def _hide_sphere(self, sphere) -> None:
        self._place_sphere(sphere, 0, 0, -100)

    def _hide_peak_text(self) -> None:
        off = (0.0, 0.0, -100.0)
        for item in (self._live_label, self._live_freq, self._live_power,
                     self._max_label, self._max_freq, self._max_power):
            item.setData(pos=off, text="")

    def set_peak_search_enabled(self, is_enabled: bool) -> None:
        self.peak_search_enabled = is_enabled
        if not is_enabled:
            self._hide_sphere(self.peak_sphere)
            self._hide_sphere(self.max_peak_sphere)
            self._hide_peak_text()

    def set_max_peak_search_enabled(self, is_enabled: bool) -> None:
        self.max_peak_search_enabled = is_enabled
        if not is_enabled:
            if self.max_hold_z is not None:
                self.max_hold_z.fill(0)
            if self.max_hold_trace is not None:
                self.max_hold_trace.setData(color=(0, 0, 0, 0))

    def set_min_hold_enabled(self, is_enabled: bool) -> None:
        self.min_hold_enabled = is_enabled
        if not is_enabled and self.min_hold_trace is not None:
            self.min_hold_trace.setData(color=(0, 0, 0, 0))

    def set_log_freq(self, enabled: bool) -> None:
        """Switch the X axis between linear and logarithmic frequency spacing."""
        self.log_freq = enabled
        if self.frequency_bins is not None and len(self.frequency_bins) > 0:
            self.traces_initialised = False
            self.initialise_traces()
        logger.debug(f"ThreeD: log freq {'enabled' if enabled else 'disabled'}")

    def set_history_lines(self, n: int) -> None:
        """Set the number of scrolling history lines and reinitialise traces."""
        if n == self.num_history_lines:
            return
        self.num_history_lines = n
        self.line_y_values = np.linspace(self.Y_RANGE[1], self.Y_RANGE[0], n)
        self.max_hold_z = np.zeros(len(self.frequency_bins)) if self.frequency_bins is not None else None
        self.traces_initialised = False
        if self.frequency_bins is not None and len(self.frequency_bins) > 0:
            self.initialise_traces()
        logger.debug(f"ThreeD: history lines set to {n}")

    def set_grid_visible(self, visible: bool) -> None:
        """Show or hide the frequency/amplitude reference grid."""
        self._grid_visible = visible
        self._grid.setVisible(visible)
        logger.debug(f"ThreeD: grid {'shown' if visible else 'hidden'}")

    def toggle_auto_rotate(self) -> None:
        """Toggle continuous camera azimuth rotation."""
        self.auto_rotate = not self.auto_rotate
        logger.debug(f"ThreeD: auto-rotate {'on' if self.auto_rotate else 'off'}")

    def set_amplitude(self, ref_level: float, range_db: float) -> None:
        self.ref_level = ref_level
        self.range_db  = range_db

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def set_plotdata(self, name, points, colour, width):
        if name == "max_hold":
            self.max_hold_trace.setData(pos=points, color=colour, width=width)
        else:
            self.traces[name].setData(pos=points, color=colour, width=width)

    def update_widget_data(
        self,
        live_power_levels,
        max_power_levels: np.ndarray,
        frequency_bins:   np.ndarray,
        min_power_levels  = None,
    ) -> None:
        if live_power_levels is None or frequency_bins is None:
            return
        if max_power_levels is None:
            max_power_levels = live_power_levels

        if isinstance(live_power_levels, tuple):
            live_power_levels = live_power_levels[0]

        self.live_power_levels = live_power_levels
        self.max_hold_levels   = max_power_levels

        if (self.frequency_bins is None
                or len(self.frequency_bins) != len(frequency_bins)
                or self.frequency_bins[0]  != frequency_bins[0]
                or self.frequency_bins[-1] != frequency_bins[-1]):
            self.update_frequency_bins(frequency_bins)

        if not self.traces_initialised:
            self.initialise_traces()
            if not self.traces_initialised:
                return

        ref_bottom = self.ref_level - self.range_db

        def _to_z(power_db):
            z = (power_db - ref_bottom) / self.range_db * self.Z_SCALE
            return np.clip(z, 0.0, self.Z_SCALE)

        # shift history
        for i in range(self.num_history_lines - 1):
            src = self.num_history_lines - i - 2
            dst = self.num_history_lines - i - 1
            trace = self.traces[src]
            pos = trace.pos
            pos[:, 1] = self.line_y_values[dst]
            self.set_plotdata(dst, pos, trace.color, 1)

        # newest live trace
        self.y = np.full_like(self.frequency_bins, self.line_y_values[0])
        self.z = _to_z(live_power_levels)

        hues = int(self.Z_SCALE * 1.4)
        ind  = (self.Z_SCALE - self.z).astype(np.int32) % hues
        hsv  = np.stack([ind.astype(np.float32) / hues,
                         np.ones(len(ind), dtype=np.float32),
                         np.ones(len(ind), dtype=np.float32)], axis=1)
        colours = np.empty((len(self.frequency_bins), 4), dtype=np.float32)
        colours[:, :3] = hsv_to_rgb(hsv).astype(np.float32)
        colours[:, 3]  = 1.0
        self.set_plotdata(0, np.vstack((self.x, self.y, self.z)).T,
                          colours, self.TRACE_WIDTH)

        # max hold
        if self.max_peak_search_enabled:
            max_z = _to_z(max_power_levels)
            self.max_hold_z = np.maximum(self.max_hold_z, max_z)
            pts = np.vstack((self.x, self.y, self.max_hold_z)).T
            self.set_plotdata("max_hold", pts, self.MAX_HOLD_COLOUR, self.MAX_HOLD_WIDTH)

        # min hold
        if self.min_hold_enabled and min_power_levels is not None:
            min_z = _to_z(min_power_levels)
            pts = np.vstack((self.x, self.y, min_z)).T
            self.min_hold_trace.setData(
                pos=pts, color=self.MIN_HOLD_COLOUR, width=self.MAX_HOLD_WIDTH
            )

        # auto-rotate
        if self.auto_rotate:
            self.widget.opts['azimuth'] = (self.widget.opts['azimuth'] + 0.1) % 360
        self.widget.update()

        # peak search
        if self.peak_search_enabled:
            gy  = float(self.DEFAULT_GRID_Y)
            top = float(self.Z_SCALE)
            dz  = 0.9  # vertical gap between label lines

            # live peak (green sphere)
            li   = int(np.argmax(self.z))
            lx   = float(self.x[li])
            ldbm = float(live_power_levels[li])
            self._place_sphere(self.peak_sphere, lx, float(self.line_y_values[0]),
                               float(self.z[li]))
            self._live_label.setData(pos=(lx, gy, top + 3 * dz),
                                     color=(0, 255, 0, 255), text="Live peak")
            self._live_freq.setData(pos=(lx, gy, top + 2 * dz),
                                    color=(255, 255, 255, 255),
                                    text=self._format_freq(float(self.frequency_bins[li])))
            self._live_power.setData(pos=(lx, gy, top + 1 * dz),
                                     color=(255, 255, 255, 255),
                                     text=f"{ldbm:.1f} dBm")

            # max hold peak (yellow sphere) — only when max hold active
            if self.max_peak_search_enabled and self.max_hold_z is not None:
                mi   = int(np.argmax(self.max_hold_z))
                mx   = float(self.x[mi])
                mdbm = float(max_power_levels[mi])
                self._place_sphere(self.max_peak_sphere, mx, float(self.line_y_values[0]),
                                   float(self.max_hold_z[mi]))
                self._max_label.setData(pos=(mx, gy, top + 3 * dz),
                                        color=(255, 255, 0, 255), text="Max peak")
                self._max_freq.setData(pos=(mx, gy, top + 2 * dz),
                                       color=(255, 255, 255, 255),
                                       text=self._format_freq(float(self.frequency_bins[mi])))
                self._max_power.setData(pos=(mx, gy, top + 1 * dz),
                                        color=(255, 255, 255, 255),
                                        text=f"{mdbm:.1f} dBm")
            else:
                self._hide_sphere(self.max_peak_sphere)
                for item in (self._max_label, self._max_freq, self._max_power):
                    item.setData(pos=(0.0, 0.0, -100.0), text="")
