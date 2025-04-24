import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple
import json

@dataclass
class FrequencyInfo:
    start: float       # Hz
    stop: float        # Hz
    centre: float      # Hz
    span: float        # Hz
    bins: int          # Number of bins
    step: float        # Hz/bin
    units: str = "Hz"  # Display units

    def validate(self):
        """Validate the frequency information."""
        if self.start >= self.stop:
            raise ValueError(f"Start frequency ({self.start} Hz) must be less than stop frequency ({self.stop} Hz)")
        if self.bins <= 0:
            raise ValueError(f"Number of bins ({self.bins}) must be positive")
        expected_span = self.stop - self.start
        if abs(self.span - expected_span) > 1e-6:
            raise ValueError(f"Span ({self.span} Hz) does not match stop - start ({expected_span} Hz)")
        expected_centre = (self.start + self.stop) / 2
        if abs(self.centre - expected_centre) > 1e-6:
            raise ValueError(f"centre frequency ({self.centre} Hz) does not match (start + stop) / 2 ({expected_centre} Hz)")
        expected_step = self.span / (self.bins - 1) if self.bins > 1 else 0
        if abs(self.step - expected_step) > 1e-6:
            raise ValueError(f"Step ({self.step} Hz/bin) does not match span / (bins - 1) ({expected_step} Hz/bin)")

@dataclass 
class SpectrumData:
    frequency: FrequencyInfo
    live: np.ndarray   # dBm
    max: np.ndarray    # dBm
    min: Optional[np.ndarray] = None
    avg: Optional[np.ndarray] = None
    
    # Metadata
    source: str = ""
    sample_rate: float = 0
    gain: float = 0
    window: str = ""
    fft_size: int = 0
    resolution_bw: float = 0
    
    # Display hints
    y_range: Tuple[float, float] = (-100, 0)  # dBm
    color_map: str = "magma"
    peak_search: bool = False
    max_hold: bool = False
    
    @property
    def frequency_bins(self) -> np.ndarray:
        """Get the frequency bin centres."""
        return np.linspace(
            self.frequency.start, 
            self.frequency.stop, 
            self.frequency.bins
        )

    def validate(self):
        """Validate the spectrum data."""
        # Validate frequency info
        self.frequency.validate()
        
        # Validate data arrays
        expected_len = self.frequency.bins
        if len(self.live) != expected_len:
            raise ValueError(f"Live data length ({len(self.live)}) does not match number of bins ({expected_len})")
        if len(self.max) != expected_len:
            raise ValueError(f"Max data length ({len(self.max)}) does not match number of bins ({expected_len})")
        if self.min is not None and len(self.min) != expected_len:
            raise ValueError(f"Min data length ({len(self.min)}) does not match number of bins ({expected_len})")
        if self.avg is not None and len(self.avg) != expected_len:
            raise ValueError(f"Avg data length ({len(self.avg)}) does not match number of bins ({expected_len})")
        
        # Validate other fields
        if self.y_range[0] >= self.y_range[1]:
            raise ValueError(f"Y-range min ({self.y_range[0]}) must be less than max ({self.y_range[1]})")
        if self.sample_rate < 0:
            raise ValueError(f"Sample rate ({self.sample_rate}) must be non-negative")
        if self.gain < 0:
            raise ValueError(f"Gain ({self.gain}) must be non-negative")
        if self.fft_size < 0:
            raise ValueError(f"FFT size ({self.fft_size}) must be non-negative")
        if self.resolution_bw < 0:
            raise ValueError(f"Resolution bandwidth ({self.resolution_bw}) must be non-negative")

    def to_dict(self):
        """Convert to a dictionary for serialization."""
        return {
            "frequency": {
                "start": self.frequency.start,
                "stop": self.frequency.stop,
                "centre": self.frequency.centre,
                "span": self.frequency.span,
                "bins": self.frequency.bins,
                "step": self.frequency.step,
                "units": self.frequency.units
            },
            "live": self.live.tolist(),
            "max": self.max.tolist(),
            "min": self.min.tolist() if self.min is not None else None,
            "avg": self.avg.tolist() if self.avg is not None else None,
            "source": self.source,
            "sample_rate": self.sample_rate,
            "gain": self.gain,
            "window": self.window,
            "fft_size": self.fft_size,
            "resolution_bw": self.resolution_bw,
            "y_range": self.y_range,
            "color_map": self.color_map,
            "peak_search": self.peak_search,
            "max_hold": self.max_hold
        }

    @classmethod
    def from_dict(cls, data: dict):
        """Create a SpectrumData instance from a dictionary."""
        frequency = FrequencyInfo(
            start=data["frequency"]["start"],
            stop=data["frequency"]["stop"],
            centre=data["frequency"]["centre"],
            span=data["frequency"]["span"],
            bins=data["frequency"]["bins"],
            step=data["frequency"]["step"],
            units=data["frequency"]["units"]
        )
        return cls(
            frequency=frequency,
            live=np.array(data["live"]),
            max=np.array(data["max"]),
            min=np.array(data["min"]) if data["min"] is not None else None,
            avg=np.array(data["avg"]) if data["avg"] is not None else None,
            source=data["source"],
            sample_rate=data["sample_rate"],
            gain=data["gain"],
            window=data["window"],
            fft_size=data["fft_size"],
            resolution_bw=data["resolution_bw"],
            y_range=tuple(data["y_range"]),
            color_map=data["color_map"],
            peak_search=data["peak_search"],
            max_hold=data["max_hold"]
        )

    def to_json(self):
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str):
        """Deserialize from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
