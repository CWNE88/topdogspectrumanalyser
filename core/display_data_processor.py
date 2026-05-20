"""Data acquisition and processing pipeline for the spectrum analyser display.

Handles the periodic update_data cycle: fetching samples/sweep data from the
active source, applying calibration/tare/averaging/hold, and dispatching the
result to the active display widget.

All state that must persist between frames (_sweep_averager, _sweep_rate_update_counter)
is owned by this class.  Tare state (_tare_buffer, _tare_count, _tare_collecting)
remains on DisplayManager because it is also managed by the _tare_action menu handler.
"""

import time
import numpy as np
import logging

from datasources.base import SampleDataSource, SweepDataSource
from core.tare_state import TareState
from utils.constants import DisplayMode, UIConstants, FrequencyPresets
from utils.signal_processing import TraceAverager
from utils.frequency_helpers import format_hz

_STALE_DATA_TIMEOUT = 3.0  # seconds

logger = logging.getLogger(__name__)


class DataProcessor:
    """Owns the periodic data-update pipeline and all frame-by-frame DSP."""

    _DISPLAY_TIMER_MODES = frozenset({
        DisplayMode.TWO_D,
        DisplayMode.THREE_D,
        DisplayMode.SURFACE,
        DisplayMode.RIBBON,
        DisplayMode.DENSITY,
    })

    def __init__(self, main_window, display_manager):
        self.mw = main_window
        self.dm = display_manager
        self._sweep_averager = TraceAverager()
        self._sweep_rate_update_counter = 0

    def reset_sweep_averager(self) -> None:
        """Reset the sweep averaging buffer (call when switching sources)."""
        self._sweep_averager.reset()

    # ------------------------------------------------------------------
    # Timer entry point
    # ------------------------------------------------------------------

    def update_data(self) -> None:
        """Periodic entry point: route to the correct processing path and refresh display."""
        mw = self.mw
        dm = self.dm
        if mw.current_source is None or mw.paused:
            return

        self._check_stale_data()

        if self.dm.zero_span_active and isinstance(mw.current_source, SampleDataSource):
            self._process_zero_span_data()
            return

        if mw.analysis_mode == "constellation" and isinstance(mw.current_source, SampleDataSource):
            self._process_constellation_data()
            mw.marker_manager.update()
            return

        widget = self._get_active_widget()
        if widget is None:
            return

        try:
            if isinstance(mw.current_source, SampleDataSource):
                self._process_sample_data()
            elif isinstance(mw.current_source, SweepDataSource):
                self._process_sweep_data()
            else:
                mw.status_label.setText(f"Invalid source type: {type(mw.current_source)}")
                logger.error(f"Invalid source type: {type(mw.current_source)}")
                return

            if mw.current_stacked_index == DisplayMode.WATERFALL:
                tpr = dm._calc_time_per_row()
                if tpr > 0:
                    mw.waterfall_widget.set_time_per_row(tpr)
                self._dispatch_widget_data(widget)
            else:
                self._refresh_display()
        except Exception as e:
            mw.status_label.setText(f"Error updating data: {str(e)}")
            logger.error(f"Error updating data: {str(e)}")

    # ------------------------------------------------------------------
    # Display routing
    # ------------------------------------------------------------------

    def _get_active_widget(self):
        """Return the currently active display widget, or None for logo."""
        getter = self.dm.DISPLAY_WIDGETS_MAP.get(self.mw.current_stacked_index)
        return getter(self.mw) if getter else None

    def _dispatch_widget_data(self, widget) -> None:
        """Send the current data snapshot to the widget, honouring popout state."""
        mw = self.mw
        if mw.live_power_levels is None or mw.frequency_bins is None:
            return
        max_levels = mw.max_power_levels
        try:
            if mw.is_popped_out and mw.popout_clone_widget:
                mw.popout_clone_widget.update_widget_data(
                    mw.live_power_levels, max_levels,
                    mw.frequency_bins, mw.min_power_levels
                )
            elif widget.isVisible():
                widget.update_widget_data(
                    mw.live_power_levels, max_levels,
                    mw.frequency_bins, mw.min_power_levels
                )
            mw.marker_manager.update()
        except Exception as e:
            mw.status_label.setText(f"Error updating display: {str(e)}")
            logger.error(f"Error updating display: {str(e)}")

    def _refresh_display(self) -> None:
        """Render the latest accumulated data for timer-driven display modes."""
        mw = self.mw
        if mw.current_stacked_index not in self._DISPLAY_TIMER_MODES:
            return
        widget = self._get_active_widget()
        if widget is None:
            return
        self._dispatch_widget_data(widget)

    def _check_stale_data(self) -> None:
        """Warn on status label if a sample source has stopped delivering data."""
        mw = self.mw
        if not isinstance(mw.current_source, SampleDataSource):
            return
        if mw.live_power_levels is None:
            return
        t = mw.current_source.last_data_time
        if t > 0 and (time.monotonic() - t) > _STALE_DATA_TIMEOUT:
            mw.status_label.setText(
                f"No data for {time.monotonic() - t:.1f}s — source may have stopped"
            )

    # ------------------------------------------------------------------
    # Source-specific processing paths
    # ------------------------------------------------------------------

    def _process_sample_data(self) -> None:
        """Fetch a frame from the sample source, apply cal/tare, store results."""
        mw = self.mw
        result, freq_bins = mw.current_source.get_power_levels()

        # Audio stereo: (left_db, right_db) tuple
        if isinstance(result, tuple):
            left_db, right_db = result
            if left_db is None or len(left_db) == 0:
                return
            left_db  = self._apply_cal_offset(left_db)
            right_db = self._apply_cal_offset(right_db)
            mw.frequency_bins = freq_bins
            mw.live_power_levels = (left_db, right_db)
            self._update_max_hold(left_db)
            self._update_min_hold(left_db)
            return

        power_levels = result
        if power_levels is None or len(power_levels) == 0:
            logger.debug("No data from sample source yet")
            return

        mw.frequency_bins = freq_bins
        power_levels = self._apply_cal_offset(power_levels)
        power_levels = self._apply_tare(power_levels)
        mw.live_power_levels = power_levels
        self._update_max_hold(power_levels)
        self._update_min_hold(power_levels)
        self._update_duty_cycle(power_levels)
        self._update_peak_list(freq_bins, power_levels)

    def _process_sweep_data(self) -> None:
        """Process data from sweep sources and periodically refresh the RBW readout."""
        mw = self.mw
        power_levels = mw.current_source.get_data()
        if power_levels is None or len(power_levels) == 0:
            logger.debug("No data from source yet")
            return

        if mw.frequency.start is None or mw.frequency.stop is None:
            logger.warning("Frequency start/stop is None, resetting to default")
            # Direct set_start_stop intentional here — this is an error-recovery
            # reset inside the hot data path; a full set_frequency_range() call
            # would trigger source restarts and disk writes unnecessarily.
            mw.frequency.set_start_stop(
                FrequencyPresets.HACKRF_DEFAULT_START,
                FrequencyPresets.HACKRF_DEFAULT_STOP
            )

        mw.frequency_bins = np.linspace(
            mw.frequency.start, mw.frequency.stop, len(power_levels)
        )

        power_levels = self._apply_cal_offset(power_levels)

        # Skip NaN-only frames (sweep not yet complete) — feeding NaN to the
        # averager would poison its buffer permanently via NaN arithmetic.
        if np.all(np.isnan(power_levels)):
            return

        if self._sweep_averager.is_active:
            linear = 10.0 ** (power_levels / 10.0)
            power_levels = 10.0 * np.log10(
                np.maximum(self._sweep_averager.process(linear), 1e-30)
            )

        mw.live_power_levels = power_levels
        self._update_max_hold(power_levels)
        self._update_min_hold(power_levels)
        self._update_peak_list(mw.frequency_bins, power_levels)

        self._sweep_rate_update_counter += 1
        if self._sweep_rate_update_counter >= UIConstants.SWEEP_RATE_UPDATE_INTERVAL:
            self._sweep_rate_update_counter = 0
            mw.frequency_manager.update_frequency_values()

    def _process_constellation_data(self) -> None:
        """Fetch raw IQ samples and push to the active constellation widget."""
        mw = self.mw
        dm = self.dm
        samples = mw.current_source.read_samples_only()
        if samples is None or len(samples) == 0:
            return

        idx = mw.current_stacked_index
        if idx == DisplayMode.CONSTELLATION_2D:
            widget = getattr(mw, 'constellation_2d_widget', None)
        elif idx == DisplayMode.CONSTELLATION_3D:
            widget = getattr(mw, 'constellation_3d_widget', None)
        else:
            idx = mw._resolve_display_index()
            dm.set_display(idx, UIConstants.BUTTON_ACTIVE_STYLE, None)
            return

        if widget is not None:
            widget.update_iq_data(samples)
            evm = getattr(widget, 'last_evm_rms', None)
            readout = getattr(mw, 'marker_readout_label', None)
            if readout is not None:
                if evm is not None and evm > 0:
                    evm_pct = evm * 100.0
                    evm_db  = 20.0 * np.log10(evm)
                    mod     = getattr(self.dm, 'constellation_modulation', '').upper()
                    readout.setText(f"EVM  {mod}\n{evm_pct:.1f}%  ({evm_db:+.1f} dB)")
                else:
                    readout.setText("")

    def _process_zero_span_data(self) -> None:
        """Fetch samples and update the zero-span time-domain display."""
        mw = self.mw
        raw = mw.current_source.read_samples_only()
        if raw is None or len(raw) == 0:
            return

        if raw.ndim == 2:
            raw = raw.mean(axis=1)
        samples = (
            raw.real if np.iscomplexobj(raw) else raw.ravel()
        ).astype(np.float32)

        sample_rate = float(getattr(mw.current_source, 'sample_rate', 44100))
        _ZS_BUFFER_SECONDS = 2.0

        buf = self.dm.zero_span_buffer
        buf = samples if buf is None else np.concatenate((buf, samples))
        max_buf = int(_ZS_BUFFER_SECONDS * sample_rate)
        if len(buf) > max_buf:
            buf = buf[-max_buf:]
        self.dm.zero_span_buffer = buf

        n_display = max(int(self.dm.zero_span_time_window * sample_rate), 4)

        if len(buf) < n_display:
            chunk = buf
        elif self.dm.zero_span_trigger_mode == "free_run":
            chunk = buf[-n_display:]
        else:
            search_end   = len(buf) - n_display
            search_start = max(0, search_end - n_display * 8)
            level = self.dm.zero_span_trigger_level
            if search_end > search_start:
                seg = buf[search_start:search_end]
                if self.dm.zero_span_trigger_mode == "rise":
                    mask = (seg[:-1] < level) & (seg[1:] >= level)
                else:
                    mask = (seg[:-1] >= level) & (seg[1:] < level)
                crossings = np.where(mask)[0]
            else:
                crossings = np.array([], dtype=int)

            if len(crossings) > 0:
                cross_idx = search_start + int(crossings[-1]) + 1
                chunk = buf[cross_idx : cross_idx + n_display]
            else:
                chunk = buf[-n_display:]

        time_s = np.arange(len(chunk), dtype=np.float32) / sample_rate
        mw.zero_span_widget.update_zero_span_data(time_s, chunk)

    # ------------------------------------------------------------------
    # DSP helpers
    # ------------------------------------------------------------------

    def _apply_cal_offset(self, power_levels: np.ndarray) -> np.ndarray:
        """Add the per-source calibration offset if one is configured."""
        mw = self.mw
        cal = getattr(mw, 'calibration_manager', None)
        if cal is None:
            return power_levels
        source_type = mw.source_manager.last_source_type
        if not source_type:
            return power_levels
        offset = cal.get_offset(source_type)
        return power_levels + offset if offset != 0.0 else power_levels

    def _apply_tare(self, power_levels: np.ndarray) -> np.ndarray:
        """Accumulate the tare baseline if collecting, then subtract it if active."""
        mw = self.mw
        dm = self.dm
        ts = dm.tare_state  # TareState owned by DisplayManager

        if ts.collecting:
            linear = 10.0 ** (power_levels / 10.0)
            if ts.buffer is None or ts.buffer.shape != linear.shape:
                ts.buffer = linear.copy()
                ts.count = 1
            else:
                ts.buffer += linear
                ts.count += 1

            remaining = UIConstants.TARE_NUM_SAMPLES - ts.count
            mw.status_label.setText(
                f"Collecting normalisation baseline... "
                f"{remaining} frame{'s' if remaining != 1 else ''} remaining"
            )

            if ts.count >= UIConstants.TARE_NUM_SAMPLES:
                avg_linear = ts.buffer / ts.count
                mw.baseline_power_levels = 10.0 * np.log10(
                    np.maximum(avg_linear, 1e-30)
                )
                mw.tare_active = True
                dm.tare_state = TareState()
                dm._update_tare_button_label("Clear\nNormalisation")
                mw.status_label.setText("Tare active — baseline captured")
                logger.debug("Tare baseline captured")

        if mw.tare_active and mw.baseline_power_levels is not None:
            if power_levels.shape != mw.baseline_power_levels.shape:
                dm._clear_tare()
                mw.status_label.setText("Tare cleared — frequency range changed")
                logger.warning("Tare cleared due to shape mismatch")
            else:
                power_levels = power_levels - mw.baseline_power_levels

        return power_levels

    def _update_max_hold(self, power_levels: np.ndarray) -> None:
        """Update max hold buffer — no-op when hold is disabled."""
        mw = self.mw
        if not self.dm.max_peak_search_enabled:
            if (mw.max_power_levels is not None
                    and mw.max_power_levels.shape != power_levels.shape):
                mw.max_power_levels = None
            return
        if mw.max_power_levels is None or mw.max_power_levels.shape != power_levels.shape:
            mw.max_power_levels = self._nan_safe(power_levels, -500.0)
        else:
            np.fmax(mw.max_power_levels, power_levels, out=mw.max_power_levels)

    def _update_min_hold(self, power_levels: np.ndarray) -> None:
        """Update min hold buffer — no-op when hold is disabled."""
        mw = self.mw
        if not mw.min_hold_enabled:
            if (mw.min_power_levels is not None
                    and mw.min_power_levels.shape != power_levels.shape):
                mw.min_power_levels = None
            return
        if mw.min_power_levels is None or mw.min_power_levels.shape != power_levels.shape:
            mw.min_power_levels = self._nan_safe(power_levels, 500.0)
        else:
            np.fmin(mw.min_power_levels, power_levels, out=mw.min_power_levels)

    def _update_duty_cycle(self, power_levels: np.ndarray) -> None:
        """Push the latest frame to the duty-cycle analyser if it is enabled."""
        mw = self.mw
        if not self.dm.duty_cycle_enabled:
            return
        self.dm.duty_cycle_analyser.update_from_power(power_levels)
        readout = getattr(mw, 'marker_readout_label', None)
        if readout is not None:
            readout.setText(self.dm.duty_cycle_analyser.get_readout())

    def _update_peak_list(self, freq_bins: np.ndarray, power_levels: np.ndarray) -> None:
        """Find top-5 peaks and update the 2D widget markers and readout label."""
        mw = self.mw
        if not self.dm.peak_list_enabled:
            return
        widget = mw.two_d_widget
        if not hasattr(widget, 'set_peak_list'):
            return

        min_sep  = max(10, len(freq_bins) // 50)
        excursion = getattr(mw, 'peak_excursion', 10.0)
        peaks = self._find_top_peaks(
            freq_bins, power_levels, n=5,
            min_sep_bins=min_sep, min_excursion_db=excursion
        )
        widget.set_peak_list(peaks)

        readout = getattr(mw, 'marker_readout_label', None)
        if readout is not None:
            lines = [
                f"{i}: Freq: {format_hz(freq)}, Power: {pwr:.1f} dBm"
                for i, (freq, pwr) in enumerate(peaks, 1)
            ]
            readout.setText("\n".join(lines))

    @staticmethod
    def _find_top_peaks(freq_bins: np.ndarray, power: np.ndarray,
                        n: int = 5, min_sep_bins: int = 10,
                        min_excursion_db: float = 10.0) -> list:
        """Return up to n (freq, power) tuples for the highest local maxima.

        Two candidates are treated as the same signal unless there is both a
        minimum bin separation AND a valley at least min_excursion_db below
        both peaks between them.
        """
        if len(power) < 3:
            return []
        is_max = (power[1:-1] > power[:-2]) & (power[1:-1] > power[2:])
        indices = np.where(is_max)[0] + 1

        if len(indices) == 0:
            return []

        indices = indices[np.argsort(power[indices])[::-1]]
        selected, selected_power = [], []

        for idx in indices:
            if len(selected) >= n:
                break
            reject = False
            for sel_idx, sel_pwr in zip(selected, selected_power):
                if abs(idx - sel_idx) < min_sep_bins:
                    reject = True
                    break
                lo, hi = min(idx, sel_idx), max(idx, sel_idx)
                valley = float(np.min(power[lo : hi + 1]))
                if (power[idx] - valley < min_excursion_db
                        or sel_pwr - valley < min_excursion_db):
                    reject = True
                    break
            if not reject:
                selected.append(idx)
                selected_power.append(float(power[idx]))

        return [(float(freq_bins[i]), float(power[i])) for i in selected]

    @staticmethod
    def _nan_safe(arr: np.ndarray, fill: float) -> np.ndarray:
        """Return arr with NaN replaced by fill."""
        if not np.any(np.isnan(arr)):
            return arr
        out = arr.copy()
        out[np.isnan(out)] = fill
        return out
