# Frequency Management System

## Overview

The spectrum analyzer manages frequency settings using four interdependent parameters:
- **Start Frequency**: The lowest frequency in the range
- **Stop Frequency**: The highest frequency in the range
- **Centre Frequency**: The midpoint between start and stop
- **Span**: The width of the frequency range (stop - start)

These parameters are automatically synchronized - when you change any one of them, the others update according to well-defined rules.

## Frequency Relationships

The four parameters maintain these mathematical relationships:

```
centre = (start + stop) / 2
span = stop - start
start = centre - span / 2
stop = centre + span / 2
```

## Parameter Update Rules

### Changing Centre Frequency
**Preserves:** Span
**Updates:** Start and Stop

When you change the centre frequency, the span stays constant and the start/stop frequencies shift to maintain the same span around the new centre.

**Example:**
```
Initial:  start=100 MHz, stop=200 MHz, centre=150 MHz, span=100 MHz
Set centre to 300 MHz:
Result:   start=250 MHz, stop=350 MHz, centre=300 MHz, span=100 MHz
```

**Use case:** Tuning to a different frequency band while keeping the same bandwidth.

### Changing Span
**Preserves:** Centre
**Updates:** Start and Stop

When you change the span, the centre frequency stays constant and the start/stop frequencies adjust to achieve the new span around the same centre.

**Example:**
```
Initial:  start=100 MHz, stop=200 MHz, centre=150 MHz, span=100 MHz
Set span to 200 MHz:
Result:   start=50 MHz,  stop=250 MHz, centre=150 MHz, span=200 MHz
```

**Use case:** Zooming in/out on a frequency band while staying centred on the same point.

### Changing Start Frequency
**Preserves:** Stop
**Updates:** Centre and Span

When you change the start frequency, the stop frequency stays constant and the centre/span adjust based on the new range.

**Example:**
```
Initial:  start=100 MHz, stop=200 MHz, centre=150 MHz, span=100 MHz
Set start to 150 MHz:
Result:   start=150 MHz, stop=200 MHz, centre=175 MHz, span=50 MHz
```

**Use case:** Adjusting the lower bound of a frequency sweep.

### Changing Stop Frequency
**Preserves:** Start
**Updates:** Centre and Span

When you change the stop frequency, the start frequency stays constant and the centre/span adjust based on the new range.

**Example:**
```
Initial:  start=100 MHz, stop=200 MHz, centre=150 MHz, span=100 MHz
Set stop to 300 MHz:
Result:   start=100 MHz, stop=300 MHz, centre=200 MHz, span=200 MHz
```

**Use case:** Adjusting the upper bound of a frequency sweep.

## Backend Implementation

### Sweep Sources (HackRF Sweep, RTL Sweep)
Sweep sources operate by scanning across a frequency range and are configured using:
- **Start frequency** (lower bound)
- **Stop frequency** (upper bound)

The backend uses `start` and `stop` directly. The `centre` and `span` are computed for display purposes.

### Sample Sources (HackRF Samples, RTL Samples, Microphone)
Sample sources acquire data at a fixed centre frequency with a certain bandwidth and are configured using:
- **Centre frequency** (tuning frequency)
- **Sample rate** (determines span/bandwidth)

The backend uses `centre` directly. The `span` is determined by the sample rate. The `start` and `stop` are computed as:
```
start = centre - sample_rate / 2
stop = centre + sample_rate / 2
```

**Note:** In the current implementation, span and sample rate are synchronized. Future versions may allow independent sample rate selection.

## Validation

The `FrequencyRange` class validates all frequency changes to prevent invalid states:

1. **Stop must be greater than start**: `stop > start`
2. **Frequencies must be non-negative**: `start >= 0`, `stop >= 0`
3. **Span must be positive**: `span > 0`
4. **No negative frequencies**: Operations that would result in negative frequencies are rejected

Invalid operations raise `ValueError` with a descriptive error message.

## GUI Display

All frequency parameters are always displayed on the GUI:
- **Start Frequency**: Lower bound of the frequency range
- **Stop Frequency**: Upper bound of the frequency range
- **Centre Frequency**: Midpoint of the frequency range
- **Span**: Width of the frequency range
- **Resolution Bandwidth (RBW)**: Frequency resolution of each measurement bin
- **Sample Rate**: Sample rate (for sample-mode sources only)

The display automatically updates when any parameter changes, showing the synchronized values.

Units are shown as:
- **RF sources** (HackRF, RTL-SDR): MHz for frequency parameters
- **Audio sources** (Microphone): kHz for frequency parameters
- **RBW**: Automatically formatted (Hz, kHz, or MHz based on magnitude)

### Resolution Bandwidth (RBW)

The **Resolution Bandwidth (RBW)** represents the frequency resolution of the spectrum analyzer - essentially how "wide" each frequency bin is. A smaller RBW means better frequency resolution but slower updates.

**For Sweep Sources:**
```
RBW = bin_size
```
- HackRF Sweep: Typically 30 kHz
- RTL Sweep: Typically 10 kHz

**For Sample Sources:**
```
RBW = sample_rate / fft_size
```
- HackRF Samples (20 MHz, 1024 FFT): RBW = 19.53 kHz
- RTL Samples (2 MHz, 1024 FFT): RBW = 1.95 kHz
- Microphone (44.1 kHz, 1024 FFT): RBW = 43.07 Hz

**Key Insights:**
- Smaller FFT size → Larger RBW → Less frequency resolution, faster updates
- Larger FFT size → Smaller RBW → Better frequency resolution, slower updates
- Higher sample rate → Larger RBW (for same FFT size)
- RBW determines the minimum frequency spacing you can resolve between two signals

**Example:** With an RBW of 10 kHz, two signals separated by less than 10 kHz will blend together and appear as a single peak.

### Changing FFT Size (Sample Sources Only)

For sample sources (HackRF Samples, RTL Samples, Microphone), you can change the FFT size to adjust the RBW:

**Menu Path:** Input → [Source] → FFT → Sample Size → [512/1024/2048/4096]

**Available FFT Sizes:**
- 512 samples
- 1024 samples (default)
- 2048 samples
- 4096 samples

**Implementation Note:** Different sample sources use different internal attributes:
- HackRF Samples uses `num_samples` attribute and `set_num_samples()` method
- RTL Samples uses `fft_size` attribute and `set_fft_size()` method
- Microphone Samples uses `fft_size` attribute and `set_fft_size()` method

The system automatically detects which method to call based on the source type and class name.

**Effect of Changing FFT Size:**

When you increase the FFT size:
- ✓ **Better frequency resolution** (smaller RBW)
- ✓ Can distinguish closer signals
- ✗ Slower processing/updates
- ✗ More computation required

When you decrease the FFT size:
- ✓ **Faster processing/updates**
- ✓ Less computation required
- ✗ Worse frequency resolution (larger RBW)
- ✗ Signals blend together more

**Example RBW Values:**

| FFT Size | HackRF (20 MHz) | RTL (2 MHz) | Microphone (44.1 kHz) |
|----------|-----------------|-------------|----------------------|
| 512      | 39.06 kHz      | 3.91 kHz   | 86.13 Hz            |
| 1024     | 19.53 kHz      | 1.95 kHz   | 43.07 Hz            |
| 2048     | 9.77 kHz       | 0.98 kHz   | 21.53 Hz            |
| 4096     | 4.88 kHz       | 0.49 kHz   | 10.77 Hz            |

**Note:** Sweep sources (HackRF Sweep, RTL Sweep) do not support changing FFT size. Their RBW is determined by the bin size parameter.

## Implementation Details

### Core Classes

**`FrequencyRange`** ([utils/frequency_selector.py](utils/frequency_selector.py))
- Manages the four interdependent frequency parameters
- Provides methods: `set_start()`, `set_stop()`, `set_centre()`, `set_span()`, `set_start_stop()`
- Enforces validation rules
- Automatically maintains consistency

**`FrequencyManager`** ([core/frequency_manager.py](core/frequency_manager.py))
- Handles user input for frequency changes
- Updates GUI displays
- Coordinates with data sources
- Applies hardware-specific limits

**`SourceManager`** ([core/source_manager.py](core/source_manager.py))
- Manages data source initialization
- Applies frequency clamping for hardware limits
- Preserves frequency settings when switching between RF sources
- Handles source-specific frequency updates

### Hardware Limits

Different hardware has different frequency and span limits, which vary depending on whether you're using **sweep mode** or **sample mode**:

### Sweep Mode (HackRF Sweep, RTL Sweep)
In sweep mode, the hardware scans across a frequency range. The span is only limited by the hardware's total frequency range.

**HackRF Sweep:**
- Frequency range: 1 MHz - 6 GHz
- **Max span: ~6 GHz** (entire frequency range)
- Example: Centre at 2.45 GHz with 1 GHz span (1.95 GHz to 2.95 GHz) ✓

**RTL Sweep:**
- Frequency range: 24 MHz - 1766 MHz
- **Max span: ~1.74 GHz** (entire frequency range)
- Example: Centre at 900 MHz with 500 MHz span (650 MHz to 1150 MHz) ✓

### Sample Mode (HackRF Samples, RTL Samples, Microphone)
In sample mode, the hardware captures data at a fixed centre frequency. The span is limited by the maximum sample rate.

**HackRF Samples:**
- Frequency range: 1 MHz - 6 GHz
- **Max span: 20 MHz** (limited by max sample rate)
- Example: Centre at 2.45 GHz with 1 GHz span ✗ (rejected, exceeds 20 MHz limit)
- Example: Centre at 2.45 GHz with 20 MHz span ✓

**RTL Samples:**
- Frequency range: 24 MHz - 1766 MHz
- **Max span: 2.4 MHz** (limited by max sample rate)
- Example: Centre at 100 MHz with 2 MHz span ✓
- Example: Centre at 100 MHz with 10 MHz span ✗ (rejected, exceeds 2.4 MHz limit)

**Microphone:**
- Frequency range: 0 Hz - 22.05 kHz (at 44.1 kHz sample rate)
- **Max span: 44.1 kHz** (limited by sample rate)

### Key Difference: Sweep vs Sample Mode

**Sweep Mode:**
- Span can be **very large** (up to the entire hardware range)
- Hardware physically tunes across frequencies over time
- Slower updates but wider coverage
- Ideal for: Finding signals across a wide range, spectrum monitoring

**Sample Mode:**
- Span is **limited by sample rate** (much smaller)
- Hardware captures a snapshot at a fixed frequency
- Faster updates but narrower coverage
- Ideal for: Analyzing specific signals in detail, real-time monitoring

When you change frequency parameters, the `SourceManager` and `FrequencyManager` automatically validate and clamp values to stay within the appropriate limits for your current mode.

## User Controls

### Direct Entry
Use the keypad to enter specific values:
1. Press a frequency button (Start, Stop, Centre, or Span)
2. Enter the value using the keypad
3. The other parameters automatically update

### Quick Controls
- **Centre ÷ 2**: Halves the centre frequency, preserving span
- **Centre × 2**: Doubles the centre frequency, preserving span

### Mouse/Touch
- Click frequency display labels to enter new values
- Use frequency selector controls in the menu

## Example Workflow

**Scenario:** Find WiFi signals around 2.4 GHz with HackRF

1. Select HackRF Samples source
2. Set centre to 2450 MHz (2.45 GHz - middle of 2.4 GHz band)
3. Set span to 100 MHz (covers 2.4-2.5 GHz)
4. Observe the display showing:
   - Start: 2400 MHz
   - Stop: 2500 MHz
   - Centre: 2450 MHz
   - Span: 100 MHz

5. To zoom in on a specific channel:
   - Adjust centre to the channel frequency (e.g., 2437 MHz for channel 6)
   - Reduce span to 20 MHz for more detail
   - Display updates:
     - Start: 2427 MHz
     - Stop: 2447 MHz
     - Centre: 2437 MHz
     - Span: 20 MHz

## Testing

Run the test script to verify frequency relationships:

```bash
python3 test_frequency_range.py
```

This validates all parameter interactions and edge cases.
