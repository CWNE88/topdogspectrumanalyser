from PyQt6.QtWidgets import QPushButton
from typing import List, Dict, Optional, Callable
from datasources.rtl_samples import RtlSamplesDataSource
from datasources.hackrf_samples import HackrfSamplesDataSource
from datasources.audio_samples import MicrophoneSamplesDataSource
import math
import logging

logger = logging.getLogger(__name__)

class MenuItem:
    def __init__(self, id: str, label: str, sub_menu: Optional[List["MenuItem"]] = None):
        self.id = id
        self.label = label
        self.sub_menu = sub_menu or []

class MenuManager:
    ITEMS_PER_PAGE = 7  # items per page when a menu overflows all 8 slots; button 8 becomes the page navigator

    def __init__(self, on_selection: Callable[[MenuItem], None], parent):
        self.on_selection = on_selection
        self.parent = parent
        self.current_menu: List[MenuItem] = []
        self.menu_stack: List[List[MenuItem]] = []
        self._current_page: int = 0
        self.soft_buttons: List[Optional[QPushButton]] = [
            getattr(parent, f"button_soft_{i}", None) for i in range(1, 9)
        ]
        self.menus: Dict[str, List[MenuItem]] = self._create_menus()

    def _create_menus(self) -> Dict[str, List[MenuItem]]:
        return {
            "Frequency":        self._create_frequency_menu(),
            "Span":             self._create_span_menu(),
            "BW":               self._create_bw_menu(),
            "Amplitude":        self._create_amplitude_menu(),
            "Scale":            self._create_scale_menu(),
            "Log\ndB/div":      self._create_db_per_div_menu(),
            "Input":            self._create_source_menu(),
            "RTL-SDR":          self._create_rtl_mode_menu(),
            "HackRF":           self._create_hackrf_mode_menu(),
            "Analysis":         self._create_analysis_menu(),
            "FFT":              self._create_fft_menu(),
            "Constellation":    self._create_constellation_menu(),
            "Modulation":  self._create_const_modulation_menu(),
            "Range":       self._create_const_range_menu(),
            "Points":      self._create_const_points_menu(),
            "Window":           self._create_window_menu(),
            "Sample Size":      self._create_sample_size_menu(),
            "Channel":          self._create_audio_channel_menu(),
            "Marker":           self._create_marker_menu(),
            "Trace":            self._create_trace_menu(),
            "Averaging":        self._create_averaging_menu(),
            "Hold":             self._create_hold_menu(),
            "Persistence":      self._create_persistence_menu(),
            "Memory":           self._create_trace_memory_menu(),
            "Display":          self._create_display_menu(),
            "Display\nType":    self._create_display_mode_menu(),
            "Display\nLine":    self._create_display_line_menu(),
            "2D\nDisplay":      self._create_2d_display_menu(),
            "Colour":           self._create_2d_colour_menu(),
            "Fill":             self._create_2d_fill_menu(),
            "3D\nDisplay":      self._create_3d_display_menu(),
            "Ribbon\nDisplay":  [],
            "Density\nDisplay": self._create_density_display_menu(),
            "Colourmap":        self._create_density_colour_menu(),
            "Decay":            self._create_density_decay_menu(),
            "History\nLines":   self._create_3d_history_menu(),
            "Waterfall\nDisplay": self._create_waterfall_display_menu(),
            "Colour\nMap":        self._create_waterfall_colour_menu(),
            "Time\nSpan":         self._create_waterfall_span_menu(),
            "Export\nImage":      self._create_export_menu(),
            "Current\nDisplay":  self._create_export_display_formats(),
            "Full\nWindow":      self._create_export_window_formats(),
            "Surface\nDisplay": self._create_surface_display_menu(),
            "History":          self._create_surface_history_menu(),
            "Zero\nSpan":       self._create_zero_span_menu(),
            "RF\nGain":         self._create_rf_gain_menu(),
            "HackRF\nSamples":  self._create_hackrf_samples_menu(),
            "LNA\nGain":        self._create_hackrf_lna_menu(),
            "VGA\nGain":        self._create_hackrf_vga_menu(),
            "DC\nAlpha":        self._create_hackrf_dc_alpha_menu(),
            "RBW":              self._create_hackrf_sweep_rbw_menu(),
            "Cal":              self._create_cal_menu(),
            "Preset":           self._create_preset_menu(),
            "Recall":           self._create_preset_slots_menu(),
            "Save":             self._create_preset_slots_menu(),
            "Name\nSlot":       self._create_preset_slots_menu(),
            "Delete":           self._create_preset_slots_menu(),
        }

    def _create_frequency_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnCentreFrequency", "Centre\nFrequency"),
            MenuItem("btnStartFrequency", "Start\nFrequency"),
            MenuItem("btnStopFrequency", "Stop\nFrequency"),            
            MenuItem("btnCfDividedByTwo", "Centre Freq\n÷ 2"),            
            MenuItem("btnCfTimesTwo", "Centre Freq\n× 2"),            
        ]

    def _create_zero_span_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnZeroSpanFreeRun",  "Free\nRun"),
            MenuItem("btnZeroSpanRise",     "Rise"),
            MenuItem("btnZeroSpanFall",     "Fall"),
            MenuItem("btnZeroSpanTime",     "Time"),
        ]

    def _create_span_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnSpan",     "Span"),
            MenuItem("btnFullSpan", "Full\nSpan"),
        ]

    def _create_bw_menu(self) -> List[MenuItem]:
        src = getattr(self.parent, 'current_source', None)
        zero_span = MenuItem("btnZeroSpan", "Zero\nSpan", sub_menu=self._create_zero_span_menu())
        if isinstance(src, RtlSamplesDataSource):
            return [
                MenuItem("btnSampleRate250k",  "250 kHz"),
                MenuItem("btnSampleRate1024k", "1.024 MHz"),
                MenuItem("btnSampleRate1440k", "1.44 MHz"),
                MenuItem("btnSampleRate1800k", "1.8 MHz"),
                MenuItem("btnSampleRate2000k", "2.0 MHz"),
                MenuItem("btnSampleRate2048k", "2.048 MHz"),
                MenuItem("btnSampleRate2400k", "2.4 MHz"),
                zero_span,
            ]
        if isinstance(src, HackrfSamplesDataSource):
            return [
                MenuItem("btnHackRFSampleRate2M",  "2 MHz"),
                MenuItem("btnHackRFSampleRate4M",  "4 MHz"),
                MenuItem("btnHackRFSampleRate8M",  "8 MHz"),
                MenuItem("btnHackRFSampleRate10M", "10 MHz"),
                MenuItem("btnHackRFSampleRate16M", "16 MHz"),
                MenuItem("btnHackRFSampleRate20M", "20 MHz"),
                zero_span,
            ]
        if isinstance(src, MicrophoneSamplesDataSource):
            return [
                MenuItem("btnAudioSR8k",  "8 kHz"),
                MenuItem("btnAudioSR11k", "11.025 kHz"),
                MenuItem("btnAudioSR16k", "16 kHz"),
                MenuItem("btnAudioSR22k", "22.05 kHz"),
                MenuItem("btnAudioSR44k", "44.1 kHz"),
                MenuItem("btnAudioSR48k", "48 kHz"),
                MenuItem("btnAudioSR96k", "96 kHz"),
                zero_span,
            ]
        from datasources.hackrf_sweep import HackRFSweepDataSource
        if isinstance(src, HackRFSweepDataSource):
            return self._create_hackrf_sweep_rbw_menu()
        return [MenuItem("btnBwNotAvailable", "Not\nAvailable")]

    def _create_hackrf_sweep_rbw_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnHackRFSweepRbw5k",   "5 kHz"),
            MenuItem("btnHackRFSweepRbw10k",  "10 kHz"),
            MenuItem("btnHackRFSweepRbw20k",  "20 kHz"),
            MenuItem("btnHackRFSweepRbw30k",  "30 kHz"),
            MenuItem("btnHackRFSweepRbw50k",  "50 kHz"),
            MenuItem("btnHackRFSweepRbw100k", "100 kHz"),
            MenuItem("btnHackRFSweepRbw200k", "200 kHz"),
            MenuItem("btnHackRFSweepRbw500k", "500 kHz"),
        ]

    def _create_audio_sample_rate_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnAudioSR8k",  "8 kHz"),
            MenuItem("btnAudioSR11k", "11.025 kHz"),
            MenuItem("btnAudioSR16k", "16 kHz"),
            MenuItem("btnAudioSR22k", "22.05 kHz"),
            MenuItem("btnAudioSR44k", "44.1 kHz"),
            MenuItem("btnAudioSR48k", "48 kHz"),
            MenuItem("btnAudioSR96k", "96 kHz"),
        ]

    def _create_rtl_sample_rate_menu(self) -> List[MenuItem]:
        """RTL-SDR sample rate options (hardware-tested rates only)."""
        return [
            MenuItem("btnSampleRate250k", "250 kS/s"),
            MenuItem("btnSampleRate1024k", "1.024 MS/s"),
            MenuItem("btnSampleRate1440k", "1.44 MS/s"),
            MenuItem("btnSampleRate1800k", "1.8 MS/s"),
            MenuItem("btnSampleRate2000k", "2.0 MS/s"),
            MenuItem("btnSampleRate2048k", "2.048 MS/s"),
            MenuItem("btnSampleRate2400k", "2.4 MS/s"),
        ]

    def _create_hackrf_samples_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnHackrfDcAlpha", "DC\nAlpha", sub_menu=self._create_hackrf_dc_alpha_menu()),
        ]

    def _create_hackrf_sample_rate_menu(self) -> List[MenuItem]:
        """HackRF sample rate options."""
        return [
            MenuItem("btnHackRFSampleRate2M", "2 MS/s"),
            MenuItem("btnHackRFSampleRate4M", "4 MS/s"),
            MenuItem("btnHackRFSampleRate8M", "8 MS/s"),
            MenuItem("btnHackRFSampleRate10M", "10 MS/s"),
            MenuItem("btnHackRFSampleRate16M", "16 MS/s"),
            MenuItem("btnHackRFSampleRate20M", "20 MS/s"),
        ]

    def _create_amplitude_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnRfGain",   "RF\nGain",  sub_menu=self._create_rf_gain_menu()),
            MenuItem("btnReflevel", "Ref\nLevel"),
            MenuItem("btnScale",    "Scale",     sub_menu=self._create_scale_menu()),
            MenuItem("btnLogdbdiv", "Log\ndB/div", sub_menu=self._create_db_per_div_menu()),
            MenuItem("btnTare",     "Trace\nNormalise"),
        ]

    def _create_rf_gain_menu(self) -> List[MenuItem]:
        src = getattr(self.parent, 'current_source', None)
        if isinstance(src, RtlSamplesDataSource):
            return self._create_rtl_gain_menu()
        if isinstance(src, HackrfSamplesDataSource):
            return self._create_hackrf_rf_gain_menu()
        from datasources.hackrf_sweep import HackRFSweepDataSource
        if isinstance(src, HackRFSweepDataSource):
            return self._create_hackrf_sweep_gain_menu()
        return [MenuItem("btnGainNotAvailable", "Not\nAvailable")]

    def _create_rtl_gain_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnRtlGainAuto", "Auto"),
            MenuItem("btnRtlGain0",    "0 dB"),
            MenuItem("btnRtlGain10",   "10 dB"),
            MenuItem("btnRtlGain20",   "20 dB"),
            MenuItem("btnRtlGain30",   "30 dB"),
            MenuItem("btnRtlGain40",   "40 dB"),
            MenuItem("btnRtlGain50",   "50 dB"),
        ]

    def _create_hackrf_rf_gain_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnHackrfLnaGain", "LNA\nGain", sub_menu=self._create_hackrf_lna_menu()),
            MenuItem("btnHackrfVgaGain", "VGA\nGain", sub_menu=self._create_hackrf_vga_menu()),
            MenuItem("btnHackrfAmpOn",   "Amp\nOn"),
            MenuItem("btnHackrfAmpOff",  "Amp\nOff"),
            MenuItem("btnHackrfDcAlpha",  "DC\nAlpha", sub_menu=self._create_hackrf_dc_alpha_menu()),
        ]

    def _create_hackrf_sweep_gain_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnHackrfLnaGain", "LNA\nGain", sub_menu=self._create_hackrf_lna_menu()),
            MenuItem("btnHackrfVgaGain", "VGA\nGain", sub_menu=self._create_hackrf_vga_menu()),
            MenuItem("btnHackrfAmpOn",   "Amp\nOn"),
            MenuItem("btnHackrfAmpOff",  "Amp\nOff"),
        ]

    def _create_hackrf_dc_alpha_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnHackrfDcAlpha1_0",  "1.0\n(instant)"),
            MenuItem("btnHackrfDcAlpha0_5",  "0.5\n(fast)"),
            MenuItem("btnHackrfDcAlpha0_1",  "0.1\n(medium)"),
            MenuItem("btnHackrfDcAlpha0_01", "0.01\n(slow)"),
            MenuItem("btnHackrfDcAlphaOff",  "Off\n(none)"),
        ]

    def _create_hackrf_lna_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnHackrfLna0",  "0 dB"),
            MenuItem("btnHackrfLna8",  "8 dB"),
            MenuItem("btnHackrfLna16", "16 dB"),
            MenuItem("btnHackrfLna24", "24 dB"),
            MenuItem("btnHackrfLna32", "32 dB"),
            MenuItem("btnHackrfLna40", "40 dB"),
        ]

    def _create_hackrf_vga_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnHackrfVga0",  "0 dB"),
            MenuItem("btnHackrfVga10", "10 dB"),
            MenuItem("btnHackrfVga20", "20 dB"),
            MenuItem("btnHackrfVga30", "30 dB"),
            MenuItem("btnHackrfVga40", "40 dB"),
            MenuItem("btnHackrfVga50", "50 dB"),
            MenuItem("btnHackrfVga60", "60 dB"),
            MenuItem("btnHackrfVga62", "62 dB"),
        ]

    def _create_scale_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnLog",    "Log"),
            MenuItem("btnLinear", "Linear"),
        ]

    def _create_db_per_div_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnDbPerDiv1",  "1 dB/div"),
            MenuItem("btnDbPerDiv2",  "2 dB/div"),
            MenuItem("btnDbPerDiv5",  "5 dB/div"),
            MenuItem("btnDbPerDiv10", "10 dB/div"),
            MenuItem("btnDbPerDiv20", "20 dB/div"),
        ]


    def _create_source_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnSourceRtl",         "RTL-SDR",    sub_menu=self._create_rtl_mode_menu()),
            MenuItem("btnSourceHackRF",       "HackRF",     sub_menu=self._create_hackrf_mode_menu()),
            MenuItem("btnMicrophoneSamples", "Microphone"),
        ]

    def _create_rtl_mode_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnRtlSamples", "Samples"),
            MenuItem("btnRtlSweep",   "Sweep"),
        ]

    def _create_hackrf_mode_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnHackrfSamples", "Samples"),
            MenuItem("btnHackRFSweep",   "Sweep"),
        ]

    def _create_marker_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnMarkerF1",        "Mkr 1\nFreq"),
            MenuItem("btnMarkerF2",        "Mkr 2\nFreq"),
            MenuItem("btnMarkerP1",        "Mkr 1\nPower"),
            MenuItem("btnMarkerP2",        "Mkr 2\nPower"),
            MenuItem("btnMarkerToPeak",    "Mkr→\nPeak"),
            MenuItem("btnMarkerNextPeak",  "Next\nPeak"),
            MenuItem("btnMarkerToCentre",  "Mkr→\nCentre"),
            MenuItem("btnMarkerClearAll",  "Clear\nAll"),
            MenuItem("btnPeakList",        "Peak\nList"),
        ]

    def _create_display_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnDisplayLine", "Display\nLine", sub_menu=self._create_display_line_menu()),
            MenuItem("btnPkThreshold", "Pk\nThreshold"),
            MenuItem("btnPkExcursion", "Excursion"),
            MenuItem("btnLogFreq",     "Log\nFreq"),
        ]

    def _create_display_mode_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btn2d",        "2D"),
            MenuItem("btn3d",        "3D"),
            MenuItem("btnWaterfall", "Waterfall"),
            MenuItem("btnSurface",   "Surface"),
            MenuItem("btnRibbon",    "Ribbon"),
            MenuItem("btnDensity",   "Density"),
        ]

    def _create_2d_display_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnTwoDFill",       "Fill",   sub_menu=self._create_2d_fill_menu()),
            MenuItem("btnTwoDColourMenu", "Colour", sub_menu=self._create_2d_colour_menu()),
        ]

    def _create_2d_fill_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnTwoDFillGradient", "Gradient"),
            MenuItem("btnTwoDFillSolid",    "Solid"),
            MenuItem("btnTwoDFillGlow",     "Glow"),
            MenuItem("btnTwoDFillOff",      "Off"),
        ]

    def _create_2d_colour_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnTwoDColourGreen",  "Green"),
            MenuItem("btnTwoDColourYellow", "Yellow"),
            MenuItem("btnTwoDColourCyan",   "Cyan"),
            MenuItem("btnTwoDColourWhite",  "White"),
            MenuItem("btnTwoDColourBlue",   "Blue"),
        ]

    def _create_density_display_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnDensityColourmap", "Colourmap",    sub_menu=self._create_density_colour_menu()),
            MenuItem("btnDensityDecay",     "Decay",        sub_menu=self._create_density_decay_menu()),
            MenuItem("btnDensityClear",     "Clear"),
        ]

    def _create_density_colour_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnDensityColourmapMagma",   "Magma"),
            MenuItem("btnDensityColourmapViridis",  "Viridis"),
            MenuItem("btnDensityColourmapPlasma",   "Plasma"),
            MenuItem("btnDensityColourmapInferno",  "Inferno"),
        ]

    def _create_density_decay_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnDensityDecayFast",   "Fast"),
            MenuItem("btnDensityDecayMedium", "Medium"),
            MenuItem("btnDensityDecaySlow",   "Slow"),
            MenuItem("btnDensityDecayOff",    "Off\n(Accum)"),
        ]

    def _create_3d_display_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btn3dHistoryLines", "History\nLines", sub_menu=self._create_3d_history_menu()),
            MenuItem("btn3dGrid",         "Grid\nOn/Off"),
            MenuItem("btn3dAutoRotate",   "Auto\nRotate"),
        ]

    def _create_3d_history_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btn3dHist50",  "50 lines"),
            MenuItem("btn3dHist100", "100 lines"),
            MenuItem("btn3dHist200", "200 lines"),
            MenuItem("btn3dHist300", "300 lines"),
            MenuItem("btn3dHist500", "500 lines"),
        ]

    def _create_surface_display_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnSurfaceHistLines", "History", sub_menu=self._create_surface_history_menu()),
            MenuItem("btnSurfaceAutoRotate", "Auto\nRotate"),
        ]

    def _create_surface_history_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnSurfaceHist10",  "10 lines"),
            MenuItem("btnSurfaceHist25",  "25 lines"),
            MenuItem("btnSurfaceHist50",  "50 lines"),
            MenuItem("btnSurfaceHist100", "100 lines"),
            MenuItem("btnSurfaceHist200", "200 lines"),
        ]

    def _create_waterfall_display_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnWfColourMenu", "Colour\nMap",  sub_menu=self._create_waterfall_colour_menu()),
            MenuItem("btnWfSpanMenu",   "Time\nSpan",   sub_menu=self._create_waterfall_span_menu()),
            MenuItem("btnWfFloor",      "Floor"),
            MenuItem("btnWfCeiling",    "Ceiling"),
            MenuItem("btnWfFreeze",     "Freeze"),
        ]

    def _create_waterfall_colour_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnWfallColourGqrx",    "GQRX"),
            MenuItem("btnWfallColourMagma",   "Magma"),
            MenuItem("btnWfallColourViridis",  "Viridis"),
            MenuItem("btnWfallColourInferno",  "Inferno"),
            MenuItem("btnWfallColourPlasma",   "Plasma"),
            MenuItem("btnWfallColourGrey",     "Grey"),
            MenuItem("btnWfallColourRainbow",  "Rainbow"),
        ]

    def _create_waterfall_span_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnWfSpan30",  "30 s"),
            MenuItem("btnWfSpan60",  "1 min"),
            MenuItem("btnWfSpan300", "5 min"),
            MenuItem("btnWfSpan600", "10 min"),
        ]

    def _create_export_display_formats(self) -> List[MenuItem]:
        return [
            MenuItem("btnExportDisplayPng",  "PNG"),
            MenuItem("btnExportDisplayJpeg", "JPEG"),
            MenuItem("btnExportDisplaySvg",  "SVG\n(2D only)"),
        ]

    def _create_export_window_formats(self) -> List[MenuItem]:
        return [
            MenuItem("btnExportWindowPng",  "PNG"),
            MenuItem("btnExportWindowJpeg", "JPEG"),
        ]

    def _create_export_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnExportDisplay", "Current\nDisplay", sub_menu=self._create_export_display_formats()),
            MenuItem("btnExportWindow",  "Full\nWindow",     sub_menu=self._create_export_window_formats()),
        ]

    def _create_hold_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnMaxHold",   "Max Hold"),
            MenuItem("btnMinHold",   "Min Hold"),
            MenuItem("btnClearHold", "Clear\nHold"),
        ]

    def _create_display_line_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnDispLineOnOff", "On / Off"),
            MenuItem("btnDispLineLevel", "Level"),
        ]

    def _create_persistence_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnPersistOff",    "Off"),
            MenuItem("btnPersistShort",  "Short"),
            MenuItem("btnPersistMedium", "Medium"),
            MenuItem("btnPersistLong",   "Long"),
        ]

    def _create_trace_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnTraceLive",   "Live\nOn/Off"),
            MenuItem("btnAveraging",   "Averaging",   sub_menu=self._create_averaging_menu()),
            MenuItem("btnHold",        "Hold",        sub_menu=self._create_hold_menu()),
            MenuItem("btnPersistence", "Persistence", sub_menu=self._create_persistence_menu()),
            MenuItem("btnTraceMemory", "Memory",      sub_menu=self._create_trace_memory_menu()),
        ]

    def _create_trace_memory_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnTraceStoreA",  "Store A"),
            MenuItem("btnTraceShowA",   "Show A"),
            MenuItem("btnTraceStoreB",  "Store B"),
            MenuItem("btnTraceShowB",   "Show B"),
            MenuItem("btnTraceAMinusB", "A − B"),
            MenuItem("btnTraceClear",   "Clear\nAll"),
        ]

    def _create_averaging_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnAvgOff",   "Average\nOff"),
            MenuItem("btnAvgExp2",  "Exp ×2"),
            MenuItem("btnAvgExp4",  "Exp ×4"),
            MenuItem("btnAvgExp8",  "Exp ×8"),
            MenuItem("btnAvgExp16", "Exp ×16"),
            MenuItem("btnAvgLin4",  "Lin ×4"),
            MenuItem("btnAvgLin16", "Lin ×16"),
            MenuItem("btnAvgLin64", "Lin ×64"),
        ]

    def _create_analysis_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnFFT",           "FFT",          sub_menu=self._create_fft_menu()),
            MenuItem("btnPSD",           "PSD\n(dB/Hz)"),
            MenuItem("btnConstellation", "Constellation", sub_menu=self._create_constellation_menu()),
            MenuItem("btnDutyCycle",     "Duty\nCycle"),
        ]

    def _create_fft_menu(self) -> List[MenuItem]:
        items = [
            MenuItem("btnWindow",     "Window",      sub_menu=self._create_window_menu()),
            MenuItem("btnSampleSize", "Sample Size", sub_menu=self._create_sample_size_menu()),
        ]
        if isinstance(getattr(self.parent, 'current_source', None), MicrophoneSamplesDataSource):
            items.append(MenuItem("btnAudioChannel", "Channel", sub_menu=self._create_audio_channel_menu()))
        return items

    def _create_constellation_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnConstellationDensity", "Density"),
            MenuItem("btnConstellationScatter", "Scatter"),
            MenuItem("btnConstModulation", "Modulation", sub_menu=self._create_const_modulation_menu()),
            MenuItem("btnConstRange",      "Range",      sub_menu=self._create_const_range_menu()),
            MenuItem("btnConstPoints",     "Points",     sub_menu=self._create_const_points_menu()),
        ]

    def _create_const_modulation_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnConstBPSK",  "BPSK"),
            MenuItem("btnConstQPSK",  "QPSK"),
            MenuItem("btnConst8PSK",  "8PSK"),
            MenuItem("btnConst16QAM", "16QAM"),
            MenuItem("btnConst64QAM", "64QAM"),
        ]

    def _create_const_range_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnConstRange15", "±1.5"),
            MenuItem("btnConstRange20", "±2.0"),
            MenuItem("btnConstRange30", "±3.0"),
        ]

    def _create_const_points_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnConstPoints500",  "500"),
            MenuItem("btnConstPoints2K",   "2k"),
            MenuItem("btnConstPoints5K",   "5k"),
            MenuItem("btnConstPoints10K",  "10k"),
        ]

    def _create_audio_channel_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnAudioMono",   "Mono"),
            MenuItem("btnAudioLeft",   "Left"),
            MenuItem("btnAudioRight",  "Right"),
            MenuItem("btnAudioStereo", "Stereo"),
        ]

    def _create_window_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnHamming", "Hamming"),
            MenuItem("btnHanning", "Hanning"),
            MenuItem("btnRectangle", "Rectangle"),
        ]

    def _create_sample_size_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnFFT512", "512"),
            MenuItem("btnFFT1024", "1024"),
            MenuItem("btnFFT2048", "2048"),
            MenuItem("btnFFT4096", "4096"),
        ]

    def _create_cal_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnCalSet",    "Set\nCal"),
            MenuItem("btnCalOffset", "Offset"),
            MenuItem("btnCalClear",  "Clear\nCal"),
        ]

    def _create_preset_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnPresetRecall", "Recall",     sub_menu=self._create_preset_slots_menu()),
            MenuItem("btnPresetSave",   "Save",       sub_menu=self._create_preset_slots_menu()),
            MenuItem("btnPresetName",   "Name\nSlot", sub_menu=self._create_preset_slots_menu()),
            MenuItem("btnPresetDelete", "Delete",     sub_menu=self._create_preset_slots_menu()),
        ]

    def _create_preset_slots_menu(self) -> List[MenuItem]:
        pm = getattr(self.parent, 'preset_manager', None)
        return [
            MenuItem(f"btnPresetSlot{i}", pm.slot_label(i) if pm else f"Slot {i}")
            for i in range(1, 9)
        ]

    def update_item_label(self, menu_name: str, item_id: str, new_label: str) -> None:
        """Update a menu item label and refresh soft buttons if that menu is active."""
        for item in self.menus.get(menu_name, []):
            if item.id == item_id:
                item.label = new_label
                break
        self._update_soft_buttons()

    def select_menu(self, menu_name: str):
        """Select a menu by name and update the soft buttons."""
        self.menu_stack.append(self.current_menu)

        # Dynamically regenerate source-dependent menus
        if menu_name == "Span":
            self.menus["Span"] = self._create_span_menu()
        if menu_name == "BW":
            self.menus["BW"] = self._create_bw_menu()
        if menu_name == "FFT":
            self.menus["FFT"] = self._create_fft_menu()
        if menu_name == "RF\nGain":
            self.menus["RF\nGain"] = self._create_rf_gain_menu()

        # Preset submenus: set pending operation and rebuild slot labels
        _preset_ops = {
            "Recall":     "recall",
            "Save":       "save",
            "Name\nSlot": "name",
            "Delete":     "delete",
        }
        if menu_name in _preset_ops:
            pm = getattr(self.parent, 'preset_manager', None)
            if pm:
                pm.set_pending_op(_preset_ops[menu_name])
            self.menus[menu_name] = self._create_preset_slots_menu()

        self.current_menu = self.menus.get(menu_name, [])
        if menu_name not in self.menus:
            logger.warning(f"Menu '{menu_name}' not found")
        self._current_page = 0
        self._update_soft_buttons()
        logger.debug(f"Selected menu: {menu_name}")

    def handle_button_press(self, index: int):
        """Handle a button press event."""
        n = len(self.soft_buttons)

        if self._needs_pagination():
            if index == n - 1:            # button 8 = page navigator, cycle forward, wrap
                self._current_page = (self._current_page + 1) % self._n_pages()
                self._update_soft_buttons()
                return
            actual = self._current_page * self.ITEMS_PER_PAGE + index
            if actual >= len(self.current_menu):
                return
            menu_item = self.current_menu[actual]
        else:
            if index >= len(self.current_menu):
                return
            menu_item = self.current_menu[index]

        try:
            self.on_selection(menu_item)
            logger.debug(f"on_selection called for {menu_item.id}")
        except Exception as e:
            logger.error(f"Error in on_selection for {menu_item.id}: {e}")
        
    def _n_pages(self) -> int:
        return max(1, math.ceil(len(self.current_menu) / self.ITEMS_PER_PAGE))

    def _needs_pagination(self) -> bool:
        # Pagination only when the menu won't fit in all 8 buttons
        return len(self.current_menu) > len(self.soft_buttons)

    def _update_soft_buttons(self):
        """Update the soft buttons to reflect the current menu."""
        n = len(self.soft_buttons)

        if self._needs_pagination():
            # Paginated: ITEMS_PER_PAGE items on buttons 1-7, button 8 = page nav
            n_pages    = self._n_pages()
            page       = self._current_page
            start      = page * self.ITEMS_PER_PAGE
            page_items = self.current_menu[start : start + self.ITEMS_PER_PAGE]
            if page < n_pages - 1:
                nav_label = f"More ▶\n({page + 1} of {n_pages})"
            else:
                nav_label = f"◀ Prev\n({page + 1} of {n_pages})"

            for i, button in enumerate(self.soft_buttons):
                if not button:
                    continue
                if i < len(page_items):
                    button.setText(page_items[i].label)
                    button.setEnabled(True)
                elif i == n - 1:           # button 8 = page navigator
                    button.setText(nav_label)
                    button.setEnabled(True)
                else:
                    button.setText("")
                    button.setEnabled(False)
        else:
            # Non-paginated: items fill whatever slots they need (up to all 8)
            for i, button in enumerate(self.soft_buttons):
                if not button:
                    continue
                if i < len(self.current_menu):
                    button.setText(self.current_menu[i].label)
                    button.setEnabled(True)
                    logger.debug(f"Soft button {i+1} set to: {self.current_menu[i].label}")
                else:
                    button.setText("")
                    button.setEnabled(False)
                    logger.debug(f"Soft button {i+1} disabled")

    def select_root_menu(self, menu_name: str):
        """Navigate to a top-level menu with no parent.

        Used by hard buttons (Frequency, Span, Marker, etc.).  The stack is
        cleared so ▲ Menu Up never shows at root level, and entering a
        submenu from here puts only this menu on the stack — not anything
        from a previous unrelated tree.
        """
        self.menu_stack.clear()
        self._current_page = 0
        self.select_menu(menu_name)
        # select_menu pushed the stale previous menu; discard it so
        # root menus have no parent and ▲ Menu Up is not shown.
        if self.menu_stack:
            self.menu_stack.pop()
        self._update_soft_buttons()

    def go_back(self):
        """Navigate back to the previous menu, or clear all soft keys if already at root."""
        if self.menu_stack:
            self.current_menu = self.menu_stack.pop()
        else:
            self.current_menu = []
        self._current_page = 0
        self._update_soft_buttons()
        logger.debug("Navigated back to previous menu")