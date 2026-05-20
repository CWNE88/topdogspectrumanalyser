"""2D IQ Constellation display using pyqtgraph density histogram or scatter plot."""

import numpy as np
import pyqtgraph as pg
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QRectF
import logging

logger = logging.getLogger(__name__)

try:
    from scipy.signal import hilbert as _scipy_hilbert
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


# Ideal normalised symbol positions (unit average power) for each modulation type
def _qam_grid(levels):
    coords = np.arange(-(levels - 1), levels, 2, dtype=np.float32)
    pts = np.array([(i, q) for i in coords for q in coords], dtype=np.float32)
    rms = np.sqrt(np.mean(pts[:, 0]**2 + pts[:, 1]**2))
    return pts / rms if rms > 0 else pts

_CONST_REFS = {
    "bpsk":  np.array([(-1.0, 0.0), (1.0, 0.0)], dtype=np.float32),
    "qpsk":  np.array([(-1.0,-1.0),(-1.0,1.0),(1.0,-1.0),(1.0,1.0)],
                      dtype=np.float32) / np.sqrt(2.0),
    "8psk":  np.array([(np.cos(k * np.pi / 4), np.sin(k * np.pi / 4))
                       for k in range(8)], dtype=np.float32),
    "16qam": _qam_grid(4),
    "64qam": _qam_grid(8),
}


class Constellation2D(QWidget):
    """IQ constellation diagram with density (histogram) and scatter display modes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._plot = pg.PlotWidget(background='k')
        self._plot.setAspectLocked(True)
        self._plot.setLabel('bottom', 'I (Real)')
        self._plot.setLabel('left', 'Q (Imaginary)')
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        layout.addWidget(self._plot)

        # Density mode: 2D histogram as ImageItem
        self._img = pg.ImageItem()
        cm = pg.colormap.get('viridis')
        self._img.setColorMap(cm)
        self._plot.addItem(self._img)

        # Scatter mode
        self._scatter = pg.ScatterPlotItem(
            size=3, pen=None, brush=pg.mkBrush(0, 200, 255, 140)
        )
        self._plot.addItem(self._scatter)

        # Reference grid overlay (always on top, always visible)
        self._ref_scatter = pg.ScatterPlotItem(
            size=10, pen=pg.mkPen('w', width=1),
            symbol='o', brush=pg.mkBrush(255, 255, 255, 0)
        )
        self._plot.addItem(self._ref_scatter)

        self._mode = "density"
        self._resolution = 128
        self._range = 1.5
        self._max_points = 2000
        self._modulation = "qpsk"
        self.last_evm_rms: float | None = None

        self._apply_range()
        self._apply_ref_points()
        self._update_mode_visibility()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def set_mode(self, mode: str) -> None:
        if mode in ("density", "scatter"):
            self._mode = mode
            self._update_mode_visibility()

    def set_modulation(self, mod: str) -> None:
        self._modulation = mod
        self._apply_ref_points()

    def set_range(self, r: float) -> None:
        self._range = r
        self._apply_range()

    def set_max_points(self, n: int) -> None:
        self._max_points = n

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def update_iq_data(self, samples: np.ndarray) -> None:
        if samples is None or len(samples) == 0:
            return
        try:
            iq = self._to_complex(samples)

            # RMS AGC — normalise to unit average power
            rms = np.sqrt(np.mean(np.abs(iq) ** 2))
            if rms > 1e-10:
                iq = iq / rms

            i_data = np.real(iq).astype(np.float32)
            q_data = np.imag(iq).astype(np.float32)

            self.last_evm_rms = self._compute_evm(i_data, q_data)

            r = self._range
            if self._mode == "density":
                res = self._resolution
                hist, _, _ = np.histogram2d(
                    i_data, q_data, bins=res, range=[[-r, r], [-r, r]]
                )
                disp = np.log1p(hist).T
                self._img.setImage(disp, autoLevels=True)
                self._img.setRect(QRectF(-r, -r, 2 * r, 2 * r))
            else:
                n = min(self._max_points, len(i_data))
                self._scatter.setData(x=i_data[-n:], y=q_data[-n:])
        except Exception as e:
            logger.error(f"Constellation2D update error: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _apply_range(self) -> None:
        r = self._range
        self._plot.setXRange(-r, r)
        self._plot.setYRange(-r, r)

    def _apply_ref_points(self) -> None:
        pts = _CONST_REFS.get(self._modulation)
        if pts is not None and len(pts):
            self._ref_scatter.setData(x=pts[:, 0], y=pts[:, 1])
            self._ref_scatter.setVisible(True)
        else:
            self._ref_scatter.setVisible(False)

    def _compute_evm(self, i_data: np.ndarray, q_data: np.ndarray) -> float | None:
        pts = _CONST_REFS.get(self._modulation)
        if pts is None or len(pts) == 0:
            return None
        iq = np.column_stack([i_data, q_data])          # (N, 2)
        diffs = iq[:, np.newaxis, :] - pts[np.newaxis, :, :]  # (N, M, 2)
        min_dist_sq = np.min(np.sum(diffs ** 2, axis=2), axis=1)  # (N,)
        return float(np.sqrt(np.mean(min_dist_sq)))

    def _update_mode_visibility(self) -> None:
        self._img.setVisible(self._mode == "density")
        self._scatter.setVisible(self._mode == "scatter")

    def _to_complex(self, samples: np.ndarray) -> np.ndarray:
        if np.iscomplexobj(samples):
            return samples.astype(np.complex64)
        if _HAS_SCIPY:
            return _scipy_hilbert(samples.astype(np.float64)).astype(np.complex64)
        n = (len(samples) // 2) * 2
        return (samples[:n:2] + 1j * samples[1:n:2]).astype(np.complex64)

    # ------------------------------------------------------------------
    # Compatibility stubs
    # ------------------------------------------------------------------

    def update_widget_data(self, live, max_hold, freq_bins, min_hold=None): pass
    def set_marker(self, *a, **kw): pass
    def clear_marker(self, *a, **kw): pass
    def set_amplitude(self, *a, **kw): pass
    def set_log_freq(self, *a, **kw): pass
    def set_log_scale(self, *a, **kw): pass
    def set_peak_search_enabled(self, *a, **kw): pass
    def set_max_peak_search_enabled(self, *a, **kw): pass
    def set_min_hold_enabled(self, *a, **kw): pass
    def set_persistence(self, *a, **kw): pass
    def set_display_line(self, *a, **kw): pass
    def set_threshold_line(self, *a, **kw): pass
    def set_live_visible(self, *a, **kw): pass
    def update_trace_a(self, *a, **kw): pass
    def update_trace_b(self, *a, **kw): pass
    def update_trace_ab_diff(self, *a, **kw): pass
    def clear_all_traces(self, *a, **kw): pass
