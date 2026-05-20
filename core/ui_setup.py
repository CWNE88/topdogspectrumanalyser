from PyQt6.QtWidgets import QStackedWidget, QPushButton, QSizePolicy, QWidget, QLabel, QFrame
from PyQt6.QtCore import QTimer, Qt
from displays.two_dimension import TwoD
from displays.three_dimension import ThreeD
from displays.waterfall import Waterfall
from displays.surface import Surface
from displays.ribbon import RibbonWidget
from displays.density_display import DensityDisplay
from displays.logo import Logo
from displays.constellation_2d import Constellation2D
from displays.constellation_3d import Constellation3D
from displays.zero_span import ZeroSpan
from menu.menu_manager import MenuManager
from input.keypad import Keypad
import logging

class UISetup:
    def __init__(self, main_window):
        self.main_window = main_window
        self._layout_vertical = False

        # Initialise display widgets (created once, survive layout toggles)
        self.main_window.two_d_widget = TwoD()
        self.main_window.three_d_widget = ThreeD()
        self.main_window.waterfall_widget = Waterfall()
        self.main_window.surface_widget = Surface()
        self.main_window.ribbon_widget = RibbonWidget()
        self.main_window.density_widget = DensityDisplay()
        self.main_window.logo_widget = Logo()
        self.main_window.constellation_2d_widget = Constellation2D()
        self.main_window.constellation_3d_widget = Constellation3D()
        self.main_window.zero_span_widget = ZeroSpan()

        self.main_window.stacked_widget = QStackedWidget()
        self.main_window.stacked_widget.addWidget(self.main_window.two_d_widget)             # Index 0
        self.main_window.stacked_widget.addWidget(self.main_window.three_d_widget)           # Index 1
        self.main_window.stacked_widget.addWidget(self.main_window.waterfall_widget)         # Index 2
        self.main_window.stacked_widget.addWidget(self.main_window.surface_widget)           # Index 3
        self.main_window.stacked_widget.addWidget(self.main_window.logo_widget)              # Index 4
        self.main_window.stacked_widget.addWidget(self.main_window.constellation_2d_widget)  # Index 5
        self.main_window.stacked_widget.addWidget(self.main_window.constellation_3d_widget)  # Index 6
        self.main_window.stacked_widget.addWidget(self.main_window.zero_span_widget)         # Index 7
        self.main_window.stacked_widget.addWidget(self.main_window.ribbon_widget)            # Index 8
        self.main_window.stacked_widget.addWidget(self.main_window.density_widget)            # Index 9

        self.main_window.graphical_display.layout().addWidget(self.main_window.stacked_widget)
        self.main_window.stacked_widget.setCurrentIndex(self.main_window.current_stacked_index)
        self._setup_output_area()
        QTimer.singleShot(0, self._fit_status_box_to_remainder)

        # Initialise menu and keypad
        self.main_window.menu = MenuManager(self.main_window.display_manager.on_menu_selection, self.main_window)
        self.main_window.keypad = Keypad(self.main_window, self.main_window.frequency_manager.on_keypad_change,
                                         self.main_window.frequency_manager.on_frequency_select)

        # Initialise timers — started after window.show() via start_timers()
        self.main_window.logo_timer = QTimer(self.main_window)
        self.main_window.logo_timer.timeout.connect(self.main_window.logo_widget.update_rotation)

        self.main_window.timer = QTimer(self.main_window)
        self.main_window.timer.timeout.connect(self.main_window.display_manager.update_data)

        self._connect_buttons()

        # Disable buttons initially (no source connected yet)
        self.main_window.button_peak_search.setEnabled(False)
        self.main_window.button_max_hold.setEnabled(False)
        self.main_window.button_hold.setEnabled(False)

        self._set_no_focus_on_buttons()

    def _connect_buttons(self):
        mw = self.main_window
        mw.button_frequency.pressed.connect(lambda: mw.menu.select_root_menu("Frequency"))
        mw.button_frequency.setToolTip("Shortcut key: F")
        mw.button_frequency.setToolTipDuration(-1)
        def _span_pressed():
            from datasources.base import SampleDataSource
            if isinstance(mw.current_source, SampleDataSource):
                mw.status_label.setText("Not applicable in sample mode.\nUse BW to change sample rate")
            else:
                mw.menu.select_root_menu("Span")
        mw.button_span.pressed.connect(_span_pressed)
        mw.button_span.setToolTip("Shortcut key: S")
        mw.button_amplitude.pressed.connect(lambda: mw.menu.select_root_menu("Amplitude"))
        mw.button_amplitude.setToolTip("Shortcut key: A")
        mw.button_source_1.pressed.connect(lambda: mw.menu.select_root_menu("Input"))
        mw.button_source_1.setToolTip("Shortcut key: I")
        mw.buttonmarker1.pressed.connect(lambda: mw.menu.select_root_menu("Marker"))
        mw.buttonmarker1.setToolTip("Shortcut key: K")
        mw.buttonmarker2.setText("")
        mw.button_instrument_10.pressed.connect(lambda: mw.menu.select_root_menu("Analysis"))
        mw.button_instrument_10.setToolTip("Shortcut key: N")
        mw.buttoncontrol6.pressed.connect(lambda: mw.menu.select_root_menu("Display"))
        mw.buttoncontrol6.setToolTip("Shortcut key: D")
        mw.button_preset.pressed.connect(lambda: mw.menu.select_root_menu("Preset"))
        mw.button_export_image.pressed.connect(lambda: mw.menu.select_root_menu("Export\nImage"))

        # BW/Display group: top row = BW, Display Type, Trace; bottom row blanked
        mw.button_2d.setText("BW")
        mw.button_2d.pressed.connect(lambda: mw.menu.select_root_menu("BW"))
        mw.button_2d.setToolTip("Shortcut key: W")
        mw.button_3d.setText("Display\nType")
        mw.button_3d.pressed.connect(lambda: mw.menu.select_root_menu("Display\nType"))
        mw.button_waterfall.setText("Trace")
        mw.button_waterfall.pressed.connect(lambda: mw.menu.select_root_menu("Trace"))
        mw.button_waterfall.setToolTip("Shortcut key: T")
        for btn_name in ("button_surface", "button_ribbon", "button_display_spare"):
            getattr(mw, btn_name).setText("")

        mw.button_hold.pressed.connect(mw.display_manager.toggle_hold)
        mw.button_hold.setToolTip("Shortcut key: Space")
        mw.button_max_hold.pressed.connect(mw.display_manager.toggle_max_peak_search)
        mw.button_max_hold.setToolTip("Shortcut key: X")
        mw.button_peak_search.pressed.connect(mw.display_manager.toggle_peak_search)
        mw.button_peak_search.setToolTip("Shortcut key: P")

        for i in range(1, 9):
            button = getattr(mw, f"button_soft_{i}", None)
            if button:
                button.pressed.connect(lambda idx=i-1: mw.menu.handle_button_press(idx))
                button.setToolTip(f"Shortcut key: F{i}")

        mw.dial.valueChanged.connect(mw.handle_dial_change)
        mw.last_dial_value = mw.dial.value()

        mw.button_up.pressed.connect(mw.handle_frequency_up)
        mw.button_down.pressed.connect(mw.handle_frequency_down)

        if hasattr(mw, 'button_return'):
            mw.button_return.pressed.connect(mw.menu.go_back)
            mw.button_return.setToolTip("Shortcut key: Esc")

        mw.button_vert_horiz.pressed.connect(self.toggle_layout)
        mw.button_vert_horiz.setToolTip("Shortcut key: V")

        def _on_cal():
            mw.menu.select_root_menu("Cal")
            mw.display_manager.cal_show_status()

        mw.buttonconfig.setText("Cal")
        mw.buttonconfig.pressed.connect(_on_cal)

    def toggle_layout(self):
        """Toggle between horizontal and vertical layout by rearranging the existing
        layout hierarchy — no widgets are recreated, so no button references go stale
        and the menu/keypad state is fully preserved across the toggle."""
        from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout
        mw = self.main_window
        self._layout_vertical = not self._layout_vertical

        central = mw.centralWidget()
        outer = central.layout()   # outermost QHBoxLayout (horizontalLayout_2)

        # Verify expected structure before touching anything
        if outer is None or outer.count() == 0:
            return
        inner_wrapper = outer.itemAt(0)
        if inner_wrapper is None:
            return
        inner = inner_wrapper.layout()   # current inner layout (HBox or VBox)
        if inner is None or inner.count() < 2:
            return

        # Pull both items out of the inner layout
        display_item = inner.takeAt(0)   # display column (QVBoxLayout: graphical + frame_2)
        frame_item   = inner.takeAt(0)   # control panel (QFrame)

        # Remove empty inner from outer and schedule it for deletion
        outer.takeAt(0)
        inner.deleteLater()

        # Build replacement inner with correct orientation
        if self._layout_vertical:
            new_inner = QVBoxLayout()
            mw.frame.setMaximumWidth(16777215)
            mw.frame.setMaximumHeight(700)
        else:
            new_inner = QHBoxLayout()
            mw.frame.setMaximumWidth(720)
            mw.frame.setMaximumHeight(16777215)

        new_inner.addItem(display_item)
        new_inner.addItem(frame_item)
        outer.addLayout(new_inner)

        QTimer.singleShot(0, self._fit_status_box_to_remainder)

    def _setup_output_area(self):
        """Add a dedicated marker readout label below status_label in the output box."""
        layout = self.main_window.horizontalLayoutWidget.layout()
        layout.setContentsMargins(4, 4, 4, 2)
        layout.setSpacing(2)

        sl = self.main_window.status_label
        sl.setWordWrap(False)
        sl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        sl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        mrl = QLabel()
        mrl.setWordWrap(True)
        mrl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        mrl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        mrl.setFont(sl.font())
        mrl.setStyleSheet("color: #e0e0e0;")
        layout.insertWidget(1, mrl)
        self.main_window.marker_readout_label = mrl

    def _fit_status_box_to_remainder(self):
        """Stretch the status/output box to fill everything below the panel content."""
        frame = self.main_window.frame
        hlw = self.main_window.horizontalLayoutWidget
        GAP = 8

        content_bottom = 0
        for child in frame.children():
            if not isinstance(child, QWidget) or child is hlw:
                continue
            b = child.geometry().y() + child.geometry().height()
            if b > content_bottom:
                content_bottom = b

        top = content_bottom + GAP
        available = frame.height() - top - GAP
        if available > 60:
            hlw.setGeometry(hlw.x(), top, hlw.width(), available)

    def _set_no_focus_on_buttons(self):
        """Set NoFocus on buttons and interactive display widgets so keyboard shortcuts always reach MainWindow."""
        for widget in self.main_window.findChildren(QPushButton):
            widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        try:
            from pyqtgraph.opengl import GLViewWidget
            for widget in self.main_window.findChildren(GLViewWidget):
                widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        except ImportError:
            pass

        try:
            from pyqtgraph import PlotWidget
            for widget in self.main_window.findChildren(PlotWidget):
                widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        except ImportError:
            pass

        logging.debug("Set NoFocus policy on buttons and display widgets")

    def start_timers(self):
        """Start display and logo timers. Call after window.show() to avoid pre-visible GPU work."""
        self.main_window.logo_timer.start(20)
        self.main_window.timer.start(20)

    def initialise_labels(self):
        mw = self.main_window
        if mw.current_source is not None:
            from core.source_manager import SourceManager
            display_name = SourceManager.SOURCE_DISPLAY_NAMES.get(mw.current_source_id, mw.current_source_id or "")
            mw.output_source.setText(f"Input: {display_name}")
        else:
            mw.output_source.setText("Input: None")
        mw.output_centre_freq.setText("-")
        mw.output_span.setText("-")
        mw.output_start_freq.setText("-")
        mw.output_stop_freq.setText("-")
        mw.output_res_bw.setText("-")
        mw.output_sample_rate.setText("-")
        mw.output_sample_size.setText("-")
        mw.output_gain.setText("-")
        if mw.current_source is None:
            mw.status_label.setText(
                "<span style='color:#4db8ff;'>Top Dog Spectrum Analyser<br>"
                "Paul Stanley<br>"
                "Copyright 2026</span><br><br>"
                "<span style='color:#ffffff;'>Select input to begin</span>"
            )
            mw.status_label.setTextFormat(Qt.TextFormat.RichText)
        mw.input_value.setText("")
        logging.debug("Labels initialised")
