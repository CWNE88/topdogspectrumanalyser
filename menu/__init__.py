from typing import Callable
from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QWidget, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QKeySequence

class MenuItem:
    """
    Label of the menu item
    """
    name: str = ""

    """
    Refers to the element in the UI that binds to this MenuItem.
    """
    elementId: str = ""

    children: list["MenuItem"] = []

    manager: "MenuManager" = None
    
    action: callable = None

    key: QKeySequence = None

    def __init__(self, manager: "MenuManager", elementId: str, key: str, name: str = "", children: list["MenuItem"] = []):
        self.manager = manager
        self.elementId = elementId
        self.name = name
        self.children = children
        self.key = QKeySequence.fromString(key) if key else None

class MenuManager:
    menu: MenuItem = None
    ui: QObject = None
    
    on_selection: Callable[[MenuItem], None] = None

    def __init__(self, ui: QObject, on_selection: Callable[[MenuItem], None]):
        self.ui = ui
        self.on_selection = on_selection

        self.menu = MenuItem(self, None, "root", None, [

            MenuItem(self, "button_frequency", "f", "Frequency", [
                MenuItem(self, None, None, "Centre\nFrequency"),
                MenuItem(self, None, None, "Start\nFrequency"),
                MenuItem(self, None, None, "Stop\nFrequency")
            ]),
            MenuItem(self, "button_span", "s", "Span", [
                MenuItem(self, None, None, "Full Span"),
                MenuItem(self, None, None, "Zero Span")
            ]),
            MenuItem(self, "button_amplitude", "a", "Amplitude", [
                MenuItem(self, None, None, "Reference\nLevel"),
                MenuItem(self, None, None, "Attenuation\nAuto"),
                MenuItem(self, None, None, "Log dB /\nDivision"),
                MenuItem(self, None, None, "Lin / Log"),
                MenuItem(self, None, None, "Units", [
                    MenuItem(self, None, None, "dBm"),
                    MenuItem(self, None, None, "dBµV"),
                    MenuItem(self, None, None, "dBmV"),
                    MenuItem(self, None, None, "Volts"),
                    MenuItem(self, None, None, "Watts")
                ]),
                MenuItem(self, None, None, "Range\nLevel"),
                MenuItem(self, None, None, "Ref Level\nOffset")
                ]),

            MenuItem(self, "button_hold", "space", "Hold"),


            MenuItem(self, "button_mode", "ctrl+m", "Mode", [
                MenuItem(self, None, None, "Wi-Fi"),
                MenuItem(self, None, None, "Aviation"),
                MenuItem(self, None, None, "Digital"),
            ]),
            MenuItem(self, "button_preset", "r", "Preset"),
            MenuItem(self, "button_max_hold", "x", "Max Hold"),
            MenuItem(self, "button_peak_search", "p", "Peak Search"),
            
            
            MenuItem(self, "button_input_1", "i", "Input", [
                MenuItem(self, None, None, "RTL\nSamples", [
                    MenuItem(self, None, None, "Bias Tee", [
                        MenuItem(self, None, None, "On"),
                        MenuItem(self, None, None, "Off")
                    ]),
                    MenuItem(self, None, None, "Gain", [
                        MenuItem(self, None, None, "AGC"),
                        MenuItem(self, None, None, "Medium"),
                        MenuItem(self, None, None, "High")
                    ])
                ]),
                MenuItem(self, None, None, "HackRF\nSamples"),
                MenuItem(self, None, None, "RTL\nSweep"),
                MenuItem(self, None, None, "HackRF\nSweep"),
                MenuItem(self, None, None, "Audio\nSamples"),
            ]),
            #########

            ### Curser UP/DOWN buttons to be mapped too
            
            ##########

            MenuItem(self, "button_2d", "2", "2D"),
            MenuItem(self, "button_3d", "3", "3D"),

            # https://matplotlib.org/stable/users/explain/colors/colormaps.html

            MenuItem(self, "button_waterfall", "4", "Waterfall", [
                MenuItem(self, None, None, "Colour", [
                    MenuItem(self, None, None, "Magma"),
                    MenuItem(self, None, None, "Hot"),
                    MenuItem(self, None, None, "Viridis")
                ])
            ]),
                        
                        
            MenuItem(self, "button_boxes", "5", "Boxes"),

        ])


        self._bind_ui(self.menu, ui)

    def keyPressEvent(self, event: QKeyEvent):
        # find menu item that corresponds to the key
        # that was pressed

        soft_button_index = event.key() - Qt.Key.Key_F1
        if soft_button_index >= 0 and soft_button_index < 8:
            self.on_action(self.current_menu.children[soft_button_index])()
            return


        for item in self.walk_menu(self.menu):
            if not item.key:
                continue

            match = item.key.matches(event.key() | event.modifiers().value)

            if match == QKeySequence.SequenceMatch.ExactMatch:
                self.on_action(item)()
                return


    def walk_menu(self, item: MenuItem):
        """
        Walks the menu tree and prints the menu items
        """
        yield item

        if item.children:
            for child in item.children:
                yield from self.walk_menu(child)
                
        
        
    def _bind_ui(self, item: "MenuItem", ui: QObject):
        element: QWidget = None

        if item.elementId:
            element = ui.findChild(QWidget, item.elementId)

        if isinstance(element, QPushButton):
            element.pressed.connect(self.on_action(item))

        if item.children:
            for i, child in enumerate(item.children):
                self._bind_ui(child, ui)

    def _bind_soft_buttons(self, item: MenuItem):
        """
        Renders the current menu children into the soft buttons
        """
        if item is None:
            return

        self.current_menu = item

        children = item.children if item.children else []

        for i in range(1,9):
            item = children[i-1] if i-1 < len(children) else None
            name = item.name if item else ""
            element = self.ui.findChild(QWidget, f"button_soft_{i}")

            if isinstance(element, QPushButton):
                element.setText(name)

                try:
                    element.pressed.disconnect()
                except:
                    pass

                if item is not None: # and item.children is not None and len(item.children) > 0:
                    element.pressed.connect(self.on_action(item))
                    
    def on_action(self, item: MenuItem):
        def on_action_inner():
            print(f"Menu item {item.name} pressed")
            if item.children and len(item.children) > 0:
                self._bind_soft_buttons(item)
                self._bind_ui(item, self.ui)

            if callable(self.on_selection):
                self.on_selection(item)
        
        return on_action_inner