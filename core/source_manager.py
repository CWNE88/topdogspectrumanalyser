from datasources.base import SweepDataSource, SampleDataSource
from datasources.rtl_sweep import RtlSweepDataSource
from datasources.hackrf_sweep import HackRFSweepDataSource
from datasources.rtl_samples import RtlSamplesDataSource
from datasources.audio_samples import MicrophoneSamplesDataSource
from datasources.hackrf_samples import HackrfSamplesDataSource
from utils.constants import (
    SourceType, FrequencyPresets, SourceLimits,
    UIConstants, MenuButtonId, DisplayMode
)
from utils.frequency_helpers import calculate_frequency_bins_from_range, update_display_frequency_bins, update_all_display_frequency_bins, format_hz
from utils.validators import clamp_centre_span
from utils.config_paths import config_dir
from typing import Optional, Dict, Type
import logging
import os
import numpy as np

logger = logging.getLogger(__name__)

class SourceManager:
    """Manages data sources for the spectrum analyser."""

    SOURCE_DISPLAY_NAMES: Dict[str, str] = {
        SourceType.RTL_SWEEP.value:          "RTL Sweep",
        SourceType.HACKRF_SWEEP.value:       "HackRF Sweep",
        SourceType.RTL_SAMPLES.value:        "RTL Samples",
        SourceType.MICROPHONE_SAMPLES.value: "Microphone",
        SourceType.HACKRF_SAMPLES.value:     "HackRF Samples",
    }

    # Class-level mapping of source types to classes
    SOURCE_CLASSES: Dict[str, Type] = {
        SourceType.RTL_SWEEP.value: RtlSweepDataSource,
        SourceType.HACKRF_SWEEP.value: HackRFSweepDataSource,
        SourceType.RTL_SAMPLES.value: RtlSamplesDataSource,
        SourceType.MICROPHONE_SAMPLES.value: MicrophoneSamplesDataSource,
        SourceType.HACKRF_SAMPLES.value: HackrfSamplesDataSource
    }

    # Mapping from button IDs to source types
    BUTTON_TO_SOURCE: Dict[str, str] = {
        MenuButtonId.RTL_SAMPLES.value: SourceType.RTL_SAMPLES.value,
        MenuButtonId.MICROPHONE_SAMPLES.value: SourceType.MICROPHONE_SAMPLES.value,
        MenuButtonId.HACKRF_SAMPLES.value: SourceType.HACKRF_SAMPLES.value
    }

    # Source categories for transfer logic
    _SWEEP_SOURCES  = frozenset({SourceType.RTL_SWEEP.value, SourceType.HACKRF_SWEEP.value})
    _SAMPLE_SOURCES = frozenset({SourceType.RTL_SAMPLES.value, SourceType.HACKRF_SAMPLES.value})
    _AUDIO_SOURCES  = frozenset({SourceType.MICROPHONE_SAMPLES.value})

    # Hardware limits: min/max centre frequency and maximum displayable span
    _SOURCE_LIMITS: Dict[str, Dict] = {
        SourceType.RTL_SWEEP.value:          {'min': SourceLimits.RTL_MIN_FREQ,    'max': SourceLimits.RTL_MAX_FREQ,    'max_span': SourceLimits.RTL_MAX_FREQ    - SourceLimits.RTL_MIN_FREQ},
        SourceType.HACKRF_SWEEP.value:       {'min': SourceLimits.HACKRF_MIN_FREQ, 'max': SourceLimits.HACKRF_MAX_FREQ, 'max_span': SourceLimits.HACKRF_MAX_FREQ - SourceLimits.HACKRF_MIN_FREQ},
        SourceType.RTL_SAMPLES.value:        {'min': SourceLimits.RTL_MIN_FREQ,    'max': SourceLimits.RTL_MAX_FREQ,    'max_span': SourceLimits.RTL_MAX_SAMPLE_RATE},
        SourceType.HACKRF_SAMPLES.value:     {'min': SourceLimits.HACKRF_MIN_FREQ, 'max': SourceLimits.HACKRF_MAX_FREQ, 'max_span': SourceLimits.HACKRF_MAX_SAMPLE_RATE},
        SourceType.MICROPHONE_SAMPLES.value: {'min': 0.0,                          'max': 48000.0,                      'max_span': 48000.0},
    }

    # First-use defaults per source (centre Hz, span Hz)
    # For sample sources span == sample_rate; for microphone span == Nyquist == sample_rate/2
    _SOURCE_DEFAULTS: Dict[str, Dict] = {
        SourceType.RTL_SWEEP.value:          {'centre': 98e6,    'span': 20e6},
        SourceType.HACKRF_SWEEP.value:       {'centre': 2450e6,  'span': 100e6},
        SourceType.RTL_SAMPLES.value:        {'centre': 98e6,    'span': 2.048e6},
        SourceType.HACKRF_SAMPLES.value:     {'centre': 2450e6,  'span': 20e6},
        SourceType.MICROPHONE_SAMPLES.value: {'centre': 11025.0, 'span': 22050.0},
    }

    def __init__(self, main_window):
        self.main_window = main_window
        self.last_source_type: Optional[str] = None
        self._source_memory: Dict[str, Dict] = {}   # source_id → {centre, span}
        self._switch_message: Optional[str] = None  # shown in status bar after switch
        self.paused_rtl_source = None
        self._last_state_path = str(config_dir() / "source_memory.json")
        self._load_last_state()

    def _clamp_frequency_to_source_limits(self, centre_freq: float, span: float, source_type: str) -> tuple[float, float]:
        """Delegate to the canonical clamp_centre_span utility."""
        return clamp_centre_span(centre_freq, span, source_type, self._SOURCE_LIMITS)

    # ------------------------------------------------------------------
    # Per-source frequency memory
    # ------------------------------------------------------------------

    def _source_category(self, src: Optional[str]) -> str:
        if src in self._SWEEP_SOURCES:  return 'sweep'
        if src in self._SAMPLE_SOURCES: return 'sample'
        return 'audio'

    def _save_source_frequency(self) -> None:
        """Snapshot the current frequency into per-source memory and persist to disk."""
        src = self.last_source_type
        if src is None:
            return
        freq = self.main_window.frequency
        if freq.centre is None or freq.span is None:
            return
        self._source_memory[src] = {'centre': freq.centre, 'span': freq.span}
        self._write_last_state()
        logger.debug(f"Saved {src}: centre={freq.centre:.0f} Hz span={freq.span:.0f} Hz")

    def update_source_memory(self) -> None:
        """Public hook for FrequencyManager to call after every committed frequency change."""
        self._save_source_frequency()

    def _load_last_state(self) -> None:
        import json, os
        try:
            if os.path.exists(self._last_state_path):
                with open(self._last_state_path) as f:
                    data = json.load(f)
                if 'hackrf_lna_gain' in data:
                    self.main_window.hackrf_lna_gain = int(data['hackrf_lna_gain'])
                if 'hackrf_vga_gain' in data:
                    self.main_window.hackrf_vga_gain = int(data['hackrf_vga_gain'])
                for src, rec in data.items():
                    if isinstance(rec, dict) and 'centre' in rec and 'span' in rec:
                        self._source_memory[src] = {
                            'centre': float(rec['centre']),
                            'span':   float(rec['span']),
                        }
                logger.debug(f"Loaded last state for {list(self._source_memory.keys())}")
        except Exception as e:
            logger.warning(f"Could not load {self._last_state_path}: {e}")

    def _write_last_state(self) -> None:
        import json
        try:
            data = {
                'hackrf_lna_gain': self.main_window.hackrf_lna_gain,
                'hackrf_vga_gain': self.main_window.hackrf_vga_gain,
            }
            data.update(self._source_memory)
            with open(self._last_state_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not write {self._last_state_path}: {e}")

    def _set_frequency_clamped(self, new_src: str, centre: float, span: float) -> None:
        """Apply centre+span to mw.frequency, clamped to new_src hardware limits."""
        cc, cs = self._clamp_frequency_to_source_limits(centre, span, new_src)
        self.main_window.frequency_manager.set_frequency_range(cc - cs / 2, cc + cs / 2)

    def _apply_memory_or_default(self, new_src: str) -> None:
        """Restore per-source memory (or first-use default) for new_src."""
        display = self.SOURCE_DISPLAY_NAMES.get(new_src, new_src)
        mem = self._source_memory.get(new_src)
        if mem:
            self._set_frequency_clamped(new_src, mem['centre'], mem['span'])
            self._switch_message = f"{display}: restored to {format_hz(self.main_window.frequency.centre)}"
        else:
            dflt = self._SOURCE_DEFAULTS[new_src]
            self._set_frequency_clamped(new_src, dflt['centre'], dflt['span'])
            self._switch_message = None  # first use — no noise

    def _apply_frequency_for_source(self, new_src: str, from_src: Optional[str]) -> None:
        """Decide and apply the best frequency when switching to new_src.

        Rules (in priority order):
          1. Audio is always isolated — restore its own memory or default.
          2. Coming from audio to RF — restore RF source's own memory or default.
          3. RF → RF: if current centre is valid for new source, transfer it.
             - sweep → sweep:  keep current span (clamped to new source's max).
             - sweep → sample: transfer centre, restore sample source's remembered rate.
             - sample → sweep: transfer centre, restore sweep source's remembered span.
             - sample → sample: transfer centre, restore sample source's remembered rate.
          4. Current centre out of range — restore per-source memory or default.
        """
        mw = self.main_window
        to_cat   = self._source_category(new_src)
        from_cat = self._source_category(from_src) if from_src else None
        lim      = self._SOURCE_LIMITS.get(new_src)

        # Rule 1 & 2 — audio boundary: never transfer across it
        if to_cat == 'audio' or from_cat == 'audio' or from_src is None or lim is None:
            self._apply_memory_or_default(new_src)
            return

        current_centre = mw.frequency.centre
        current_span   = mw.frequency.span

        if lim['min'] <= current_centre <= lim['max']:
            # Rule 3 — centre is valid for new source; choose span intelligently
            if to_cat == 'sample':
                # Sample sources: span = sample_rate (hardware-discrete).
                # Always restore the sample source's own remembered rate.
                mem = self._source_memory.get(new_src)
                span = mem['span'] if mem else self._SOURCE_DEFAULTS[new_src]['span']
            elif from_cat == 'sample':
                # Sample → Sweep: sample span (e.g. 2 MHz) is meaningless for a sweep.
                # Restore sweep's own remembered span instead.
                mem = self._source_memory.get(new_src)
                span = mem['span'] if mem else self._SOURCE_DEFAULTS[new_src]['span']
            else:
                # Sweep → Sweep: keep current span, clamped to new hardware max.
                span = min(current_span, lim['max_span'])

            cc, cs = self._clamp_frequency_to_source_limits(current_centre, span, new_src)
            self.main_window.frequency_manager.set_frequency_range(cc - cs / 2, cc + cs / 2)

            display = self.SOURCE_DISPLAY_NAMES.get(new_src, new_src)
            if abs(cc - current_centre) > 1e3:
                self._switch_message = f"{display}: {format_hz(cc)} (adjusted to fit range)"
            else:
                self._switch_message = None  # clean transfer, no noise
        else:
            # Rule 4 — centre out of range: restore memory or default
            self._apply_memory_or_default(new_src)
            display = self.SOURCE_DISPLAY_NAMES.get(new_src, new_src)
            old_str = format_hz(current_centre)
            new_str = format_hz(self.main_window.frequency.centre)
            self._switch_message = f"{display}: {old_str} out of range — restored to {new_str}"

    def update_source_frequency(self) -> None:
        """Update the frequency settings for the current source."""
        if self.main_window.current_source is None:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("No current source, skipping frequency update")
            return

        try:
            if isinstance(self.main_window.current_source, SampleDataSource):
                self._update_sample_source_frequency()
            else:
                self._update_sweep_source_frequency()

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Source frequency updated successfully")
        except Exception as e:
            self.main_window.status_label.setText(f"Error updating source: {str(e)}")
            logger.error(f"Error updating source: {str(e)}")

    def _update_sample_source_frequency(self) -> None:
        """Update frequency for sample-based sources."""
        current_span = self.main_window.frequency.span
        span_changed = (not hasattr(self.main_window, 'last_span') or
                       abs(self.main_window.last_span - current_span) > 1e-6)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Span check: last={getattr(self.main_window, 'last_span', None)}, "
                         f"current={current_span}, changed={span_changed}")

        if span_changed:
            self._perform_full_frequency_update()
        else:
            self._update_centre_frequency_only()

    def _perform_full_frequency_update(self) -> None:
        """Perform full frequency update including sample rate change."""
        span = self.main_window.frequency.span
        centre = self.main_window.frequency.centre
        src = self.main_window.current_source

        # Clamp span to hardware sample-rate limits; update displayed range to match
        max_span = None
        if isinstance(src, RtlSamplesDataSource):
            max_span = SourceLimits.RTL_MAX_SAMPLE_RATE
        elif isinstance(src, HackrfSamplesDataSource):
            max_span = SourceLimits.HACKRF_MAX_SAMPLE_RATE

        if max_span is not None and span > max_span:
            span = max_span
            self.main_window.frequency.set_start_stop(
                centre - span / 2, centre + span / 2
            )
            self.main_window.frequency_manager.update_frequency_values()
            if max_span >= 1e6:
                lim_str = f"{max_span / 1e6:.2f} MHz"
            else:
                lim_str = f"{max_span / 1e3:.2f} kHz"
            self.main_window.status_label.setText(f"Span clamped to {lim_str} (hardware limit)")
            logger.warning(f"Span clamped to {span} Hz for {src.__class__.__name__}")

        src.update_frequency(span, centre)
        self.main_window.last_span = span

    def _update_centre_frequency_only(self) -> None:
        """Update only centre frequency without reinitialising device."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Centre frequency changed, updating without reinitialisation")

        if hasattr(self.main_window.current_source, 'update_centre_frequency'):
            self.main_window.current_source.update_centre_frequency(self.main_window.frequency.centre)

            # Update display widgets with new frequency bins
            from utils.frequency_helpers import calculate_frequency_bins
            # Use the source's actual sample_count (works for RTL, HackRF, and Microphone)
            num_bins = getattr(self.main_window.current_source, 'sample_count', UIConstants.DEFAULT_FFT_SIZE)
            freq_bins = calculate_frequency_bins(
                self.main_window.frequency.centre,
                self.main_window.current_source.sample_rate,
                num_bins
            )
            update_display_frequency_bins(self.main_window, freq_bins)
        else:
            logger.warning("update_centre_frequency not implemented, falling back to full update")
            self._perform_full_frequency_update()

    def _update_sweep_source_frequency(self) -> None:
        """Update frequency for sweep-based sources."""
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Updating sweep source frequency")
        self.main_window.current_source.start(self.main_window.frequency)    

    def _stop_current_source(self, new_source_type: str = None) -> None:
        """Stop and clean up the current source.

        Args:
            new_source_type: The source type we're switching to (for smart RTL handling).
        """
        if not self.main_window.current_source:
            return

        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Stopping source: {self.main_window.current_source.__class__.__name__}")

            # Smart RTL-SDR handling: keep device alive when switching between RTL samples and other sources
            # Only release when switching to RTL sweep (which needs exclusive hardware access)
            is_rtl_samples = isinstance(self.main_window.current_source, RtlSamplesDataSource)
            switching_to_rtl_sweep = new_source_type == SourceType.RTL_SWEEP.value

            if is_rtl_samples and not switching_to_rtl_sweep:
                # Pause RTL samples but keep device alive
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Pausing RTL samples source (keeping device alive)")
                self.main_window.current_source.pause()
                self.paused_rtl_source = self.main_window.current_source
            else:
                # Normal stop for all other sources
                self.main_window.current_source.stop()

                # If switching to RTL sweep, release any paused RTL samples
                if switching_to_rtl_sweep and self.paused_rtl_source:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug("Releasing paused RTL samples for RTL sweep")
                    self.paused_rtl_source = None

            # Verify source stopped
            if hasattr(self.main_window.current_source, 'is_running') and self.main_window.current_source.is_running:
                logger.warning("Source did not stop properly, retrying")
                self.main_window.current_source.stop()

            # Clean up thread if exists
            self._cleanup_source_thread()

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Source stopped successfully")
        except Exception as e:
            self.main_window.status_label.setText(f"Error stopping source: {str(e)}")
            logger.error(f"Error stopping source: {str(e)}")
        finally:
            self._reset_source_state()

    def _cleanup_source_thread(self) -> None:
        """Clean up source thread if it exists."""
        if not hasattr(self.main_window.current_source, 'thread'):
            return

        thread = self.main_window.current_source.thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=UIConstants.THREAD_JOIN_TIMEOUT)
            if thread.is_alive():
                logger.warning("Source thread did not terminate in time")
            self.main_window.current_source.thread = None

    def _reset_source_state(self) -> None:
        """Clear the source reference and delegate DSP/hold/tare reset to DisplayManager."""
        self.main_window.display_manager._reset_dsp_state()
        self.main_window.current_source = None

    def set_source(self, source: str) -> None:
        """Set the active data source.

        Args:
            source: Source identifier string (can be button ID or source type).
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Attempting to set source: {source}")

        self._switch_message = None  # Reset before each source switch

        try:
            # Map button ID to source type if needed
            actual_source = self.BUTTON_TO_SOURCE.get(source, source)

            if logger.isEnabledFor(logging.DEBUG):
                if source != actual_source:
                    logger.debug(f"Mapped button ID '{source}' to source type '{actual_source}'")

            # Validate source
            source_class = self.SOURCE_CLASSES.get(actual_source)
            if source_class is None:
                self.main_window.status_label.setText(f"Invalid source: {source}")
                logger.error(f"Invalid source: {source} (mapped to: {actual_source})")
                return

            # Check if the same source is being selected - if so, just continue without reinitialization
            if self.last_source_type == actual_source and self.main_window.current_source is not None:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Same source '{actual_source}' selected, continuing without reinitialization")
                self.main_window.status_label.setText(f"Input: {actual_source} (already active)")
                return

            from_source = self.last_source_type  # capture BEFORE update

            # Save the departing source's current frequency into memory
            self._save_source_frequency()

            # Stop current source (pass new source type for smart RTL handling)
            # _stop_current_source → _reset_source_state → _reset_dsp_state
            self._stop_current_source(actual_source)

            # Use the mapped source type for the rest of the method
            source = actual_source

            # Update last source type BEFORE applying frequency so memory saves go to new source
            self.last_source_type = source
            self._switch_message = None

            # Set the best frequency for the new source (transfer, restore from memory, or default)
            self._apply_frequency_for_source(source, from_source)

            # Check if we can resume a paused RTL samples source
            if source == SourceType.RTL_SAMPLES.value and self.paused_rtl_source is not None:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Resuming paused RTL samples source")
                self.main_window.current_source = self.paused_rtl_source
                self.paused_rtl_source = None
                self.main_window.current_source.resume()
                # Sync hardware with whatever frequency _apply_frequency_for_source set
                self.update_source_frequency()
                # Rebuild display bins using the resumed source's sample_count
                self.main_window.frequency_manager._update_display_bins()
            else:
                # Initialise source based on type — frequency already set above
                if source == SourceType.RTL_SWEEP.value:
                    self._initialise_rtl_sweep(source_class)
                elif source == SourceType.HACKRF_SWEEP.value:
                    self._initialise_hackrf_sweep(source_class)
                elif source == SourceType.HACKRF_SAMPLES.value:
                    self._initialise_hackrf_samples(source_class)
                elif source == SourceType.RTL_SAMPLES.value:
                    self._initialise_rtl_samples(source_class)
                elif source == SourceType.MICROPHONE_SAMPLES.value:
                    self._initialise_microphone_samples(source_class)

            # Enable UI controls and update display
            self._enable_source_controls()
            display_name = self.SOURCE_DISPLAY_NAMES.get(source, source)
            cal = getattr(self.main_window, 'calibration_manager', None)
            if cal and cal.is_calibrated(source):
                info     = cal.get_info(source)
                cal_freq = info.get('cal_freq_hz')
                ref_db   = info.get('reference_db')
                offset   = info.get('offset_db', 0.0)
                if cal_freq is not None:
                    freq_str = f" @ {format_hz(cal_freq)}"
                    pwr_str  = f" / {ref_db:.1f} dBm" if ref_db is not None else ""
                    badge = f" (Calibrated{freq_str}{pwr_str})"
                else:
                    badge = f" (Calibrated with {offset:+.1f} dB offset)"
            else:
                badge = ""
            self.main_window.output_source.setText(f"Input: {display_name}{badge}")
            self.main_window.status_label.setText(
                self._switch_message if self._switch_message else f"Input set: {source}"
            )
            # Only switch away from the logo; keep whatever display is currently active
            if self.main_window.current_stacked_index == DisplayMode.LOGO:
                self.main_window.display_manager.set_display(
                    DisplayMode.TWO_D,
                    UIConstants.BUTTON_ACTIVE_STYLE,
                    None
                )
            self.main_window.frequency_manager.update_frequency_values()

            # Keep current_source_id in sync so analysis mode (constellation etc.)
            # works regardless of whether the source was selected via menu or preset.
            source_to_button = {v: k for k, v in self.BUTTON_TO_SOURCE.items()}
            if source in source_to_button:
                self.main_window.current_source_id = source_to_button[source]

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Source set successfully: {source}")
        except Exception as e:
            self.main_window.output_source.setText("Input: None")
            self.main_window.status_label.setText(f"Error setting source: {str(e)}")
            self._reset_source_state()
            logger.error(f"Error setting source: {str(e)}")

    def _initialise_rtl_sweep(self, source_class: Type) -> None:
        """Initialise RTL sweep source. Frequency already set by _apply_frequency_for_source."""
        try:
            self.main_window.current_source = source_class(
                self.main_window.frequency.start,
                self.main_window.frequency.stop,
                bin_size=100000
            )
            self.main_window.current_source.start(self.main_window.frequency)
        except Exception as e:
            self._reset_source_state()
            self.main_window.status_label.setText(f"RTL Sweep start failed: {str(e)}")
            logger.error(f"RTL Sweep start failed: {str(e)}")
            raise

    def _initialise_hackrf_sweep(self, source_class: Type) -> None:
        """Initialise HackRF sweep source. Frequency already set by _apply_frequency_for_source."""
        try:
            mw = self.main_window
            src = source_class(mw.frequency.start, mw.frequency.stop, bin_size=30000)
            src.lna_gain = mw.hackrf_lna_gain
            src.vga_gain = mw.hackrf_vga_gain
            mw.current_source = src
            mw.current_source.start(mw.frequency)
        except Exception as e:
            self._reset_source_state()
            self.main_window.status_label.setText(f"HackRF Sweep start failed: {str(e)}")
            logger.error(f"HackRF Sweep start failed: {str(e)}")
            raise

    def _post_start_sample_source(self) -> None:
        """Common post-start steps for every sample source.

        Syncs last_span and pushes frequency bins to all display widgets so that
        switching displays after source init always shows the correct axis.
        """
        mw = self.main_window
        mw.last_span = mw.frequency.span
        num_bins = getattr(mw.current_source, 'sample_count', 1024) or 1024
        freq_bins = np.linspace(mw.frequency.start, mw.frequency.stop, num_bins)
        update_all_display_frequency_bins(mw, freq_bins)

    def _initialise_hackrf_samples(self, source_class: Type) -> None:
        """Initialise HackRF samples source. Frequency already set by _apply_frequency_for_source."""
        mw = self.main_window
        src = source_class(sample_rate=mw.frequency.span, centre_freq=mw.frequency.centre)
        src.lna_gain = mw.hackrf_lna_gain
        src.vga_gain = mw.hackrf_vga_gain
        mw.current_source = src
        try:
            mw.current_source.start(mw.frequency)
            self._post_start_sample_source()
        except Exception as e:
            self._reset_source_state()
            self.main_window.status_label.setText(f"HackRF Samples start failed: {str(e)}")
            logger.error(f"HackRF Samples start failed: {str(e)}")
            raise

    def _initialise_rtl_samples(self, source_class: Type) -> None:
        """Initialise RTL samples source. Frequency already set by _apply_frequency_for_source."""
        logger.debug(
            f"Initialising RtlSamplesDataSource with "
            f"span={self.main_window.frequency.span/1e6:.2f} MHz, "
            f"centre={self.main_window.frequency.centre/1e6:.2f} MHz"
        )
        self.main_window.current_source = source_class(
            sample_rate=self.main_window.frequency.span,
            centre_freq=self.main_window.frequency.centre
        )
        try:
            self.main_window.current_source.start(self.main_window.frequency)
            self._post_start_sample_source()
        except Exception as e:
            self._reset_source_state()
            self.main_window.status_label.setText(f"RTL Samples start failed: {str(e)}")
            logger.error(f"RTL Samples start failed: {str(e)}")
            raise

    def _initialise_microphone_samples(self, source_class: Type) -> None:
        """Initialise microphone samples source. Frequency already set by _apply_frequency_for_source."""
        # span = Nyquist = sample_rate / 2  →  sample_rate = span × 2
        # Clamp to the range the audio menu offers (8 kHz – 96 kHz) in case the
        # span was restored from a preset that belonged to a different source type.
        _AUDIO_MIN = 8_000
        _AUDIO_MAX = 96_000
        sample_rate = max(_AUDIO_MIN, min(_AUDIO_MAX, int(round(self.main_window.frequency.span * 2))))
        self.main_window.current_source = source_class(
            sample_rate=sample_rate,
            centre_freq=0
        )
        try:
            self.main_window.current_source.start(self.main_window.frequency)
            self._post_start_sample_source()
            logger.debug(f"Microphone started at {sample_rate} Hz sample rate")
        except Exception as e:
            self._reset_source_state()
            self.main_window.status_label.setText(f"Microphone start failed: {str(e)}")
            logger.error(f"Microphone start failed: {str(e)}")
            raise

    def _enable_source_controls(self) -> None:
        """Enable source control buttons in UI."""
        self.main_window.button_peak_search.setEnabled(True)
        self.main_window.button_max_hold.setEnabled(True)
        self.main_window.button_hold.setEnabled(True)

    def start_fft(self, source_id: str):
        if not source_id:
            logger.error("start_fft called with None source_id")
            self.main_window.status_label.setText("Cannot start FFT: No source selected")
            return
        source = self.BUTTON_TO_SOURCE.get(source_id)
        if not source:
            self.main_window.status_label.setText(f"Invalid source for FFT: {source_id}")
            logger.error(f"Invalid source for FFT: {source_id}")
            return
        self.main_window.current_source_id = source_id
        logger.debug(f"Starting FFT for source_id={source_id}, mapped to {source}")
        self.set_source(source)

    def set_fft_window(self, window_type: str):
        if not self.main_window.current_source or not isinstance(self.main_window.current_source, SampleDataSource):
            self.main_window.status_label.setText("No sample source running. Start FFT first.")
            logger.warning("No sample source running for FFT window")
            return
        try:
            self.main_window.current_source.set_window_type(window_type.lower())
            self.main_window.status_label.setText(f"{window_type} window selected")
            logger.debug(f"Set FFT window: {window_type}")
        except Exception as e:
            self.main_window.status_label.setText(f"Error setting FFT window: {str(e)}")
            logger.error(f"Error setting FFT window: {str(e)}")

    def set_fft_size(self, size: int):
        """Set the FFT/sample size for the current sample source.

        Handles both set_fft_size() (RTL, Microphone) and set_num_samples() (HackRF).
        Also updates the RBW display after changing the size.

        Args:
            size: The new FFT/sample size (must be power of 2).
        """
        if not self.main_window.current_source or not isinstance(self.main_window.current_source, SampleDataSource):
            self.main_window.status_label.setText("No sample source running. Start FFT first.")
            logger.warning("No sample source running for FFT sample size")
            return
        try:
            self.main_window.current_source.sample_count = size
            logger.debug(f"Set sample_count to {size} on {self.main_window.current_source.__class__.__name__}")

            # Update the frequency display (which includes RBW calculation)
            self.main_window.frequency_manager.update_frequency_values()

            # Calculate new RBW for status message
            sample_rate = getattr(self.main_window.current_source, 'sample_rate', 0)
            if sample_rate > 0:
                new_rbw = sample_rate / size
                if new_rbw >= 1e3:
                    rbw_str = f"{new_rbw/1e3:.2f} kHz"
                else:
                    rbw_str = f"{new_rbw:.2f} Hz"
                self.main_window.status_label.setText(f"FFT size: {size}, RBW: {rbw_str}")
            else:
                self.main_window.status_label.setText(f"FFT size set to {size}")

            logger.debug(f"Updated FFT size to {size}, RBW recalculated")
        except Exception as e:
            self.main_window.status_label.setText(f"Error setting FFT size: {str(e)}")
            logger.error(f"Error setting FFT size: {str(e)}")

    def _set_sample_rate(self, expected_class: Type, mode_label: str, sample_rate: int) -> None:
        """Shared logic for updating the sample rate on the active source.

        Args:
            expected_class: The class the source must be an instance of.
            mode_label: Human-readable source label for status messages.
            sample_rate: Requested sample rate in Hz.
        """
        if not self.main_window.current_source:
            self.main_window.status_label.setText("No source running")
            logger.warning("No source running for sample rate change")
            return

        if not isinstance(self.main_window.current_source, expected_class):
            self.main_window.status_label.setText(f"Sample rate only applies to {mode_label} mode")
            logger.warning(f"Attempted to set sample rate for non-{mode_label} source")
            return

        try:
            current_sample_rate = getattr(self.main_window.current_source, 'last_sample_rate', 0)
            if abs(sample_rate - current_sample_rate) < 100:
                logger.debug(f"Sample rate unchanged at {current_sample_rate} Hz, skipping update")
                self.main_window.status_label.setText("Sample rate unchanged")
                return

            self.main_window.current_source.update_frequency(sample_rate, self.main_window.frequency.centre)

            # Frequency bins change with sample rate — old hold data is now at wrong frequencies
            self.main_window.display_manager._clear_hold()

            actual_sample_rate = getattr(self.main_window.current_source, 'sample_rate', sample_rate)
            self.main_window.frequency.set_span(actual_sample_rate)
            self.main_window.frequency_manager.update_frequency_values()

            if actual_sample_rate >= 1e6:
                rate_str = f"{actual_sample_rate/1e6:.3g} MS/s"
            else:
                rate_str = f"{actual_sample_rate/1e3:.3g} kS/s"

            fft_size = getattr(self.main_window.current_source, 'sample_count', 1024) or 1024
            new_rbw = actual_sample_rate / fft_size
            rbw_str = f"{new_rbw/1e3:.2f} kHz" if new_rbw >= 1e3 else f"{new_rbw:.2f} Hz"

            self.main_window.status_label.setText(f"Sample rate: {rate_str}, RBW: {rbw_str}")
            logger.debug(f"{mode_label} sample rate set to {actual_sample_rate} Hz (requested {sample_rate} Hz), RBW={new_rbw:.2f} Hz")
        except Exception as e:
            self.main_window.status_label.setText(f"Error setting sample rate: {str(e)}")
            logger.error(f"Error setting {mode_label} sample rate: {str(e)}")

    def set_audio_sample_rate(self, sample_rate: int) -> None:
        """Set the sample rate for the microphone source and update the frequency range."""
        self._exit_zero_span_if_active()
        if not self.main_window.current_source or \
                not isinstance(self.main_window.current_source, MicrophoneSamplesDataSource):
            self.main_window.status_label.setText("Sample rate only applies to Microphone mode")
            return
        try:
            self.main_window.current_source.update_frequency(sample_rate, 0)
            nyquist = sample_rate / 2
            # Set last_span BEFORE set_frequency_range so _perform_full_frequency_update
            # is not triggered (it would pass nyquist as sample_rate, halving it again)
            self.main_window.last_span = nyquist
            self.main_window.frequency_manager.set_frequency_range(0, nyquist)
            if sample_rate >= 1000:
                rate_str = f"{sample_rate / 1e3:.3g} kHz"
            else:
                rate_str = f"{sample_rate} Hz"
            self.main_window.status_label.setText(f"Audio sample rate: {rate_str}  (0 – {rate_str})")
            logger.debug(f"Audio sample rate set to {sample_rate} Hz")
        except Exception as e:
            self.main_window.status_label.setText(f"Error setting audio sample rate: {e}")
            logger.error(f"Error setting audio sample rate: {e}")

    def set_sweep_bin_size(self, bin_size: int) -> None:
        """Restart the HackRF sweep source with a new bin size (= RBW).

        Stops the running sweep, recreates the source with the requested
        bin_size, and restarts it over the current frequency range.
        """
        src = self.main_window.current_source
        if not isinstance(src, HackRFSweepDataSource):
            self.main_window.status_label.setText("RBW only applies to HackRF Sweep mode")
            return
        try:
            mw = self.main_window
            src.stop()
            mw.display_manager._reset_dsp_state()
            new_src = HackRFSweepDataSource(mw.frequency.start, mw.frequency.stop, bin_size=bin_size)
            new_src.lna_gain = mw.hackrf_lna_gain
            new_src.vga_gain = mw.hackrf_vga_gain
            mw.current_source = new_src
            mw.current_source.start(mw.frequency)
            rbw_str = f"{bin_size // 1000} kHz" if bin_size >= 1000 else f"{bin_size} Hz"
            self.main_window.status_label.setText(f"HackRF Sweep RBW: {rbw_str}")
            self.main_window.frequency_manager.update_frequency_values()
            logger.debug(f"HackRF sweep restarted with bin_size={bin_size} Hz")
        except Exception as e:
            self.main_window.status_label.setText(f"Error setting RBW: {str(e)}")
            logger.error(f"Error setting sweep bin_size: {str(e)}")

    def _exit_zero_span_if_active(self) -> None:
        """Exit zero span mode before changing sample rate, if currently active."""
        if getattr(getattr(self.main_window, 'display_manager', None), 'zero_span_active', False):
            self.main_window.display_manager._exit_zero_span()

    def set_rtl_sample_rate(self, sample_rate: int):
        self._exit_zero_span_if_active()
        self._set_sample_rate(RtlSamplesDataSource, "RTL Samples", sample_rate)

    def set_hackrf_sample_rate(self, sample_rate: int):
        self._exit_zero_span_if_active()
        self._set_sample_rate(HackrfSamplesDataSource, "HackRF Samples", sample_rate)

    # ------------------------------------------------------------------
    # Preset contribution
    # ------------------------------------------------------------------

    def capture_preset(self) -> dict:
        mw = self.main_window
        source_type = None
        if mw.current_source:
            for st, cls in self.SOURCE_CLASSES.items():
                if isinstance(mw.current_source, cls):
                    source_type = st
                    break
        return {
            'source_type':  source_type,
            'fft_size':     getattr(mw.current_source, 'sample_count', None) if mw.current_source else None,
            'window_type':  getattr(mw.current_source, 'window_type',  None) if mw.current_source else None,
            'sweep_bin_size': getattr(mw.current_source, 'bin_size',   None) if mw.current_source else None,
        }

    def apply_preset(self, s: dict) -> None:
        mw = self.main_window
        source_type = s.get('source_type')
        if source_type:
            current_type = None
            if mw.current_source:
                for st, cls in self.SOURCE_CLASSES.items():
                    if isinstance(mw.current_source, cls):
                        current_type = st
                        break
            if current_type != source_type:
                try:
                    self.set_source(source_type)
                    if mw.current_source is None:
                        raise RuntimeError("source not started")
                except Exception:
                    display_name = self.SOURCE_DISPLAY_NAMES.get(source_type, source_type)
                    mw.status_label.setText(
                        f"Preset: {display_name} not available — settings applied without source"
                    )
                    logger.warning(f"Preset source '{source_type}' unavailable; continuing with display settings")
                    source_type = None

        fft_size = s.get('fft_size')
        if fft_size:
            self.set_fft_size(fft_size)
        window_type = s.get('window_type')
        if window_type:
            mw.set_window_type(window_type)
        sweep_bin_size = s.get('sweep_bin_size')
        if sweep_bin_size and source_type == 'hackrf_sweep':
            self.set_sweep_bin_size(int(sweep_bin_size))

    def close(self):
        if self.main_window.current_source and hasattr(self.main_window.current_source, 'stop'):
            self.main_window.current_source.stop()
            self._cleanup_source_thread()

        if self.paused_rtl_source is not None:
            logger.debug("Stopping paused RTL samples on application close")
            self.paused_rtl_source.stop()
            self.paused_rtl_source = None

