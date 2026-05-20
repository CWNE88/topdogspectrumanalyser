"""Export functionality for saving display images and full window screenshots."""

import logging
from utils.constants import DisplayMode

logger = logging.getLogger(__name__)


class ExportManager:
    """Handles all image export operations for the spectrum analyser."""

    _EXPORT_FMT = {
        'png':  ('PNG',  '.png'),
        'jpeg': ('JPEG', '.jpg'),
        'svg':  ('SVG',  '.svg'),
    }

    def __init__(self, main_window):
        self.mw = main_window

    @staticmethod
    def _ensure_ext(filename: str, ext: str) -> str:
        """Append extension if the user omitted it (common on Linux dialogs)."""
        return filename if filename.lower().endswith(ext) else filename + ext

    @staticmethod
    def _save_pixmap(pixmap, filename: str, qt_fmt: str) -> None:
        """Save pixmap and raise if Qt reports failure."""
        if not pixmap.save(filename, qt_fmt):
            raise RuntimeError(
                f"QPixmap.save() failed — check path and format ({filename!r})"
            )

    def export_display(self, fmt: str) -> None:
        """Export the active display in the requested format (png / jpeg / svg)."""
        import numpy as np
        from PyQt6.QtWidgets import QFileDialog
        from PyQt6.QtGui import QImage, QPixmap
        mw = self.mw
        qt_fmt, ext = self._EXPORT_FMT.get(fmt, ('PNG', '.png'))
        filters = {
            'png':  "PNG Image (*.png)",
            'jpeg': "JPEG Image (*.jpg)",
            'svg':  "SVG Vector (*.svg)",
        }
        mode = mw.current_stacked_index
        was_paused = mw.paused

        try:
            if mode == DisplayMode.SURFACE:
                mw.paused = True

            filename, _ = QFileDialog.getSaveFileName(
                mw, "Export Display", "", filters[fmt]
            )
            if not filename:
                return
            filename = self._ensure_ext(filename, ext)

            if fmt == 'svg':
                if mode != DisplayMode.TWO_D:
                    mw.status_label.setText("SVG export only available for 2D display")
                    return
                from pyqtgraph.exporters import SVGExporter
                SVGExporter(mw.two_d_widget.plot_widget.plotItem).export(filename)

            elif mode == DisplayMode.WATERFALL:
                wf = mw.waterfall_widget
                arr = wf.waterfall_array
                if arr is None or arr.size == 0:
                    raise RuntimeError("No waterfall data to export yet")
                norm = np.clip(
                    (arr - wf.wf_min_db) / max(wf.wf_max_db - wf.wf_min_db, 1e-9),
                    0.0, 1.0,
                )
                lut  = wf._lut_rgba
                rgba = np.ascontiguousarray(
                    lut[(norm * 255).astype(np.uint8)], dtype=np.uint8
                )
                h, w = rgba.shape[:2]
                qi = QImage(bytes(rgba), w, h, w * 4, QImage.Format.Format_RGBA8888)
                if qi.isNull():
                    raise RuntimeError("QImage construction failed")
                self._save_pixmap(QPixmap.fromImage(qi), filename, qt_fmt)

            elif mode == DisplayMode.SURFACE:
                raw = mw.surface_widget.canvas.render()
                if raw is None or raw.ndim < 3 or 0 in raw.shape:
                    raise RuntimeError(
                        f"canvas.render() returned invalid data "
                        f"(shape={getattr(raw, 'shape', None)})"
                    )
                h, w = raw.shape[:2]
                img_data = bytes(np.ascontiguousarray(raw, dtype=np.uint8))
                qi = QImage(img_data, w, h, w * 4, QImage.Format.Format_RGBA8888)
                if qi.isNull():
                    raise RuntimeError("QImage construction failed")
                self._save_pixmap(QPixmap.fromImage(qi), filename, qt_fmt)

            else:
                widget_map = {
                    DisplayMode.TWO_D:     mw.two_d_widget,
                    DisplayMode.THREE_D:   mw.three_d_widget,
                    DisplayMode.RIBBON:    mw.ribbon_widget,
                    DisplayMode.ZERO_SPAN: mw.zero_span_widget,
                    DisplayMode.DENSITY:   mw.density_widget,
                }
                self._save_pixmap(
                    widget_map.get(mode, mw.stacked_widget).grab(), filename, qt_fmt
                )

            mw.status_label.setText(f"Exported: {filename.rsplit('/', 1)[-1]}")

        except Exception as e:
            mw.status_label.setText(f"Export failed: {e}")
            logger.error(f"Export display error: {e}")
        finally:
            mw.paused = was_paused

    def export_window(self, fmt: str) -> None:
        """Export the entire application window."""
        from PyQt6.QtWidgets import QFileDialog
        mw = self.mw
        qt_fmt, ext = self._EXPORT_FMT.get(fmt, ('PNG', '.png'))
        filters = {'png': "PNG Image (*.png)", 'jpeg': "JPEG Image (*.jpg)"}
        filename, _ = QFileDialog.getSaveFileName(
            mw, "Export Window", "", filters[fmt]
        )
        if not filename:
            return
        filename = self._ensure_ext(filename, ext)
        try:
            self._save_pixmap(mw.grab(), filename, qt_fmt)
            mw.status_label.setText(f"Exported: {filename.rsplit('/', 1)[-1]}")
        except Exception as e:
            mw.status_label.setText(f"Export failed: {e}")
            logger.error(f"Export window error: {e}")
