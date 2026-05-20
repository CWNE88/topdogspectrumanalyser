"""Centralised user-data directory for all persistent settings.

All files that need to survive across runs (presets, calibration, source
memory) should call config_dir() to get the writable path.  This keeps
everything in one standard location that works correctly when the app is
run as an AppImage (where the app directory is read-only).
"""

from pathlib import Path


def config_dir() -> Path:
    """Return ~/.config/topdogspectrumanalyser/, creating it if necessary."""
    d = Path.home() / ".config" / "topdogspectrumanalyser"
    d.mkdir(parents=True, exist_ok=True)
    return d
