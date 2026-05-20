import json
import os
import logging
from utils.config_paths import config_dir

logger = logging.getLogger(__name__)

PRESET_FILE = str(config_dir() / "presets.json")
NUM_SLOTS = 8


class PresetManager:
    """Stores and recalls full instrument state across 8 named slots."""

    def __init__(self, main_window):
        self.main_window = main_window
        self._presets: dict = self._load()
        self._pending_op: str | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_pending_op(self, op: str) -> None:
        self._pending_op = op

    def execute_slot(self, slot: int) -> None:
        if self._pending_op == 'recall':
            self._recall(slot)
        elif self._pending_op == 'save':
            self._save(slot)
        elif self._pending_op == 'name':
            self._rename(slot)
        elif self._pending_op == 'delete':
            self._delete(slot)

    def slot_label(self, slot: int) -> str:
        """Return button label for a slot — name if saved, 'Empty' if not."""
        entry = self._presets.get(str(slot))
        if entry:
            return entry.get('name', f"Preset {slot}")
        return f"Slot {slot}\nEmpty"

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    def _save(self, slot: int) -> None:
        key = str(slot)
        name = self._presets.get(key, {}).get('name', f"Preset {slot}")
        self._presets[key] = {'name': name, 'settings': self._capture()}
        self._persist()
        self.main_window.status_label.setText(f"Saved to: {name}")
        logger.debug(f"Preset saved to slot {slot}: {name}")

    def _recall(self, slot: int) -> None:
        entry = self._presets.get(str(slot))
        if not entry:
            self.main_window.status_label.setText(f"Slot {slot} is empty")
            return
        self._apply(entry['settings'])
        self.main_window.status_label.setText(f"Recalled: {entry['name']}")
        logger.debug(f"Preset recalled from slot {slot}: {entry['name']}")

    def _rename(self, slot: int) -> None:
        mw = self.main_window
        mw.preset_name_slot = slot
        mw.preset_name_text = self._presets.get(str(slot), {}).get('name', f"Preset {slot}")
        mw.input_value.setText(mw.preset_name_text)
        mw.frequency_manager.change_entry_mode('preset_name')

    def confirm_name(self, slot: int, name: str) -> None:
        """Called when the user confirms the preset name via Enter or Hz."""
        mw = self.main_window
        name = name.strip()
        if not name:
            mw.status_label.setText("Name cancelled")
            mw.frequency_manager.change_entry_mode('centre')
            mw.input_value.setText("")
            return
        key = str(slot)
        if key not in self._presets:
            self._presets[key] = {'name': name, 'settings': {}}
        else:
            self._presets[key]['name'] = name
        self._persist()
        mw.input_value.setText("")
        mw.preset_name_text = ""
        mw.frequency_manager.change_entry_mode('centre')
        mw.status_label.setText(f"Slot {slot} named: {name}")
        logger.debug(f"Preset slot {slot} renamed to: {name}")

    def _delete(self, slot: int) -> None:
        key = str(slot)
        if key not in self._presets:
            self.main_window.status_label.setText(f"Slot {slot} already empty")
            return
        name = self._presets.pop(key).get('name', f"Preset {slot}")
        self._persist()
        self.main_window.status_label.setText(f"Deleted: {name}")
        logger.debug(f"Preset slot {slot} deleted: {name}")

    # ------------------------------------------------------------------
    # Capture / apply — coordinated via manager contributions
    # ------------------------------------------------------------------

    # Order is significant for apply_preset:
    #   1. source_manager   — must run first; sets mw.current_source which
    #                         display_manager.apply_preset accesses for set_psd_mode
    #   2. frequency_manager — sets freq range after source is known
    #   3. display_manager   — restores visual state; may read mw.current_source
    #   4. marker_manager    — repositions markers after frequency range is set
    _CONTRIBUTOR_ATTRS = (
        'source_manager',
        'frequency_manager',
        'display_manager',
        'marker_manager',
    )

    def _capture(self) -> dict:
        """Collect state from each manager and merge into a single dict."""
        result = {}
        for attr in self._CONTRIBUTOR_ATTRS:
            mgr = getattr(self.main_window, attr, None)
            if mgr and hasattr(mgr, 'capture_preset'):
                result.update(mgr.capture_preset())
        return result

    def _apply(self, s: dict) -> None:
        """Distribute stored state to each manager in dependency order."""
        for attr in self._CONTRIBUTOR_ATTRS:
            mgr = getattr(self.main_window, attr, None)
            if mgr and hasattr(mgr, 'apply_preset'):
                mgr.apply_preset(s)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> dict:
        if os.path.exists(PRESET_FILE):
            try:
                with open(PRESET_FILE) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load presets: {e}")
        return {}

    def _persist(self) -> None:
        try:
            with open(PRESET_FILE, 'w') as f:
                json.dump(self._presets, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save presets: {e}")
