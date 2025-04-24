from typing import Callable
from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtCore import Qt

class Keypad:
    data_buttons: list[QPushButton] = []
    ui: QObject = None

    button_mhz: QPushButton = None
    button_dot: QPushButton = None
    button_ghz: QPushButton = None
    button_khz: QPushButton = None
    button_hz: QPushButton = None
    button_minus: QPushButton = None

    data_input: str = ""
    on_change: Callable[[str], None] = None
    on_frequency_select: Callable[[int], None] = None

    def __init__(self, ui: QObject, on_change: Callable[[str], None], on_frequency_select: Callable[[int], None]):
        self.ui = ui
        self.on_change = on_change
        self.on_frequency_select = on_frequency_select

        self.data_buttons = [ui.findChild(QPushButton, f"button_data_{i}") for i in range(0, 10)]
        self.button_mhz = ui.findChild(QPushButton, "button_mhz")
        self.button_dot = ui.findChild(QPushButton, "button_dot")
        self.button_ghz = ui.findChild(QPushButton, "button_ghz")
        self.button_khz = ui.findChild(QPushButton, "button_khz")
        self.button_hz = ui.findChild(QPushButton, "button_hz")
        self.button_minus = ui.findChild(QPushButton, "button_minus")

        self.bind_ui()

    def bind_ui(self):
        """Bind UI buttons to their respective handlers."""
        for i, button in enumerate(self.data_buttons):
            button.pressed.connect(self.handle_data_character(i))

        self.button_minus.pressed.connect(self.handle_data_character("-"))
        self.button_dot.pressed.connect(self.handle_data_character("."))

        self.button_mhz.pressed.connect(self.on_frequency_select_inner(1e6))
        self.button_ghz.pressed.connect(self.on_frequency_select_inner(1e9))
        self.button_khz.pressed.connect(self.on_frequency_select_inner(1e3))
        self.button_hz.pressed.connect(self.on_frequency_select_inner(1))

    def reset(self):
        """Clear the current input data."""
        self.data_input = ""
        self.on_change(None)

    def on_frequency_select_inner(self, multiplier: int):
        """Convert input to Hz and trigger frequency selection."""
        def on_frequency_select():
            try:
                freq_hz = float(self.data_input)
                freq_hz = int(freq_hz * multiplier)
                self.on_frequency_select(freq_hz)
            except ValueError:
                self.ui.status_label.setText("Invalid frequency input")
                return
        return on_frequency_select

    def handle_data_character(self, button_index: str | int):
        """Handle input from numeric or special character buttons."""
        def handle_button_inner():
            if button_index == "-":
                if len(self.data_input) > 0:
                    self.data_input = self.data_input[:-1]  # Delete last character
                elif self.data_input != "-":
                    self.data_input = "-"  # Prepend negative sign
                self.on_change(self.data_input)
                return
            
            if button_index == ".":
                if "." in self.data_input:
                    return
                if len(self.data_input) == 0 or self.data_input == "-":
                    self.data_input += "0."
                else:
                    self.data_input += "."
                self.on_change(self.data_input)
                return

            self.data_input += str(button_index)
            self.on_change(self.data_input)

        return handle_button_inner

    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard input for numeric and special keys."""
        button_index = event.key() - Qt.Key.Key_0
        if button_index >= 0 and button_index < 10:
            self.handle_data_character(button_index)()
            return

        if event.key() == Qt.Key.Key_Minus:
            self.handle_data_character("-")()
            return

        if event.key() == Qt.Key.Key_Period:
            self.handle_data_character(".")()
            return
