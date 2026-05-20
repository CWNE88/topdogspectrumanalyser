import numpy as np
from PyQt6 import QtWidgets
import pyqtgraph.opengl as gl
from matplotlib.colors import hsv_to_rgb
import logging

logger = logging.getLogger(__name__)


class RibbonWidget(QtWidgets.QWidget):
    """3-D ribbon waterfall display.

    Each frame's spectrum becomes a solid ribbon mesh.  History scrolls away
    from the viewer so the newest data is always at the front.  Ribbons are
    colour-coded from red (newest / highest power) to blue (oldest / lowest).
    """

    NUM_ROWS = 30
    SPACING  = 0.7    # Y gap between ribbon rows in GL units
    Z_SCALE  = 8.0    # maximum height in GL units

    def __init__(self):
        super().__init__()

        self.ref_level = 0.0
        self.range_db  = 100.0

        self.widget = gl.GLViewWidget()
        self.widget.opts['distance']        = 40
        self.widget.opts['elevation']       = 20
        self.widget.opts['azimuth']         = -45
        self.widget.opts['bgcolor']         = (0.0, 0.0, 0.0, 1.0)
        self.widget.opts['devicePixelRatio'] = 1

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.widget)

        self.frequency_bins  = None
        self.num_bins        = 0
        self.all_heights     = None   # shape (NUM_ROWS, num_bins)
        self.ribbons: list   = []
        self.faces           = None
        self._x              = None
        self._initialised    = False

        logger.debug("RibbonWidget: initialised")

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    def _dbm_to_z(self, dbm: np.ndarray) -> np.ndarray:
        ref_bottom = self.ref_level - self.range_db
        return np.clip(
            (dbm - ref_bottom) / self.range_db * self.Z_SCALE,
            0.0, self.Z_SCALE
        ).astype(np.float32)

    def _make_x(self) -> np.ndarray:
        n = self.num_bins
        if self.frequency_bins is not None and len(self.frequency_bins) >= 2:
            f0 = float(self.frequency_bins[0])
            f1 = float(self.frequency_bins[-1])
            span = f1 - f0 if f1 != f0 else 1.0
            return (-10.0 + (self.frequency_bins.astype(np.float32) - f0) / span * 20.0)
        return np.linspace(-10.0, 10.0, n, dtype=np.float32)

    # ------------------------------------------------------------------
    # Geometry builders
    # ------------------------------------------------------------------

    def _make_faces(self, n: int) -> np.ndarray:
        """Pre-compute face index array for an n-bin ribbon."""
        faces = []
        for i in range(n - 1):
            faces.append([i * 2,     i * 2 + 1, i * 2 + 2])
            faces.append([i * 2 + 1, i * 2 + 3, i * 2 + 2])
        return np.array(faces, dtype=np.uint32)

    def _row_verts_colors(self, row_idx: int, heights: np.ndarray):
        """Return (verts, vertex_colors) for one ribbon row."""
        x        = self._x
        y_front  = row_idx * self.SPACING
        y_back   = y_front + self.SPACING * 0.85
        n        = len(heights)

        verts = np.empty((n * 2, 3), dtype=np.float32)
        verts[0::2, 0] = x
        verts[0::2, 1] = y_front
        verts[0::2, 2] = heights
        verts[1::2, 0] = x
        verts[1::2, 1] = y_back
        verts[1::2, 2] = heights

        # Colour: hue from red (new/high) to blue (old/low) per vertex
        t   = np.clip(heights / self.Z_SCALE, 0.0, 1.0)
        age = row_idx / max(self.NUM_ROWS - 1, 1)
        # hue: newest high-power → red (0.0), oldest low-power → blue (0.66)
        hue = (1.0 - t) * 0.66 * (0.3 + 0.7 * age)
        sat = np.ones_like(hue)
        val = np.clip(1.0 - age * 0.6, 0.3, 1.0) * np.ones_like(hue)

        hsv    = np.stack([hue, sat, val], axis=1)
        rgb    = hsv_to_rgb(hsv).astype(np.float32)
        alpha  = np.full((n, 1), max(0.3, 1.0 - age * 0.5), dtype=np.float32)
        per_v  = np.concatenate([rgb, alpha], axis=1)

        colors = np.empty((n * 2, 4), dtype=np.float32)
        colors[0::2] = per_v
        colors[1::2] = per_v

        return verts, colors

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_geometry(self, num_bins: int) -> None:
        for r in self.ribbons:
            self.widget.removeItem(r)
        self.ribbons.clear()

        self.num_bins    = num_bins
        self.all_heights = np.zeros((self.NUM_ROWS, num_bins), dtype=np.float32)
        self.faces       = self._make_faces(num_bins)
        self._x          = self._make_x()

        for i in range(self.NUM_ROWS):
            verts, colors = self._row_verts_colors(i, self.all_heights[i])
            ribbon = gl.GLMeshItem(
                vertexes=verts,
                faces=self.faces,
                vertexColors=colors,
                drawEdges=False,
                smooth=False,
                computeNormals=False,
            )
            self.widget.addItem(ribbon)
            self.ribbons.append(ribbon)

        self._initialised = True
        logger.debug(f"RibbonWidget: initialised geometry for {num_bins} bins")

    # ------------------------------------------------------------------
    # Public interface (matches ThreeD / Surface)
    # ------------------------------------------------------------------

    def update_frequency_bins(self, bins: np.ndarray) -> None:
        if bins is None or len(bins) == 0:
            return
        needs_reinit = (
            self.frequency_bins is None
            or len(self.frequency_bins) != len(bins)
        )
        self.frequency_bins = bins.copy()
        if needs_reinit:
            self._init_geometry(len(bins))
        else:
            self._x = self._make_x()

    def update_widget_data(
        self,
        live_power_levels,
        max_power_levels: np.ndarray,
        frequency_bins:   np.ndarray,
        min_power_levels  = None,
    ) -> None:
        if live_power_levels is None or frequency_bins is None:
            return

        if isinstance(live_power_levels, tuple):
            live_power_levels = live_power_levels[0]

        # Re-init if bin count or range changed
        if (self.frequency_bins is None
                or len(self.frequency_bins) != len(frequency_bins)
                or self.frequency_bins[0]  != frequency_bins[0]
                or self.frequency_bins[-1] != frequency_bins[-1]):
            self.update_frequency_bins(frequency_bins)

        if not self._initialised:
            return

        new_heights = self._dbm_to_z(live_power_levels)

        # Scroll history and insert newest row at front
        self.all_heights[1:] = self.all_heights[:-1]
        self.all_heights[0]  = new_heights

        for i, ribbon in enumerate(self.ribbons):
            verts, colors = self._row_verts_colors(i, self.all_heights[i])
            ribbon.setMeshData(
                vertexes=verts,
                faces=self.faces,
                vertexColors=colors,
            )

    def set_amplitude(self, ref_level: float, range_db: float) -> None:
        self.ref_level = ref_level
        self.range_db  = range_db

    def set_log_freq(self, enabled: bool) -> None:
        pass  # ribbon uses linear X; no-op keeps compatibility with display_manager calls
