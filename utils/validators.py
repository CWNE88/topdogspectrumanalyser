import logging
from typing import Dict
from utils.constants import FFTSize

logger = logging.getLogger(__name__)


def clamp_frequency(hz: float, min_hz: float, max_hz: float) -> float:
    if hz < min_hz:
        logger.warning(f"Frequency {hz:.0f} Hz below minimum {min_hz:.0f} Hz, clamped")
        return min_hz
    if hz > max_hz:
        logger.warning(f"Frequency {hz:.0f} Hz above maximum {max_hz:.0f} Hz, clamped")
        return max_hz
    return hz


def clamp_ref_level(dbm: float) -> float:
    lo, hi = -200.0, 100.0
    if dbm < lo or dbm > hi:
        clamped = max(lo, min(hi, dbm))
        logger.warning(f"Ref level {dbm} dBm out of range [{lo}, {hi}], clamped to {clamped}")
        return clamped
    return dbm


def clamp_range_db(db: float) -> float:
    lo, hi = 10.0, 200.0
    if db < lo or db > hi:
        clamped = max(lo, min(hi, db))
        logger.warning(f"Range {db} dB out of [{lo}, {hi}], clamped to {clamped}")
        return clamped
    return db


def clamp_centre_span(centre: float, span: float, source_type: str,
                      source_limits: Dict[str, Dict]) -> tuple[float, float]:
    """Clamp a centre/span pair to the hardware limits for the given source type.

    This is the single authoritative implementation of frequency clamping.
    Span is capped first, then the window is slid to fit within [min, max].

    Args:
        centre: Desired centre frequency in Hz.
        span: Desired span in Hz.
        source_type: Source type string (snake_case, e.g. 'rtl_samples').
        source_limits: Mapping from source type → {'min', 'max', 'max_span'}.

    Returns:
        (clamped_centre, clamped_span) in Hz.
    """
    lim = source_limits.get(source_type)
    if lim is None:
        return centre, span

    min_freq  = lim['min']
    max_freq  = lim['max']
    max_span  = lim['max_span']

    clamped_span = min(span, max_span)
    half         = clamped_span / 2

    if centre < min_freq:
        clamped_centre = min_freq + half
    elif centre > max_freq:
        clamped_centre = max_freq - half
    elif centre - half < min_freq:
        clamped_centre = min_freq + half
    elif centre + half > max_freq:
        clamped_centre = max_freq - half
    else:
        clamped_centre = centre

    return clamped_centre, clamped_span


def validate_fft_size(n: int) -> int:
    if FFTSize.is_valid(n):
        return n
    valid = sorted(s.value for s in FFTSize)
    best = min(valid, key=lambda x: abs(x - n))
    logger.warning(f"FFT size {n} not valid, using nearest {best}")
    return best
