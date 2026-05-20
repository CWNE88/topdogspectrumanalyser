import numpy as np
from PyQt6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ZeroSpan(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('k')
        self.plot_widget.setLabel('left', 'Amplitude')
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.setMouseEnabled(x=True, y=True)

        self.live_plot = self.plot_widget.plot(pen=pg.mkPen('g', width=1), name='Signal')

        # Draggable trigger level line — shown in triggered modes
        self._trigger_line: Optional[pg.InfiniteLine] = None
        self._trigger_level: float = 0.0
        self._trigger_mode: str = "free_run"
        self._drag_callback = None

        self._first_data = True

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

        logger.debug("ZeroSpan: widget initialised")

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------

    def set_amplitude(self, ref_level: float, range_db: float) -> None:
        pass  # Y axis is user-controlled via mouse

    def set_trigger_mode(self, mode: str) -> None:
        self._trigger_mode = mode
        self._show_trigger_line(mode != "free_run")

    def set_trigger_level(self, level: float) -> None:
        self._trigger_level = level
        if self._trigger_line is not None:
            self._trigger_line.setPos(level)
        if self._trigger_mode != "free_run":
            self._show_trigger_line(True)

    def update_zero_span_data(self, time_s: np.ndarray, samples: np.ndarray) -> None:
        if len(time_s) == 0:
            return
        self.live_plot.setData(time_s, samples)
        # Auto-range on first frame only, then leave control to user
        if self._first_data:
            self.plot_widget.autoRange()
            self._first_data = False

    def update_widget_data(self, live_power_levels, max_power_levels, frequency_bins, min_levels=None):
        pass  # not used in zero span mode

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _show_trigger_line(self, show: bool) -> None:
        if show:
            if self._trigger_line is None:
                self._trigger_line = pg.InfiniteLine(
                    angle=0, movable=True,
                    pen=pg.mkPen(color='r', width=1),
                    label='Trigger', labelOpts={'color': 'r', 'position': 0.05}
                )
                self._trigger_line.setPos(self._trigger_level)
                self._trigger_line.sigPositionChangeFinished.connect(self._on_trigger_dragged)
                self.plot_widget.addItem(self._trigger_line)
            self._trigger_line.setVisible(True)
        elif self._trigger_line is not None:
            self._trigger_line.setVisible(False)

    def set_drag_callback(self, cb) -> None:
        self._drag_callback = cb

    def _on_trigger_dragged(self, line) -> None:
        self._trigger_level = float(line.value())
        if self._drag_callback:
            self._drag_callback(self._trigger_level)
