"""3D IQ Constellation display — time-depth scatter using pyqtgraph.opengl."""

import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
import logging

logger = logging.getLogger(__name__)

try:
    import pyqtgraph.opengl as gl
    _HAS_GL = True
except ImportError:
    _HAS_GL = False
    logger.warning("pyqtgraph.opengl not available — Constellation3D will be blank")

try:
    from scipy.signal import hilbert as _scipy_hilbert
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False

_MAX_FRAMES = 20      # Time slices kept
_Z_STEP = 0.15        # Spacing between time planes
_POINTS_PER_FRAME = 400


class Constellation3D(QWidget):
    """3D IQ scatter with time depth: X=I, Y=Q, Z=time (newest at Z=0)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._frames = []  # list of (i_data, q_data) float32 arrays

        if _HAS_GL:
            self._view = gl.GLViewWidget()
            self._view.setBackgroundColor('k')
            self._view.opts['distance'] = 4.0
            self._view.opts['elevation'] = 25
            self._view.opts['azimuth'] = -60

            grid = gl.GLGridItem()
            grid.scale(0.5, 0.5, 0.5)
            self._view.addItem(grid)

            self._scatter = gl.GLScatterPlotItem()
            self._view.addItem(self._scatter)
            layout.addWidget(self._view)
        else:
            from PyQt6.QtWidgets import QLabel
            lbl = QLabel("OpenGL not available", self)
            layout.addWidget(lbl)

    def set_range(self, r: float) -> None:
        self._range = r

    def set_max_points(self, n: int) -> None:
        self._points_per_frame = n // max(_MAX_FRAMES, 1)

    def set_modulation(self, mod: str) -> None:
        pass  # reference overlay not implemented for 3D view

    def update_iq_data(self, samples: np.ndarray) -> None:
        if not _HAS_GL or samples is None or len(samples) == 0:
            return
        try:
            iq = self._to_complex(samples)

            # RMS AGC
            rms = np.sqrt(np.mean(np.abs(iq) ** 2))
            if rms > 1e-10:
                iq = iq / rms

            i_data = np.real(iq).astype(np.float32)
            q_data = np.imag(iq).astype(np.float32)

            ppf = getattr(self, '_points_per_frame', _POINTS_PER_FRAME)
            n = min(ppf, len(i_data))
            idx = np.linspace(0, len(i_data) - 1, n, dtype=int)
            self._frames.append((i_data[idx], q_data[idx]))
            if len(self._frames) > _MAX_FRAMES:
                self._frames.pop(0)

            self._rebuild_scatter()
        except Exception as e:
            logger.error(f"Constellation3D update error: {e}")

    def _rebuild_scatter(self) -> None:
        if not self._frames:
            return
        n_frames = len(self._frames)
        all_pos = []
        all_colors = []

        for z_idx, (i_data, q_data) in enumerate(self._frames):
            z_val = (z_idx - n_frames + 1) * _Z_STEP
            n = len(i_data)
            pos = np.column_stack([
                i_data, q_data, np.full(n, z_val, dtype=np.float32)
            ]).astype(np.float32)

            age = (z_idx + 1) / n_frames  # 0=oldest, 1=newest
            colors = np.zeros((n, 4), dtype=np.float32)
            colors[:, 0] = 0.0
            colors[:, 1] = age
            colors[:, 2] = 1.0
            colors[:, 3] = age * 0.8 + 0.2

            all_pos.append(pos)
            all_colors.append(colors)

        pos = np.vstack(all_pos).astype(np.float32)
        colors = np.vstack(all_colors).astype(np.float32)
        self._scatter.setData(pos=pos, color=colors, size=3)

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

    def update_widget_data(self, live, max_hold, freq_bins, min_hold=None):
        pass

    def set_marker(self, *args, **kwargs): pass
    def clear_marker(self, *args, **kwargs): pass
    def set_amplitude(self, *args, **kwargs): pass
    def set_log_freq(self, *args, **kwargs): pass
    def set_log_scale(self, *args, **kwargs): pass
    def set_peak_search_enabled(self, *args, **kwargs): pass
    def set_max_peak_search_enabled(self, *args, **kwargs): pass
    def set_min_hold_enabled(self, *args, **kwargs): pass
    def set_persistence(self, *args, **kwargs): pass
    def set_display_line(self, *args, **kwargs): pass
    def set_threshold_line(self, *args, **kwargs): pass
    def set_live_visible(self, *args, **kwargs): pass
    def update_trace_a(self, *args, **kwargs): pass
    def update_trace_b(self, *args, **kwargs): pass
    def update_trace_ab_diff(self, *args, **kwargs): pass
    def clear_all_traces(self, *args, **kwargs): pass
