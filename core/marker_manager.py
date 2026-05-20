import numpy as np
import logging
from utils.frequency_helpers import format_hz

logger = logging.getLogger(__name__)

from scipy.signal import find_peaks as _scipy_find_peaks


class _Marker:
    def __init__(self, kind: str):
        self.kind = kind        # 'freq' or 'power'
        self.position = None    # Hz for freq, dBm for power
        self.enabled = False

# Dial steps to traverse the full span / full power range
_FREQ_STEPS  = 200
_POWER_STEPS = 100


class MarkerManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.markers = {
            'F1': _Marker('freq'),
            'F2': _Marker('freq'),
            'P1': _Marker('power'),
            'P2': _Marker('power'),
        }
        self.active_marker: str | None = None

    # ------------------------------------------------------------------
    # Public API called by menu actions and dial routing
    # ------------------------------------------------------------------

    @property
    def has_active(self) -> bool:
        return self.active_marker is not None

    def toggle_marker(self, name: str) -> None:
        """Enable and select a marker, or deselect it if pressing it again while already in marker mode."""
        marker = self.markers[name]
        current_mode = getattr(self.main_window, 'frequency_entry_mode', 'centre')
        if marker.enabled and self.active_marker == name and current_mode == 'marker':
            self._deactivate(name)
        else:
            self._activate(name)

    def move_active(self, delta: int) -> None:
        """Move the active marker by one dial step."""
        if self.active_marker is None:
            return
        marker = self.markers[self.active_marker]
        if not marker.enabled:
            return

        if marker.kind == 'freq':
            freq = self.main_window.frequency
            if freq is None or freq.span is None:
                return
            step = freq.span / _FREQ_STEPS
            new_pos = marker.position + delta * step
            # Clamp to current view
            if freq.start is not None and freq.stop is not None:
                new_pos = max(freq.start, min(freq.stop, new_pos))
            marker.position = new_pos
        else:
            step = self.main_window.range_db / _POWER_STEPS
            marker.position = marker.position + delta * step

        self._sync_display(self.active_marker)
        self._refresh_status()

    def snap_to_peak(self) -> None:
        """Snap the active frequency marker to the highest peak above threshold."""
        if self.active_marker is None:
            return
        marker = self.markers[self.active_marker]
        if marker.kind != 'freq':
            self.main_window.status_label.setText("Snap to peak: select a frequency marker first")
            return
        bins, levels = self._data()
        if bins is None:
            return

        threshold = getattr(self.main_window, 'peak_threshold', -200.0)
        excursion = getattr(self.main_window, 'peak_excursion', 6.0)

        peaks, props = _scipy_find_peaks(levels, height=threshold,
                                          prominence=excursion, distance=3)
        if len(peaks) > 0:
            best = peaks[int(np.argmax(props['peak_heights']))]
            marker.position = float(bins[best])
        else:
            marker.position = float(bins[np.argmax(levels)])

        marker.enabled = True
        self._sync_display(self.active_marker)
        self._refresh_status()

    def snap_to_next_peak(self) -> None:
        """Move the active frequency marker to the next local peak to the right."""
        if self.active_marker is None:
            return
        marker = self.markers[self.active_marker]
        if marker.kind != 'freq' or not marker.enabled:
            self.main_window.status_label.setText("Next peak: select a frequency marker first")
            return
        bins, levels = self._data()
        if bins is None:
            return

        threshold = getattr(self.main_window, 'peak_threshold', -200.0)
        excursion = getattr(self.main_window, 'peak_excursion', 6.0)

        peaks, _ = _scipy_find_peaks(levels, height=threshold,
                                      prominence=excursion, distance=3)

        if len(peaks) == 0:
            return

        current_idx = int(np.searchsorted(bins, marker.position))
        right = peaks[peaks > current_idx]
        target = int(right[0]) if len(right) > 0 else int(peaks[0])  # wrap
        marker.position = float(bins[target])
        self._sync_display(self.active_marker)
        self._refresh_status()

    def marker_to_centre(self) -> None:
        """Set the centre frequency to the active F marker position."""
        if self.active_marker is None:
            return
        marker = self.markers[self.active_marker]
        if marker.kind != 'freq' or not marker.enabled:
            self.main_window.status_label.setText("Mkr→Centre: select a frequency marker first")
            return
        self.main_window.frequency_manager.set_frequency_range(
            marker.position - self.main_window.frequency.span / 2,
            marker.position + self.main_window.frequency.span / 2
        )

    def reposition_on_frequency_change(self, old_start: float, old_stop: float,
                                        new_start: float, new_stop: float) -> None:
        """Reposition frequency markers proportionally when the displayed range changes."""
        old_span = old_stop - old_start
        new_span = new_stop - new_start
        if old_span <= 0 or new_span <= 0:
            return
        changed = False
        for marker in self.markers.values():
            if marker.kind == 'freq' and marker.enabled and marker.position is not None:
                fraction = (marker.position - old_start) / old_span
                marker.position = new_start + fraction * new_span
                changed = True
        if changed:
            for name in self.markers:
                self._sync_display(name)
            self._refresh_status()

    def clear_all(self) -> None:
        mw = self.main_window
        three_d = getattr(mw, 'three_d_widget', None)
        for name, marker in self.markers.items():
            marker.enabled = False
            marker.position = None
            mw.two_d_widget.clear_marker(name)
            if marker.kind == 'freq':
                mw.waterfall_widget.clear_marker(name)
            if three_d is not None:
                three_d.clear_marker(name)
        self.active_marker = None
        readout = getattr(mw, 'marker_readout_label', None)
        if readout is not None:
            readout.setText("")
        fm = getattr(mw, 'frequency_manager', None)
        if fm is not None:
            fm.change_entry_mode('centre')
        mw.status_label.setText("All markers cleared")

    def update(self) -> None:
        """Called each display frame to refresh the readout."""
        if any(m.enabled for m in self.markers.values()):
            self._refresh_status()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _activate(self, name: str) -> None:
        marker = self.markers[name]
        if marker.position is None:
            marker.position = self._default_position(marker.kind)
        marker.enabled = True
        self.active_marker = name
        self._sync_display(name)
        self._refresh_status()
        fm = getattr(self.main_window, 'frequency_manager', None)
        if fm is not None:
            fm.change_entry_mode('marker')
        logger.debug(f"Marker {name} activated at {marker.position}")

    def _deactivate(self, name: str) -> None:
        marker = self.markers[name]
        marker.enabled = False
        self.active_marker = None
        mw = self.main_window
        mw.two_d_widget.clear_marker(name)
        if marker.kind == 'freq':
            mw.waterfall_widget.clear_marker(name)
        self._refresh_status()
        logger.debug(f"Marker {name} deactivated")

    def _default_position(self, kind: str) -> float:
        if kind == 'freq':
            freq = self.main_window.frequency
            return float(freq.centre) if freq and freq.centre is not None else 0.0
        else:
            return float(self.main_window.ref_level - self.main_window.range_db / 2)

    def _sync_display(self, name: str) -> None:
        marker = self.markers[name]
        mw = self.main_window
        active = (name == self.active_marker)
        if marker.enabled and marker.position is not None:
            mw.two_d_widget.set_marker(name, marker.kind, marker.position, active=active)
            if marker.kind == 'freq':
                mw.waterfall_widget.set_marker(name, marker.kind, marker.position, active=active)
            three_d = getattr(mw, 'three_d_widget', None)
            if three_d is not None:
                three_d.set_marker(name, marker.kind, marker.position)
        else:
            mw.two_d_widget.clear_marker(name)
            if marker.kind == 'freq':
                mw.waterfall_widget.clear_marker(name)
            three_d = getattr(mw, 'three_d_widget', None)
            if three_d is not None:
                three_d.clear_marker(name)

    def _data(self):
        bins   = self.main_window.frequency_bins
        levels = self.main_window.live_power_levels
        if bins is None or levels is None or len(bins) == 0:
            return None, None
        return bins, levels

    def _refresh_status(self) -> None:
        mw = self.main_window
        parts = []

        marker_text = self._build_readout()
        if marker_text:
            parts.append(marker_text)

        # Append duty cycle readout when active
        if getattr(mw, 'duty_cycle_enabled', False):
            dc_text = mw.display_manager.duty_cycle_analyser.get_readout()
            if dc_text:
                parts.append(dc_text)

        readout = getattr(mw, 'marker_readout_label', None)
        if readout is not None:
            readout.setText("<br>".join(parts))

    _FREQ_COLOUR = '#ffd700'
    _PWR_COLOUR  = '#00FFFF'

    def _build_readout(self) -> str:
        f1 = self.markers['F1']
        f2 = self.markers['F2']
        p1 = self.markers['P1']
        p2 = self.markers['P2']

        def _lbl(text, active):
            indicator = " ◀" if active else ""
            return f'<span style="color:white;font-weight:bold;">{text}:{indicator}</span>'

        def _val(text, colour):
            return f'<span style="color:{colour};">{text}</span>'

        lines = []

        if f1.enabled:
            lines.append(f'{_lbl("Freq 1", self.active_marker == "F1")} '
                         f'{_val(format_hz(f1.position), self._FREQ_COLOUR)}')
        if f2.enabled:
            lines.append(f'{_lbl("Freq 2", self.active_marker == "F2")} '
                         f'{_val(format_hz(f2.position), self._FREQ_COLOUR)}')
        if f1.enabled and f2.enabled:
            delta = f2.position - f1.position
            lines.append(f'{_lbl("ΔF", False)} {_val(format_hz(abs(delta)), self._FREQ_COLOUR)}')
            bp = self._band_power(f1.position, f2.position)
            if bp is not None:
                lines.append(f'{_lbl("Band Power", False)} '
                             f'{_val(f"{bp:.1f} dBm", self._FREQ_COLOUR)}')

        if p1.enabled:
            lines.append(f'{_lbl("Pwr 1", self.active_marker == "P1")} '
                         f'{_val(f"{p1.position:.1f} dBm", self._PWR_COLOUR)}')
        if p2.enabled:
            lines.append(f'{_lbl("Pwr 2", self.active_marker == "P2")} '
                         f'{_val(f"{p2.position:.1f} dBm", self._PWR_COLOUR)}')
        if p1.enabled and p2.enabled:
            lines.append(f'{_lbl("ΔP", False)} '
                         f'{_val(f"{p2.position - p1.position:.1f} dB", self._PWR_COLOUR)}')

        return "<br>".join(lines)

    def _band_power(self, f_start: float, f_stop: float):
        bins, levels = self._data()
        if bins is None:
            return None
        lo, hi = min(f_start, f_stop), max(f_start, f_stop)
        mask = (bins >= lo) & (bins <= hi)
        if not np.any(mask):
            return None
        bin_width = (bins[-1] - bins[0]) / max(len(bins) - 1, 1)
        total = np.sum(10.0 ** (levels[mask] / 10.0)) * bin_width
        return 10.0 * np.log10(max(total, 1e-30))

    # ------------------------------------------------------------------
    # Preset contribution
    # ------------------------------------------------------------------

    def capture_preset(self) -> dict:
        return {
            'markers': {
                name: {'enabled': m.enabled, 'position': m.position}
                for name, m in self.markers.items()
            },
            'active_marker': self.active_marker,
        }

    def apply_preset(self, s: dict) -> None:
        self.clear_all()
        for name, data in s.get('markers', {}).items():
            if name in self.markers:
                m = self.markers[name]
                m.enabled  = data.get('enabled', False)
                m.position = data.get('position')
        active = s.get('active_marker')
        self.active_marker = (
            active if active and active in self.markers
            and self.markers[active].enabled else None
        )
        for name in self.markers:
            self._sync_display(name)
        self._refresh_status()
