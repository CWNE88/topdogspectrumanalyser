"""Per-source-type calibration offset manager.

Stores a single dB scalar offset per source type.  Applied to raw power
values before tare/averaging so all downstream code sees calibrated levels.
Persisted to calibration.json alongside presets.json.
"""

import json
import os
import logging
from utils.config_paths import config_dir

CAL_FILE = str(config_dir() / "calibration.json")
logger   = logging.getLogger(__name__)


class CalibrationManager:
    def __init__(self) -> None:
        self._cal: dict = self._load()
        # Pending calibration workflow state — set by _cal_set_from_marker,
        # consumed by frequency_manager._handle_value_entry on keypad confirm.
        self.pending_measured_db: float | None = None
        self.pending_freq_hz:     float | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_offset(self, source_type: str) -> float:
        """Return the dB offset for a source type, or 0.0 if not calibrated."""
        return float(self._cal.get(source_type, {}).get('offset_db', 0.0))

    def is_calibrated(self, source_type: str) -> bool:
        return source_type in self._cal and self._cal[source_type].get('offset_db', 0.0) != 0.0

    def get_info(self, source_type: str) -> dict:
        return dict(self._cal.get(source_type, {}))

    def set_from_marker(self, source_type: str, measured_db: float,
                        reference_db: float, cal_freq_hz: float | None = None) -> float:
        """Compute and store offset from a measured and a reference value.

        offset = reference − measured  (positive means source reads too low)
        Returns the computed offset.
        """
        offset = reference_db - measured_db
        entry: dict = {
            'offset_db':    offset,
            'measured_db':  measured_db,
            'reference_db': reference_db,
        }
        if cal_freq_hz is not None:
            entry['cal_freq_hz'] = cal_freq_hz
        self._cal[source_type] = entry
        self._persist()
        logger.debug(f"Cal set for {source_type}: {offset:+.1f} dB "
                     f"(measured={measured_db:.1f}, ref={reference_db:.1f})")
        return offset

    def set_offset(self, source_type: str, offset_db: float) -> None:
        """Set offset directly (user-supplied dB value)."""
        entry = dict(self._cal.get(source_type, {}))
        entry['offset_db'] = offset_db
        self._cal[source_type] = entry
        self._persist()
        logger.debug(f"Cal direct offset for {source_type}: {offset_db:+.1f} dB")

    def clear(self, source_type: str) -> None:
        if source_type in self._cal:
            del self._cal[source_type]
            self._persist()
            logger.debug(f"Cal cleared for {source_type}")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> dict:
        if os.path.exists(CAL_FILE):
            try:
                with open(CAL_FILE) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load calibration: {e}")
        return {}

    def _persist(self) -> None:
        try:
            with open(CAL_FILE, 'w') as f:
                json.dump(self._cal, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save calibration: {e}")
