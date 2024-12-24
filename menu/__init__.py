from typing import Callable
from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QWidget, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QKeySequence

class MenuItem:
    id: str = ""
    """
    Internal ID of the menu item
    """
    
    name: str = ""
    """
    Label of the menu item
    """

    elementId: str = ""
    """
    Refers to the element in the UI that binds to this MenuItem.
    """

    children: list["MenuItem"] = []

    manager: "MenuManager" = None
    
    action: callable = None

    key: QKeySequence = None

    def __init__(self, id: str, manager: "MenuManager", elementId: str, key: str, name: str = "", children: list["MenuItem"] = []):
        self.id = id
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

        self.menu = MenuItem("root", self, None, "root", None, [
            MenuItem("btnFrequency", self, "button_frequency", "f", "Frequency", [
                MenuItem("btnCentreFrequency", self, None, None, "Centre\nFrequency"),
                MenuItem("btnStartFrequency", self, None, None, "Start\nFrequency"),
                MenuItem("btnStopFrequency", self, None, None, "Stop\nFrequency")
            ]),
            MenuItem("btnSpanRoot", self, "button_span", "s", "Span", [
                MenuItem("btnSpan", self, None, None, "Span"),
                MenuItem("btnFullSpan", self, None, None, "Full Span"),
                MenuItem("btnZeroSpan", self, None, None, "Zero Span")
            ]),
            MenuItem("btnAmplitude", self, "button_amplitude", "a", "Amplitude", [
                MenuItem("btnReferenceLevel", self, None, None, "Reference\nLevel"),
                MenuItem("btnAutoAttenuation", self, None, None, "Attenuation\nAuto"),
                MenuItem("btnLogDbPerDivision", self, None, None, "Log dB /\nDivision"),
                MenuItem("btnLinLog", self, None, None, "Lin / Log"),
                MenuItem("btnUnits", self, None, None, "Units", [
                    MenuItem("btnUnitDbm", self, None, None, "dBm"),
                    MenuItem("btnUnitMicroVolt", self, None, None, "dBµV"),
                    MenuItem("btnUnitDbmv", self, None, None, "dBmV"),
                    MenuItem("btnUnitVolts", self, None, None, "Volts"),
                    MenuItem("btnUnitWatts", self, None, None, "Watts")
                ]),
                MenuItem("btnRangeLevel", self, None, None, "Range\nLevel"),
                MenuItem("btnRefLevel", self, None, None, "Ref Level\nOffset")
                ]),

            MenuItem("btnHold", self, "button_hold", "space", "Hold"),


            MenuItem("btnMode", self, "button_mode", "ctrl+m", "Mode", [
                MenuItem("btnWifi", self, None, None, "Wi-Fi", [
                    MenuItem("btnISM24", self, None, None, "ISM\n2.4 GHz"),
                    MenuItem("btnUNII1", self, None, None, "UNII-1\n5 GHz"),
                    MenuItem("btnUNII2A", self, None, None, "UNII-2A\n5 GHz"),
                    MenuItem("btnUNII3", self, None, None, "UNII-3\n5 GHz"),
                    MenuItem("btnUNII5", self, None, None, "UNII-5\n6 GHz"),
                    MenuItem("btnUNII6", self, None, None, "UNII-6\n6 GHz"),
                    MenuItem("btnUNII7", self, None, None, "UNII-7\n6 GHz"),
                    MenuItem("btnUNII8", self, None, None, "UNII-8\n6 GHz")
                ]),
                MenuItem("btnModeAviation", self, None, None, "Aviation"),
                MenuItem("btnModeDigital", self, None, None, "Digital"),
            ]),
            MenuItem("btnPreset", self, "button_preset", "r", "Preset"),
            MenuItem("btnMaxHold", self, "button_max_hold", "x", "Max Hold"),
            MenuItem("btnPeakSearch", self, "button_peak_search", "p", "Peak Search"),
            
            
            MenuItem("btnInput1", self, "button_input_1", "i", "Input", [
                MenuItem("btnRtlSamples", self, None, None, "RTL\nSamples", [
                    MenuItem("btnBiasTee", self, None, None, "Bias Tee", [
                        MenuItem("btnBiasTeeOn", self, None, None, "On"),
                        MenuItem("btnBiasTeeOff", self, None, None, "Off")
                    ]),
                    MenuItem("btnRtlSamplesGain", self, None, None, "Gain", [
                        MenuItem("btnRtlSamplesAgc", self, None, None, "AGC"),
                        MenuItem("btnRtlSamplesAgcMedium", self, None, None, "Medium"),
                        MenuItem("btnRtlSamplesAgcHigh", self, None, None, "High")
                    ])
                ]),
                MenuItem("btnHackRfSamples", self, None, None, "HackRF\nSamples"),
                MenuItem("btnRtlSweep", self, None, None, "RTL\nSweep"),
                MenuItem("btnHackRfSweep", self, None, None, "HackRF\nSweep"),
                MenuItem("btnAudioSamples", self, None, None, "Audio\nSamples"),
            ]),
            #########

            ### Curser UP/DOWN buttons to be mapped too
            
            ##########

            MenuItem("btn2d", self, "button_2d", "ctrl+2", "2D"),
            MenuItem("btn3d", self, "button_3d", "ctrl+3", "3D"),

            # https://matplotlib.org/stable/users/explain/colors/colormaps.html

            MenuItem("btnWaterfall", self, "button_waterfall", "ctrl+4", "Waterfall", [
                MenuItem("btnWaterfallColour", self, None, None, "Colour", [
                    MenuItem("btnWaterfallColourMagma", self, None, None, "Magma"),
                    MenuItem("btnWaterfallColourHot", self, None, None, "Hot"),
                    MenuItem("btnWaterfallColourViridis", self, None, None, "Viridis")
                ])
            ]),
            MenuItem("btnBoxes", self, "button_boxes", "ctrl+5", "Boxes")
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
            try:
                element.pressed.disconnect()
            except:
                pass
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
            #print(f"Menu item {item.name} pressed")
            if item.children and len(item.children) > 0:
                self._bind_soft_buttons(item)
                self._bind_ui(item, self.ui)

            if callable(self.on_selection):
                self.on_selection(item)
        
        return on_action_inner