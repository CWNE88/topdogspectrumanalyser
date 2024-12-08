from typing import Callable, TYPE_CHECKING, Literal, Union
from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QPushButton, QToolButton, QAbstractButton
from PyQt6.QtGui import QKeyEvent, QKeySequence
from PyQt6.QtCore import Qt

if TYPE_CHECKING:
    import main

class Keypad:
    data_buttons: list[QPushButton] = []
    ui: 'main.MainWindow' = None

    button_mhz: QPushButton = None
    button_dot: QPushButton = None
    button_ghz: QPushButton = None
    button_khz: QPushButton = None
    button_hz: QPushButton = None
    button_minus: QPushButton = None

    data_input: str = ""
    on_change: Callable[[str], None] = None
    on_frequency_select: Callable[[int], None] = None

    def __init__(self, ui: 'main.MainWindow', on_change: Callable[[str], None], on_frequency_select: Callable[[int], None]):
        self.ui = ui
        self.on_change = on_change
        self.on_frequency_select = on_frequency_select

        self.data_buttons = [ui.findChild(QAbstractButton, f"button_data_{i}") for i in range(0,10)]
        self.button_mhz = ui.findChild(QAbstractButton, "button_mhz")
        self.button_dot = ui.findChild(QAbstractButton, "button_dot")
        self.button_ghz = ui.findChild(QAbstractButton, "button_ghz")
        self.button_khz = ui.findChild(QAbstractButton, "button_khz")
        self.button_hz = ui.findChild(QAbstractButton, "button_hz")
        self.button_minus = ui.findChild(QAbstractButton, "button_minus")

        self.bind_ui()

    def bind_ui(self):
        for i, button in enumerate(self.data_buttons):
            button.pressed.connect(self.handle_data_character(i))

        self.button_minus.pressed.connect(self.handle_data_character("-"))
        self.button_dot.pressed.connect(self.handle_data_character("."))

        self.button_mhz.pressed.connect(self.on_frequency_select_inner(1e6))
        self.button_ghz.pressed.connect(self.on_frequency_select_inner(1e9))
        self.button_khz.pressed.connect(self.on_frequency_select_inner(1e3))
        self.button_hz.pressed.connect(self.on_frequency_select_inner(1))

    def reset(self):
        self.data_input = ""
        self.on_change(None)

    def on_frequency_select_inner(self, multiplier: int):
        def on_frequency_select():
            try:
                freq_hz = float(self.data_input)
                freq_hz = int(freq_hz * multiplier)
            except:
                return
            
            self.on_frequency_select(freq_hz)
        return on_frequency_select

    def handle_data_character(self, button_index: str | int):
        def handle_button_inner():
            if button_index == "-":
                if len(self.data_input) > 0:
                    self.data_input = self.data_input[:-1]
                    self.on_change(self.data_input)
                    return
            
            if button_index == ".":
                if "." in self.data_input:
                    return
                if len(self.data_input) == 0:
                    self.data_input += "0."
                else:
                    self.data_input += "."
                self.on_change(self.data_input)
                return

            self.data_input += str(button_index)
            self.on_change(self.data_input)

        return handle_button_inner


    def keyPressEvent(self, event: QKeyEvent, mode: Union[Literal['centre', 'start', 'stop', 'span'], None]):
        # find menu item that corresponds to the key
        # that was pressed

        button_index = event.key() - Qt.Key.Key_0
        if button_index >= 0 and button_index <= 9:
            self.handle_data_character(button_index)()
            return

        if event.key() == Qt.Key.Key_Minus or event.key() == Qt.Key.Key_Backspace:
            self.handle_data_character("-")()
            return

        if event.key() == Qt.Key.Key_Period:
            self.handle_data_character(".")()
            return

        if event.key() == Qt.Key.Key_M and mode is not None and self.data_input != "":
            self.button_mhz.pressed.emit()
            return True

        if event.key() == Qt.Key.Key_G and mode is not None and self.data_input != "":
            self.button_ghz.pressed.emit()
            return True
        
        if event.key() == Qt.Key.Key_K and mode is not None and self.data_input != "":
            self.button_khz.pressed.emit()
            return True
        
        if event.key() == Qt.Key.Key_H and mode is not None and self.data_input != "":
            self.button_hz.pressed.emit()
            return True

