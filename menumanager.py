from PyQt6.QtWidgets import QPushButton
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

class MenuItem:
    def __init__(self, id: str, label: str, action=None, sub_menu: Optional[List["MenuItem"]] = None):
        self.id = id
        self.label = label
        self.action = action
        self.sub_menu = sub_menu or []

class MenuManager:
    def __init__(self, on_selection, parent):
        self.on_selection = on_selection
        self.parent = parent
        self.current_menu: List[MenuItem] = []
        self.menu_stack: List[List[MenuItem]] = []
        self.soft_buttons: List[QPushButton] = [
            getattr(parent, f"button_soft_{i}", None) for i in range(1, 9)
        ]
        self.menus: Dict[str, List[MenuItem]] = self._create_menus()

    def _create_menus(self) -> Dict[str, List[MenuItem]]:
        return {
            "Main": [
                MenuItem("btnFrequency", "Frequency", sub_menu=self._create_frequency_menu()),
                MenuItem("btnInput1", "Input 1", sub_menu=self._create_input_menu()),
                MenuItem("btnMarker", "Marker", sub_menu=self._create_marker_menu()),
                MenuItem("btnDisplay", "Display", sub_menu=self._create_display_menu()),
            ],
            "Frequency": self._create_frequency_menu(),
            "Input 1": self._create_input_menu(),
            "Marker": self._create_marker_menu(),
            "Display": self._create_display_menu(),
            "RTL\nSamples": self._create_rtl_samples_functions_menu(),
            "Microphone\nSamples": self._create_sample_functions_menu(),
            "HackRF\nSamples": self._create_sample_functions_menu(),
            "FFT": self._create_fft_menu(),
            "Window": self._create_window_menu(),
            "Sample Size": self._create_sample_size_menu(),
        }

    def _create_frequency_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnCentreFrequency", "Centre\nFrequency"),
            MenuItem("btnStartFrequency", "Start\nFrequency"),
            MenuItem("btnStopFrequency", "Stop\nFrequency"),            
        ]

    def _create_input_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnRtlSamples", "RTL\nSamples", sub_menu=self._create_rtl_samples_functions_menu()),
            MenuItem("btnRtlSweep", "RTL\nSweep"),
            MenuItem("btnHackrfSamples", "HackRF\nSamples", sub_menu=self._create_sample_functions_menu()),
            MenuItem("btnHackRFSweep", "HackRF\nSweep"),
            MenuItem("btnMicrophoneSamples", "Microphone\nSamples", sub_menu=self._create_sample_functions_menu()),
            
        ]

    def _create_marker_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnHold", "Hold"),
            MenuItem("btnPeakSearch", "Peak Search"),
            MenuItem("btnMaxPeakSearch", "Max Hold"),
        ]

    def _create_display_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btn2d", "2D"),
            MenuItem("btn3d", "3D"),
            MenuItem("btnWaterfall", "Waterfall"),
        ]

    def _create_rtl_samples_functions_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnFFT", "FFT", sub_menu=self._create_fft_menu()),
        ]

    def _create_sample_functions_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnFFT", "FFT", sub_menu=self._create_fft_menu()),
        ]

    def _create_fft_menu(self) -> List[MenuItem]:
        return [
            MenuItem("btnWindow", "Window", sub_menu=self._create_window_menu()),
            MenuItem("btnSampleSize", "Sample Size", sub_menu=self._create_sample_size_menu()),
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

    def select_menu(self, menu_name: str):
        self.menu_stack.append(self.current_menu)
        self.current_menu = self.menus.get(menu_name, [])
        if not self.current_menu:
            logging.warning(f"Menu {menu_name} is empty or not found")
        self._update_soft_buttons()
        logging.debug(f"Selected menu: {menu_name}")

    
    def handle_button_press(self, index: int):
        if index >= len(self.current_menu):
            logging.debug(f"Button press ignored: index {index} out of range")
            return
        menu_item = self.current_menu[index]
        logging.debug(f"Button press: index={index}, menu_item={menu_item.label}, menu_stack={[ [item.label for item in menu] for menu in self.menu_stack ]}")
        
        # Special case for FFT: Trigger the FFT action with the correct source_id
        if menu_item.id == "btnFFT":
            logging.debug("Special case: Triggering FFT action")
            source_id = None
            current_menu_name = self.current_menu[0].label if self.current_menu else ""
            if current_menu_name == "FFT":
                # Map menu names to source IDs
                menu_name_to_source = {
                    "RTL\nSamples": "btnRtlSamples",
                    "Microphone\nSamples": "btnMicrophoneSamples",
                    "HackRF\nSamples": "btnHackrfSamples"
                }
                # Find the parent menu name from the previous menu in menu_stack
                if self.menu_stack:
                    parent_menu = self.menu_stack[-1]
                    for item in parent_menu:
                        if item.label in menu_name_to_source and item.id == menu_item.id.replace("FFT", "HackrfSamples") or item.label == "HackRF\nSamples":
                            source_id = menu_name_to_source[item.label]
                            break
                    # Fallback: Check parent menu name directly
                    if not source_id and parent_menu and parent_menu[0].label in menu_name_to_source:
                        source_id = menu_name_to_source[parent_menu[0].label]
            logging.debug(f"Inferred source_id={source_id} for FFT")
            if source_id:
                self.parent.start_fft(source_id)
            else:
                logging.error("Could not infer source_id for FFT")
                self.parent.status_label.setText("Error: No valid source selected for FFT")
        
        if menu_item.sub_menu:
            self.select_menu(menu_item.label)
        self.on_selection(menu_item)  # Always call on_selection to update current_source_id
        
    def _update_soft_buttons(self):
        for i, button in enumerate(self.soft_buttons):
            if button and i < len(self.current_menu):
                button.setText(self.current_menu[i].label)
                button.setEnabled(True)
                logging.debug(f"Soft button {i+1} set to: {self.current_menu[i].label}")
            elif button:
                button.setText("")
                button.setEnabled(False)
                logging.debug(f"Soft button {i+1} disabled")

    def go_back(self):
        if self.menu_stack:
            self.current_menu = self.menu_stack.pop()
            self._update_soft_buttons()
            logging.debug("Navigated back to previous menu")
