# RTL Sample Rate Selection Feature

## Overview

When in RTL Samples mode, the Span button now dynamically changes to show "Sample Rate" with a submenu of RTL-SDR supported sample rates. This allows users to quickly change the sample rate without manually entering span values.

## User Experience

### When NOT in RTL Samples Mode
- Press **Span** button → Shows soft button: "Span"
- Press "Span" soft button → Enters span entry mode (keypad input)

### When IN RTL Samples Mode
- Press **Span** button → Shows soft button: "Sample\nRate"
- Press "Sample\nRate" soft button → Shows sample rate submenu (hardware-tested rates):
  - 250 kS/s
  - 1.024 MS/s
  - 1.44 MS/s
  - 1.8 MS/s
  - 2.0 MS/s
  - **2.048 MS/s** (default)
  - 2.4 MS/s

### When Sample Rate is Selected
- Checks if sample rate actually changed (100 Hz tolerance, avoids unnecessary restarts)
- If unchanged: Shows "Sample rate unchanged" and exits
- If changed:
  - Updates RTL-SDR sample rate (requires brief hardware reinitialization)
  - **Reads back ACTUAL sample rate from hardware** (may differ slightly from requested)
  - Updates frequency span to match actual sample rate
  - Updates Resolution Bandwidth (RBW) using actual sample rate
  - Shows status: "Sample rate: X.XXXXXX MS/s, RBW: Y kHz" (actual values)

## Default Sample Rate

The default sample rate for RTL Samples is **2.048 MS/s** (2,048,000 Hz):
- Centre frequency: 98 MHz
- Span: 2.048 MHz
- Frequency range: 96.976 MHz - 99.024 MHz

## Technical Implementation

### Files Modified

#### 1. [menu/menu_manager.py](menu/menu_manager.py)
**Changes:**
- Modified `_create_span_menu()` to dynamically check current source
- Added `_create_rtl_sample_rate_menu()` with 8 sample rate options
- Modified `select_menu()` to regenerate span menu each time it's opened
- Added "Sample\nRate" menu to menus dictionary

**Key Code:**
```python
def _create_span_menu(self) -> List[MenuItem]:
    # Check if we're in RTL Samples mode
    if hasattr(self.parent, 'current_source') and self.parent.current_source:
        source_class_name = self.parent.current_source.__class__.__name__
        if source_class_name == "RtlSamplesDataSource":
            # For RTL Samples, show Sample Rate submenu instead of Span
            return [
                MenuItem("btnSampleRate", "Sample\nRate", sub_menu=self._create_rtl_sample_rate_menu()),
            ]

    # Default: show regular Span button
    return [
        MenuItem("btnSpan", "Span"),
    ]
```

#### 2. [utils/constants.py](utils/constants.py)
**Changes:**
- Added 9 new MenuButtonId constants for sample rate buttons
- Changed RTL_DEFAULT_START and RTL_DEFAULT_STOP to use 2.048 MS/s span

**New Constants:**
```python
SAMPLE_RATE = "btnSampleRate"
SAMPLE_RATE_250K = "btnSampleRate250k"
SAMPLE_RATE_500K = "btnSampleRate500k"
SAMPLE_RATE_1024K = "btnSampleRate1024k"
SAMPLE_RATE_1400K = "btnSampleRate1400k"
SAMPLE_RATE_1800K = "btnSampleRate1800k"
SAMPLE_RATE_2000K = "btnSampleRate2000k"
SAMPLE_RATE_2048K = "btnSampleRate2048k"
SAMPLE_RATE_2400K = "btnSampleRate2400k"
```

#### 3. [core/source_manager.py](core/source_manager.py)
**Changes:**
- Added `set_rtl_sample_rate()` method (lines 572-619)

**Method Functionality:**
```python
def set_rtl_sample_rate(self, sample_rate: int):
    """Set the sample rate for RTL-SDR samples source.

    - Validates current source is RTL Samples
    - Updates frequency span to match sample rate
    - Calls RTL source's update_frequency()
    - Updates frequency display and RBW
    - Shows formatted status message
    """
```

#### 4. [datasources/rtl_samples.py](datasources/rtl_samples.py)
**Changes:**
- Modified `update_sample_rate()` to change sample rate without reinitializing device
- Modified `update_frequency()` to use `update_sample_rate()` instead of stop/start cycle
- Both methods now read back actual hardware sample rate after setting

**Key Implementation:**
```python
def update_sample_rate(self, sample_rate: float):
    """Update the sample rate without restarting the device"""
    sample_rate = int(sample_rate)
    if sample_rate == self.last_sample_rate:
        logging.debug("Sample rate unchanged, skipping update")
        return

    if self.running and self.sdr:
        # Change sample rate on running device without restart
        self.sdr.sample_rate = sample_rate
        # Read back actual rate (hardware may adjust slightly)
        actual_sample_rate = self.sdr.get_sample_rate()
        self.sample_rate = actual_sample_rate
        self.last_sample_rate = actual_sample_rate
        logging.debug(f"Updated sample rate to {actual_sample_rate/1e6:.6f} MHz without reinitialisation")
    else:
        self.sample_rate = sample_rate
```

#### 5. [core/display_manager.py](core/display_manager.py)
**Changes:**
- Added 7 sample rate action handlers in `menu_actions` property (lines 223-230)

**Action Mapping:**
```python
MenuButtonId.SAMPLE_RATE_250K.value: lambda: self.main_window.source_manager.set_rtl_sample_rate(250000),
MenuButtonId.SAMPLE_RATE_1024K.value: lambda: self.main_window.source_manager.set_rtl_sample_rate(1024000),
# ... etc for all 7 rates
```

## Sample Rate to Span Relationship

For RTL Samples (and all sample sources):
- **Span = Sample Rate**
- Start frequency = Centre - (Sample Rate / 2)
- Stop frequency = Centre + (Sample Rate / 2)

Example with 2.048 MS/s at 98 MHz centre:
- Sample rate: 2,048,000 Hz
- Span: 2.048 MHz
- Start: 96.976 MHz
- Stop: 99.024 MHz

## Resolution Bandwidth (RBW) Impact

Changing the sample rate affects RBW:
- **RBW = Sample Rate / FFT Size**

Examples with default FFT size (1024):
- 250 kS/s: RBW = 244.14 Hz
- 2.048 MS/s: RBW = 2.00 kHz
- 2.4 MS/s: RBW = 2.34 kHz

## Supported RTL-SDR Sample Rates

The RTL-SDR hardware supports various sample rates. The menu provides these common options:

| Label | Requested Rate (Hz) | Notes |
|-------|---------------------|-------|
| 250 kS/s | 250,000 | Actual: ~250000.000414 Hz |
| 1.024 MS/s | 1,024,000 | Power of 2 |
| 1.44 MS/s | 1,440,000 | |
| 1.8 MS/s | 1,800,000 | |
| 2.0 MS/s | 2,000,000 | Actual: ~2000000.052982 Hz |
| **2.048 MS/s** | **2,048,000** | **Default, power of 2** |
| 2.4 MS/s | 2,400,000 | Maximum supported |

**Note:** RTL-SDR hardware adjusts the requested sample rate slightly. The application reads back and uses the actual hardware rate for all calculations (RBW, frequency bins, etc.).

## Menu Flow

```
User presses Span button
    ↓
Menu system checks: Is current_source RtlSamplesDataSource?
    ↓
YES: Display "Sample\nRate" soft button
    ↓
User presses soft button
    ↓
Display 8 sample rate options
    ↓
User selects rate (e.g., "2.048 MS/s")
    ↓
source_manager.set_rtl_sample_rate(2048000)
    ↓
Check: Did sample rate actually change?
    ↓
NO: Show "Sample rate unchanged", exit
YES: Continue
    ↓
Updates:
  - frequency.span = 2048000
  - RTL source sample_rate (triggers stop/start)
  - Frequency display
  - RBW display
    ↓
Status message: "Sample rate: 2.048 MS/s, RBW: 2.00 kHz"
```

## Hardware Updates Without Reinitialization

**Important:** The RTL-SDR hardware supports changing the sample rate on a running device without requiring a full stop/restart cycle. The implementation:

1. Set new sample rate directly on running device: `self.sdr.sample_rate = new_rate`
2. Read back actual sample rate: `actual_rate = self.sdr.get_sample_rate()`
3. Update internal state with actual rate
4. Update frequency display and RBW

This approach is much faster than reinitializing (no interruption to data acquisition) and matches how the rtlsdr library is designed to be used. The `update_sample_rate()` and `update_frequency()` methods handle this automatically.

## Error Handling

The `set_rtl_sample_rate()` method includes validation:
- **No source running**: Shows "No source running"
- **Wrong source type**: Shows "Sample rate only applies to RTL Samples mode"
- **Exception during update**: Shows "Error setting sample rate: {error}"
- **Invalid sample rate**: RTL-SDR driver will reject unsupported rates

## Testing

To test the feature:
1. Start RTL Samples mode: Input → RTL Samples → FFT
2. Press the **Span** button (should show "Sample\nRate" instead of "Span")
3. Press the "Sample\nRate" soft button
4. Select different sample rates and verify:
   - Span updates to match sample rate
   - RBW recalculates correctly
   - Status message shows correct values
   - Spectrum display updates with new frequency range

## Future Enhancements

Potential improvements:
- Add sample rate selection for HackRF Samples (supports up to 20 MS/s)
- Add sample rate selection for Microphone (44.1 kHz, 48 kHz, 96 kHz, etc.)
- Remember last-used sample rate per source
- Validate sample rate against hardware capabilities
- Add visual indicator for current sample rate
