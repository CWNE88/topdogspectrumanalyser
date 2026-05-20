import numpy as np
import logging
from collections import deque

logger = logging.getLogger(__name__)

_BUFFER_FRAMES = 100  # ~2 s at 20 ms timer


class DutyCycleAnalyser:
    def __init__(self):
        self._envelope: deque = deque(maxlen=_BUFFER_FRAMES)
        self.duty_pct: float = 0.0
        self.on_power_dbm: float | None = None
        self.off_power_dbm: float | None = None
        self.threshold_dbm: float = -60.0

    def update(self, samples: np.ndarray, threshold_dbm: float) -> None:
        """Update from raw IQ or real samples (computes instantaneous envelope)."""
        if samples is None or len(samples) == 0:
            return
        self.threshold_dbm = threshold_dbm
        if np.iscomplexobj(samples):
            env_db = 10.0 * np.log10(np.mean(np.abs(samples) ** 2) + 1e-30)
        else:
            env_db = 10.0 * np.log10(np.mean(samples.ravel() ** 2) + 1e-30)
        self._envelope.append(float(env_db))
        self._recompute(threshold_dbm)

    def update_from_power(self, power_levels_db: np.ndarray, threshold_dbm: float | None = None) -> None:
        """Update from FFT power levels (dB array). Uses peak power as the frame value."""
        if power_levels_db is None or len(power_levels_db) == 0:
            return
        if threshold_dbm is not None:
            self.threshold_dbm = threshold_dbm
        peak = float(np.max(power_levels_db))
        self._envelope.append(peak)
        self._recompute(self.threshold_dbm)

    def _recompute(self, threshold_dbm: float) -> None:
        if not self._envelope:
            return
        arr = np.array(self._envelope)
        on_mask = arr >= threshold_dbm
        on_count = int(np.sum(on_mask))
        total = len(arr)
        self.duty_pct = 100.0 * on_count / total
        self.on_power_dbm = float(np.mean(arr[on_mask])) if on_count > 0 else None
        off_mask = ~on_mask
        self.off_power_dbm = float(np.mean(arr[off_mask])) if np.any(off_mask) else None

    def reset(self) -> None:
        self._envelope.clear()
        self.duty_pct = 0.0
        self.on_power_dbm = None
        self.off_power_dbm = None

    def get_readout(self) -> str:
        if not self._envelope:
            return ""
        on = f"{self.on_power_dbm:.1f} dBm" if self.on_power_dbm is not None else "—"
        off = f"{self.off_power_dbm:.1f} dBm" if self.off_power_dbm is not None else "—"
        return (
            f'<span style="color:white;font-weight:bold;">Duty:</span> '
            f'<span style="color:#00ff88;">{self.duty_pct:.1f}%</span>  '
            f'<span style="color:white;font-weight:bold;">On:</span> '
            f'<span style="color:#00ff88;">{on}</span>  '
            f'<span style="color:white;font-weight:bold;">Off:</span> '
            f'<span style="color:#888888;">{off}</span>'
        )
