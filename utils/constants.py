"""Constants and enumerations for the Top Dog Spectrum Analyser."""

from enum import IntEnum, Enum


class DisplayMode(IntEnum):
    """Display widget indices."""
    TWO_D = 0
    THREE_D = 1
    WATERFALL = 2
    SURFACE = 3
    LOGO = 4
    CONSTELLATION_2D = 5
    CONSTELLATION_3D = 6
    ZERO_SPAN        = 7
    RIBBON           = 8
    DENSITY          = 9


class FFTSize(IntEnum):
    """Valid FFT sizes (powers of 2)."""
    SIZE_512 = 512
    SIZE_1024 = 1024
    SIZE_2048 = 2048
    SIZE_4096 = 4096
    SIZE_8192 = 8192

    @classmethod
    def is_valid(cls, size: int) -> bool:
        """Check if FFT size is valid."""
        return size in [s.value for s in cls]

    @classmethod
    def get_min(cls) -> int:
        """Get minimum FFT size."""
        return min(s.value for s in cls)

    @classmethod
    def get_max(cls) -> int:
        """Get maximum FFT size."""
        return max(s.value for s in cls)


class EntryMode(str, Enum):
    """Keypad / dial input mode identifiers.

    Inherits from str so that ``EntryMode.CENTRE == 'centre'`` is True —
    all existing ``== 'centre'`` comparisons continue to work unchanged.
    """
    CENTRE             = "centre"
    START              = "start"
    STOP               = "stop"
    SPAN               = "span"
    REF_LEVEL          = "ref_level"
    DISPLAY_LINE       = "display_line"
    THRESHOLD          = "threshold"
    EXCURSION          = "excursion"
    PRESET_NAME        = "preset_name"
    CAL_OFFSET         = "cal_offset"
    CAL_OFFSET_DIRECT  = "cal_offset_direct"
    MARKER             = "marker"
    ZERO_SPAN_TIME     = "zero_span_time"
    ZERO_SPAN_TRIGGER  = "zero_span_trigger"
    WF_FLOOR           = "wf_floor"
    WF_CEILING         = "wf_ceiling"


class WindowType(str, Enum):
    """Window function types for DSP."""
    HAMMING = "hamming"
    HANNING = "hanning"
    BLACKMAN = "blackman"
    RECTANGLE = "rectangle"


class FrequencyPresets:
    """Common frequency range presets in Hz."""
    # ISM Bands
    ISM_2_4_GHZ_START = 2.4e9
    ISM_2_4_GHZ_STOP = 2.5e9
    ISM_5_8_GHZ_START = 5.7e9
    ISM_5_8_GHZ_STOP = 5.9e9

    # FM Radio
    FM_RADIO_START = 88e6
    FM_RADIO_STOP = 108e6

    # Full-span extents for sweep sources
    HACKRF_SWEEP_FULL_START = 0
    HACKRF_SWEEP_FULL_STOP  = 7e9
    RTL_SWEEP_FULL_START    = 24e6
    RTL_SWEEP_FULL_STOP     = 1.766e9
    # Default ranges for different sources
    # RTL samples: default sample rate 2.048 MS/s centered at 98 MHz
    RTL_DEFAULT_START = 98e6 - 2.048e6 / 2  # 96.976 MHz
    RTL_DEFAULT_STOP = 98e6 + 2.048e6 / 2   # 99.024 MHz
    HACKRF_DEFAULT_START = 2400e6
    HACKRF_DEFAULT_STOP = 2500e6
    MICROPHONE_DEFAULT_START = 0
    MICROPHONE_DEFAULT_STOP = 22050


class SourceLimits:
    """Hardware source frequency and sample rate limits."""
    # RTL-SDR limits
    RTL_MIN_FREQ = 24e6
    RTL_MAX_FREQ = 1.766e9
    RTL_MAX_SAMPLE_RATE = 2.4e6

    # HackRF limits
    HACKRF_MIN_FREQ = 1e6
    HACKRF_MAX_FREQ = 6e9
    HACKRF_MAX_SAMPLE_RATE = 20e6

    # Microphone (audio) limits
    MICROPHONE_MIN_FREQ = 20
    MICROPHONE_MAX_FREQ = 20e3
    MICROPHONE_SAMPLE_RATE = 44100


class UIConstants:
    """UI-related constants."""
    # Button styles
    BUTTON_ACTIVE_STYLE = "background-color: #666666; color: white; font-weight: bold;"
    BUTTON_INACTIVE_STYLE = "background-color: #404040; color: white; font-weight: bold;"
    BUTTON_ENABLED_STYLE = "background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff6666, stop:1 #cc4444); color: white; font-weight: bold; border: 1px solid #555555; border-radius: 3px;"

    # Timer intervals (milliseconds)
    LOGO_TIMER_INTERVAL = 20

    # Thread timeout (seconds)
    THREAD_JOIN_TIMEOUT = 5.0

    # Default FFT size
    DEFAULT_FFT_SIZE = FFTSize.SIZE_1024.value

    # How many update_data() calls between sweep rate refreshes (at 20 ms interval = 1 s)
    SWEEP_RATE_UPDATE_INTERVAL = 50

    # Number of frames averaged to build the tare baseline
    TARE_NUM_SAMPLES = 32


class AmplitudeConstants:
    """Amplitude display constants."""
    DEFAULT_REF_LEVEL: float = 0.0    # dBm — top of screen
    DEFAULT_RANGE_DB: float = 100.0   # 10 dB/div × 10 divisions
    DIVISIONS: int = 10               # vertical divisions on screen
    DB_PER_DIV_OPTIONS = [1, 2, 5, 10, 20]


class DSPConstants:
    """DSP processing numerical constants."""
    LOG_FLOOR = 1e-12        # Prevents log10(0) in magnitude-domain (20·log10)
    POWER_LOG_FLOOR = 1e-10  # Prevents log10(0) in power-domain (10·log10)


class FrequencyUnits:
    """Frequency unit multipliers."""
    HZ = 1
    KHZ = 1e3
    MHZ = 1e6
    GHZ = 1e9


class SourceType(str, Enum):
    """Data source types."""
    RTL_SWEEP = "rtl_sweep"
    HACKRF_SWEEP = "hackrf_sweep"
    RTL_SAMPLES = "rtl_samples"
    MICROPHONE_SAMPLES = "microphone_samples"
    HACKRF_SAMPLES = "hackrf_samples"


class MenuButtonId(str, Enum):
    """Menu button identifiers."""
    FULL_SPAN = "btnFullSpan"
    # Preset slots
    PRESET_SLOT_1 = "btnPresetSlot1"
    PRESET_SLOT_2 = "btnPresetSlot2"
    PRESET_SLOT_3 = "btnPresetSlot3"
    PRESET_SLOT_4 = "btnPresetSlot4"
    PRESET_SLOT_5 = "btnPresetSlot5"
    PRESET_SLOT_6 = "btnPresetSlot6"
    PRESET_SLOT_7 = "btnPresetSlot7"
    PRESET_SLOT_8 = "btnPresetSlot8"
    HOLD = "btnHold"
    TWO_D = "btn2d"
    THREE_D = "btn3d"
    WATERFALL = "btnWaterfall"
    SURFACE = "btnSurface"
    CENTRE_FREQUENCY = "btnCentreFrequency"
    START_FREQUENCY = "btnStartFrequency"
    STOP_FREQUENCY = "btnStopFrequency"
    SPAN = "btnSpan"
    ISM_24 = "btnISM24"
    ISM_58 = "btnISM58"
    RTL_SWEEP = "btnRtlSweep"
    HACKRF_SWEEP = "btnHackRFSweep"
    RIBBON       = "btnRibbon"
    TWO_D_FILL_GRADIENT = "btnTwoDFillGradient"
    TWO_D_FILL_SOLID    = "btnTwoDFillSolid"
    TWO_D_FILL_GLOW     = "btnTwoDFillGlow"
    TWO_D_FILL_OFF      = "btnTwoDFillOff"
    TWO_D_COLOUR_GREEN  = "btnTwoDColourGreen"
    TWO_D_COLOUR_YELLOW = "btnTwoDColourYellow"
    TWO_D_COLOUR_CYAN   = "btnTwoDColourCyan"
    TWO_D_COLOUR_WHITE  = "btnTwoDColourWhite"
    TWO_D_COLOUR_BLUE   = "btnTwoDColourBlue"
    DENSITY                  = "btnDensity"
    DENSITY_COLOURMAP        = "btnDensityColourmap"
    DENSITY_COLOURMAP_MAGMA  = "btnDensityColourmapMagma"
    DENSITY_COLOURMAP_VIRIDIS = "btnDensityColourmapViridis"
    DENSITY_COLOURMAP_PLASMA  = "btnDensityColourmapPlasma"
    DENSITY_COLOURMAP_INFERNO = "btnDensityColourmapInferno"
    DENSITY_DECAY            = "btnDensityDecay"
    DENSITY_DECAY_FAST       = "btnDensityDecayFast"
    DENSITY_DECAY_MEDIUM     = "btnDensityDecayMedium"
    DENSITY_DECAY_SLOW       = "btnDensityDecaySlow"
    DENSITY_DECAY_OFF        = "btnDensityDecayOff"
    DENSITY_CLEAR            = "btnDensityClear"
    RTL_SAMPLES = "btnRtlSamples"
    MICROPHONE_SAMPLES = "btnMicrophoneSamples"
    HACKRF_SAMPLES = "btnHackrfSamples"
    HAMMING = "btnHamming"
    HANNING = "btnHanning"
    RECTANGLE = "btnRectangle"
    FFT_512 = "btnFFT512"
    FFT_1024 = "btnFFT1024"
    FFT_2048 = "btnFFT2048"
    FFT_4096 = "btnFFT4096"
    CF_DIVIDED_BY_TWO = "btnCfDividedByTwo"
    CF_TIMES_TWO = "btnCfTimesTwo"
    FFT = "btnFFT"
    PSD = "btnPSD"
    LOG_FREQ = "btnLogFreq"
    TARE = "btnTare"
    SAMPLE_RATE = "btnSampleRate"
    SAMPLE_RATE_250K = "btnSampleRate250k"
    SAMPLE_RATE_1024K = "btnSampleRate1024k"
    SAMPLE_RATE_1440K = "btnSampleRate1440k"
    SAMPLE_RATE_1800K = "btnSampleRate1800k"
    SAMPLE_RATE_2000K = "btnSampleRate2000k"
    SAMPLE_RATE_2048K = "btnSampleRate2048k"
    SAMPLE_RATE_2400K = "btnSampleRate2400k"
    HACKRF_SAMPLE_RATE_2M = "btnHackRFSampleRate2M"
    HACKRF_SAMPLE_RATE_4M = "btnHackRFSampleRate4M"
    HACKRF_SAMPLE_RATE_8M = "btnHackRFSampleRate8M"
    HACKRF_SAMPLE_RATE_10M = "btnHackRFSampleRate10M"
    HACKRF_SAMPLE_RATE_16M = "btnHackRFSampleRate16M"
    HACKRF_SAMPLE_RATE_20M = "btnHackRFSampleRate20M"
    # Amplitude
    REF_LEVEL = "btnReflevel"
    LOG_DB_DIV = "btnLogdbdiv"
    LOG = "btnLog"
    LINEAR = "btnLinear"
    DB_PER_DIV_1 = "btnDbPerDiv1"
    DB_PER_DIV_2 = "btnDbPerDiv2"
    DB_PER_DIV_5 = "btnDbPerDiv5"
    DB_PER_DIV_10 = "btnDbPerDiv10"
    DB_PER_DIV_20 = "btnDbPerDiv20"
    # Hold
    MAX_HOLD         = "btnMaxHold"
    MIN_HOLD         = "btnMinHold"
    CLEAR_HOLD       = "btnClearHold"
    # Display line, threshold, persistence
    DISP_LINE_ONOFF  = "btnDispLineOnOff"
    DISP_LINE_LEVEL  = "btnDispLineLevel"
    PK_THRESHOLD     = "btnPkThreshold"
    PK_EXCURSION     = "btnPkExcursion"
    PERSIST_OFF      = "btnPersistOff"
    PERSIST_SHORT    = "btnPersistShort"
    PERSIST_MEDIUM   = "btnPersistMedium"
    PERSIST_LONG     = "btnPersistLong"
    # Trace A/B
    TRACE_STORE_A    = "btnTraceStoreA"
    TRACE_SHOW_A     = "btnTraceShowA"
    TRACE_STORE_B    = "btnTraceStoreB"
    TRACE_SHOW_B     = "btnTraceShowB"
    TRACE_A_MINUS_B  = "btnTraceAMinusB"
    TRACE_LIVE       = "btnTraceLive"
    TRACE_CLEAR      = "btnTraceClear"
    # Audio sample rates
    AUDIO_SAMPLE_RATE_8K    = "btnAudioSR8k"
    AUDIO_SAMPLE_RATE_11K   = "btnAudioSR11k"
    AUDIO_SAMPLE_RATE_16K   = "btnAudioSR16k"
    AUDIO_SAMPLE_RATE_22K   = "btnAudioSR22k"
    AUDIO_SAMPLE_RATE_44K   = "btnAudioSR44k"
    AUDIO_SAMPLE_RATE_48K   = "btnAudioSR48k"
    AUDIO_SAMPLE_RATE_96K   = "btnAudioSR96k"
    # Audio channel mode
    AUDIO_MONO   = "btnAudioMono"
    AUDIO_LEFT   = "btnAudioLeft"
    AUDIO_RIGHT  = "btnAudioRight"
    AUDIO_STEREO = "btnAudioStereo"
    # Averaging
    AVG_OFF    = "btnAvgOff"
    AVG_EXP_2  = "btnAvgExp2"
    AVG_EXP_4  = "btnAvgExp4"
    AVG_EXP_8  = "btnAvgExp8"
    AVG_EXP_16 = "btnAvgExp16"
    AVG_LIN_4  = "btnAvgLin4"
    AVG_LIN_16 = "btnAvgLin16"
    AVG_LIN_64 = "btnAvgLin64"
    # Markers
    MARKER_F1          = "btnMarkerF1"
    MARKER_F2          = "btnMarkerF2"
    MARKER_P1          = "btnMarkerP1"
    MARKER_P2          = "btnMarkerP2"
    MARKER_TO_PEAK     = "btnMarkerToPeak"
    MARKER_NEXT_PEAK   = "btnMarkerNextPeak"
    MARKER_TO_CENTRE   = "btnMarkerToCentre"
    MARKER_CLEAR_ALL   = "btnMarkerClearAll"
    PEAK_LIST          = "btnPeakList"
    # Constellation / Duty cycle
    CONSTELLATION         = "btnConstellation"
    CONSTELLATION_SCATTER   = "btnConstellationScatter"
    CONSTELLATION_DENSITY   = "btnConstellationDensity"
    CONST_MODULATION        = "btnConstModulation"
    CONST_BPSK              = "btnConstBPSK"
    CONST_QPSK              = "btnConstQPSK"
    CONST_8PSK              = "btnConst8PSK"
    CONST_16QAM             = "btnConst16QAM"
    CONST_64QAM             = "btnConst64QAM"
    CONST_RANGE             = "btnConstRange"
    CONST_RANGE_15          = "btnConstRange15"
    CONST_RANGE_20          = "btnConstRange20"
    CONST_RANGE_30          = "btnConstRange30"
    CONST_POINTS            = "btnConstPoints"
    CONST_POINTS_500        = "btnConstPoints500"
    CONST_POINTS_2K         = "btnConstPoints2K"
    CONST_POINTS_5K         = "btnConstPoints5K"
    CONST_POINTS_10K        = "btnConstPoints10K"
    DUTY_CYCLE            = "btnDutyCycle"
    # 3D display options
    THREE_D_GRID        = "btn3dGrid"
    THREE_D_AUTO_ROTATE = "btn3dAutoRotate"
    THREE_D_HIST_50     = "btn3dHist50"
    THREE_D_HIST_100    = "btn3dHist100"
    THREE_D_HIST_200    = "btn3dHist200"
    THREE_D_HIST_300    = "btn3dHist300"
    THREE_D_HIST_500    = "btn3dHist500"
    # Surface display options
    SURFACE_AUTO_ROTATE = "btnSurfaceAutoRotate"
    SURFACE_HIST_10     = "btnSurfaceHist10"
    SURFACE_HIST_25     = "btnSurfaceHist25"
    SURFACE_HIST_50     = "btnSurfaceHist50"
    SURFACE_HIST_100    = "btnSurfaceHist100"
    SURFACE_HIST_200    = "btnSurfaceHist200"
    # Span
    ZERO_SPAN                = "btnZeroSpan"
    ZERO_SPAN_FREE_RUN       = "btnZeroSpanFreeRun"
    ZERO_SPAN_RISE           = "btnZeroSpanRise"
    ZERO_SPAN_FALL           = "btnZeroSpanFall"
    ZERO_SPAN_TRIGGER_LEVEL  = "btnZeroSpanTriggerLevel"
    ZERO_SPAN_TIME           = "btnZeroSpanTime"
    # RF Gain
    RF_GAIN              = "btnRfGain"
    GAIN_NOT_AVAILABLE   = "btnGainNotAvailable"
    BW_NOT_AVAILABLE     = "btnBwNotAvailable"
    RTL_GAIN_AUTO        = "btnRtlGainAuto"
    RTL_GAIN_0           = "btnRtlGain0"
    RTL_GAIN_10          = "btnRtlGain10"
    RTL_GAIN_20          = "btnRtlGain20"
    RTL_GAIN_30          = "btnRtlGain30"
    RTL_GAIN_40          = "btnRtlGain40"
    RTL_GAIN_50          = "btnRtlGain50"
    HACKRF_LNA_0         = "btnHackrfLna0"
    HACKRF_LNA_8         = "btnHackrfLna8"
    HACKRF_LNA_16        = "btnHackrfLna16"
    HACKRF_LNA_24        = "btnHackrfLna24"
    HACKRF_LNA_32        = "btnHackrfLna32"
    HACKRF_LNA_40        = "btnHackrfLna40"
    HACKRF_VGA_0         = "btnHackrfVga0"
    HACKRF_VGA_10        = "btnHackrfVga10"
    HACKRF_VGA_20        = "btnHackrfVga20"
    HACKRF_VGA_30        = "btnHackrfVga30"
    HACKRF_VGA_40        = "btnHackrfVga40"
    HACKRF_VGA_50        = "btnHackrfVga50"
    HACKRF_VGA_60        = "btnHackrfVga60"
    HACKRF_VGA_62        = "btnHackrfVga62"
    HACKRF_AMP_ON        = "btnHackrfAmpOn"
    HACKRF_AMP_OFF       = "btnHackrfAmpOff"
    # HackRF Samples DC Alpha
    HACKRF_DC_ALPHA_OFF  = "btnHackrfDcAlphaOff"
    HACKRF_DC_ALPHA_1_0  = "btnHackrfDcAlpha1_0"
    HACKRF_DC_ALPHA_0_5  = "btnHackrfDcAlpha0_5"
    HACKRF_DC_ALPHA_0_1  = "btnHackrfDcAlpha0_1"
    HACKRF_DC_ALPHA_0_01 = "btnHackrfDcAlpha0_01"
    # HackRF Sweep RBW (bin width passed to hackrf_sweep -w)
    HACKRF_SWEEP_RBW_5K   = "btnHackRFSweepRbw5k"
    HACKRF_SWEEP_RBW_10K  = "btnHackRFSweepRbw10k"
    HACKRF_SWEEP_RBW_20K  = "btnHackRFSweepRbw20k"
    HACKRF_SWEEP_RBW_30K  = "btnHackRFSweepRbw30k"
    HACKRF_SWEEP_RBW_50K  = "btnHackRFSweepRbw50k"
    HACKRF_SWEEP_RBW_100K = "btnHackRFSweepRbw100k"
    HACKRF_SWEEP_RBW_200K = "btnHackRFSweepRbw200k"
    HACKRF_SWEEP_RBW_500K = "btnHackRFSweepRbw500k"
    # Waterfall colour maps
    WFALL_COLOUR_GQRX    = "btnWfallColourGqrx"
    WFALL_COLOUR_MAGMA   = "btnWfallColourMagma"
    WFALL_COLOUR_VIRIDIS = "btnWfallColourViridis"
    WFALL_COLOUR_INFERNO = "btnWfallColourInferno"
    WFALL_COLOUR_PLASMA  = "btnWfallColourPlasma"
    WFALL_COLOUR_GREY    = "btnWfallColourGrey"
    WFALL_COLOUR_RAINBOW = "btnWfallColourRainbow"
    WFALL_SPAN_30        = "btnWfSpan30"
    WFALL_SPAN_60        = "btnWfSpan60"
    WFALL_SPAN_300       = "btnWfSpan300"
    WFALL_SPAN_600       = "btnWfSpan600"
    WFALL_FLOOR          = "btnWfFloor"
    WFALL_CEILING        = "btnWfCeiling"
    WFALL_FREEZE         = "btnWfFreeze"
    # Calibration
    CAL_SET    = "btnCalSet"
    CAL_OFFSET = "btnCalOffset"
    CAL_CLEAR  = "btnCalClear"
    # Export image — format chosen via soft buttons
    EXPORT_DISPLAY_PNG  = "btnExportDisplayPng"
    EXPORT_DISPLAY_JPEG = "btnExportDisplayJpeg"
    EXPORT_DISPLAY_SVG  = "btnExportDisplaySvg"
    EXPORT_WINDOW_PNG   = "btnExportWindowPng"
    EXPORT_WINDOW_JPEG  = "btnExportWindowJpeg"
