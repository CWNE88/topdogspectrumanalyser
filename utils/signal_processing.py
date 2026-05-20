import numpy as np
from typing import Optional


class TraceAverager:
    """Averages successive power spectra in the linear domain.

    Operates on linear power values (|FFT|² or PSD) so that averaging is
    physically correct — identical to the VBW filter on a real analyser.
    The dB conversion is applied by the caller after process() returns.
    """

    def __init__(self):
        self._mode: str = "off"
        self._n: int = 1
        self._buffer: Optional[np.ndarray] = None
        self._count: int = 0

    def set_mode(self, mode: str, n: int) -> None:
        """Set averaging mode and count, resetting the buffer.

        Args:
            mode: "off", "exp" (exponential IIR), or "lin" (running mean).
            n: Decay constant for exp (alpha = 1/n), or frame cap for lin.
        """
        self._mode = mode
        self._n = max(1, n)
        self.reset()

    def reset(self) -> None:
        """Clear the buffer — call whenever FFT size or frequency range changes."""
        self._buffer = None
        self._count = 0

    def process(self, linear_power: np.ndarray) -> np.ndarray:
        """Average a linear-domain power frame and return the averaged result.

        Args:
            linear_power: |FFT|² or PSD values (linear, not dB).

        Returns:
            Averaged power array in the same linear domain.
        """
        if self._mode == "off" or self._n <= 1:
            return linear_power

        if self._buffer is None or self._buffer.shape != linear_power.shape:
            self._buffer = linear_power.astype(np.float64).copy()
            self._count = 1
            return self._buffer

        if self._mode == "exp":
            alpha = 1.0 / self._n
            self._buffer *= (1.0 - alpha)
            self._buffer += alpha * linear_power
        elif self._mode == "lin":
            if self._count < self._n:
                self._count += 1
            self._buffer += (linear_power - self._buffer) / self._count

        return self._buffer

    @property
    def is_active(self) -> bool:
        return self._mode != "off" and self._n > 1

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def n(self) -> int:
        return self._n
