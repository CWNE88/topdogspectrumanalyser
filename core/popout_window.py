"""Pop-out window for display widgets."""

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QKeyEvent
from utils.frequency_helpers import format_hz
import logging


class PopoutWindow(QMainWindow):
    """A pop-out window that can display a single widget."""

    def __init__(self, parent=None, title="Display", display_mode=None):
        """Initialise the pop-out window.

        Args:
            parent: Parent widget (MainWindow instance).
            title: Window title.
            display_mode: The display mode index (for creating clone widgets).
        """
        super().__init__(parent)
        self.parent_window = parent
        self.popped_widget = None
        self.original_parent = None
        self.display_mode = display_mode
        self.is_clone_widget = False  # Track if we created a clone

        # Window configuration
        self.setWindowTitle(title)
        self.resize(1200, 800)

        # Create central widget with layout
        central_widget = QWidget()
        self.layout = QVBoxLayout(central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(central_widget)

        logging.debug("PopoutWindow: Initialised")

    def create_clone_widget(self, widget_class):
        """Create a clone of a widget for OpenGL-based displays.

        Args:
            widget_class: The class of the widget to clone.

        Returns:
            The newly created widget instance.
        """
        clone = widget_class()
        self.popped_widget = clone
        self.is_clone_widget = True
        self.layout.addWidget(clone)
        clone.show()
        logging.debug(f"PopoutWindow: Created clone widget {widget_class.__name__}")
        return clone

    def set_widget(self, widget: QWidget, original_parent: QWidget):
        """Set the widget to display in this window.

        Args:
            widget: The widget to display.
            original_parent: The original parent of the widget.
        """
        self.popped_widget = widget
        self.original_parent = original_parent
        self.is_clone_widget = False

        # Reparent widget to this window
        self.layout.addWidget(widget)
        widget.show()

        logging.debug(f"PopoutWindow: Widget {widget.__class__.__name__} added")

    def update_title(self) -> None:
        """Rebuild the window title from current source and frequency state."""
        mw = self.parent_window
        if mw is None:
            return

        src_mgr = getattr(mw, 'source_manager', None)
        if src_mgr is not None:
            src_name = src_mgr.SOURCE_DISPLAY_NAMES.get(
                src_mgr.last_source_type, src_mgr.last_source_type or "None"
            )
        else:
            src_name = "None"

        freq = getattr(mw, 'frequency', None)
        if freq is None:
            self.setWindowTitle(f"Input: {src_name}")
            return

        def _fmt(hz):
            return "—" if hz is None else format_hz(hz)

        title = (
            f"Input: {src_name}"
            f"  Start Freq: {_fmt(freq.start)}"
            f"  Centre Freq: {_fmt(freq.centre)}"
            f"  Stop Freq: {_fmt(freq.stop)}"
            f"  Span: {_fmt(freq.span)}"
        )
        self.setWindowTitle(title)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard events."""
        key  = event.key()
        mods = event.modifiers()

        # Alt+Enter / Alt+Return: return display to main window (same as opening)
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and mods & Qt.KeyboardModifier.AltModifier:
            if self.parent_window:
                self.parent_window.return_widget_from_popout()
            event.accept()
            return

        # Escape: return to main window
        if key == Qt.Key.Key_Escape:
            if self.parent_window:
                self.parent_window.return_widget_from_popout()
            event.accept()
            return

        if self.parent_window:
            if key == Qt.Key.Key_P:
                self.parent_window.display_manager.toggle_peak_search()
                event.accept()
                return
            if key == Qt.Key.Key_X:
                self.parent_window.display_manager.toggle_max_peak_search()
                event.accept()
                return
            if key == Qt.Key.Key_D:
                self.parent_window.status_label.setText("Cannot cycle displays while popped out")
                event.accept()
                return

        super().keyPressEvent(event)

    def closeEvent(self, event):
        """Handle window close event.

        Args:
            event: The close event.
        """
        # Return widget to main window when closing
        if self.parent_window and self.popped_widget:
            self.parent_window.return_widget_from_popout()
        event.accept()
