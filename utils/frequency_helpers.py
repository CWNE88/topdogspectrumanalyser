"""Helper functions for frequency calculations."""

import numpy as np
import logging


def calculate_frequency_bins(centre_freq: float, sample_rate: float, num_bins: int) -> np.ndarray:
    """Calculate frequency bins for a given centre frequency and sample rate.

    Args:
        centre_freq: Centre frequency in Hz.
        sample_rate: Sample rate in Hz.
        num_bins: Number of frequency bins.

    Returns:
        Array of frequency bins in Hz.
    """
    return np.linspace(
        centre_freq - sample_rate / 2,
        centre_freq + sample_rate / 2,
        num_bins
    )


def calculate_frequency_bins_from_range(start_freq: float, stop_freq: float, num_bins: int) -> np.ndarray:
    """Calculate frequency bins for a given frequency range.

    Args:
        start_freq: Start frequency in Hz.
        stop_freq: Stop frequency in Hz.
        num_bins: Number of frequency bins.

    Returns:
        Array of frequency bins in Hz.
    """
    return np.linspace(start_freq, stop_freq, num_bins)


def update_display_frequency_bins(main_window, freq_bins: np.ndarray) -> None:
    """Update frequency bins for the current display widget.

    Args:
        main_window: MainWindow instance.
        freq_bins: Frequency bins array.
    """
    display_widgets = {
        0: main_window.two_d_widget,
        1: main_window.three_d_widget,
        2: main_window.waterfall_widget,
        3: main_window.surface_widget
    }

    widget = display_widgets.get(main_window.current_stacked_index)
    if widget and hasattr(widget, 'update_frequency_bins'):
        widget.update_frequency_bins(freq_bins)
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug(f"Updated frequency bins for display widget {main_window.current_stacked_index}")


def update_all_display_frequency_bins(main_window, freq_bins: np.ndarray) -> None:
    """Update frequency bins for ALL display widgets (used when switching sources).

    Args:
        main_window: MainWindow instance.
        freq_bins: Frequency bins array.
    """
    all_widgets = [
        main_window.two_d_widget,
        main_window.three_d_widget,
        main_window.waterfall_widget,
        main_window.surface_widget,
    ]
    for widget in all_widgets:
        if hasattr(widget, 'update_frequency_bins'):
            widget.update_frequency_bins(freq_bins)
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        logging.debug("Updated frequency bins for all display widgets")


def format_hz(hz: float, precision: int = 4) -> str:
    """Format a frequency in Hz as a human-readable string with unit (GHz/MHz/kHz/Hz).

    Args:
        hz: Frequency in Hz. May be a delta (negative values are formatted with sign).
        precision: Significant figures for the numeric part (default 4).

    Returns:
        e.g. '98.0000 MHz', '1.4204 GHz', '440.0 Hz'.
    """
    a = abs(hz)
    if a >= 1e9:
        return f"{hz / 1e9:.{precision}g} GHz"
    if a >= 1e6:
        return f"{hz / 1e6:.{precision}g} MHz"
    if a >= 1e3:
        return f"{hz / 1e3:.{precision}g} kHz"
    return f"{hz:.1f} Hz"


def format_frequency(freq: float, is_microphone: bool = False) -> tuple[str, str]:
    """Format frequency value with appropriate unit.

    Args:
        freq: Frequency value in Hz.
        is_microphone: Whether this is for microphone/audio source.

    Returns:
        Tuple of (formatted_value, unit).
    """
    if is_microphone:
        if abs(freq) < 1000:
            return f"{freq:.1f}", "Hz"
        return f"{freq / 1e3:.3f}", "kHz"
    else:
        return f"{freq / 1e6:.2f}", "MHz"
