"""TareState dataclass — shared between DisplayManager and DataProcessor."""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class TareState:
    """Mutable tare-collection state shared between DisplayManager and DataProcessor."""
    collecting: bool = False
    buffer: Optional[np.ndarray] = None
    count: int = 0
