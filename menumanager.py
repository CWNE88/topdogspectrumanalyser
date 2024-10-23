class MenuManager:
    def __init__(self, option_callback=None):
        self.menu_stack = []  # Stack to track the current menu path
        self.option_callback = option_callback
        
        # Define the menu structure
        self.menu_data = {
            "Frequency": {
                "options": ["Centre\nFrequency", "Start\nFrequency", "Stop\nFrequency"]
            },
            "Span": {
                "options": ["Full Span"]
            },
            "Amplitude": {
                "options": [
                    "Reference\nLevel",
                    "Attenuation\nAuto/Man",
                    "Log dB /\nDivision",
                    "Lin / Log",
                    "Units",  
                    "Range\nLevel",
                    "Ref Level\nOffset"
                ],
                "submenus": {
                    "Units": {
                        "options": ["dBm", "dBµV", "dBmV", "Volts", "Watts"]
                    }
                }
            },
            "Mode": {
                "options": []
            },
           "Input": {
                "options": ["RTL FFT", "HackRF FFT", "RTL Sweep", "HackRF Sweep", "Audio FFT"], 
                "submenus": {
                    "RTL FFT": {
                        "submenus": {
                            "Bias Tee": {
                                "options": ["On", "Off"]
                            },
                            "Gain": {
                                "options": ["AGC", "Medium", "High"]
                            }
                        }
                    },
                    "HackRF FFT": {
                        "options": []
                    },
                    "Audio FFT": {
                        "options": []
                    }
                }
            }

        }

    def set_callback(self, callback):
        """Set the callback function for menu options."""
        self.option_callback = callback

    def select_menu(self, menu_name):
        """Select a top-level menu."""
        if menu_name in self.menu_data:
            self.menu_stack = [menu_name]  # Reset the stack with the top-level menu
            print(f"Selected menu: {menu_name}")
            self.update_button_labels()
        else:
            print(f"Menu '{menu_name}' does not exist.")


    def select_submenu(self, submenu_name):
        if not self.menu_stack:
            print("No menu selected.")
            return

        current_menu = self.menu_stack[-1]
        parent_menu = self.menu_stack[-2] if len(self.menu_stack) > 1 else None

        if parent_menu and "submenus" in self.menu_data.get(parent_menu, {}):
            if submenu_name in self.menu_data[parent_menu]["submenus"]:
                self.menu_stack.append(submenu_name)  
                print(f"Selected submenu: {submenu_name}")
                self.update_button_labels()
            else:
                print(f"Submenu '{submenu_name}' does not exist in '{parent_menu}'.")
        else:
            print(f"No submenus available for the current menu: {current_menu}.")



    def get_button_labels(self):
        if not self.menu_stack:
            print("No menu selected.")
            return []

        current_menu = self.menu_stack[-1]
        parent_menu = self.menu_stack[-2] if len(self.menu_stack) > 1 else None

        print(f"Getting button labels for current menu: {current_menu} under parent menu: {parent_menu}")

        if parent_menu and "submenus" in self.menu_data.get(parent_menu, {}):
            if current_menu in self.menu_data[parent_menu]["submenus"]:
                return self.menu_data[parent_menu]["submenus"][current_menu]["options"]

        return self.menu_data.get(current_menu, {}).get("options", [])

    def update_button_labels(self):
        """Update the button labels based on the current selection."""
        button_labels = self.get_button_labels()
        print(f"Updated button labels: {button_labels}")

    def handle_button_press(self, button_index):
        options = self.get_button_labels()
        if options and 0 <= button_index < len(options):
            option = options[button_index]
            current_menu = self.menu_stack[-1]
            parent_menu = self.menu_stack[-2] if len(self.menu_stack) > 1 else None

            print(f"Button pressed: {option} at index {button_index} in {current_menu}")

            # Check if the selected option has submenus
            if parent_menu == "Input":
                if option in self.menu_data[parent_menu]["submenus"]:
                    self.select_submenu(option)  # Navigate into the submenu
                    return  # Exit after handling submenu

                # Handle the main options directly if there are no submenus
                if self.option_callback:
                    self.option_callback(parent_menu or current_menu, current_menu, option)
            else:
                if self.option_callback:
                    self.option_callback(parent_menu or current_menu, current_menu, option)

            print(f"Action triggered: {parent_menu or current_menu} - {current_menu} - Option {option} selected")
        else:
            print("Invalid option index.")


    def go_back(self):
        """Go back to the previous menu level."""
        if len(self.menu_stack) > 1:
            self.menu_stack.pop()  # Remove the current menu
            print(f"Returned to menu: {self.menu_stack[-1]}")
            self.update_button_labels()
        else:
            print("Already at the top-level menu.")

# Example callback function
def example_callback(menu, submenu, option):
    print(f"Callback executed: {menu} - {submenu} - {option}")

# Example usage
#menu_manager = MenuManager(option_callback=example_callback)
# Navigate to "Amplitude"
#menu_manager.select_menu("Amplitude")
# Triggering "Units" as if it were a normal option
#menu_manager.handle_button_press(4)  # This selects "Units"
# Now navigate to "Units" submenu
#menu_manager.select_submenu("Units")
#menu_manager.handle_button_press(2)  # This will trigger "dBmV"
